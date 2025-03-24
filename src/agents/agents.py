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

# Create agents using configured LLM types
from langchain_core.tools import tool
from pathlib import Path
from src.interface.agent_types import Agent
import uuid
import logging

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

        self.available_agents = {
            "researcher":  create_react_agent(
                            get_llm_by_type(AGENT_LLM_MAP["researcher"]),
                            tools=[tavily_tool, crawl_tool],
                            prompt=lambda state: apply_prompt_template("researcher", state),
                        ),
            "coder": create_react_agent(
                            get_llm_by_type(AGENT_LLM_MAP["coder"]),
                            tools=[python_repl_tool, bash_tool],
                            prompt=lambda state: apply_prompt_template("coder", state),
                        ),
            "browser": create_react_agent(
                            get_llm_by_type(AGENT_LLM_MAP["browser"]),
                            tools=[browser_tool],
                            prompt=lambda state: apply_prompt_template("browser", state),
                        ),
            "reporter": create_react_agent(
                            get_llm_by_type(AGENT_LLM_MAP["reporter"]),
                            tools=[],
                            prompt=lambda state: apply_prompt_template("reporter", state),
                        ),
        }
        self.available_mcp_agents = {}
        self.available_mcp_agents["researcher"] = self._create_mcp_agent("researcher", AGENT_LLM_MAP["researcher"], [tavily_tool, crawl_tool], 
                                                 get_prompt_template("researcher"))
        self.available_mcp_agents["coder"] =  self._create_mcp_agent("coder", AGENT_LLM_MAP["coder"], [python_repl_tool, bash_tool], 
                                            get_prompt_template("coder"))
        self.available_mcp_agents["browser"] = self._create_mcp_agent("browser", AGENT_LLM_MAP["browser"], [browser_tool], 
                                              get_prompt_template("browser"))
        self.available_mcp_agents["reporter"] = self._create_mcp_agent("reporter", AGENT_LLM_MAP["reporter"], [], 
                                            get_prompt_template("reporter"))
        self.available_tools = {
            "bash_tool": bash_tool,
            "browser_tool": browser_tool,
            "crawl_tool": crawl_tool,
            "python_repl_tool": python_repl_tool,
            "tavily_tool": tavily_tool,
        }
        
        
    def _create_mcp_agent(self, name: str, llm_type: str, tools: list[tool], prompt: str):
        mcp_tools = []
        for tool in tools:
            mcp_tools.append(Tool(
                name=tool.name,
                description=tool.description,
                inputSchema=eval(tool.args_schema.schema_json()),
            ))
        
        mcp_agent = Agent(
            agent_name=name,
            agent_id=str(uuid.uuid4()),
            llm_type=llm_type,
            selected_tools=mcp_tools,
            prompt=str(prompt),
        )
        
        self.available_mcp_agents[name] = mcp_agent
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
        

    def _create_agent_by_prebuilt(self, name: str, llm_type: str, tools: list[tool], prompt: str):
        langchain_agent = create_react_agent(
            llm_type=llm_type,
            tools=tools,
            prompt=lambda state: apply_prompt_template(name, state),
        )
        self.available_agents[name] = langchain_agent
        self._create_mcp_agent(name, llm_type, tools, prompt)                
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
            self.available_mcp_agents[agent_name] = Agent.model_validate_json(json_str)
            self.available_agents[agent_name] = self._convert_mcp_agent_to_langchain_agent(self.available_mcp_agents[agent_name])
            return
        
    def _list_agents(self, user_id: str, match: str):
        agents = self.agents
        if user_id:
            agents = [agent for agent in agents if agent.user_id == user_id]
        if match:
            agents = [agent for agent in agents if match in agent.agent_name]
        return agents

    
    def _save_agents(self, agents: list[Agent], flush=False):
        for agent in agents:
            self._save_agent(agent, flush)  
        return
        
    def _load_agents(self):
        for agent_path in self.agents_dir.glob("*.json"):
            self._load_agent(agent_path.stem)
        return    
    

from src.utils.path_utils import get_project_root

tools_dir = get_project_root() / "store" / "tools"
agents_dir = get_project_root() / "store" / "agents"
prompts_dir = get_project_root() / "store" / "prompts"

agent_manager = AgentManager(tools_dir, agents_dir, prompts_dir)

    
if __name__ == "__main__":

    _tavily_tool = Tool(
        name=tavily_tool.name,
        description=tavily_tool.description,
        inputSchema=eval(tavily_tool.args_schema.schema_json()),
    )
    
    _crawl_tool = Tool(
        name=crawl_tool.name,
        description=crawl_tool.description,
        inputSchema=eval(crawl_tool.args_schema.schema_json()),
    )
    
    _research_agent = Agent(
        agent_name="researcher",
        agent_id="researcher",
        llm_type=AGENT_LLM_MAP["researcher"],
        selected_tools=[_tavily_tool, _crawl_tool],
        prompt=get_structured_prompt("researcher") ,
    )
    agent_manager._save_agent(_research_agent, flush=True)
    agent = agent_manager._load_agent("researcher")
    
