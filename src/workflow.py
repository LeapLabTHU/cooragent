import logging
from src.graph import build_graph
from src.agents import agent_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Default level is INFO
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def enable_debug_logging():
    """Enable debug level logging for more detailed execution information."""
    logging.getLogger("src").setLevel(logging.DEBUG)


logger = logging.getLogger(__name__)

# Create the graph
graph = build_graph()

DEFAULT_TEAM_MEMBERS_DESCRIPTION = """
- **`researcher`**: Uses search engines and web crawlers to gather information from the internet. Outputs a Markdown report summarizing findings. Researcher can not do math or programming.
- **`coder`**: Executes Python or Bash commands, performs mathematical calculations, and outputs a Markdown report. Must be used for all mathematical computations.
- **`browser`**: Directly interacts with web pages, performing complex operations and interactions. You can also leverage `browser` to perform in-domain search, like Facebook, Instagram, Github, etc.
- **`reporter`**: Write a professional report based on the result of each step.
- **`create_agent`**: Create a new agent based on the user's requirement.
"""

TEAM_MEMBERS_DESCRIPTION_TEMPLATE = """
- **`{agent_name}`**: {agent_description}
"""

def run_agent_workflow(user_id: str, user_input: str, debug: bool = False):
    """Run the agent workflow with the given user input.

    Args:
        user_input: The user's query or request
        debug: If True, enables debug level logging

    Returns:
        The final state after the workflow completes
    """
    if not user_input:
        raise ValueError("Input could not be empty")

    if debug:
        enable_debug_logging()

    logger.info(f"Starting workflow with user input: {user_input}")
    TEAM_MEMBERS_DESCRIPTION = DEFAULT_TEAM_MEMBERS_DESCRIPTION
    TEAM_MEMBERS = ["create_agent"]
    for agent in agent_manager.available_agents:
        if agent["mcp_obj"].user_id == user_id or agent["mcp_obj"].user_id == "share":
            TEAM_MEMBERS.append(agent["mcp_obj"].agent_name)
            if agent["mcp_obj"].user_id != "share":
                MEMBER_DESCRIPTION = TEAM_MEMBERS_DESCRIPTION_TEMPLATE.format(agent_name=agent["mcp_obj"].agent_name, agent_description=agent["mcp_obj"].description)
                TEAM_MEMBERS_DESCRIPTION += '\n' + MEMBER_DESCRIPTION
    
    logger.info(f"TEAM_MEMBERS: {TEAM_MEMBERS}")
    logger.info(f"TEAM_MEMBERS_DESCRIPTION: {TEAM_MEMBERS_DESCRIPTION}")
    result = graph.invoke(
        {
            "TEAM_MEMBERS": TEAM_MEMBERS,
            "TEAM_MEMBERS_DESCRIPTION": TEAM_MEMBERS_DESCRIPTION,
            "user_id": user_id,
            "messages": [{"role": "user", "content": user_input}],
            "deep_thinking_mode": True,
            "search_before_planning": True,
        }
    )
    logger.debug(f"Final workflow state: {result}")
    logger.info("Workflow completed successfully")
    return result


if __name__ == "__main__":
    print(graph.get_graph().draw_mermaid())
    graph.get_graph().draw_png(output_file_path="workflow.png")
