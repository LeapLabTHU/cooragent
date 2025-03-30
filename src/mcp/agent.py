import asyncio

from src.mcp.fastagent import FastAgent

fast = FastAgent("MCPAgent")

@fast.agent(
    "url_fetcher",
    instruction="Given a URL, provide a complete and comprehensive summary",
    servers=["fetch"],
)
@fast.agent(
    "social_media",
    instruction="""
    Write a 280 character social media post for any given text. 
    Respond only with the post, never use hashtags.
    """,
)
@fast.chain(
    name="post_writer",
    sequence=["url_fetcher", "social_media"],
)
async def main() -> None:
    async with fast.run() as agent:
        if isinstance(agent, str):
            return agent
        
        result = agent.url_fetcher.send("https://github.com/evalstate/fast-agent")
        return result

if __name__ == "__main__":
    result = asyncio.run(main())  
    print(f"Final result: {result}")   