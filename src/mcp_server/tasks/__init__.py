"""
Tasks module for MCP Server.
Initializes a shared FastMCP server instance and imports all task modules.
"""
from mcp.server.fastmcp import FastMCP
from typing import Any, Dict, List

# Create a single shared FastMCP server instance
mcp_server = FastMCP("MCP Server")

# Import all task modules to register their tools with the shared server
from . import configuration
