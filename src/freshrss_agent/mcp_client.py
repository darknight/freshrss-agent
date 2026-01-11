"""MCP Client for connecting to FreshRSS MCP Server.

This module implements an MCP client that connects to a FreshRSS MCP Server
using the Streamable HTTP transport. It provides tool discovery and execution
capabilities through the MCP protocol.

Key learning points:
- MCP uses async/await for all operations
- Tools are discovered dynamically from the server
- Tool format differs from Anthropic format and needs conversion
"""

import json
from contextlib import asynccontextmanager
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


class FreshRSSMCPClient:
    """MCP Client that connects to FreshRSS MCP Server.

    This client wraps the MCP protocol to provide a simple interface for:
    - Connecting to an MCP server
    - Discovering available tools
    - Calling tools and getting results

    Usage:
        async with FreshRSSMCPClient("http://localhost:8080/mcp") as client:
            tools = await client.list_tools()
            result = await client.call_tool("get_unread_articles", {"limit": 10})

        # With authentication:
        async with FreshRSSMCPClient(url, auth_token="...") as client:
            ...
    """

    def __init__(self, server_url: str, auth_token: str | None = None):
        """Initialize MCP client.

        Args:
            server_url: URL of the MCP server (e.g., "http://localhost:8080/mcp")
            auth_token: Optional Bearer token for authentication
        """
        self.server_url = server_url
        self.auth_token = auth_token
        self._session: ClientSession | None = None
        self._streams = None
        self._context_manager = None

    async def connect(self) -> None:
        """Connect to MCP Server.

        Establishes a connection to the MCP server using Streamable HTTP transport.
        The connection is maintained until close() is called.
        """
        # Build headers if auth token is provided
        headers = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        # Create the streamable HTTP client context manager
        self._context_manager = streamablehttp_client(
            self.server_url,
            headers=headers if headers else None,
        )
        # Enter the context manager to get the streams
        self._streams = await self._context_manager.__aenter__()
        read_stream, write_stream, _ = self._streams

        # Create and initialize the session
        self._session = ClientSession(read_stream, write_stream)
        await self._session.__aenter__()
        await self._session.initialize()

    async def list_tools(self) -> list[dict]:
        """List available tools from server.

        Returns:
            List of tool definitions in MCP format.
            Each tool has: name, description, inputSchema
        """
        if not self._session:
            raise RuntimeError("Not connected. Call connect() first.")

        result = await self._session.list_tools()
        return [
            {
                "name": tool.name,
                "description": tool.description or "",
                "inputSchema": tool.inputSchema,
            }
            for tool in result.tools
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> str:
        """Call a tool on the server.

        Args:
            name: Name of the tool to call
            arguments: Tool arguments (optional)

        Returns:
            Tool result as a JSON string
        """
        if not self._session:
            raise RuntimeError("Not connected. Call connect() first.")

        result = await self._session.call_tool(name, arguments or {})

        # Extract content from result
        # MCP returns a list of content blocks
        if result.content:
            # Combine all text content
            texts = []
            for content in result.content:
                if hasattr(content, "text"):
                    texts.append(content.text)
            return "\n".join(texts) if texts else json.dumps({"result": "success"})

        return json.dumps({"result": "no content"})

    async def close(self) -> None:
        """Close connection."""
        if self._session:
            await self._session.__aexit__(None, None, None)
            self._session = None
        if self._context_manager:
            await self._context_manager.__aexit__(None, None, None)
            self._context_manager = None
            self._streams = None

    async def __aenter__(self) -> "FreshRSSMCPClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()


def convert_mcp_tools_to_anthropic(mcp_tools: list[dict]) -> list[dict]:
    """Convert MCP tool format to Anthropic tool format.

    MCP format:
        {"name": "...", "description": "...", "inputSchema": {...}}

    Anthropic format:
        {"name": "...", "description": "...", "input_schema": {...}}

    Args:
        mcp_tools: List of tools in MCP format

    Returns:
        List of tools in Anthropic format
    """
    return [
        {
            "name": tool["name"],
            "description": tool["description"],
            "input_schema": tool["inputSchema"],
        }
        for tool in mcp_tools
    ]


@asynccontextmanager
async def create_mcp_client(server_url: str, auth_token: str | None = None):
    """Create and connect an MCP client.

    Convenience async context manager for creating a connected client.

    Usage:
        async with create_mcp_client("http://localhost:8080/mcp") as client:
            tools = await client.list_tools()

        # With authentication:
        async with create_mcp_client(url, auth_token="...") as client:
            ...

    Args:
        server_url: URL of the MCP server
        auth_token: Optional Bearer token for authentication

    Yields:
        Connected FreshRSSMCPClient instance
    """
    client = FreshRSSMCPClient(server_url, auth_token=auth_token)
    try:
        await client.connect()
        yield client
    finally:
        await client.close()
