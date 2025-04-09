import logging
import json
from copy import deepcopy
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from typing import Literal
from src.llm import get_llm_by_type
from src.config.agents import AGENT_LLM_MAP
from src.prompts.template import apply_prompt_template
from src.tools.search import tavily_tool
from src.interface.agent_types import State, Router
from src.manager import agent_manager
from src.prompts.template import apply_prompt
from langgraph.prebuilt import create_react_agent
from src.mcp.register import MCPManager
from src.workflow.graph import AgentWorkflow

logger = logging.getLogger(__name__)

RESPONSE_FORMAT = "Response from {}:\n\n<response>\n{}\n</response>\n\n*Please execute the next step.*"

def agent_factory_node(state: State) -> Command[Literal["publisher","__end__"]]:
    """Node for the create agent agent that creates a new agent."""
    logger.info("Create agent agent starting task")
    messages = apply_prompt_template("agent_factory", state)
    response = (
        get_llm_by_type(AGENT_LLM_MAP["agent_factory"])
        .with_structured_output(Router)
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
                HumanMessage(
                    content=RESPONSE_FORMAT.format(
                        state["next"], f'New agent {response["agent_name"]} created.'
                    ),
                    new_agent_name=response["agent_name"],
                )
            ],
        },
        goto="publisher",
    )


def publisher_node(state: State) -> Command[Literal["agent_proxy", "agent_factory", "__end__"]]:
    """publisher node that decides which agent should act next."""
    logger.info("publisher evaluating next action")
    messages = apply_prompt_template("publisher", state)
    response = (
        get_llm_by_type(AGENT_LLM_MAP["publisher"])
        .with_structured_output(Router)
        .invoke(messages)
    )
    agent = response["next"]

    
    if agent == "FINISH":
        goto = "__end__"
        logger.info("Workflow completed")
        return Command(goto=goto, update={"next": goto})
    elif agent != "agent_factory":
        goto = "agent_proxy"
        logger.info(f"publisher delegating to: {agent}")
        return Command(goto=goto, 
                       update={
                           "messages": [HumanMessage(content=f"Next step is delegating to: {agent}", name="publisher")],
                           "next": agent})
    else:
        goto = "agent_factory"
        logger.info(f"publisher delegating to: {agent}")
        return Command(goto=goto, 
                       update={
                           "messages": [HumanMessage(content=f"Next step is delegating to: {agent}", name="publisher")],
                           "next": agent})


def agent_proxy_node(state: State) -> Command[Literal["publisher","__end__"]]:
    """Proxy node that acts as a proxy for the agent."""
    logger.info("Agent starting task")
    _agent = agent_manager.available_agents[state["next"]]
    agent = create_react_agent(
        # get_llm_by_type(_agent.llm_type),
        get_llm_by_type("basic"),
        tools=[agent_manager.available_tools[tool.name] for tool in _agent.selected_tools],
        prompt=apply_prompt(state, _agent.prompt),
    )
    if _agent.agent_name.startswith("mcp_"):
        response = MCPManager._agents_runtime[_agent.agent_name].invoke(state)
    else:
        response = agent.invoke(state)

    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=RESPONSE_FORMAT.format(
                        state["next"], response["messages"][-1].content
                    ),
                    name=state["next"],
                )
            ],
            "processing_agent_name": _agent.agent_name
        },
        goto="publisher",
    )


def planner_node(state: State) -> Command[Literal["publisher", "__end__"]]:
    """Planner node that generate the full plan."""
    logger.info("Planner generating full plan")
    messages = apply_prompt_template("planner", state)
    llm = get_llm_by_type("basic")
    if state.get("deep_thinking_mode"):
        llm = get_llm_by_type("reasoning")
    if state.get("search_before_planning"):
        searched_content = tavily_tool.invoke({"query": state["messages"][-1].content})
        messages = deepcopy(messages)
        messages[-1]["content"] += f"\n\n# Relative Search Results\n\n{json.dumps([{'titile': elem['title'], 'content': elem['content']} for elem in searched_content], ensure_ascii=False)}"
    
    stream = llm.stream(messages)
    full_response = ""
    for chunk in stream:
        full_response += chunk.content


    if full_response.startswith("```json"):
        full_response = full_response.removeprefix("```json")

    if full_response.endswith("```"):
        full_response = full_response.removesuffix("```")

    goto = "publisher"
    try:
        json.loads(full_response)
    except json.JSONDecodeError:
        logger.warning("Planner response is not a valid JSON")
        goto = "__end__"

    return Command(
        update={
            "messages": [HumanMessage(content=full_response, name="planner")],
            "full_plan": full_response,
        },
        goto=goto,
    )


def coordinator_node(state: State) -> Command[Literal["planner", "__end__"]]:
    """Coordinator node that communicate with customers."""
    logger.info("Coordinator talking.")
    messages = apply_prompt_template("coordinator", state)
    response = get_llm_by_type(AGENT_LLM_MAP["coordinator"]).invoke(messages)

    goto = "__end__"
    if "handoff_to_planner" in response.content:
        goto = "planner"

    return Command(
        goto=goto,
    )



def build_graph():
    """Build and return the agent workflow graph."""
    workflow = AgentWorkflow()    
    workflow.add_node("coordinator", coordinator_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("publisher", publisher_node)
    workflow.add_node("agent_factory", agent_factory_node)
    workflow.add_node("agent_proxy", agent_proxy_node)
    
    workflow.set_start("coordinator")    
    return workflow.compile()