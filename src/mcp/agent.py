import asyncio

from src.mcp.fastagent import FastAgent
from src.mcp import register_mcp

MCPAgent = FastAgent("MCPAgent")

@register_mcp
@fast.agent(
    "url_fetcher",
    instruction="Given a URL, provide a complete and comprehensive summary",
    servers=["fetch"],
)

@register_mcp
@fast.agent(
    "social_media",
    instruction="""
    Write a 280 character social media post for any given text. 
    Respond only with the post, never use hashtags.
    """,
)

@register_mcp
@fast.chain(
    name="post_writer",
    sequence=["url_fetcher", "social_media"],
)


async def test() -> None:
    async with fast.run() as agent:
        if isinstance(agent, str):
            return agent
        
        result = agent.url_fetcher.send("https://github.com/evalstate/fast-agent")
        return result

if __name__ == "__main__":
    result = asyncio.run(test())  
    print(f"Final result: {result}")