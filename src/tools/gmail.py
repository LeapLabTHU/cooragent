import asyncio
import smithery
import mcp
from mcp.client.websocket import websocket_client

# Create Smithery URL with server endpoint
url = smithery.create_smithery_url("wss://server.smithery.ai/@MaitreyaM/gmail-mcp-server/ws", {
  "SMTP_PASSWORD": "",
  "SMTP_USERNAME": ""
})

async def main():
    # Connect to the server using websocket client
    async with websocket_client(url) as streams:
        async with mcp.ClientSession(*streams) as session:
            # List available tools
            tools_result = await session.list_tools()
            print(f"Available tools: {', '.join([t.name for t in tools_result])}")
            
            # Example: Call a tool
            # result = await session.call_tool("tool_name", {"param1": "value1"})

if __name__ == "__main__":
    asyncio.run(main())