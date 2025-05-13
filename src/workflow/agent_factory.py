import logging
import json
from copy import deepcopy
from typing import Literal
from langgraph.types import Command

from src.llm.llm import get_llm_by_type
from src.llm.agents import AGENT_LLM_MAP
from src.prompts.template import apply_prompt_template
from src.tools.search import tavily_tool
from src.interface.agent_types import State, Router, AgentBuilder
from src.manager import agent_manager
from src.workflow.graph import AgentWorkflow


logger = logging.getLogger(__name__)

RESPONSE_FORMAT = "Response from {}:\n\n<response>\n{}\n</response>\n\n*Please execute the next step.*"

async def agent_factory_node(state: State) -> Command[Literal["publisher","__end__"]]:
    """Node for the create agent agent that creates a new agent."""
    logger.info("Agent Factory Start to work \n")
    messages = apply_prompt_template("agent_factory", state)
    response = (
        get_llm_by_type(AGENT_LLM_MAP["agent_factory"])
        .with_structured_output(AgentBuilder)
        .invoke(messages)
    )
    
    tools = [agent_manager.available_tools[tool["name"]] for tool in response["selected_tools"]]

    agent_manager._create_agent_by_prebuilt(
        user_id=state["user_id"],
        name=response["agent_name"],
        nick_name=response["agent_name"],
        llm_type=response["llm_type"],
        tools=tools,
        prompt=response["prompt"],
        description=response["agent_description"],
    )
    
    state["TEAM_MEMBERS"].append(response["agent_name"])

    return Command(
        update={
            "messages": [
                {"content":f'New agent {response["agent_name"]} created. \n', "tool":"agent_factory", "role":"assistant"}
            ],
            "new_agent_name": response["agent_name"],
            "agent_name": "agent_factory",
        },
        goto="__end__",
    )


async def publisher_node(state: State) -> Command[Literal["agent_factory", "agent_factory", "__end__"]]:
    """publisher node that decides which agent should act next."""
    logger.info("publisher evaluating next action")
    messages = apply_prompt_template("publisher", state)
    response = await (
        get_llm_by_type(AGENT_LLM_MAP["publisher"])
        .with_structured_output(Router)
        .ainvoke(messages)
    )
    agent = response["next"]
    
    if agent == "FINISH":
        goto = "__end__"
        logger.info("Workflow completed \n")
        return Command(goto=goto, update={"next": goto})
    elif agent != "agent_factory":
        logger.info(f"publisher delegating to: {agent}")
        return Command(goto=goto, update={"next": agent})
    else:
        goto = "agent_factory"
        logger.info(f"publisher delegating to: {agent}")
        return Command(goto=goto, update={"next": agent})


async def planner_node(state: State) -> Command[Literal["publisher", "__end__"]]:
    """Planner node that generate the full plan."""
    logger.info("Planner generating full plan \n")
    messages = apply_prompt_template("planner", state)
    llm = get_llm_by_type(AGENT_LLM_MAP["planner"])
    if state.get("deep_thinking_mode"):
        llm = get_llm_by_type("reasoning")
    if state.get("search_before_planning"):
        searched_content = tavily_tool.invoke({"query": state["messages"][-1]["content"]})
        messages = deepcopy(messages)
        messages[-1]["content"] += f"\n\n# Relative Search Results\n\n{json.dumps([{'titile': elem['title'], 'content': elem['content']} for elem in searched_content], ensure_ascii=False)}"
    
    response = await llm.ainvoke(messages)
    content = response.content

    if content.startswith("```json"):
        content = content.removeprefix("```json")

    if content.endswith("```"):
        content = content.removesuffix("```")

    goto = "publisher"
    try:
        json.loads(content)
    except json.JSONDecodeError:
        logger.warning("Planner response is not a valid JSON")
        goto = "__end__"

    return Command(
        update={
            "messages": [{"content":content, "tool":"planner", "role":"assistant"}],
            "agent_name": "planner",
            "full_plan": content,
        },
        goto=goto,
    )


async def coordinator_node(state: State) -> Command[Literal["planner", "__end__"]]:
    """Coordinator node that communicate with customers."""
    logger.info("Coordinator talking. \n")
    messages = apply_prompt_template("coordinator", state)
    response = await get_llm_by_type(AGENT_LLM_MAP["coordinator"]).ainvoke(messages)

    goto = "__end__"
    if "handover_to_planner" in response.content:
        goto = "planner"
        
    return Command(
        update={
            "messages": [{"content":response.content, "tool":"coordinator", "role":"assistant"}],
            "agent_name": "coordinator",
        },
        goto=goto,
    )


def agent_factory_graph():
    workflow = AgentWorkflow()    
    workflow.add_node("coordinator", coordinator_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("publisher", publisher_node)
    workflow.add_node("agent_factory", agent_factory_node)
    
    workflow.set_start("coordinator")    
    return workflow.compile()
