"""Load MCP connections for the pinned langchain-mcp-adapters client.

This loader never appends credentials to remote URLs. Configure them in headers.
``env`` remains a child-process setting for stdio servers only.
"""

import json
import logging
import math
import os
import re
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv

from src.utils import get_project_root

load_dotenv()
logger = logging.getLogger(__name__)
CONFIG_FILE_PATH = str(get_project_root() / "config" / "mcp.json")

_ENV_REFERENCE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
_ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_HEADER_NAME = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+\Z")
_INVALID_HEADER_VALUE = re.compile(r"[\x00-\x1f\x7f]")


def _remote_url_is_safe(url: object) -> bool:
    if not isinstance(url, str):
        return False
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return False
        if (
            parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or "${" in url
        ):
            return False
        return True
    except ValueError:
        return False


def _header_value(template: object) -> str:
    if not isinstance(template, str) or _INVALID_HEADER_VALUE.search(template):
        raise ValueError("invalid header value")

    def replace(match: re.Match) -> str:
        value = os.environ.get(match.group(1))
        if not value:
            raise ValueError("missing header environment variable")
        return value

    value = _ENV_REFERENCE.sub(replace, template)
    if "${" in value or not value or _INVALID_HEADER_VALUE.search(value):
        raise ValueError("invalid or unresolved header value")
    return value


def _remote_headers(config: dict) -> dict[str, str]:
    raw_headers = config.get("headers", {})
    if not isinstance(raw_headers, dict):
        raise ValueError("headers must be an object")

    headers = {}
    seen_names = set()
    for name, template in raw_headers.items():
        if not isinstance(name, str) or not _HEADER_NAME.fullmatch(name):
            raise ValueError("invalid header name")
        normalized_name = name.lower()
        if normalized_name in seen_names:
            raise ValueError("duplicate header name")
        seen_names.add(normalized_name)
        headers[name] = _header_value(template)

    token_env = config.get("bearerTokenEnv")
    if token_env is not None:
        if not isinstance(token_env, str) or not _ENV_NAME.fullmatch(token_env):
            raise ValueError("invalid bearerTokenEnv")
        if "authorization" in seen_names:
            raise ValueError("Authorization and bearerTokenEnv conflict")
        token = os.environ.get(token_env)
        if not token or _INVALID_HEADER_VALUE.search(token):
            raise ValueError("missing or invalid bearer token")
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _positive_seconds(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("timeout must be numeric seconds")
    # Check before float() so arbitrarily large JSON integers cannot overflow.
    if value <= 0 or value >= 86400:
        raise ValueError("timeout must be below one day")
    seconds = float(value)
    if not math.isfinite(seconds):
        raise ValueError("timeout must be positive and finite")
    return seconds


def mcp_client_config() -> dict[str, dict]:
    """Return only valid MCP server connections, without logging credentials."""
    path = Path(CONFIG_FILE_PATH)
    try:
        with path.open(encoding="utf-8") as config_file:
            document = json.load(config_file)
    except (FileNotFoundError, json.JSONDecodeError) as error:
        logger.error("Cannot read MCP configuration %s: %s", path, type(error).__name__)
        return {}

    servers = document.get("mcpServers") if isinstance(document, dict) else None
    if not isinstance(servers, dict):
        logger.error("MCP configuration needs an mcpServers object")
        return {}

    connections = {}
    for name, config in servers.items():
        if not isinstance(config, dict):
            logger.error("Invalid MCP server configuration for %s", name)
            continue

        transport = config.get("transport")
        if transport is None:
            if "command" in config and "url" in config:
                logger.error("Ambiguous MCP transport for server %s", name)
                continue
            transport = (
                "stdio" if "command" in config else "sse" if "url" in config else None
            )
        if transport == "stdio":
            if (
                not isinstance(config.get("command"), str)
                or not config["command"]
                or not isinstance(config.get("args"), list)
                or not all(isinstance(arg, str) for arg in config["args"])
            ):
                logger.error("Invalid stdio MCP server %s", name)
                continue
            env = config.get("env")
            if env is not None and (
                not isinstance(env, dict)
                or not all(
                    isinstance(k, str) and isinstance(v, str) for k, v in env.items()
                )
            ):
                logger.error("Invalid stdio environment for MCP server %s", name)
                continue
            if (
                "session_kwargs" in config
                and config["session_kwargs"] is not None
                and not isinstance(config["session_kwargs"], dict)
            ):
                logger.error("Invalid MCP session options for server %s", name)
                continue
            connection = {
                key: config[key]
                for key in (
                    "command",
                    "args",
                    "env",
                    "cwd",
                    "encoding",
                    "encoding_error_handler",
                    "session_kwargs",
                )
                if key in config
            }
            connection["transport"] = "stdio"
        elif transport in {"sse", "streamable_http"}:
            if "env" in config:
                logger.error("Remote MCP server %s must use headers, not env", name)
                continue
            if (
                "session_kwargs" in config
                and config["session_kwargs"] is not None
                and not isinstance(config["session_kwargs"], dict)
            ):
                logger.error("Invalid MCP session options for server %s", name)
                continue
            if not _remote_url_is_safe(config.get("url")):
                logger.error(
                    "Invalid or credential-bearing URL for MCP server %s", name
                )
                continue
            try:
                headers = _remote_headers(config)
            except ValueError:
                logger.error(
                    "Invalid or missing header configuration for MCP server %s", name
                )
                continue
            parsed = urlsplit(config["url"])
            if (
                headers
                and parsed.scheme != "https"
                and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
            ):
                logger.error("Credential headers require HTTPS for MCP server %s", name)
                continue
            connection = {"transport": transport, "url": config["url"]}
            if headers:
                connection["headers"] = headers
            try:
                for key in ("timeout", "sse_read_timeout"):
                    if key in config:
                        seconds = _positive_seconds(config[key])
                        if transport == "streamable_http" and (
                            not seconds.is_integer() or seconds >= 86400
                        ):
                            raise ValueError(
                                "Streamable HTTP timeout must be whole seconds below one day"
                            )
                        connection[key] = (
                            timedelta(seconds=seconds)
                            if transport == "streamable_http"
                            else seconds
                        )
            except ValueError:
                logger.error("Invalid MCP timeout for server %s", name)
                continue
            if "session_kwargs" in config:
                connection["session_kwargs"] = config["session_kwargs"]
            if "terminate_on_close" in config:
                logger.warning(
                    "terminate_on_close is unsupported for MCP server %s", name
                )
        else:
            logger.error("Unsupported MCP transport for server %s", name)
            continue
        connections[name] = connection
    return connections
