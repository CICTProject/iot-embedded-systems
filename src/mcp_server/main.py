"""
Main entry point for the MCP server.
"""
from tasks import mcp_server


def create_server():
    """Create and return the MCP server instance with all registered tools."""
    return mcp_server


if __name__ == "__main__":
    mcp = create_server()
    mcp.run()