import logging
import json
import uuid
from copy import deepcopy
from langgraph.types import Command
from typing import Literal
from src.llm.llm import get_llm_by_type, parse_json
from src.llm.agents import AGENT_LLM_MAP
from src.prompts.template import (apply_prompt_template,
                                  apply_common_prompt,
                                  apply_publisher_prompt,
                                  get_agent_task,
                                  apply_created_agent_prompt,
                                  get_critic_prompt)
from src.tools.search import tavily_tool
from src.interface.agent_types import State, Router
from src.manager import agent_manager
from src.prompts.template import apply_prompt
from langgraph.prebuilt import create_react_agent
from src.workflow.graph import AgentWorkflow
from langchain_mcp_adapters.client import MultiServerMCPClient
from src.manager.mcp import mcp_client_config

logger = logging.getLogger(__name__)



async def agent_factory_node(state: State) -> Command[Literal["publisher","__end__"]]:
    """Node for the create agent agent that creates a new agent."""
    logger.info("Agent Factory Start to work \n")

    get_agent_task(state)
    state["NEW_AGENT_NAME"] = state["new_agent_name"]
    messages = apply_prompt_template("agent_factory", state)

    model_res = (
        get_llm_by_type(AGENT_LLM_MAP["agent_factory"])
        .stream(messages)
    )
    response = parse_json(model_res)
    goto = "publisher"
    try:
        content = json.loads(response)
    except json.JSONDecodeError:
        logger.warning("Planner response is not a valid JSON \n")
        goto = "__end__"

    tools = [agent_manager.available_tools[tool["name"]] for tool in content["selected_tools"]]
    prompt = apply_created_agent_prompt(content["prompt"])
    agent_manager._create_agent_by_prebuilt(
        user_id=state["user_id"],
        name=content["agent_name"],
        nick_name=content["agent_name"],
        llm_type=content["llm_type"],
        tools=tools,
        prompt=prompt,
        description=content["agent_description"],
    )
    state["TEAM_MEMBERS"].append(content["agent_name"])
    state["agent_memory"]["execution_flow"].append({
        "uuid":uuid.uuid4(),
        "Step_id":state["step_id"],
        "agent_name":"agent_factory",
        "status":"success",
        "agent_messages":(f'A new agent {content["agent_name"]} has been successfully '
                                                                f'created, with the following description:'
                                                                f'{content["agent_description"]}')
    })


    return Command(
        update={
            "messages": [
                {"content":f'New agent {content["agent_name"]} created. \n', "tool":"agent_factory", "role":"assistant"}
            ],
            "new_agent_name": content["agent_name"],
            "agent_name": "agent_factory",
        },
        goto=goto,
    )


async def publisher_node(state: State) -> Command[Literal["agent_proxy", "agent_factory", "__end__"]]:
    """publisher node that decides which agent should act next."""
    logger.info("publisher evaluating next action")
    messages = apply_publisher_prompt(state,agent_manager.available_agents)
    model_res = (
        get_llm_by_type(AGENT_LLM_MAP["publisher"])
        .stream(messages)
    )
    response = parse_json(model_res)
    response = json.loads(response)
    agent = response["next"]
    
    if agent == "FINISH":
        goto = "__end__"
        logger.info("Workflow completed \n")
        return Command(goto=goto, update={"next": goto})
    elif agent != "agent_factory":
        goto = "agent_proxy"
    else:
        goto = "agent_factory"
        state["new_agent_name"] = response["new_agent_name"]
    state["step_id"] = response["step_id"]
    logger.info(f"publisher delegating to: {agent} \n")
    return Command(goto=goto, 
                    update={
                        "messages": [{"content":f"Next step is delegating to: {agent}\n", "tool":"publisher", "role":"assistant"}],
                        "next": agent,
                        "next_agent_messages":{"task_description":response["description"],
                                               "know_information":response["know_information"],
                                               "note":response["note"],
                                               }})


async def agent_proxy_node(state: State) -> Command[Literal["publisher","__end__"]]:
    """Proxy node that acts as a proxy for the agent."""
    _agent = agent_manager.available_agents[state["next"]]
    get_agent_task(state)
    llm = get_llm_by_type("basic")
    async with MultiServerMCPClient(mcp_client_config()) as client:
        mcp_tools = client.get_tools()
        for _tool in mcp_tools:
            agent_manager.available_tools[_tool.name] = _tool
        agent = create_react_agent(
            llm,
            tools=[agent_manager.available_tools[tool.name] for tool in _agent.selected_tools],
            prompt=apply_prompt(state, _agent.prompt),
        )

        response = await agent.ainvoke({'role':'user','content':'Please be sure to complete your task carefully and conscientiously!'},{"recursion_limit": 100},)

    response = response['messages'][-1].content
    content = llm.stream(get_critic_prompt(state,response))
    content = parse_json(content)
    goto = "publisher"
    try:
        content = json.loads(content)
    except json.JSONDecodeError:
        logger.warning(f"{_agent.agent_name} response is not a valid JSON \n")
        goto = "__end__"

    state["agent_memory"]["execution_flow"].append({
        "uuid": uuid.uuid4(),
        "Step_id":state["step_id"],
        "agent_name":_agent.agent_name,
        "status":content["status"],
        "agent_messages":response
    })
    return Command(
        update={
            "messages": [{"content": response, "tool":state["next"], "role":"assistant"}],
            "processing_agent_name": _agent.agent_name,
            "agent_name": _agent.agent_name
        },
        goto=goto,
    )


async def planner_node(state: State) -> Command[Literal["publisher", "__end__"]]:
    """Planner node that generate the full plan."""
    logger.info("Planner generating full plan \n")
    messages = apply_common_prompt("planner", state)
    llm = get_llm_by_type(AGENT_LLM_MAP["planner"])
    if state.get("deep_thinking_mode"):
        llm = get_llm_by_type("reasoning")
    if state.get("search_before_planning"):
        searched_content = tavily_tool.invoke({"query": [''.join(message["content"]) for message in state["messages"] if message["role"] == "user"][0]})
        messages = deepcopy(messages)
        messages[-1]["content"] += f"\n\n# Relative Search Results\n\n{json.dumps([{'titile': elem['title'], 'content': elem['content']} for elem in searched_content], ensure_ascii=False)}"
    response = llm.stream(messages)
    content = parse_json(response)

    goto = "publisher"
    try:
        plan_content = json.loads(content)
    except json.JSONDecodeError:
        logger.warning("Planner response is not a valid JSON \n")
        plan_content = ''
        goto = "__end__"

    return Command(
        update={
            "messages": [{"content":content, "tool":"planner", "role":"assistant"}],
            "agent_name": "planner",
            "full_plan": content,
            "agent_memory": {
                "plan_content": plan_content,
                "execution_flow": []
            }
        },
        goto=goto,
    )

async def coordinator_node(state: State) -> Command[Literal["planner", "__end__"]]:
    """Coordinator node that communicate with customers."""
    logger.info("Coordinator talking. \n")
    messages = apply_common_prompt("coordinator", state)
    response = get_llm_by_type(AGENT_LLM_MAP["coordinator"]).invoke(messages)

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