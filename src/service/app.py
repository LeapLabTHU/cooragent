import os
from typing import Dict, Generator, List, Sequence, Tuple, AsyncGenerator
import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

load_dotenv()
import logging
from src.interface.agent_types import *
from src.service.workflow_service import run_agent_workflow
from src.agents import agent_manager
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

        response = await run_agent_workflow(session_messages)
        for res in response:
            yield res

    @staticmethod
    async def _list_agents(
         request: "listAgentRequest"
    ) -> List[Agent]:
        try:
            return agent_manager.list_agents(request.user_id, request.match)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    
    @staticmethod
    async def _edit_agent(
        request: "AgentRequest"
    ) -> str:
        try:
            return agent_manager.edit_agent(request.agent)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @staticmethod
    async def _list_default_agents() -> List[Agent]:
        return agent_manager.list_default_agents()
    
    @staticmethod
    async def _list_default_tools() -> List[Tool]:
        return agent_manager.list_default_tools()


    @staticmethod
    async def _stream_agents(agents: List[Agent]) -> AsyncGenerator[bytes, None]:
        """将代理列表转换为可流式传输的格式"""
        for agent in agents:
            # 将每个代理对象转换为JSON字符串，并添加换行符
            yield (agent.model_dump_json() + "\n").encode("utf-8")

    def launch(self):
        @self.app.post("/v1/workflow", status_code=status.HTTP_200_OK)
        async def agent_workflow(request: AgentRequest):
            return StreamingResponse(
                self._run_agent_workflow(request),
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
        async def edit_agent(request: AgentRequest):
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