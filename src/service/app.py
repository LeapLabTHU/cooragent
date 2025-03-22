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
from src.workflow import create_agent_graph
from src.agents import agent_manager
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
    def _create_agents(
            messages: Sequence[Dict[str, str]]
    ) -> List[Agent]:
        # result = create_agent_graph.invoke(
        #     {
        #         "messages": messages,
        #     }
        # )
        tool = Tool(
            name="test_tool",
            description="test",
            inputSchema={'description': 'Input for the Tavily tool.', 'properties': {'query': {'type': 'string'}}, 'required': ['query'], 'title': 'TavilyInput', 'type': 'object'}
        )
        
        agent = Agent(
            agent_name="test_agent",
            agent_id="test_id",
            llm_type=LLMType.BASIC,
            selected_tools=[tool],
            prompt=Prompt(
                name="test_prompt",
                description="test",
                arguments=["query"],
                content="test"
            )
        )
        agents = [agent]
        return agents

    @staticmethod
    def _list_agents(
         request: "listAgentRequest"
    ) -> List[Agent]:
        # return agent_manager.list_agents(request.user_id, request.match)
        tool = Tool(
            name="test_tool",
            description="test",
            inputSchema={'description': 'Input for the Tavily tool.', 'properties': {'query': {'type': 'string'}}, 'required': ['query'], 'title': 'TavilyInput', 'type': 'object'}
        )
        
        agent = Agent(
            agent_name="test_agent",
            agent_id="test_id",
            llm_type=LLMType.BASIC,
            selected_tools=[tool],
            prompt=Prompt(
                name="test_prompt",
                description="test",
                arguments=["query"],
                content="test"
            )
        )
        return [agent]

    @staticmethod
    async def _stream_agents(agents: List[Agent]) -> AsyncGenerator[bytes, None]:
        """将代理列表转换为可流式传输的格式"""
        for agent in agents:
            # 将每个代理对象转换为JSON字符串，并添加换行符
            yield (agent.model_dump_json() + "\n").encode("utf-8")

    def launch(self):
        @self.app.post("/v1/create_agents", status_code=status.HTTP_200_OK)
        async def create_agents(request: AgentRequest):
            messages = self._process_request(request)
            agents = self._create_agents(messages)
            return StreamingResponse(
                self._stream_agents(agents),
                media_type="application/x-ndjson"
            )

        @self.app.post("/v1/list_agents", status_code=status.HTTP_200_OK)
        async def list_agents(request: listAgentRequest):
            agents = self._list_agents(request)
            return StreamingResponse(
                self._stream_agents(agents),
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