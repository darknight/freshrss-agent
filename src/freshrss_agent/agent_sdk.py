"""FreshRSS Agent implemented with Claude Agent SDK.

This module provides an alternative implementation of FreshRSSAgent using
the Claude Agent SDK. Compare this with agent.py to see what the SDK
does for you.

Key differences from hand-written agent.py:
- No manual agent loop (SDK handles it)
- No manual MCP connection management
- Tools are dynamically discovered from MCP Server
- Built-in streaming support

There are TWO modes in this module:
1. External MCP Mode (recommended) - connects to external MCP Server, dynamic tool discovery
2. In-Process Mode - defines tools locally with @tool decorator

Prerequisites:
    pip install claude-agent-sdk

Usage:
    from freshrss_agent.agent_sdk import FreshRSSAgentSDK

    # External MCP mode (connects to MCP Server)
    async with FreshRSSAgentSDK(settings) as agent:
        response = await agent.chat("Show me my articles")
        print(response)
"""

from .config import Settings

# Check if claude-agent-sdk is installed
try:
    from claude_agent_sdk import (
        ClaudeAgentOptions,
        ClaudeSDKClient,
        ResultMessage,
    )

    AGENT_SDK_AVAILABLE = True
except ImportError:
    AGENT_SDK_AVAILABLE = False


def check_sdk_available() -> None:
    """Check if Claude Agent SDK is available."""
    if not AGENT_SDK_AVAILABLE:
        raise ImportError(
            "Claude Agent SDK is not installed. "
            "Install it with: pip install claude-agent-sdk"
        )


# =============================================================================
# FreshRSS Agent (SDK Version) - External MCP Mode
# =============================================================================


class FreshRSSAgentSDK:
    """FreshRSS Agent implemented with Claude Agent SDK.

    This class connects to an EXTERNAL MCP Server and dynamically discovers
    available tools. This is the key difference from in-process mode:

    ┌─────────────────────────────────────────────────────────────────────┐
    │ In-Process Mode (wrong approach)                                    │
    ├─────────────────────────────────────────────────────────────────────┤
    │ - Tools defined with @tool decorator in this file                  │
    │ - Must manually sync with MCP Server capabilities                  │
    │ - If Server adds/removes tools, must update this code              │
    └─────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────────┐
    │ External MCP Mode (this implementation)                             │
    ├─────────────────────────────────────────────────────────────────────┤
    │ - Connects to MCP Server via stdio/sse                              │
    │ - Tools dynamically discovered from Server                          │
    │ - Server changes automatically reflected                            │
    │ - All 5 tools available: get_unread_articles, get_article_content, │
    │   mark_as_read, get_subscriptions, fetch_full_article              │
    └─────────────────────────────────────────────────────────────────────┘

    Comparison with agent.py:
    ┌─────────────────────────────────────────────────────────────────────┐
    │ agent.py (hand-written)         │ agent_sdk.py (SDK)               │
    ├─────────────────────────────────────────────────────────────────────┤
    │ while True:                     │ async for msg in query():        │
    │     response = call_claude()    │     process(msg)                 │
    │     if tool_use:                │                                  │
    │         execute_tools()         │ # SDK handles everything:        │
    │         continue                │ # - Agent loop                   │
    │                                 │ # - MCP connection               │
    │ # Manual MCP connection:        │ # - Tool discovery               │
    │ await mcp_client.connect()      │ # - Tool execution               │
    │ tools = await list_tools()      │                                  │
    │ await mcp_client.close()        │                                  │
    └─────────────────────────────────────────────────────────────────────┘

    Usage:
        async with FreshRSSAgentSDK(settings) as agent:
            response = await agent.chat("Show me my articles")
            print(response)
    """

    def __init__(self, settings: Settings, verbose: bool = False):
        """Initialize the Agent SDK version.

        Args:
            settings: Application settings (must include mcp_server_command or mcp_server_url)
            verbose: If True, print status messages during processing
        """
        check_sdk_available()

        self.settings = settings
        self.verbose = verbose

        # SDK client (will be initialized in __aenter__)
        self._client: ClaudeSDKClient | None = None

        # System prompt
        self.system_prompt = (
            "You are an RSS reading assistant that helps users manage and read "
            "articles from FreshRSS.\n\n"
            "You have access to tools for:\n"
            "1. Getting unread articles (get_unread_articles)\n"
            "2. Getting full article content (get_article_content)\n"
            "3. Marking articles as read (mark_as_read)\n"
            "4. Getting subscription list (get_subscriptions)\n"
            "5. Fetching full article from URL (fetch_full_article)\n\n"
            "When users ask about articles, first fetch the article list, "
            "then process according to user needs."
        )

        # Build MCP server configuration for EXTERNAL server
        # The SDK will connect to this server and discover tools dynamically
        self._mcp_config = self._build_mcp_config()

        # Build options
        # IMPORTANT: Set tools=[] to disable built-in Claude Code tools (Bash, Glob, etc.)
        # This ensures only MCP server tools are available
        self._options = ClaudeAgentOptions(
            system_prompt=self.system_prompt,
            mcp_servers={"freshrss": self._mcp_config},
            tools=[],  # Disable all built-in tools, only use MCP server tools
            max_turns=10,
        )

    def _build_mcp_config(self) -> dict:
        """Build MCP server configuration.

        The Agent SDK supports multiple transport types:
        - stdio: Launch MCP server as subprocess
        - sse: Connect via Server-Sent Events
        - streamable-http: Connect via Streamable HTTP (what we used in Phase 2)

        Returns:
            MCP server configuration dict
        """
        # Option 1: If MCP server is a command (stdio transport)
        # This launches the MCP server as a subprocess
        if hasattr(self.settings, "mcp_server_command") and self.settings.mcp_server_command:
            self._print_status(f"📡 Using stdio MCP: {self.settings.mcp_server_command}")
            return {
                "command": self.settings.mcp_server_command,
                "args": self._get_mcp_server_args(),
            }

        # Option 2: If MCP server is a URL (sse or streamable-http transport)
        # This connects to an already-running MCP server
        if self.settings.mcp_server_url:
            self._print_status(f"📡 Using HTTP MCP: {self.settings.mcp_server_url}")
            config: dict = {
                "type": "sse",  # SDK requires explicit type for URL-based configs
                "url": self.settings.mcp_server_url,
            }
            if self.settings.mcp_auth_token:
                config["headers"] = {
                    "Authorization": f"Bearer {self.settings.mcp_auth_token}"
                }
            return config

        # Fallback: Use a default stdio command if available
        raise ValueError(
            "No MCP server configured. Set either:\n"
            "  - MCP_SERVER_COMMAND (e.g., 'freshrss-mcp-server')\n"
            "  - MCP_SERVER_URL (e.g., 'http://localhost:8080/mcp')"
        )

    def _get_mcp_server_args(self) -> list[str]:
        """Get command-line arguments for MCP server subprocess."""
        args = []
        if self.settings.freshrss_api_url:
            args.extend(["--url", self.settings.freshrss_api_url])
        if self.settings.freshrss_username:
            args.extend(["--username", self.settings.freshrss_username])
        if self.settings.freshrss_api_password:
            args.extend(["--password", self.settings.freshrss_api_password])
        return args

    def _print_status(self, message: str) -> None:
        """Print status message if verbose mode is enabled."""
        if self.verbose:
            print(f"\033[90m{message}\033[0m", flush=True)

    async def chat(self, user_message: str) -> str:
        """Process a user message and return the response.

        This is the main interface - same as agent.py but using the SDK.
        The SDK handles:
        - Agent loop (no while True needed)
        - MCP connection (no connect/disconnect needed)
        - Tool discovery (no list_tools needed)
        - Tool execution (no execute_tool needed)

        Args:
            user_message: The user's input message

        Returns:
            The agent's text response
        """
        if not self._client:
            raise RuntimeError("Agent not initialized. Use 'async with' context manager.")

        self._print_status("⏳ Thinking...")

        # Send query
        await self._client.query(user_message)

        # Collect response
        result_text = ""
        async for message in self._client.receive_response():
            # Handle different message types
            if hasattr(message, "content"):
                for block in message.content:
                    if hasattr(block, "text"):
                        result_text = block.text
                    elif hasattr(block, "name"):
                        # Tool use block - SDK discovered this from MCP Server!
                        self._print_status(f"🔧 Calling tool: {block.name}...")

            elif isinstance(message, ResultMessage):
                result_text = message.result

        return result_text

    async def __aenter__(self) -> "FreshRSSAgentSDK":
        """Async context manager entry.

        The SDK handles MCP connection internally - no manual connect() needed!
        """
        self._client = ClaudeSDKClient(options=self._options)
        await self._client.__aenter__()
        self._print_status("✅ Agent SDK initialized (MCP tools discovered automatically)")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit.

        The SDK handles MCP disconnection internally - no manual close() needed!
        """
        if self._client:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)
            self._client = None

    def close(self) -> None:
        """Close resources (sync version for compatibility)."""
        pass  # SDK handles cleanup


# =============================================================================
# Comparison: What the SDK does for you
# =============================================================================

COMPARISON = """
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Phase 2 (agent.py + mcp_client.py)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  # 1. Manual MCP connection                                                 │
│  mcp_client = FreshRSSMCPClient(url, token)                                │
│  await mcp_client.connect()                                                 │
│                                                                             │
│  # 2. Manual tool discovery                                                 │
│  mcp_tools = await mcp_client.list_tools()                                 │
│  tools = convert_mcp_tools_to_anthropic(mcp_tools)                         │
│                                                                             │
│  # 3. Manual agent loop                                                     │
│  while True:                                                                │
│      response = client.messages.create(tools=tools, ...)                   │
│      if response.stop_reason == "end_turn":                                │
│          break                                                              │
│      elif response.stop_reason == "tool_use":                              │
│          # 4. Manual tool execution                                         │
│          result = await mcp_client.call_tool(name, args)                   │
│          messages.append(tool_result)                                       │
│                                                                             │
│  # 5. Manual cleanup                                                        │
│  await mcp_client.close()                                                   │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                         Agent SDK (agent_sdk.py)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  options = ClaudeAgentOptions(                                              │
│      mcp_servers={"freshrss": {"url": "http://..."}}  # Just config!       │
│  )                                                                          │
│                                                                             │
│  async with ClaudeSDKClient(options) as client:                            │
│      await client.query("Show me my articles")                             │
│      async for msg in client.receive_response():                           │
│          print(msg)                                                         │
│                                                                             │
│  # That's it! SDK handles:                                                  │
│  # ✓ MCP connection/disconnection                                          │
│  # ✓ Tool discovery (all 5 tools from server)                              │
│  # ✓ Agent loop                                                             │
│  # ✓ Tool execution                                                         │
│  # ✓ Error handling                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
"""


# =============================================================================
# Standalone Demo
# =============================================================================


async def demo():
    """Demo the Agent SDK implementation."""
    import os

    from dotenv import load_dotenv

    load_dotenv()

    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY not set")
        return

    print("=" * 60)
    print("FreshRSS Agent (SDK Version) Demo")
    print("=" * 60)
    print("\nThis demo uses the Claude Agent SDK with EXTERNAL MCP Server.")
    print("Tools are discovered dynamically from the MCP Server.")
    print("\nComparison with Phase 2:")
    print(COMPARISON)

    try:
        # Create settings
        settings = Settings()

        async with FreshRSSAgentSDK(settings, verbose=True) as agent:
            # Demo query
            response = await agent.chat("How many unread articles do I have?")
            print(f"\nResponse: {response}")
    except ValueError as e:
        print(f"\nConfiguration error: {e}")
        print("\nTo use Agent SDK mode, configure MCP server in .env:")
        print("  MCP_SERVER_URL=http://localhost:8080/mcp")
        print("  # or")
        print("  MCP_SERVER_COMMAND=freshrss-mcp-server")
    except Exception as e:
        print(f"\nError: {e}")
        print("\nMake sure you have:")
        print("  1. claude-agent-sdk installed: pip install claude-agent-sdk")
        print("  2. ANTHROPIC_API_KEY set")
        print("  3. MCP Server running or configured")


if __name__ == "__main__":
    import asyncio

    asyncio.run(demo())
