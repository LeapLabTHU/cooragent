import asyncio

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
async def test() -> None:
    async with MCPAgent.run() as agent:
        if isinstance(agent, str):
            return agent
        
        await agent.url_fetcher.send("https://github.com/evalstate/fast-agent")


if __name__ == "__main__":
    result = asyncio.run(test())  
    print(f"Final result: {result}")