import logging
import json
from copy import deepcopy
from langgraph.types import Command
from typing import Literal
from src.llm.llm import get_llm_by_type
from src.llm.agents import AGENT_LLM_MAP
from src.prompts.template import apply_prompt_template, apply_polish_template
from src.tools.search import tavily_tool
from src.interface.agent import State, Router
from src.interface.serialize_types import AgentBuilder
from src.manager import agent_manager
from src.prompts.template import apply_prompt
from langgraph.prebuilt import create_react_agent
from src.workflow.graph import AgentWorkflow
from langchain_mcp_adapters.client import MultiServerMCPClient
from src.manager.mcp import mcp_client_config
from src.workflow.cache import workflow_cache as cache
from src.interface.agent import Agent

logger = logging.getLogger(__name__)

TOOLS_DESCRIPTION_TEMPLATE = "- **`{tool_name}`**: {tool_description}"
TOOLS_DESCRIPTION = ""

async def load_tools():
    global TOOLS_DESCRIPTION
    await agent_manager.load_tools()
    for tool_name, tool in agent_manager.available_tools.items():
        TOOLS_DESCRIPTION += '\n' + TOOLS_DESCRIPTION_TEMPLATE.format(tool_name=tool_name,tool_description=tool.description)
    
async def polish_agent(user_id, _agent: Agent, instruction: str, part_to_edit: str):
    await load_tools()
    messages = apply_polish_template(_agent, instruction, part_to_edit, TOOLS_DESCRIPTION)
    response = (
        get_llm_by_type(AGENT_LLM_MAP["polisher"])
        .with_structured_output(AgentBuilder)
        .invoke(messages)
    )
    
    tools = [agent_manager.available_tools[tool["name"]] for tool in response["selected_tools"]]

    _agent = Agent(
        user_id=user_id,
        agent_name=response["agent_name"],
        nick_name=response["agent_name"],
        llm_type=response["llm_type"],
        selected_tools=tools,
        prompt=response["prompt"],
        description=response["description"])
    
    agent_manager._edit_agent(_agent)
    return _agent
