from langgraph.graph import StateGraph, START, END

from .types import State
from .nodes import (
    supervisor_node,
    coordinator_node,
    planner_node,
    create_agent_node,
    agent_proxy_node,
)


def build_graph():
    """Build and return the agent workflow graph."""
    builder = StateGraph(State)
    builder.add_edge(START, "coordinator")
    builder.add_node("coordinator", coordinator_node)
    builder.add_node("planner", planner_node)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("create_agent", create_agent_node)
    builder.add_node("agent_proxy", agent_proxy_node)
    return builder.compile()