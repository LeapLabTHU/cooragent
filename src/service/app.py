import os
from typing import Dict, List, AsyncGenerator
import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
import json

load_dotenv()
import logging
from src.interface.agent_types import *
from src.workflow.process import run_agent_workflow
from src.manager import agent_manager 
from src.manager.agents import NotFoundAgentError
from src.service.session import UserSession
from src.interface.agent_types import RemoveAgentRequest
from src.utils.path_utils import get_project_root

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class Server:
    def __init__(self, host="0.0.0.0", port="8001") -> None:
        self.app = FastAPI()
        self.app.add_middleware(
            CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
        )
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
             raise HTTPException(status_code=503, detail="Service not ready, AgentManager not initialized.")

        session = UserSession(request.user_id)
        for message in request.messages:
            session.add_message(message.role, message.content)
        session_messages = session.history[-3:]

        response_stream = run_agent_workflow(
            request.user_id,
            request.task_type,
            session_messages,
            request.debug,
            request.deep_thinking_mode,
            request.search_before_planning,
            request.coor_agents
        )

        async for res in response_stream:
            try:
                event_type = res.get("event")
                # Handle new_agent_created event (agent_obj is already an Agent instance)
                if event_type == "new_agent_created" and "data" in res and "agent_obj" in res["data"]:
                    agent_obj = res["data"]["agent_obj"]
                    # Serialize the Agent object to JSON string if needed by client
                    agent_json = agent_obj.model_dump_json(indent=2) if agent_obj else None
                    if agent_json:
                        res["data"]["agent_obj"] = agent_json # Replace object with JSON string
                    else:
                        # Handle case where agent object is missing or serialization fails
                        logger.warning("Could not serialize agent object for new_agent_created event.")
                        # Optionally remove the agent_obj key or the entire event
                        if "agent_obj" in res["data"]: del res["data"]["agent_obj"]

                # This yield should be outside the if/else block for serialization
                yield res
            except (TypeError, ValueError, json.JSONDecodeError) as e:
                from traceback import print_stack
                print_stack()
                logging.error(f"Error serializing event: {e}", exc_info=True)
                
    @staticmethod
    async def _list_agents(
         request: "listAgentRequest"
    ) -> AsyncGenerator[str, None]:
        if agent_manager is None:
             raise HTTPException(status_code=503, detail="Service not ready, AgentManager not initialized.")
        try:
            agents = await agent_manager._list_agents(request.user_id, request.match)
            for agent in agents:
                yield agent.model_dump_json() + "\n"
        except Exception as e:
            logger.error(f"Error listing agents: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def _list_default_agents() -> AsyncGenerator[str, None]:
        if agent_manager is None:
             raise HTTPException(status_code=503, detail="Service not ready, AgentManager not initialized.")
        try:
            agents = await agent_manager._list_default_agents()
            for agent in agents:
                yield agent.model_dump_json() + "\n"
        except Exception as e:
            logger.error(f"Error listing default agents: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def _list_default_tools() -> AsyncGenerator[str, None]:
        if agent_manager is None:
             raise HTTPException(status_code=503, detail="Service not ready, AgentManager not initialized.")
        try:
            tools = await agent_manager._list_default_tools()
            for tool in tools:
                yield tool.model_dump_json() + "\n"
        except Exception as e:
            logger.error(f"Error listing default tools: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def _edit_agent(
        request: "Agent"
    ) -> AsyncGenerator[str, None]:
        if agent_manager is None:
             raise HTTPException(status_code=503, detail="Service not ready, AgentManager not initialized.")
        try:
            result = await agent_manager._edit_agent(request)
            yield json.dumps({"result": result}) + "\n"
        except NotFoundAgentError as e:
            logger.warning(f"Edit agent failed: {e}")
            yield json.dumps({"result": "agent not found", "error": str(e)}) + "\n"
        except Exception as e:
            logger.error(f"Error editing agent {request.agent_name}: {e}", exc_info=True)
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

    def launch(self):
        @self.app.post("/v1/workflow", status_code=status.HTTP_200_OK)
        async def agent_workflow_endpoint(request: AgentRequest):
            return StreamingResponse(
                self._run_agent_workflow(request),
                media_type="application/x-ndjson"
            )

        @self.app.post("/v1/list_agents", status_code=status.HTTP_200_OK)
        async def list_agents_endpoint(request: listAgentRequest):
            return StreamingResponse(
                self._list_agents(request),
                media_type="application/x-ndjson"
            )

        @self.app.get("/v1/list_default_agents", status_code=status.HTTP_200_OK)
        async def list_default_agents_endpoint():
            return StreamingResponse(
                self._list_default_agents(),
                media_type="application/x-ndjson"
            )
        
        @self.app.get("/v1/list_default_tools", status_code=status.HTTP_200_OK)
        async def list_default_tools_endpoint():
            return StreamingResponse(
                self._list_default_tools(),
                media_type="application/x-ndjson"
            )
        
        @self.app.post("/v1/edit_agent", status_code=status.HTTP_200_OK)
        async def edit_agent_endpoint(request: Agent):
            return StreamingResponse(
                self._edit_agent(request),
                media_type="application/x-ndjson"
            )
        
        @self.app.post("/v1/remove_agent", status_code=status.HTTP_200_OK)
        async def remove_agent_endpoint(request: RemoveAgentRequest):
            return StreamingResponse(
                self._remove_agent(request),
                media_type="application/x-ndjson"
            )
        
        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            workers=1
        )


def parse_arguments():
    import argparse
    parser = argparse.ArgumentParser(description="Agent Server API")
    parser.add_argument("--host", default="0.0.0.0", type=str, help="Service host")
    parser.add_argument("--port", default=8001, type=int, help="Service port")
    
    return parser.parse_args()


if __name__ == "__main__":

    args = parse_arguments()

    server = Server(host=args.host, port=args.port)
    server.launch()
