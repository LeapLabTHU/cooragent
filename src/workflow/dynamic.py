from typing import Dict, Callable, List, Optional
from src.interface.agent import State
from langgraph.types import Command
from src.manager import agent_manager
from langchain_mcp_adapters.client import MultiServerMCPClient
from src.manager.mcp import mcp_client_config
from src.llm.llm import get_llm_by_type
from langchain_core.prompts import ChatPromptTemplate
from langgraph.prebuilt import create_react_agent
from src.prompts.template import apply_prompt
from src.workflow.graph import AgentWorkflow
from src.workflow.coor_task import coordinator_node, planner_node, publisher_node, agent_factory_node, agent_proxy_node
import asyncio
import logging
from config.global_functions import func_map
from config.global_variables import context_variables   

logger = logging.getLogger(__name__)

system_agent_nodes ={
    "coordinator_node": coordinator_node,
    "planner_node": planner_node,
    "publisher_node": publisher_node,
    "agent_factory_node": agent_factory_node,
    "agent_proxy_node": agent_proxy_node,
}

class DynamicWorkflow:
    def __init__(self):
        self.workflow = AgentWorkflow()
        self.compiled_workflow = None

    def _build_agent_node(self, name: str, node: dict):
        async def agent_node(state: State):
            if node["agent"]["agent_name"] not in agent_manager.available_agents:
                try:
                    asyncio.run(agent_manager._load_agent(node["agent"]["agent_name"], user_agent_flag=True))
                    _agent = agent_manager.available_agents[node["agent"]["agent_name"]]
                except:
                    agent_manager._create_agent_by_prebuilt(
                        user_id=node["agent"]["user_id"],
                        name=node["agent"]["agent_name"],
                        nick_name=node["agent"]["agent_name"],
                        llm_type=node["agent"]["llm_type"],
                        tools=node["agent"]["tools"],
                    prompt=node["agent"]["prompt"],
                    description=node["agent"]["description"])
                    _agent = agent_manager.available_agents[node["agent"]["agent_name"]]
            async with MultiServerMCPClient(mcp_client_config()) as client:
                mcp_tools = client.get_tools()
                for _tool in mcp_tools:
                    agent_manager.available_tools[_tool.name] = _tool
                agent = create_react_agent(
                    get_llm_by_type(_agent.llm_type),
                    tools=[agent_manager.available_tools[tool.name] for tool in _agent.selected_tools],
                    prompt=apply_prompt(state, _agent.prompt),
                )

                response = await agent.ainvoke(state)
            
            next = "publisher"
            proposed_next = node["next_to"]
            
            if node["condition"]["type"] == "function":
                func = func_map[node["condition"]["function"]]
                _vars = context_variables
                next = node["condition"]["branches"][func(_vars)]


            return Command(
                update={
                    "messages": [{"content": response["messages"][-1].content, "tool":state["next"], "role":"assistant"}],
                    "processing_agent_name": _agent.agent_name,
                    "agent_name": _agent.agent_name,
                    "proposed_next": proposed_next
                },
                goto=next,
            )            
        return agent_node

    def _add_node(self, name: str, node: dict):
        if node["type"] == "system_agent":
            self.workflow.add_node(name, system_agent_nodes[name])
        elif node["type"] == "execution_agent":
            self.workflow.add_node(name, self._build_agent_node(name, node))

    def _build_workflow(self, json_workflow: dict):
        nodes = json_workflow["agent_nodes"]
        for node in json_workflow["graph"]:
            self.add_node(nodes[node["node_name"]])
        self.workflow.set_start(json_workflow["start_node"])
        self.compiled_workflow = self.workflow.compile()
        return self.compiled_workflow
