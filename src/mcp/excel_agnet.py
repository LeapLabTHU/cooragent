import asyncio
import os

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from beeai_framework.adapters.openai.backend.chat import OpenAIChatModel
from beeai_framework.agents.react import ReActAgent
from beeai_framework.memory import UnconstrainedMemory
from beeai_framework.tools.mcp_tools import MCPTool
from src.mcp.register import MCPManager
load_dotenv()

current_path = os.getcwd()
parent_path = os.path.dirname(current_path)

# Create server parameters for stdio connection
server_params = StdioServerParameters(
    command="python",
    args=[current_path + '/excel_mcp/__main__.py'],
    env={
        "EXCEL_FILES_PATH": parent_path+'/excel_files/'
    },
)


async def slack_tool() -> MCPTool:
    async with stdio_client(server_params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        # Discover Slack tools via MCP client
        slacktools = await MCPTool.from_client(session)
        filter_tool = filter(lambda tool: tool.name == "excel_tools", slacktools)
        slack = list(filter_tool)
        return slack[0]

print("xxxx")
agent = ReActAgent(llm=OpenAIChatModel("deepseek-chat",{"base_url":'https://api.deepseek.com/v1',"api_key":'sk-fe4891f5e92642d9b2af32b3761f3f0c'}), tools=[asyncio.run(slack_tool())], memory=UnconstrainedMemory())
MCPManager.register_agent("mcp_react_agent", agent)
# a = agent.run(prompt="创建一个excel文件")
# for i in a:
#     print(i)
