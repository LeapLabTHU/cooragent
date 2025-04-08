import logging
from typing import Optional, Dict, Any, AsyncGenerator
import asyncio
from src.workflow import build_graph, agent_factory_graph
from langchain_community.adapters.openai import convert_message_to_dict
from src.manager import agent_manager
from src.interface.agent_types import TaskType
import uuid
import json
from rich.syntax import Syntax
from rich.console import Console

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

console = Console()

def enable_debug_logging():
    """Enable debug level logging for more detailed execution information."""
    logging.getLogger("src").setLevel(logging.DEBUG)


logger = logging.getLogger(__name__)


DEFAULT_TEAM_MEMBERS_DESCRIPTION = """
- **`researcher`**: Uses search engines and web crawlers to gather information from the internet. Outputs a Markdown report summarizing findings. Researcher can not do math or programming.
- **`coder`**: Executes Python or Bash commands, performs mathematical calculations, and outputs a Markdown report. Must be used for all mathematical computations.
- **`browser`**: Directly interacts with web pages, performing complex operations and interactions. You can also leverage `browser` to perform in-domain search, like Facebook, Instagram, Github, etc.
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

    DEFAULT_TEAM_MEMBERS_DESCRIPTION = """
    - **`researcher`**: Uses search engines and web crawlers to gather information from the internet. Outputs a Markdown report summarizing findings. Researcher can not do math or programming.
    - **`coder`**: Executes Python or Bash commands, performs mathematical calculations, and outputs a Markdown report. Must be used for all mathematical computations.
    - **`browser`**: Directly interacts with web pages, performing complex operations and interactions. You can also leverage `browser` to perform in-domain search, like Facebook, Instagram, Github, etc.
    - **`reporter`**: Write a professional report based on the result of each step.Please note that this agent is unable to perform any code or command-line operations.
    - **`agent_factory`**: Create a new agent based on the user's requirement.
    """

    TEAM_MEMBERS_DESCRIPTION_TEMPLATE = """
    - **`{agent_name}`**: {agent_description}
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
    streaming_llm_agents = [*TEAM_MEMBERS, "agent_factory", "coordinator", "planner", "publisher"]

    global coordinator_cache
    coordinator_cache = []
    global is_handoff_case
    is_handoff_case = False

    async for event_data in _process_workflow(
        graph,
        {
            "user_id": user_id,
            "TEAM_MEMBERS": TEAM_MEMBERS,
            "TEAM_MEMBERS_DESCRIPTION": TEAM_MEMBERS_DESCRIPTION,
            "messages": user_input_messages,
            "deep_thinking_mode": deep_thinking_mode,
            "search_before_planning": search_before_planning,
        },
        workflow_id,
        streaming_llm_agents,
    ):
        yield event_data

async def _process_workflow(
    workflow, 
    initial_state: Dict[str, Any], 
    workflow_id: str,
    streaming_llm_agents: list
) -> AsyncGenerator[Dict[str, Any], None]:
    """处理自定义工作流的事件流"""
    current_node = None

    yield {
        "event": "start_of_workflow",
        "data": {"workflow_id": workflow_id, "input": initial_state["messages"]},
    }
    
    try:
        current_node = workflow.start_node
        state = initial_state.copy()
        
        # 添加next字段，确保与原有工作流兼容
        if "next" not in state:
            state["next"] = current_node
        
        while current_node != "__end__":
            # 发送节点开始事件
            agent_name = current_node
            logger.info(f"Started node: {agent_name}")
            
            yield {
                "event": "start_of_agent",
                "data": {
                    "agent_name": agent_name,
                    "agent_id": f"{workflow_id}_{agent_name}_1",
                },
            }
            
            yield {
                "event": "start_of_llm",
                "data": {"agent_name": agent_name},
            }
            
            node_func = workflow.nodes[current_node]
            command = node_func(state)
            
            if hasattr(command, 'update') and command.update:
                for key, value in command.update.items():
                    print(f"update {key} to {value}")
                    state[key] = value
                    
                    # 如果更新了消息，发送消息事件
                    if key == "messages" and isinstance(value, list) and value:
                        last_message = value[-1]
                        if hasattr(last_message, 'content') and last_message.content:
                            # 处理coordinator节点的特殊情况
                            if agent_name == "coordinator":
                                # 检查是否是handoff情况
                                content = last_message.content
                                if content.startswith("handoff"):
                                    # 标记为handoff情况，不发送消息
                                    global is_handoff_case
                                    is_handoff_case = True
                                    continue
                            
                            content = last_message.content
                            chunk_size = 10  # 每次发送10个字符
                            for i in range(0, len(content), chunk_size):
                                chunk = content[i:i+chunk_size]
                                yield {
                                    "event": "message",
                                    "node": agent_name,
                                    "data": {
                                        "message_id": f"{workflow_id}_{agent_name}_msg_{i}",
                                        "delta": {"content": chunk},
                                    },
                                }
                                # 添加小延迟以模拟流式效果
                                await asyncio.sleep(0.01)
            
            # 发送LLM结束事件
            yield {
                "event": "end_of_llm",
                "data": {"agent_name": agent_name},
            }
            
            # 发送代理结束事件
            yield {
                "event": "end_of_agent",
                "data": {
                    "agent_name": agent_name,
                    "agent_id": f"{workflow_id}_{agent_name}_1",
                },
            }
            
            # 获取下一个节点
            next_node = command.goto
            
            current_node = next_node
            
        # 工作流结束事件
        yield {
            "event": "end_of_workflow",
            "data": {
                "workflow_id": workflow_id,
                "messages": [
                    convert_message_to_dict(msg) if hasattr(msg, 'to_dict') else msg
                    for msg in state.get("messages", [])
                ],
            },
        }
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"Error in custom workflow: {str(e)}")
        # 发送错误事件
        yield {
            "event": "error",
            "data": {
                "workflow_id": workflow_id,
                "error": str(e),
            },
        }



