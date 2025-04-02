import asyncio
from server import run_server


def main():
    """Start the Excel MCP server."""
    try:
        print("Excel MCP Server")
        print("---------------")
        print("Starting server... Press Ctrl+C to exit")
        asyncio.run(run_server())
    except KeyboardInterrupt:
        print("\nShutting down server...")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Server stopped.")

if __name__ == "__main__":
    main() 