from langgraph.prebuilt import create_react_agent

from src.prompts import apply_prompt_template
from src.tools import (
    bash_tool,
    browser_tool,
    crawl_tool,
    python_repl_tool,
    tavily_tool,
)

from .llm import get_llm_by_type
from src.config.agents import AGENT_LLM_MAP

# Create agents using configured LLM types

# class Agent:
#     def __init__(self, llm_type: str, tools: list[Tool], prompt: str):
#         self.llm_type = llm_type
#         self.tools = tools
#         self.prompt = prompt 
        
    
#     def _serialize(self):
#         return json.dumps(state)
    
#     def _deserialize_state(self, state: str):
#         return json.loads(state)

research_agent = create_react_agent(
    llm_type=AGENT_LLM_MAP["researcher"],
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
