import os
from typing import Dict, Generator, List, Sequence, Tuple, AsyncGenerator
import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
import json

load_dotenv()
import logging
from src.interface.agent_types import *
from src.service.workflow_service import run_agent_workflow
from src.manager import agent_manager
from src.manager.agents import NotFoundAgentError
from src.service.session import UserSession


logging.basicConfig(filename='app.log', level=logging.INFO)


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
        session = UserSession(request.user_id)
        for message in request.messages:
            session.add_message(message.role, message.content)
        session_messages = session.history[-3:]

        response = run_agent_workflow(
            request.user_id,
            request.task_type,
            session_messages,
            request.debug,
            request.deep_thinking_mode,
            request.search_before_planning,
            request.coor_agents
        )
        async for res in response:
            yield res

    @staticmethod
    async def _list_agents(
         request: "listAgentRequest"
    ) -> AsyncGenerator[str, None]:
        try:
            agents = agent_manager._list_agents(request.user_id, request.match)
            for agent in agents:
                yield agent.model_dump_json() + "\n"
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def _list_default_agents() -> AsyncGenerator[str, None]:
        agents = agent_manager._list_default_agents()
        for agent in agents:
            yield agent.model_dump_json() + "\n"
    
    @staticmethod
    async def _list_default_tools() -> AsyncGenerator[str, None]:
        tools = agent_manager._list_default_tools()
        for tool in tools:
            yield tool.model_dump_json() + "\n"

    @staticmethod
    async def _edit_agent(
        request: "Agent"
    ) -> AsyncGenerator[str, None]:
        try:
            result = agent_manager._edit_agent(request)
            yield json.dumps({"result": result}) + "\n"
        except NotFoundAgentError as e:
            yield json.dumps({"result": "agent not found"}) + "\n"
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def launch(self):
        @self.app.post("/v1/workflow", status_code=status.HTTP_200_OK)
        async def agent_workflow(request: AgentRequest):
            async def response_generator():
                async for chunk in self._run_agent_workflow(request):
                    yield json.dumps(chunk) + "\n"
                    
            return StreamingResponse(
                response_generator(),
                media_type="application/x-ndjson"
            )

        @self.app.post("/v1/list_agents", status_code=status.HTTP_200_OK)
        async def list_agents(request: listAgentRequest):
            return StreamingResponse(
                self._list_agents(request),
                media_type="application/x-ndjson"
            )

        @self.app.get("/v1/list_default_agents", status_code=status.HTTP_200_OK)
        async def list_default_agents():
            return StreamingResponse(
                self._list_default_agents(),
                media_type="application/x-ndjson"
            )
        
        @self.app.get("/v1/list_default_tools", status_code=status.HTTP_200_OK)
        async def list_default_tools():
            return StreamingResponse(
                self._list_default_tools(),
                media_type="application/x-ndjson"
            )
        
        @self.app.post("/v1/edit_agent", status_code=status.HTTP_200_OK)
        async def edit_agent(request: Agent):
            return StreamingResponse(
                self._edit_agent(request),
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