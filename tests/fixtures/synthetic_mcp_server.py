"""Local-only MCP fixture. Run with a port argument or over stdio."""

import os
import sys

from mcp.server.fastmcp import FastMCP

server = FastMCP("cooragent-synthetic")


@server.tool()
def echo(value: str) -> str:
    return f"synthetic:{value}"


@server.tool()
def child_env() -> str:
    return os.environ.get("SYNTHETIC_CHILD_ONLY", "not-set")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        server.run(transport="stdio")
    else:
        import uvicorn

        app = (
            server.sse_app()
            if len(sys.argv) > 2 and sys.argv[2] == "sse"
            else server.streamable_http_app()
        )

        async def authenticated_app(scope, receive, send):
            if scope["type"] == "http":
                headers = dict(scope["headers"])
                expected = f"Bearer {os.environ['SYNTHETIC_EXPECTED_TOKEN']}".encode()
                if headers.get(b"authorization") != expected:
                    await send(
                        {"type": "http.response.start", "status": 401, "headers": []}
                    )
                    await send({"type": "http.response.body", "body": b"Unauthorized"})
                    return
            await app(scope, receive, send)

        uvicorn.run(
            authenticated_app,
            host="127.0.0.1",
            port=int(sys.argv[1]),
            log_level="error",
        )
