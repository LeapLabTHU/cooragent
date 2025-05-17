import logging
import uuid
import asyncio
from typing import Optional, Dict, Any, AsyncGenerator
from src.workflow import build_graph, agent_factory_graph
from src.manager import agent_manager
from src.interface.agent_types import TaskType
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from src.interface.agent_types import State
from src.service.env import USE_BROWSER

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

console = Console()

def enable_debug_logging():
    """Enable debug level logging for more detailed execution information."""
    logging.getLogger("src").setLevel(logging.DEBUG)


logger = logging.getLogger(__name__)

if USE_BROWSER:
    DEFAULT_TEAM_MEMBERS_DESCRIPTION = """
        - **`researcher`**: Uses search engines and web crawlers to gather information from the internet. Outputs a Markdown report summarizing findings. Researcher can not do math or programming.
        - **`coder`**: Executes Python or Bash commands, performs mathematical calculations, and outputs a Markdown report. Must be used for all mathematical computations.
        - **`browser`**: Directly interacts with web pages, performing complex operations and interactions. You can also leverage `browser` to perform in-domain search, like Facebook, Instagram, Github, etc.
        - **`reporter`**: Write a professional report based on the result of each step.
        - **`agent_factory`**: Create a new agent based on the user's requirement.
        """
else:
    DEFAULT_TEAM_MEMBERS_DESCRIPTION = """
        - **`researcher`**: Uses search engines and web crawlers to gather information from the internet. Outputs a Markdown report summarizing findings. Researcher can not do math or programming.
        - **`coder`**: Executes Python or Bash commands, performs mathematical calculations, and outputs a Markdown report. Must be used for all mathematical computations.
        - **`reporter`**: Write a professional report based on the result of each step.
        - **`agent_factory`**: Create a new agent based on the user's requirement.
        """

TEAM_MEMBERS_DESCRIPTION_TEMPLATE = """
- **`{agent_name}`**: {agent_description}
"""
# Cache for coordinator messages
coordinator_cache = []
MAX_CACHE_SIZE = 2


async def run_agent_workflow(
    user_id: str,
    task_type: str,
    user_input_messages: list,
    debug: bool = False,
    deep_thinking_mode: bool = False,
    search_before_planning: bool = False,
    coor_agents: Optional[list[str]] = None,
):
    """Run the agent workflow with the given user input.

    Args:
        user_input_messages: The user request messages
        debug: If True, enables debug level logging

    Returns:
        The final state after the workflow completes
    """
    if task_type == TaskType.AGENT_FACTORY:
        graph = agent_factory_graph()
    else:
        graph = build_graph()
    if not user_input_messages:
        raise ValueError("Input could not be empty")

    if debug:
        enable_debug_logging()

    logger.info(f"Starting workflow with user input: {user_input_messages}")

    workflow_id = str(uuid.uuid4())


    TEAM_MEMBERS_DESCRIPTION_TEMPLATE = """
    - **`{agent_name}`**: {agent_description}
    """
    TOOLS_DESCRIPTION_TEMPLATE = """
    - **`{tool_name}`**: {tool_description}
    """
    TOOLS_DESCRIPTION = """
    """
    TEAM_MEMBERS_DESCRIPTION = DEFAULT_TEAM_MEMBERS_DESCRIPTION
    TEAM_MEMBERS = ["agent_factory"]
    for agent in agent_manager.available_agents.values():
        if agent.user_id == "share":
            TEAM_MEMBERS.append(agent.agent_name)

        if agent.user_id == user_id or agent.agent_name in coor_agents:
            TEAM_MEMBERS.append(agent.agent_name)

        if agent.user_id != "share":
            MEMBER_DESCRIPTION = TEAM_MEMBERS_DESCRIPTION_TEMPLATE.format(agent_name=agent.agent_name, agent_description=agent.description)
            TEAM_MEMBERS_DESCRIPTION += '\n' + MEMBER_DESCRIPTION

    await agent_manager.load_tools()
    for tool_name, tool in agent_manager.available_tools.items():
        TOOLS_DESCRIPTION += '\n' + TOOLS_DESCRIPTION_TEMPLATE.format(tool_name=tool_name,tool_description=tool.description)

    global coordinator_cache
    coordinator_cache = []
    global is_handoff_case
    is_handoff_case = False

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
            async for event_data in _process_workflow(
                graph,
                {
                    "user_id": user_id,
                    "TEAM_MEMBERS": TEAM_MEMBERS,
                    "TEAM_MEMBERS_DESCRIPTION": TEAM_MEMBERS_DESCRIPTION,
                    "TOOLS": TOOLS_DESCRIPTION,
                    "messages": user_input_messages,
                    "user_original_messages": user_input_messages,
                    "deep_thinking_mode": deep_thinking_mode,
                    "search_before_planning": search_before_planning,
                },
                workflow_id,
            ):
                yield event_data

async def _process_workflow(
    workflow, 
    initial_state: Dict[str, Any], 
    workflow_id: str,
) -> AsyncGenerator[Dict[str, Any], None]:
    """处理自定义工作流的事件流"""
    current_node = None

    yield {
        "event": "start_of_workflow",
        "data": {"workflow_id": workflow_id, "input": initial_state["messages"]},
    }
    
    try:
        current_node = workflow.start_node
        state = State(**initial_state)
    
        
        while current_node != "__end__":
            agent_name = current_node
            logger.info(f"Started node: {agent_name}")
            
            yield {
                "event": "start_of_agent",
                "data": {
                    "agent_name": agent_name,
                    "agent_id": f"{workflow_id}_{agent_name}_1",
                },
            }
            node_func = workflow.nodes[current_node]

            command = await node_func(state)
            
            if hasattr(command, 'update') and command.update:
                for key, value in command.update.items():
                    if key != "messages":
                        state[key] = value
                    
                    if key == "messages" and isinstance(value, list) and value:
                        state["messages"] += value
                        last_message = value[-1]
                        if 'content' in last_message:
                            if agent_name == "coordinator":
                                content = last_message["content"]
                                if content.startswith("handover"):
                                    # mark handoff, do not send maesages
                                    global is_handoff_case
                                    is_handoff_case = True
                                    continue
                            if agent_name in ["planner", "coordinator", "agent_proxy"]:
                                content = last_message["content"]
                                chunk_size = 10  # send 10 words for each chunk
                                for i in range(0, len(content), chunk_size):
                                    chunk = content[i:i+chunk_size]
                                    if 'processing_agent_name' in state:
                                        agent_name = state['processing_agent_name']
                    
                                    yield {
                                        "event": "messages",
                                        "agent_name": agent_name,
                                        "data": {
                                            "message_id": f"{workflow_id}_{agent_name}_msg_{i}",
                                            "delta": {"content": chunk},
                                        },
                                    }
                                    await asyncio.sleep(0.01)

                    if agent_name == "agent_factory" and key == "new_agent_name":
                        yield {
                            "event": "new_agent_created",
                            "agent_name": value,
                            "data": {
                                "new_agent_name": value,
                                "agent_obj": agent_manager.available_agents[value],
                            },
                        }
                                                
                            

            yield {
                "event": "end_of_agent",
                "data": {
                    "agent_name": agent_name,
                    "agent_id": f"{workflow_id}_{agent_name}_1",
                },
            }
            
            next_node = command.goto            
            current_node = next_node
            
        yield {
            "event": "end_of_workflow",
            "data": {
                "workflow_id": workflow_id,
                "messages": [
                    {"role": "user", "content": "workflow completed"}
                ],
            },
        }
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"Error in Agent workflow: {str(e)}")
        yield {
            "event": "error",
            "data": {
                "workflow_id": workflow_id,
                "error": str(e),
            },
        }



