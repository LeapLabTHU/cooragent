from langgraph.prebuilt import create_react_agent
from src.interface.mcp_types import Tool
from src.prompts import apply_prompt_template, get_prompt_template

from src.tools import (
    bash_tool,
    browser_tool,
    crawl_tool,
    python_repl_tool,
    tavily_tool,
)

from src.llm import get_llm_by_type
from src.config.agents import AGENT_LLM_MAP
from langchain_core.tools import tool
from pathlib import Path
from src.interface.agent_types import Agent
import logging
import re

logger = logging.getLogger(__name__)


class AgentManager:
    def __init__(self, tools_dir, agents_dir, prompt_dir):
        for path in [tools_dir, agents_dir, prompt_dir]:
            if not path.exists():
                logger.info(f"path {path} does not exist when agent manager initializing, gona to create...")
                path.mkdir(parents=True, exist_ok=True)
                
        self.tools_dir = Path(tools_dir)
        self.agents_dir = Path(agents_dir)
        self.prompt_dir = Path(prompt_dir)

        if not self.tools_dir.exists() or not self.agents_dir.exists() or not self.prompt_dir.exists():
            raise FileNotFoundError("One or more provided directories do not exist.")

        self.available_agents = [{
        
            "runtime": create_react_agent(
                            get_llm_by_type(AGENT_LLM_MAP["researcher"]),
                            tools=[tavily_tool, crawl_tool],
                            prompt=lambda state: apply_prompt_template("researcher", state),
                        ),
            "mcp_obj": self._create_mcp_agent("share", "researcher", AGENT_LLM_MAP["researcher"], [tavily_tool, crawl_tool], 
                                                 get_prompt_template("researcher"))
            },           
            {
            "runtime": create_react_agent(
                            get_llm_by_type(AGENT_LLM_MAP["coder"]),
                            tools=[python_repl_tool, bash_tool],
                            prompt=lambda state: apply_prompt_template("coder", state),
                        ),
            "mcp_obj": self._create_mcp_agent("share", "coder", AGENT_LLM_MAP["coder"], [python_repl_tool, bash_tool], 
                                                 get_prompt_template("coder"))
            },
            {
            "runtime": create_react_agent(
                            get_llm_by_type(AGENT_LLM_MAP["browser"]),
                            tools=[browser_tool],
                            prompt=lambda state: apply_prompt_template("browser", state),
                        ),
            "mcp_obj": self._create_mcp_agent("share", "browser", AGENT_LLM_MAP["browser"], [browser_tool], 
                                                 get_prompt_template("browser"))
            },
            {
            "runtime": create_react_agent(
                            get_llm_by_type(AGENT_LLM_MAP["reporter"]),
                            tools=[],
                            prompt=lambda state: apply_prompt_template("reporter", state),
                        ),
            "mcp_obj": self._create_mcp_agent("share", "reporter", AGENT_LLM_MAP["reporter"], [], 
                                                 get_prompt_template("reporter"))
            }
        ]
        
        self.available_tools = {
            "bash_tool": bash_tool,
            "browser_tool": browser_tool,
            "crawl_tool": crawl_tool,
            "python_repl_tool": python_repl_tool,
            "tavily_tool": tavily_tool,
        }
        
        
    def _create_mcp_agent(self, user_id: str, name: str, llm_type: str, tools: list[tool], prompt: str):
        mcp_tools = []
        for tool in tools:
            mcp_tools.append(Tool(
                name=tool.name,
                description=tool.description,
                inputSchema=eval(tool.args_schema.schema_json()),
            ))
        
        mcp_agent = Agent(
            agent_name=name,
            nick_name=name,
            user_id=user_id,
            llm_type=llm_type,
            selected_tools=mcp_tools,
            prompt=str(prompt),
        )
        
        self._save_agent(mcp_agent)
        return mcp_agent
        
        
    def _convert_mcp_agent_to_langchain_agent(self, mcp_agent: Agent):
        _tools = []
        try:
            for tool in mcp_agent.selected_tools:
                _tools.append(self.available_tools[tool.name])
        except Exception as e:
            logger.error(f"Tool {tool.name} not found in available tools.")
        
        try:
            _prompt = lambda state: apply_prompt_template(mcp_agent.name, state)
        except Exception as e:
            logger.info(f"Prompt {mcp_agent.name} not found in available prompts.")
            _prompt = get_prompt_template(mcp_agent.prompt)
            
        langchain_agent = create_react_agent(
            llm_type=mcp_agent.llm_type,
            tools=_tools,
            prompt=_prompt,
        )
        return langchain_agent
        

    def _create_agent_by_prebuilt(self, user_id: str, name: str, llm_type: str, tools: list[tool], prompt: str):
        langchain_agent = create_react_agent(
            get_llm_by_type(llm_type),
            tools=tools,
            prompt=prompt,
        )
        _agent = {
            "runtime": langchain_agent,
            "mcp_obj": self._create_mcp_agent(user_id, name, llm_type, tools, prompt)
        }
        self.available_agents.append(_agent)
        return langchain_agent
    

    def _save_agent(self, agent: Agent, flush=False):
        agent_path = self.agents_dir / f"{agent.agent_name}.json"
        if not flush and agent_path.exists():
            print(f"agent {agent.agent_name} already exists, skipping save.")
            return
        with open(agent_path, "w") as f:
            f.write(agent.model_dump_json())
        print(f"agent {agent.agent_name} saved.")
    
    def _load_agent(self, agent_name: str):
        agent_path = self.agents_dir / f"{agent_name}.json"
        if not agent_path.exists():
            raise FileNotFoundError(f"agent {agent_name} not found.")
        with open(agent_path, "r") as f:
            json_str = f.read()
            mcp_obj = Agent.model_validate_json(json_str)
            _agent  = {
                "runtime": self._convert_mcp_agent_to_langchain_agent(mcp_obj),
                "mcp_obj": mcp_obj
            }
            self.available_agents.append(_agent)
            return
        
    def _list_agents(self, user_id: str, match: str):
        agents = [agent["mcp_obj"] for agent in self.available_agents]
        if user_id:
            agents = [agent for agent in agents if agent.user_id == user_id]
        if match:
            agents = [agent for agent in agents if re.match(match, agent.agent_name)]
        return agents

    def _edit_agent(self, agent: Agent):
        for _agent in self.available_agents:
            if _agent["mcp_obj"].agent_name == agent.agent_name:
                _agent["mcp_obj"] = agent
                del _agent["runtime"]
                _agent["runtime"] = self._convert_mcp_agent_to_langchain_agent(agent)
                self._save_agent(_agent)
                return "agent updated successfully"
        raise ValueError(f"agent {agent.agent_name} not found.")
    
    def _save_agents(self, agents: list[Agent], flush=False):
        for agent in agents:
            self._save_agent(agent, flush)  
        return
        
    def _load_agents(self):
        for agent_path in self.agents_dir.glob("*.json"):
            self._load_agent(agent_path.stem)
        return    
    
    def _list_default_tools(self):
        return list(self.available_tools.values())
    
    def _list_default_agents(self):
        agents = [agent["mcp_obj"] for agent in self.available_agents if agent["mcp_obj"].user_id == "share"]
        return agents
    
from src.utils.path_utils import get_project_root

tools_dir = get_project_root() / "store" / "tools"
agents_dir = get_project_root() / "store" / "agents"
prompts_dir = get_project_root() / "store" / "prompts"

agent_manager = AgentManager(tools_dir, agents_dir, prompts_dir)
