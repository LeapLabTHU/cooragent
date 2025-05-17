import asyncio
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

from src.llm.llm import get_llm_by_type
from src.llm.agents import AGENT_LLM_MAP
from langchain_core.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from pathlib import Path
from src.interface.agent_types import Agent
from src.service.env import USR_AGENT, USE_BROWSER,USE_MCP_TOOLS
from src.manager.mcp import mcp_client_config
import logging
import re

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class NotFoundAgentError(Exception):
    """when agent not found"""
    pass

class NotFoundToolError(Exception):
    """when tool not found"""
    pass

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
        self.available_agents = {}
        self.available_tools = {}

    async def initialize(self, user_agent_flag=USR_AGENT):
        """Asynchronously initializes the AgentManager by loading agents and tools."""
        await self._load_agents(user_agent_flag)
        await self.load_tools()
        logger.info(f"AgentManager initialized. {len(self.available_agents)} agents and {len(self.available_tools)} tools available.")

    def _create_agent_by_prebuilt(self, user_id: str, name: str, nick_name: str, llm_type: str, tools: list[tool], prompt: str, description: str):
        def _create(user_id: str, name: str, nick_name: str, llm_type: str, tools: list[tool], prompt: str, description: str):
            _tools = []
            for tool in tools:
                _tools.append(Tool(
                    name=tool.name,
                    description=tool.description,
                ))
            
            _agent = Agent(
                agent_name=name,
                nick_name=nick_name,
                description=description,
                user_id=user_id,
                llm_type=llm_type,
                selected_tools=_tools,
                prompt=str(prompt)
            )
        
            self._save_agent(_agent)
            return _agent
        
        _agent = _create(user_id, name, nick_name, llm_type, tools, prompt, description)
        self.available_agents[name] = _agent
        return


    async def load_mcp_tools(self):
        async with MultiServerMCPClient(mcp_client_config()) as client:
            mcp_tools = client.get_tools()
            for _tool in mcp_tools:
                self.available_tools[_tool.name] = _tool
                    
    async def load_tools(self):        
        self.available_tools.update({
            bash_tool.name: bash_tool,
            browser_tool.name: browser_tool,
            crawl_tool.name: crawl_tool,
            python_repl_tool.name: python_repl_tool,
            tavily_tool.name: tavily_tool,
        })
        if not USE_BROWSER:
            del self.available_tools[browser_tool.name]    
        if USE_MCP_TOOLS:
            await self.load_mcp_tools()

    def _save_agent(self, agent: Agent, flush=False):
        agent_path = self.agents_dir / f"{agent.agent_name}.json"
        agent_prompt_path = self.prompt_dir / f"{agent.agent_name}.md"
        if not flush and agent_path.exists():
            return
        with open(agent_path, "w") as f:
            f.write(agent.model_dump_json())
        with open(agent_prompt_path, "w") as f:
            f.write(agent.prompt)

        logger.info(f"agent {agent.agent_name} saved.")
        
    def _remove_agent(self, agent_name: str):
        agent_path = self.agents_dir / f"{agent_name}.json"
        agent_prompt_path = self.prompt_dir / f"{agent_name}.md"

        try:
            agent_path.unlink(missing_ok=True)  # delete json file
            logger.info(f"Removed agent definition file: {agent_path}")
        except Exception as e:
            logger.error(f"Error removing agent definition file {agent_path}: {e}")

        try:
            agent_prompt_path.unlink(missing_ok=True) 
            logger.info(f"Removed agent prompt file: {agent_prompt_path}")
        except Exception as e:
            logger.error(f"Error removing agent prompt file {agent_prompt_path}: {e}")

        try:
            if agent_name in self.available_agents:
                del self.available_agents[agent_name] 
                logger.info(f"Removed agent '{agent_name}' from available agents.")
        except Exception as e:
             logger.error(f"Error removing agent '{agent_name}' from available_agents dictionary: {e}")
    
    async def _load_agent(self, agent_name: str, user_agent_flag: bool=False):
        agent_path = self.agents_dir / f"{agent_name}.json"
        if not agent_path.exists():
            raise FileNotFoundError(f"agent {agent_name} not found.")
        with open(agent_path, "r") as f:
            json_str = f.read()
            _agent = Agent.model_validate_json(json_str)
            if _agent.user_id == 'share':
                self.available_agents[_agent.agent_name] = _agent
            elif user_agent_flag:
                self.available_agents[_agent.agent_name] = _agent

            return
        
    async def _list_agents(self, user_id: str = None, match: str = None):
        agents = [agent for agent in self.available_agents.values()]
        if user_id:
            agents = [agent for agent in agents if agent.user_id == user_id]
        if match:
            agents = [agent for agent in agents if re.match(match, agent.agent_name)]
        return agents

    def _edit_agent(self, agent: Agent):
        try:
            _agent = self.available_agents[agent.agent_name]
            _agent.nick_name = agent.nick_name
            _agent.description = agent.description
            _agent.selected_tools = agent.selected_tools
            _agent.prompt = agent.prompt
            _agent.llm_type = agent.llm_type
            self._save_agent(_agent, flush=True)
            return "success"
        except Exception as e:
            raise NotFoundAgentError(f"agent {agent.agent_name} not found.")
    
    def _save_agents(self, agents: list[Agent], flush=False):
        for agent in agents:
            self._save_agent(agent, flush)  
        return
    
    async def _load_default_agents(self):
        self._create_agent_by_prebuilt(user_id="share",
                                        name="researcher",
                                        nick_name="researcher",
                                        llm_type=AGENT_LLM_MAP["researcher"],
                                        tools=[tavily_tool, crawl_tool],
                                        prompt=get_prompt_template("researcher")[0],
                                        description="This agent specializes in research tasks by utilizing search engines and web crawling. It can search for information using keywords, crawl specific URLs to extract content, and synthesize findings into comprehensive reports. The agent excels at gathering information from multiple sources, verifying relevance and credibility, and presenting structured conclusions based on collected data."),

        self._create_agent_by_prebuilt(user_id="share", 
                                        name="coder", 
                                        nick_name="coder", 
                                        llm_type=AGENT_LLM_MAP["coder"], 
                                        tools=[python_repl_tool, bash_tool], 
                                        prompt=get_prompt_template("coder")[0],
                                        description="This agent specializes in software engineering tasks using Python scripts. This agent excels in data analysis and algorithm implementation. Can complete some statistical calculations, computations, and tasks that can be solved with Python code. Please note that this agent is unable to operate the system, view, create, or modify any files."),

        
        self._create_agent_by_prebuilt(user_id="share", 
                                        name="browser", 
                                        nick_name="browser", 
                                        llm_type=AGENT_LLM_MAP["browser"], 
                                        tools=[browser_tool], 
                                        prompt=get_prompt_template("browser")[0],
                                        description="This agent specializes in interacting with web browsers. It can navigate to websites, perform actions like clicking, typing, and scrolling, and extract information from web pages. The agent is adept at handling tasks such as searching specific websites, interacting with web elements, and gathering online data. It is capable of operations like logging in, form filling, clicking buttons, and scraping content."),
    
        self._create_agent_by_prebuilt(user_id="share",
                                        name="reporter",
                                        nick_name="reporter",
                                        llm_type=AGENT_LLM_MAP["reporter"],
                                        tools=[],
                                        prompt=get_prompt_template("reporter")[0],
                                        description="This agent specializes in creating clear and comprehensive reports based on the provided information and verifiable facts. It objectively presents data, logically organizes information, and highlights key findings using professional language. But its ability is limited, it can only generate text and cannot perform other advanced operations such as generating Word.")

    async def _load_agents(self, user_agent_flag):
        await self._load_default_agents()
        load_tasks = []
        for agent_path in self.agents_dir.glob("*.json"):
            agent_name = agent_path.stem
            if agent_name not in self.available_agents.keys():
                load_tasks.append(self._load_agent(agent_name, user_agent_flag))
                
        if not USE_BROWSER and "browser" in self.available_agents:
            del self.available_agents["browser"]
            

        if load_tasks:
            results = await asyncio.gather(*load_tasks, return_exceptions=True)
            for i, result in enumerate(results):
                 if isinstance(result, FileNotFoundError):
                      logger.warning(f"File not found during bulk load for agent: {load_tasks[i]}. Error: {result}")
                 elif isinstance(result, Exception):
                      logger.error(f"Error during bulk load for agent: {load_tasks[i]}. Error: {result}")
        return   
    
    async def _list_default_tools(self):
        await self.load_tools()
        mcp_tools = []
        for tool_name, tool in self.available_tools.items():
            mcp_tools.append(Tool(
                name=tool_name,
                description=tool.description,
            ))
        return mcp_tools
    
    async def _list_default_agents(self):
        agents = [agent for agent in self.available_agents.values() if agent.user_id == "share"]
        return agents
    
from src.utils.path_utils import get_project_root

tools_dir = get_project_root() / "store" / "tools"
agents_dir = get_project_root() / "store" / "agents"
prompts_dir = get_project_root() / "store" / "prompts"

agent_manager = AgentManager(tools_dir, agents_dir, prompts_dir)
asyncio.run(agent_manager.initialize())
