#!/usr/bin/env python3
"""
Learning Point 3: MCP Client Integration

This example demonstrates how to use the MCP (Model Context Protocol) to:
1. Connect to an MCP Server using Streamable HTTP transport
2. Discover available tools from the server
3. Call tools through the MCP protocol
4. Understand the differences between MCP and Anthropic tool formats

Run with:
    uv run python examples/03_mcp_client.py

Prerequisites:
    - FreshRSS MCP Server (set MCP_SERVER_URL in .env)
    - Authentication token if required (set MCP_AUTH_TOKEN in .env)
"""

import asyncio
import json
import os
from pathlib import Path

# Load .env file manually (for examples that don't use pydantic-settings)
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from freshrss_agent.mcp_client import (
    FreshRSSMCPClient,
    convert_mcp_tools_to_anthropic,
    create_mcp_client,
)


# =============================================================================
# Demo 1: Basic MCP Connection and Tool Discovery
# =============================================================================
async def demo_tool_discovery():
    """Demonstrate connecting to MCP server and listing available tools."""
    print("=" * 60)
    print("Demo 1: MCP Tool Discovery")
    print("=" * 60)

    server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8080/mcp")
    auth_token = os.getenv("MCP_AUTH_TOKEN")
    print(f"\nConnecting to MCP Server: {server_url}")
    if auth_token:
        print("Using authentication token")

    try:
        async with create_mcp_client(server_url, auth_token=auth_token) as client:
            print("Connected successfully!")

            # List available tools
            tools = await client.list_tools()
            print(f"\nFound {len(tools)} tools:")

            for tool in tools:
                print(f"\n  Tool: {tool['name']}")
                print(f"  Description: {tool['description']}")
                print(f"  Input Schema: {json.dumps(tool['inputSchema'], indent=4)}")

            # Show the conversion to Anthropic format
            print("\n" + "-" * 40)
            print("Converting to Anthropic format:")
            anthropic_tools = convert_mcp_tools_to_anthropic(tools)
            for tool in anthropic_tools:
                print(f"\n  {tool['name']}: input_schema (not inputSchema)")

    except Exception as e:
        print(f"\nError: {e}")
        print("\nMake sure the FreshRSS MCP Server is running!")
        print("You can start it with: cd freshrss-mcp-server && uv run freshrss-mcp-server")


# =============================================================================
# Demo 2: Calling Tools via MCP
# =============================================================================
async def demo_tool_calls():
    """Demonstrate calling tools through MCP protocol."""
    print("\n" + "=" * 60)
    print("Demo 2: MCP Tool Calls")
    print("=" * 60)

    server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8080/mcp")
    auth_token = os.getenv("MCP_AUTH_TOKEN")

    try:
        async with create_mcp_client(server_url, auth_token=auth_token) as client:
            # Call get_unread_articles tool
            print("\nCalling 'get_unread_articles' with limit=5...")
            result = await client.call_tool("get_unread_articles", {"limit": 5})

            # Parse and display the result
            try:
                data = json.loads(result)
                print(f"\nReceived {data.get('count', 0)} articles:")
                for article in data.get("articles", [])[:3]:  # Show first 3
                    print(f"\n  Title: {article.get('title', 'N/A')}")
                    print(f"  Feed: {article.get('feed', 'N/A')}")
                    print(f"  ID: {article.get('id', 'N/A')}")
            except json.JSONDecodeError:
                print(f"Result: {result}")

    except Exception as e:
        print(f"\nError: {e}")
        print("\nMake sure the FreshRSS MCP Server is running!")


# =============================================================================
# Demo 3: Manual Connection Management
# =============================================================================
async def demo_manual_connection():
    """Demonstrate manual connection management (without context manager)."""
    print("\n" + "=" * 60)
    print("Demo 3: Manual Connection Management")
    print("=" * 60)

    server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8080/mcp")
    auth_token = os.getenv("MCP_AUTH_TOKEN")
    client = FreshRSSMCPClient(server_url, auth_token=auth_token)

    try:
        print(f"\nManually connecting to: {server_url}")
        await client.connect()
        print("Connected!")

        tools = await client.list_tools()
        print(f"Found {len(tools)} tools")

        # Always close when done
        await client.close()
        print("Connection closed")

    except Exception as e:
        print(f"\nError: {e}")
        await client.close()  # Ensure cleanup on error


# =============================================================================
# Main
# =============================================================================
async def main():
    """Run all demos."""
    print("MCP Client Learning Example")
    print("=" * 60)
    print("""
Key Concepts:

1. MCP Protocol: Standardized protocol for AI tool integration
   - Uses Streamable HTTP for communication
   - Provides tool discovery and execution

2. Tool Discovery: Server tells client what tools are available
   - Tools have: name, description, inputSchema
   - Format differs from Anthropic (inputSchema vs input_schema)

3. Tool Execution: Client can call tools on the server
   - Pass tool name and arguments
   - Receive structured results

4. Architecture Benefit:
   - Decouple AI Agent from specific API implementations
   - Same Agent can work with different MCP servers
""")

    await demo_tool_discovery()
    await demo_tool_calls()
    await demo_manual_connection()

    print("\n" + "=" * 60)
    print("Learning Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
