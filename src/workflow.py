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

# create_agent_graph = build_agent_graph()

def run_agent_workflow(user_input: str, debug: bool = False):
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
    
    TEAM_MEMBERS = [member for member in agent_manager.available_agents.keys()] + ["create_agent"]
    
    logger.info(f"TEAM_MEMBERS: {TEAM_MEMBERS}")
    
    result = graph.invoke(
        {
            # Constants
            "TEAM_MEMBERS": TEAM_MEMBERS,
            # Runtime Variables
            "messages": [{"role": "user", "content": user_input}],
            "deep_thinking_mode": True,
            "search_before_planning": True,
        }
    )
    logger.debug(f"Final workflow state: {result}")
    logger.info("Workflow completed successfully")
    return result

# def run_create_agent_workflow(user_input: str, debug: bool = False):
#     """Run the create agent workflow with the given user input.

#     Args:
#         user_input: The user's query or request
#         debug: If True, enables debug level logging

#     Returns:
#         The final state after the workflow completes
#     """
#     if not user_input:
#         raise ValueError("Input could not be empty")        

#     if debug:
#         enable_debug_logging()

#     logger.info(f"Starting create agent workflow with user input: {user_input}")
#     result = create_agent_graph.invoke(
#         {
#             "messages": [{"role": "user", "content": user_input}],
#         }
#     )
#     logger.debug(f"Final workflow state: {result}")
#     logger.info("Workflow completed successfully")
#     return result   

if __name__ == "__main__":
    print(graph.get_graph().draw_mermaid())
    graph.get_graph().draw_png(output_file_path="workflow.png")
