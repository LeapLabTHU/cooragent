from dotenv import load_dotenv
import json
load_dotenv()
import os
import logging
from src.utils import get_project_root

logger = logging.getLogger(__name__)
CONFIG_FILE_PATH = str(get_project_root()) + "/config/mcp.json"

def mcp_client_config():
    _mcp_client_config = {}
    mcp_servers_from_json = None # Initialize to None

    try:
        with open(CONFIG_FILE_PATH, 'r') as f:
            loaded_json_data = json.load(f)
        
        # Check if "mcpServers" key exists and is a dictionary
        if isinstance(loaded_json_data.get("mcpServers"), dict):
            mcp_servers_from_json = loaded_json_data["mcpServers"]
        else:
            logger.error(f"MCP configuration file {CONFIG_FILE_PATH} is missing 'mcpServers' key or it's not a dictionary.")
            return _mcp_client_config # Return empty dict if structure is not as expected

    except FileNotFoundError:
        logger.error(f"MCP configuration file not found: {CONFIG_FILE_PATH}")
        return _mcp_client_config
    except json.JSONDecodeError:
        logger.error(f"Error decoding MCP JSON configuration from {CONFIG_FILE_PATH}")
        return _mcp_client_config

    if not mcp_servers_from_json: # Should not happen if logic above is correct, but as a safeguard
        logger.info(f"No MCP server configurations found under 'mcpServers' in {CONFIG_FILE_PATH}.")
        return _mcp_client_config

    for key, value in mcp_servers_from_json.items():
        if not isinstance(value, dict):
            logger.error(f"Invalid configuration for MCP server {key}: value is not a dictionary. Skipping.")
            continue

        transport_type = None
        if "url" in value:
            transport_type = "sse"
        elif "command" in value:
            transport_type = "stdio"
        else:
            logger.error(f"Cannot determine transport type for MCP server {key}. Missing 'url' (for SSE) or 'command' (for stdio). Skipping.")
            continue
        
        env_config = value.get("env")
        if isinstance(env_config, dict):
            for env_key, env_value in env_config.items():
                    os.environ[env_key] = env_value
                    
        if transport_type == "sse":
            if not env_value:
                logger.warning(f"Environment variable {key} (or specific var from 'env' block if applicable) not set for MCP server {key}. Skipping SSE configuration.")
                continue
            
            sse_config = value.copy()
            sse_config["url"] = sse_config["url"] + '?key=' + env_value
            sse_config["transport"] = "sse"
            _mcp_client_config[key] = sse_config
            
        elif transport_type == "stdio":
            if "args" not in value: 
                logger.error(f"Invalid configuration for MCP server {key} (transport stdio): 'args' key is missing. Skipping.")
                continue
            _mcp_client_config[key] = value.copy()
            _mcp_client_config[key]["transport"] = "stdio"

            
    return _mcp_client_config