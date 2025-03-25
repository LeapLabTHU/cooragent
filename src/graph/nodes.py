import logging
import json
from copy import deepcopy
from typing import Literal
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from langgraph.graph import END


from src.llm import get_llm_by_type
from src.config import TEAM_MEMBERS
from src.config.agents import AGENT_LLM_MAP
from src.prompts.template import apply_prompt_template
from src.tools.search import tavily_tool
from .types import State, Router
from src.agents import agent_manager

logger = logging.getLogger(__name__)

RESPONSE_FORMAT = "Response from {}:\n\n<response>\n{}\n</response>\n\n*Please execute the next step.*"

def create_agent_node(state: State) -> Command[Literal["supervisor","__end__"]]:
    """Node for the create agent agent that creates a new agent."""
    logger.info("Create agent agent starting task")
    messages = apply_prompt_template("create_agent", state)
    response = (
        get_llm_by_type(AGENT_LLM_MAP["create_agent"])
        .with_structured_output(Router)
        .invoke(messages)
    )
    
    tools = [agent_manager.available_tools[tool["name"]] for tool in response["selected_tools"]]

    agent_manager._create_agent_by_prebuilt(
        user_id=state["user_id"],
        name=response["agent_name"],
        llm_type=response["llm_type"],
        tools=tools,
        prompt=response["prompt"],
    )
    
    logger.info("Create agent agent completed task")
    user_available_agents = [agent["mcp_obj"] for agent in agent_manager.available_agents if agent["mcp_obj"].user_id == "share" or agent["mcp_obj"].user_id == state["user_id"]]
    logger.info(f"Available agents: {user_available_agents}")
    logger.info(f" agents created as, {json.dumps(response, ensure_ascii=False)}")
    state["TEAM_MEMBERS"].append(response["agent_name"])

    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=RESPONSE_FORMAT.format(
                        state["next"], f'New agent {response["agent_name"]} created.'
                    ),
                    name=state["next"],
                )
            ]
        },
        goto="supervisor",
    )


def supervisor_node(state: State) -> Command[Literal["agent_proxy", "create_agent", "__end__"]]:
    """Supervisor node that decides which agent should act next."""
    logger.info("Supervisor evaluating next action")
    messages = apply_prompt_template("supervisor", state)
    response = (
        get_llm_by_type(AGENT_LLM_MAP["supervisor"])
        .with_structured_output(Router)
        .invoke(messages)
    )
    agent = response["next"]
    logger.debug(f"Current state messages: {state['messages']}")
    logger.debug(f"Supervisor response: {response}")
    
    if agent == "FINISH":
        goto = "__end__"
        logger.info("Workflow completed")
        return Command(goto=goto, update={"next": goto})
    elif agent != "create_agent":
        goto = "agent_proxy"
        logger.info(f"Supervisor delegating to: {agent}")
        return Command(goto=goto, update={"next": agent})
    else:
        goto = "create_agent"
        logger.info(f"Supervisor delegating to: {agent}")
        return Command(goto=goto, update={"next": agent})


def agent_proxy_node(state: State) -> Command[Literal["supervisor","__end__"]]:
    """Agent proxy node that acts as a proxy for the agent."""
    logger.info("Agent proxy agent starting task")
    _agent = [agent["runtime"] for agent in agent_manager.available_agents if agent["mcp_obj"].agent_name == state["next"]][0]
    response = _agent.invoke(state)
    logger.info(f"{state['next']} agent completed task")
    logger.debug(f"{state['next']} agent response: {response['messages'][-1].content}")
    
    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=RESPONSE_FORMAT.format(
                        state["next"], response["messages"][-1].content
                    ),
                    name=state["next"],
                )
            ]
        },
        goto="supervisor",
    )



def planner_node(state: State) -> Command[Literal["supervisor", "__end__"]]:
    """Planner node that generate the full plan."""
    logger.info("Planner generating full plan")
    messages = apply_prompt_template("planner2", state)
    # whether to enable deep thinking mode
    llm = get_llm_by_type("basic")
    if state.get("deep_thinking_mode"):
        llm = get_llm_by_type("reasoning")
    if state.get("search_before_planning"):
        searched_content = tavily_tool.invoke({"query": state["messages"][-1].content})
        messages = deepcopy(messages)
        messages[
            -1
        ].content += f"\n\n# Relative Search Results\n\n{json.dumps([{'titile': elem['title'], 'content': elem['content']} for elem in searched_content], ensure_ascii=False)}"
    stream = llm.stream(messages)
    full_response = ""
    for chunk in stream:
        full_response += chunk.content
    logger.debug(f"Current state messages: {state['messages']}")
    logger.debug(f"Planner response: {full_response}")

    if full_response.startswith("```json"):
        full_response = full_response.removeprefix("```json")

    if full_response.endswith("```"):
        full_response = full_response.removesuffix("```")

    goto = "supervisor"
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
    logger.debug(f"Current state messages: {state['messages']}")
    logger.debug(f"reporter response: {response}")

    goto = "__end__"
    if "handoff_to_planner" in response.content:
        goto = "planner"

    return Command(
        goto=goto,
    )

