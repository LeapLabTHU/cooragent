from langgraph.prebuilt import create_react_agent
from src.interface.mcp_types import Tool
from src.prompts import apply_prompt_template, get_structured_prompt
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
from langchain_core.load import dumpd, dumps, load, loads
from pathlib import Path
from src.interface.agent_types import Agent, Prompt
from langgraph.graph.graph import CompiledGraph
from src.graph.types import State

research_agent = create_react_agent(
    get_llm_by_type(AGENT_LLM_MAP["researcher"]),
    tools=[tavily_tool, crawl_tool],
    prompt=lambda state: apply_prompt_template("researcher", state),
)

coder_agent = create_react_agent(
    get_llm_by_type(AGENT_LLM_MAP["coder"]),
    tools=[python_repl_tool, bash_tool],
    prompt=lambda state: apply_prompt_template("coder", state),
)

browser_agent = create_react_agent(
    get_llm_by_type(AGENT_LLM_MAP["browser"]),
    tools=[browser_tool],
    prompt=lambda state: apply_prompt_template("browser", state),
)

available_agents = {
    "researcher": research_agent,
    "coder": coder_agent,
    "browser": browser_agent,
}

class AgentManager:
    def __init__(self, tools_dir, agents_dir, prompt_dir):
        self.tools_dir = Path(tools_dir)
        self.agents_dir = Path(agents_dir)
        self.prompt_dir = Path(prompt_dir)

        if not self.tools_dir.exists() or not self.agents_dir.exists() or not self.prompt_dir.exists():
            raise FileNotFoundError("One or more provided directories do not exist.")

        self.available_agents = {
            "researcher": research_agent,
            "coder": coder_agent,
            "browser": browser_agent,
        }

        self.available_tools = {
            "bash_tool": bash_tool,
            "browser_tool": browser_tool,
            "crawl_tool": crawl_tool,
            "python_repl_tool": python_repl_tool,
            "tavily_tool": tavily_tool,
        }
        
        self.tools = self._load_tools()
        self.agents = self._load_agents()
        self.prompts = self._load_prompts()
        

    def _create_agent(self, name: str, llm_type: str, tools: list[tool], prompt: Prompt=None):
        langchain_agent = create_react_agent(
            llm_type=llm_type,
            tools=tools,
            prompt=lambda state: apply_prompt_template(name, state),
        )
        
        agent = Agent(
            agent_name=name,
            agent_id=name,
            llm_type=llm_type,
            selected_tools=tools,
            prompt=get_structured_prompt(name) if not prompt else prompt ,
        )
        
        self.agents.append(agent)
        self._save_agent(agent)
                
        return langchain_agent, agent

    def _save_tool(self, tool: Tool, flush=False):
        tool_path = self.tools_dir / f"{tool.name}.json"
        if not flush and tool_path.exists():
            print(f"工具 {tool.name} 已经存在，不需要保存。")
            return
        with open(tool_path, "w") as f:
            f.write(tool.model_dump_json())
        print(f"工具 {tool.name} 已经成功保存。")
    
    def _load_tool(self, tool_name: str):
        tool_path = self.tools_dir / f"{tool_name}.json"
        if not tool_path.exists():
            raise FileNotFoundError(f"tool {tool_name} not found.")
        with open(tool_path, "r") as f:
            json_str = f.read()
            return Tool.model_validate_json(json_str)

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
            return Agent.model_validate_json(json_str)
        
    def _list_agents(self, user_id: str, match: str):
        agents = self.agents
        if user_id:
            agents = [agent for agent in agents if agent.user_id == user_id]
        if match:
            agents = [agent for agent in agents if match in agent.agent_name]
        return agents
        
    def _save_tools(self, tools: list[tool], flush=False):
        for tool in tools:
            self._save_tool(tool, flush)

    def _load_tools(self):
        for tool_path in self.tools_dir.glob("*.json"):
            self.tools.append(self._load_tool(tool_path.stem))

    
    def _save_agents(self, agents: list[Agent], flush=False):
        for agent in agents:
            self._save_agent(agent, flush)  
            
    def _load_agents(self):
        agents = []
        for agent_path in self.agents_dir.glob("*.json"):
            agents.append(self._load_agent(agent_path.stem))
        return agents   
    
    def _save_prompt(self, prompt: str, flush=False):
        prompt_path = self.prompt_dir / f"{prompt.name}.json"
        if not flush and prompt_path.exists():
            print(f"prompt {prompt.name} already exists, skipping save.")
            return
        with open(prompt_path, "w") as f:
            f.write(dumpd(prompt))
        print(f"prompt {prompt.name} saved.")
    
    def _load_prompt(self, prompt_name: str):
        prompt_path = self.prompt_dir / f"{prompt_name}.json"
        if not prompt_path.exists():
            raise FileNotFoundError(f"prompt {prompt_name} not found.")     
        with open(prompt_path, "r") as f:
            return load(f)
    
    def _save_prompts(self, prompts: list[str], flush=False):
        for prompt in prompts:
            self._save_prompt(prompt, flush)
            
    def _load_prompts(self):
        prompts = []
        for prompt_path in self.prompt_dir.glob("*.json"):
            prompts.append(self._load_prompt(prompt_path.stem))
        return prompts

    def _add_tool(self, tool: tool):
        self.tools.append(tool)
        self._save_tool(tool)
        
    def _add_agent(self, agent: Agent):
        self.agents.append(agent)
        self._save_agent(agent)     

    def _add_prompt(self, prompt: str):
        self.prompts.append(prompt)
        self._save_prompt(prompt)
        
    def _remove_tool(self, tool: tool):
        self.tools.remove(tool)
        self._save_tool(tool)
        
    def _remove_agent(self, agent: Agent):
        self.agents.remove(agent)
        self._save_agent(agent)
        
    def _remove_prompt(self, prompt: str):
        self.prompts.remove(prompt)
        self._save_prompt(prompt)


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
    
