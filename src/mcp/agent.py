import asyncio
from typing import AsyncGenerator

from src.mcp.fastagent import FastAgent
from src.mcp import register_mcp
from dotenv import load_dotenv
import os

load_dotenv()

MCPAgent = FastAgent("MCPAgent", config_path=os.getenv("MCP_CONFIG_PATH"))

@register_mcp
@MCPAgent.agent(
    "url_fetcher",
    instruction="Given a URL, provide a complete and comprehensive summary",
    servers=["fetch"],
)

@register_mcp
@MCPAgent.agent(
    "social_media",
    instruction="""
    Write a 280 character social media post for any given text. 
    Respond only with the post, never use hashtags.
    """,
)

@register_mcp
@MCPAgent.chain(
    name="post_writer",
    sequence=["url_fetcher", "social_media"],
)
async def test():
    async with MCPAgent.run() as agent:
        if isinstance(agent, str):
            return agent
        
        result = await agent.url_fetcher.send("https://github.com/evalstate/fast-agent")
        return result


if __name__ == "__main__":
    async def run_test():
        try:
            # 直接等待test()的结果，而不是使用async for
            result = await test()
            return result
        except Exception as e:
            print(f"错误: {e}")
            return str(e)
    
    final_result = asyncio.run(run_test())  
    print(f"最终结果: {final_result}")