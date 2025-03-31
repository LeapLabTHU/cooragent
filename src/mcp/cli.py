import asyncio
from mcp_agent.core.fastagent import FastAgent

from dotenv import load_dotenv
import os

load_dotenv()

fast = FastAgent("MCPAgent", config_path=os.getenv("MCP_CONFIG_PATH"))

# Define the agent
@fast.agent(instruction="You are a helpful AI Agent", servers=["fetch"])
async def main():
    # use the --model command line switch or agent arguments to change model
    async with fast.run() as agent:
        await agent()


if __name__ == "__main__":
    asyncio.run(main())
