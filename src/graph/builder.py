from langgraph.graph import StateGraph, START, END

from .types import State
from .nodes import (
    supervisor_node,
    research_node,
    code_node,
    coordinator_node,
    browser_node,
    reporter_node,
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
    # builder.add_node("coder", code_node)
    # builder.add_node("browser", browser_node)
    # builder.add_node("reporter", reporter_node)
    return builder.compile()

# def build_agent_graph():
#     """Build and return the agent workflow graph."""
#     builder = StateGraph(State)
#     builder.add_edge(START, "create_agent")
#     builder.add_node("create_agent", create_agent_node)
#     return builder.compile()
