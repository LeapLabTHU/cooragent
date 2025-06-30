from typing import Dict, List, AsyncGenerator, Optional
from dotenv import load_dotenv
import json

load_dotenv()
import logging
from src.interface.agent import *
from src.workflow.process import run_agent_workflow
from src.manager import agent_manager 
from src.manager.agents import NotFoundAgentError
from src.service.session import SessionManager
from src.interface.agent import RemoveAgentRequest
from src.interface.workflow import WorkflowRequest
from fastapi.responses import FileResponse
from src.service.tool_tracker import tool_tracker
from src.tools.websocket_manager import websocket_manager
from src.workflow.cache import workflow_cache


logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)
session_manager = SessionManager()

class Server:
    def __init__(self, host="0.0.0.0", port=8001) -> None:
        self.host = host
        self.port = port

    def _process_request(self, request: "AgentRequest") -> List[Dict[str, str]]:
        return [{"role": message.role, "content": message.content} for message in request.messages]

    @staticmethod
    async def _run_agent_workflow(
            request: "AgentRequest"
    ) -> AsyncGenerator[str, None]:
        if agent_manager is None:
             logger.error("Agent workflow called before AgentManager was initialized.")

        session = session_manager.get_session(request.user_id)
        for message in request.messages:
            session.add_message(message.role, message.content)
        session_messages = session.history[-3:]

        response_stream = run_agent_workflow(
            user_id=request.user_id,
            task_type=request.task_type,
            user_input_messages=session_messages,
            debug=request.debug,
            deep_thinking_mode=request.deep_thinking_mode,
            search_before_planning=request.search_before_planning,
            coor_agents=request.coor_agents,
            workmode=request.workmode,
            workflow_id=request.workflow_id,
        )
        async for res in response_stream:
            try:
                event_type = res.get("event")
                # replace agent_obj with agent_json 
                if event_type == "new_agent_created" and "data" in res and "agent_obj" in res["data"]:
                    agent_obj: BaseModel = res["data"]["agent_obj"]
                    agent_json = agent_obj.model_dump_json(indent=2) if agent_obj else None
                    if agent_json:
                        res["data"]["agent_obj"] = agent_json
                    else:
                        logger.warning("Could not serialize agent object for new_agent_created event.")
                        if "agent_obj" in res["data"]: del res["data"]["agent_obj"]
                yield res
            except (TypeError, ValueError, json.JSONDecodeError) as e:
                logging.error(f"Error serializing event: {e}", exc_info=True)
                
    @staticmethod
    async def _list_agents(
         request: "listAgentRequest"
    ) -> AsyncGenerator[str, None]:
        if agent_manager is None:
             logger.error("Agent workflow called before AgentManager was initialized.")
             raise Exception("Agent workflow called before AgentManager was initialized.")
        try:
            agents = await agent_manager._list_agents(request.user_id, request.match)
            for agent in agents:
                yield agent.model_dump_json() + "\n"
        except Exception as e:
            logger.error(f"Error listing agents: {e}", exc_info=True)
            raise Exception(f"Error listing agents: {e}")

    @staticmethod
    async def _list_agents_json(user_id: str, match: Optional[str] = None):
        try:
            agents = await agent_manager._list_agents(user_id, match)
            return [agent.model_dump() for agent in agents]
        except Exception as e:
            raise Exception(f"Error listing agents: {e}")

    @staticmethod
    async def _workflow_draft(user_id: str, match: str):
        try:
            workflows = workflow_cache.list_workflows(user_id, match)
            return workflows[0]
        except Exception as e:
            raise Exception(f"Error listing workflows: {e}")
        
    @staticmethod
    async def _list_workflow_json(user_id: str, match: Optional[str] = None):
        try:
            workflows = workflow_cache.list_workflows(user_id, match)
            default_workflows = workflow_cache.list_workflows('share')
            workflows.extend(default_workflows)
            workflowJsons = []
            for workflow in workflows:
                workflowJsons.append({
                    "workflow_id": workflow["workflow_id"],
                    "version": workflow["version"],
                    "lap": workflow["lap"],
                    "user_input_messages": workflow["user_input_messages"],
                    "deep_thinking_mode": workflow["deep_thinking_mode"],
                    "search_before_planning": workflow["search_before_planning"]
                })
            return [workflowJson for workflowJson in workflowJsons]
        except Exception as e:
            raise Exception(f"Error listing workflows: {e}")
        
    @staticmethod
    def _list_workflow(
         request: "listAgentRequest"
    ) -> AsyncGenerator[str, None]:
        if workflow_cache is None:
             logger.error("Workflow cache not initialized.")
             raise Exception("Workflow cache not initialized.")
        try:
            workflows = workflow_cache.list_workflows(request.user_id, request.match)
            return workflows
        except Exception as e:
            logger.error(f"Error listing workflows: {e}", exc_info=True)
            raise Exception(f"Error listing workflows: {e}")

    @staticmethod
    async def _list_user_all_agents(user_id: str):
        try:
            agents = agent_manager._list_user_all_agents(user_id)
            return [agent.model_dump() for agent in agents]
        except Exception as e:
            raise Exception(f"Error listing user all agents: {e}")
        
    @staticmethod
    async def _list_default_agents_json():
        try:
            agents = agent_manager._list_default_agents()
            return [agent.model_dump() for agent in agents]
        except Exception as e:
            raise Exception(f"Error listing default agents: {e}")
        
    @staticmethod
    async def _edit_workflow(user_id: str, workflow):
        try:
            nodes = workflow["nodes"]
            for _, node in nodes.items():
                if node["component_type"] == "agent" and node["config"]["type"] == "execution_agent":
                    if "add" in node and node["add"] == "1":
                        agent_name = node["name"]
                        agents = agent_manager._list_user_all_agents(user_id)
                        for agent in agents:
                            if agent["agent_name"] == node["name"]:
                                from datetime import datetime
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                agent_name = f"{node['name']}_{timestamp}"
                                break
                        _tools = []
                        for tool in node["config"]["tools"]:
                            _tools.append(Tool(
                                name=tool["config"]["name"],
                                description=tool["config"]["description"],
                            ))
                        agent = Agent(
                            user_id=user_id,
                            agent_name=agent_name,
                            nick_name=node["label"],
                            description=node["config"]["description"],
                            llm_type=node["config"]["llm_type"],
                            selected_tools=_tools,
                            prompt=node["config"]["prompt"]
                        )
                        agent_manager._save_agent(agent, flush=True)
                        for graph in workflow["graph"]:
                            if graph["component_type"] == "agent" and graph["config"]["node_type"] == "execution_agent":
                                if graph["name"] == node["name"]:
                                    graph["name"] = agent_name
                                    break
                        workflow_cache.save_workflow(user_id, workflow)
                    else:
                        _tools = []
                        for tool in node["config"]["tools"]:
                            _tools.append(Tool(
                                name=tool["config"]["name"],
                                description=tool["config"]["description"],
                            ))
                        agent = Agent(
                            user_id=user_id,
                            agent_name=node["name"],
                            nick_name=node["label"],
                            description=node["config"]["description"],
                            llm_type=node["config"]["llm_type"],
                            selected_tools=_tools,
                            prompt=node["config"]["prompt"]
                        )
                        agent_manager._edit_agent(agent)
                        workflow_cache.save_workflow(user_id, workflow)
            return workflow
        except Exception as e:
            raise Exception(f"Error editing workflow: {e}")

    @staticmethod
    async def _list_default_agents() -> AsyncGenerator[str, None]:
        if agent_manager is None:
             logger.error("Agent workflow called before AgentManager was initialized.")
             raise Exception("Agent workflow called before AgentManager was initialized.")
        try:
            agents = await agent_manager._list_default_agents()
            for agent in agents:
                yield agent.model_dump_json() + "\n"
        except Exception as e:
            logger.error(f"Error listing default agents: {e}", exc_info=True)
            raise Exception(f"Error listing default agents: {e}")

    @staticmethod
    async def _list_default_tools() -> AsyncGenerator[str, None]:
        if agent_manager is None:
             logger.error("Agent workflow called before AgentManager was initialized.")
             raise Exception("Agent workflow called before AgentManager was initialized.")
        try:
            tools = await agent_manager._list_default_tools()
            for tool in tools:
                yield tool.model_dump_json() + "\n"
        except Exception as e:
            logger.error(f"Error listing default tools: {e}", exc_info=True)
            raise Exception(f"Error listing default tools: {e}")

    @staticmethod
    async def _edit_agent(
        request: "Agent"
    ) -> AsyncGenerator[str, None]:
        if agent_manager is None:
             logger.error("Agent workflow called before AgentManager was initialized.")
             raise Exception("Agent workflow called before AgentManager was initialized.")
        try:
            result = agent_manager._edit_agent(request)
            yield json.dumps({"result": result}) + "\n"
        except NotFoundAgentError as e:
            logger.warning(f"Edit agent failed: {e}")
            yield json.dumps({"result": "agent not found", "error": str(e)}) + "\n"
        except Exception as e:
            logger.error(f"Error editing agent {request.agent_name}: {e}", exc_info=True)
            yield json.dumps({"result": "error", "error": str(e)}) + "\n"

    @staticmethod
    async def _edit_planning_steps(
        request: "EditStepsRequest"
    ) -> AsyncGenerator[str, None]:
        if agent_manager is None:
             logger.error("Agent workflow called before AgentManager was initialized.")
             raise Exception("Agent workflow called before AgentManager was initialized.")
        try:
            workflow_cache.save_planning_steps(request.workflow_id,request.planning_steps)
            yield json.dumps({"result": "success"}) + "\n"
        except Exception as e:
            logger.error(f"Error editing planning steps : {e}", exc_info=True)
            yield json.dumps({"result": "error", "error": str(e)}) + "\n"

    @staticmethod
    async def _remove_agent(request: RemoveAgentRequest) -> AsyncGenerator[str, None]:
        if agent_manager is None:
             yield json.dumps({"result": "error", "message": "Service not ready, AgentManager not initialized."}) + "\n"
             return
        try:
            await agent_manager._remove_agent(request.agent_name)
            yield json.dumps({"result": "success", "message": f"Agent '{request.agent_name}' deleted successfully."}) + "\n"
        except Exception as e:
            logger.error(f"Error removing agent {request.agent_name}: {e}", exc_info=True)
            yield json.dumps({"result": "error", "message": f"Error removing Agent '{request.agent_name}': {str(e)}"}) + "\n"
