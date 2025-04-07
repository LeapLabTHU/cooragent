import logging
from typing import Optional, Dict, Any, AsyncGenerator
import asyncio  # 添加这一行
from src.workflow import build_graph, agent_factory_graph
from langchain_community.adapters.openai import convert_message_to_dict
from src.manager import agent_manager
from src.interface.agent_types import TaskType
import uuid
import json
from rich.syntax import Syntax
from rich.console import Console

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Default level is INFO
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

    json_buffer = []
    current_json_size = 0
    MAX_JSON_BUFFER_SIZE = 1024 * 1024  # 1MB限制

    # 检查是否使用自定义工作流
    is_custom_workflow = hasattr(graph, 'invoke') and not hasattr(graph, 'astream_events')
    
    if is_custom_workflow:
        # 使用自定义工作流的事件流处理
        async for event_data in _process_custom_workflow(
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
    else:
        # 原有的 langchain 工作流处理逻辑
        async for event in graph.astream_events(
            {
                "user_id": user_id,
                # Constants
                "TEAM_MEMBERS": TEAM_MEMBERS,
                "TEAM_MEMBERS_DESCRIPTION": TEAM_MEMBERS_DESCRIPTION,
                "messages": user_input_messages,
                "deep_thinking_mode": deep_thinking_mode,
                "search_before_planning": search_before_planning,
            },
            version="v2",
        ):
            kind = event.get("event")
            data = event.get("data")
            name = event.get("name")
            metadata = event.get("metadata")
            node = (
                ""
                if (metadata.get("checkpoint_ns") is None)
                else metadata.get("checkpoint_ns").split(":")[0]
            )
            langgraph_step = (
                ""
                if (metadata.get("langgraph_step") is None)
                else str(metadata["langgraph_step"])
            )
            run_id = "" if (event.get("run_id") is None) else str(event["run_id"])

            if kind == "on_chain_start" and name in streaming_llm_agents:
                if name == "planner":
                    yield {
                        "event": "start_of_workflow",
                        "data": {"workflow_id": workflow_id, "input": user_input_messages},
                    }
                print(f"started chain name: {name}")
                ydata = {
                    "event": "start_of_agent",
                    "data": {
                        "agent_name": name,
                        "agent_id": f"{workflow_id}_{name}_{langgraph_step}",
                    },
                }
            elif kind == "on_chain_end" and name in streaming_llm_agents:
                print(f"ended chain name: {name}")
                ydata = {
                    "event": "end_of_agent",
                    "data": {
                        "agent_name": name,
                        "agent_id": f"{workflow_id}_{name}_{langgraph_step}",
                    },
                }
            elif kind == "on_chat_model_start" and node in streaming_llm_agents:
                ydata = {
                    "event": "start_of_llm",
                    "data": {"agent_name": node},
                }
            elif kind == "on_chat_model_end" and node in streaming_llm_agents:
                ydata = {
                    "event": "end_of_llm",
                    "data": {"agent_name": node},
                }
            elif kind == "on_chat_model_stream" and node in streaming_llm_agents:
                content = data["chunk"].content
                if content is None or content == "":
                    if not data["chunk"].additional_kwargs.get("reasoning_content"):
                        # Skip empty messages
                        continue
                    ydata = {
                        "event": "message",
                        "data": {
                            "message_id": data["chunk"].id,
                            "delta": {
                                "reasoning_content": (
                                    data["chunk"].additional_kwargs["reasoning_content"]
                                )
                            },
                        },
                    }
                else:
                    # Check if the message is from the coordinator
                    if node == "coordinator":
                        if len(coordinator_cache) < MAX_CACHE_SIZE:
                            coordinator_cache.append(content)
                            cached_content = "".join(coordinator_cache)
                            if cached_content.startswith("handoff"):
                                is_handoff_case = True
                                continue
                            if len(coordinator_cache) < MAX_CACHE_SIZE:
                                continue
                            # Send the cached message
                            ydata = {
                                "event": "message",
                                "node": node,
                                "data": {
                                    "message_id": data["chunk"].id,
                                    "delta": {"content": cached_content},
                                },
                            }
                        elif not is_handoff_case:
                            # For other agents, send the message directly
                            ydata = {
                                "node": node,
                                "event": "message",
                                "data": {
                                    "message_id": data["chunk"].id,
                                    "delta": {"content": content},
                                },
                            }
                        else:
                            # For other agents, send the message directly
                            ydata = {
                                "node": node,
                                "event": "message",
                                "data": {
                                    "message_id": data["chunk"].id,
                                    "delta": {"content": content},
                                },
                            }
                    
            elif kind == "on_tool_start" and node in TEAM_MEMBERS:
                ydata = {
                    "event": "tool_call",
                    "data": {
                        "tool_call_id": f"{workflow_id}_{node}_{name}_{run_id}",
                        "tool_name": name,
                        "tool_input": data.get("input"),
                    },
                }
            elif kind == "on_tool_end" and node in TEAM_MEMBERS:
                ydata = {
                    "event": "tool_call_result",
                    "data": {
                        "tool_call_id": f"{workflow_id}_{node}_{name}_{run_id}",
                        "tool_name": name,
                        "tool_result": data["output"].content if data.get("output") else "",
                    },
                }
            else:
                continue

            if kind in ("end_of_agent", "end_of_workflow"):
                if json_buffer:
                    try:
                        parsed_json = json.loads(''.join(json_buffer))
                        formatted_json = json.dumps(parsed_json, indent=2, ensure_ascii=False)
                        console.print("\n")
                        syntax = Syntax(formatted_json, "json", theme="monokai", line_numbers=False)
                        console.print(syntax)
                    except:
                        console.print(f"\n[danger]不完整的JSON内容: {''.join(json_buffer)}[/danger]")
                    finally:
                        json_buffer = []
                        current_json_size = 0

            yield ydata

        if is_handoff_case:
            yield {
                "event": "end_of_workflow",
                "data": {
                    "workflow_id": workflow_id,
                    "messages": [
                        convert_message_to_dict(msg)
                        for msg in data["output"].get("messages", [])
                    ],
                },
            }


async def _process_custom_workflow(
    workflow, 
    initial_state: Dict[str, Any], 
    workflow_id: str,
    streaming_llm_agents: list
) -> AsyncGenerator[Dict[str, Any], None]:
    """处理自定义工作流的事件流"""
    # 创建事件监听器
    current_node = None
    
    # 模拟事件流
    # 首先发送工作流开始事件
    yield {
        "event": "start_of_workflow",
        "data": {"workflow_id": workflow_id, "input": initial_state["messages"]},
    }
    
    # 执行工作流
    try:
        # 设置当前节点为起始节点
        current_node = workflow.start_node
        state = initial_state.copy()
        
        # 添加next字段，确保与原有工作流兼容
        if "next" not in state:
            state["next"] = current_node
        
        while current_node != "__end__":
            # 发送节点开始事件
            agent_name = current_node
            logger.info(f"Started node: {agent_name}")
            
            # 发送代理开始事件
            yield {
                "event": "start_of_agent",
                "data": {
                    "agent_name": agent_name,
                    "agent_id": f"{workflow_id}_{agent_name}_1",
                },
            }
            
            # 发送LLM开始事件
            yield {
                "event": "start_of_llm",
                "data": {"agent_name": agent_name},
            }
            
            # 执行节点
            node_func = workflow.nodes[current_node]
            command = node_func(state)
            
            # 更新状态
            if hasattr(command, 'update') and command.update:
                for key, value in command.update.items():
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
                            
                            # 分块发送消息，模拟流式输出
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
            
            # 更新next字段，确保与原有工作流兼容
            if "next" in state and next_node != "__end__":
                state["next"] = next_node
                
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



