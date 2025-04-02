# Create server parameters for stdio connection
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
import asyncio

import os

# 获取当前工作目录
current_path = os.getcwd()
# 获取当前路径的父路径
parent_path = os.path.dirname(current_path)

model = ChatOpenAI(model='deepseek-chat',
            base_url='https://api.deepseek.com/v1',
            api_key='sk-fe4891f5e92642d9b2af32b3761f3f0c',)
server_params = StdioServerParameters(
    command="python",
    # Make sure to update to the full absolute path to your math_server.py file
    args=[current_path + "/excel_mcp/server.py"],
)

async def run_agent():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()
            # Get tools
            tools = await load_mcp_tools(session)
            # Create and run the agent
            agent = create_react_agent(model, tools)
            agent_response = await agent.ainvoke({"messages": "创建一个excel文件"})
            return agent_response
# Run the async function
if __name__ == "__main__":
    result = asyncio.run(run_agent())
    print(result)