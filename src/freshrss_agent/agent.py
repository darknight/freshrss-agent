"""Agent loop implementation.

This is the core of the AI Agent - the loop that:
1. Sends messages to Claude
2. Checks if Claude wants to use tools
3. Executes tools and returns results
4. Continues until Claude is done

Key learning points:
- Agent Loop is the core pattern of AI Agents
- stop_reason determines whether to continue the loop
- Conversation history must be properly maintained

Phase 2 additions:
- Support for MCP mode (use_mcp=True)
- Async agent loop for MCP tool execution
- Dynamic tool discovery from MCP server
"""

import asyncio

from anthropic import Anthropic
from anthropic.types import ContentBlock, Message, TextBlock, ToolUseBlock

from .config import Settings
from .freshrss_client import FreshRSSClient
from .mcp_client import FreshRSSMCPClient
from .tools import TOOLS, MCPToolExecutor, ToolExecutor, get_tools_from_mcp


class FreshRSSAgent:
    """FreshRSS Agent with tool use capabilities.

    Supports two modes:
    - Direct API mode (use_mcp=False): Calls FreshRSS API directly
    - MCP mode (use_mcp=True): Calls FreshRSS via MCP protocol
    """

    def __init__(self, settings: Settings, verbose: bool = False, use_mcp: bool | None = None):
        """Initialize the agent.

        Args:
            settings: Application settings
            verbose: If True, print status messages during processing
            use_mcp: If True, use MCP mode. If None, use settings.use_mcp
        """
        self.settings = settings
        self.verbose = verbose
        self.use_mcp = use_mcp if use_mcp is not None else settings.use_mcp
        self.client = Anthropic(api_key=settings.anthropic_api_key)

        # Mode-specific initialization
        self._mcp_client: FreshRSSMCPClient | None = None
        self._mcp_tool_executor: MCPToolExecutor | None = None
        self._tools: list[dict] = TOOLS  # Default tools, may be updated for MCP

        if not self.use_mcp:
            # Direct API mode
            self.freshrss_client = FreshRSSClient(
                api_url=settings.freshrss_api_url,
                username=settings.freshrss_username,
                password=settings.freshrss_api_password,
            )
            self.tool_executor = ToolExecutor(self.freshrss_client)
        else:
            # MCP mode - client will be initialized when connecting
            self.freshrss_client = None
            self.tool_executor = None

        # Conversation history
        self.messages: list[dict] = []

        # System prompt
        self.system_prompt = (
            "You are an RSS reading assistant that helps users manage and read "
            "articles from FreshRSS.\n\n"
            "You can:\n"
            "1. Get unread articles list\n"
            "2. Summarize article content\n"
            "3. Mark articles as read\n\n"
            "When users ask about articles, first fetch the article list, "
            "then process according to user needs."
        )

    def _print_status(self, message: str) -> None:
        """Print status message if verbose mode is enabled."""
        if self.verbose:
            print(f"\033[90m{message}\033[0m", flush=True)

    async def connect_mcp(self) -> None:
        """Connect to MCP server (MCP mode only).

        This must be called before using the agent in MCP mode.
        """
        if not self.use_mcp:
            return

        self._print_status(f"🔌 Connecting to MCP Server: {self.settings.mcp_server_url}")
        self._mcp_client = FreshRSSMCPClient(
            self.settings.mcp_server_url,
            auth_token=self.settings.mcp_auth_token,
        )
        await self._mcp_client.connect()
        self._mcp_tool_executor = MCPToolExecutor(self._mcp_client)

        # Discover tools from MCP server
        self._print_status("📋 Discovering tools from MCP Server...")
        self._tools = await get_tools_from_mcp(self._mcp_client)
        self._print_status(f"✅ Found {len(self._tools)} tools")

    async def disconnect_mcp(self) -> None:
        """Disconnect from MCP server."""
        if self._mcp_client:
            await self._mcp_client.close()
            self._mcp_client = None
            self._mcp_tool_executor = None

    def chat(self, user_message: str) -> str:
        """Process a user message and return the response (sync version).

        For MCP mode, use chat_async() instead.

        This implements the Agent Loop pattern:
        1. Add user message to history
        2. Send to Claude with tools
        3. If Claude wants to use tools, execute them and continue
        4. Return final text response

        Args:
            user_message: The user's input message

        Returns:
            The agent's text response
        """
        if self.use_mcp:
            # In MCP mode, run the async version
            return asyncio.get_event_loop().run_until_complete(self.chat_async(user_message))

        # Add user message to history
        self.messages.append({"role": "user", "content": user_message})

        # Agent loop
        while True:
            # Call Claude
            self._print_status("⏳ Thinking...")
            response = self._call_claude()

            # Add assistant response to history
            self.messages.append({"role": "assistant", "content": response.content})

            # Check stop reason
            if response.stop_reason == "end_turn":
                # Claude is done, extract text response
                return self._extract_text(response.content)

            elif response.stop_reason == "tool_use":
                # Claude wants to use tools
                tool_results = self._process_tool_calls(response.content)

                # Add tool results to history
                self.messages.append({"role": "user", "content": tool_results})

                # Continue the loop
                continue

            else:
                # Unexpected stop reason (max_tokens, etc.)
                return f"[Agent stopped: {response.stop_reason}]"

    async def chat_async(self, user_message: str) -> str:
        """Process a user message and return the response (async version).

        This is the async version that supports MCP mode.

        Args:
            user_message: The user's input message

        Returns:
            The agent's text response
        """
        # Add user message to history
        self.messages.append({"role": "user", "content": user_message})

        # Agent loop
        while True:
            # Call Claude
            self._print_status("⏳ Thinking...")
            response = self._call_claude()

            # Add assistant response to history
            self.messages.append({"role": "assistant", "content": response.content})

            # Check stop reason
            if response.stop_reason == "end_turn":
                # Claude is done, extract text response
                return self._extract_text(response.content)

            elif response.stop_reason == "tool_use":
                # Claude wants to use tools
                if self.use_mcp:
                    tool_results = await self._process_tool_calls_async(response.content)
                else:
                    tool_results = self._process_tool_calls(response.content)

                # Add tool results to history
                self.messages.append({"role": "user", "content": tool_results})

                # Continue the loop
                continue

            else:
                # Unexpected stop reason (max_tokens, etc.)
                return f"[Agent stopped: {response.stop_reason}]"

    def _call_claude(self) -> Message:
        """Make an API call to Claude.

        Returns:
            Claude's response message
        """
        return self.client.messages.create(
            model=self.settings.model,
            max_tokens=self.settings.max_tokens,
            system=self.system_prompt,
            tools=self._tools,  # Use dynamic tool list
            messages=self.messages,
        )

    def _process_tool_calls(self, content: list[ContentBlock]) -> list[dict]:
        """Process tool use requests and return results (sync version).

        Args:
            content: Response content blocks from Claude

        Returns:
            List of tool_result blocks
        """
        results = []

        for block in content:
            if isinstance(block, ToolUseBlock):
                # Execute the tool
                self._print_status(f"🔧 Calling tool: {block.name}...")
                result = self.tool_executor.execute(block.name, block.input)

                # Format as tool_result
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    }
                )

        return results

    async def _process_tool_calls_async(self, content: list[ContentBlock]) -> list[dict]:
        """Process tool use requests and return results (async version for MCP).

        Args:
            content: Response content blocks from Claude

        Returns:
            List of tool_result blocks
        """
        results = []

        for block in content:
            if isinstance(block, ToolUseBlock):
                # Execute the tool via MCP
                self._print_status(f"🔧 Calling tool via MCP: {block.name}...")
                result = await self._mcp_tool_executor.execute_async(block.name, block.input)

                # Format as tool_result
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    }
                )

        return results

    def _extract_text(self, content: list[ContentBlock]) -> str:
        """Extract text from response content.

        Args:
            content: Response content blocks

        Returns:
            Combined text from all TextBlocks
        """
        texts = []
        for block in content:
            if isinstance(block, TextBlock):
                texts.append(block.text)
        return "\n".join(texts)

    def reset(self) -> None:
        """Reset conversation history."""
        self.messages = []

    def close(self) -> None:
        """Clean up resources (sync version)."""
        if self.freshrss_client:
            self.freshrss_client.close()
        if self._mcp_client:
            # Run async cleanup in sync context
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If in async context, schedule but don't wait
                    asyncio.ensure_future(self.disconnect_mcp())
                else:
                    loop.run_until_complete(self.disconnect_mcp())
            except RuntimeError:
                # No event loop, create one
                asyncio.run(self.disconnect_mcp())

    async def aclose(self) -> None:
        """Clean up resources (async version)."""
        if self.freshrss_client:
            self.freshrss_client.close()
        await self.disconnect_mcp()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    async def __aenter__(self):
        """Async context manager entry."""
        if self.use_mcp:
            await self.connect_mcp()
        return self

    async def __aexit__(self, *args):
        """Async context manager exit."""
        await self.aclose()


# =============================================================================
# Standalone Agent Loop Example
# =============================================================================


def simple_agent_loop_example():
    """
    A simplified Agent Loop example without FreshRSS dependency.
    Used for learning the core Agent Loop pattern.
    """
    from anthropic import Anthropic

    client = Anthropic()

    # Simple tool definitions
    tools = [
        {
            "name": "get_time",
            "description": "Get current time",
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "name": "add_numbers",
            "description": "Add two numbers together",
            "input_schema": {
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"},
                },
                "required": ["a", "b"],
            },
        },
    ]

    # Tool execution
    def execute_tool(name: str, input: dict) -> str:
        import datetime

        if name == "get_time":
            return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elif name == "add_numbers":
            return str(input["a"] + input["b"])
        return "Unknown tool"

    # Conversation history
    messages = []

    # User input
    user_input = "What time is it? Then calculate 123 + 456 for me."
    messages.append({"role": "user", "content": user_input})

    print(f"User: {user_input}\n")
    print("=" * 40)
    print("Agent Loop Started")
    print("=" * 40)

    loop_count = 0
    max_loops = 10  # Prevent infinite loops

    while loop_count < max_loops:
        loop_count += 1
        print(f"\n--- Loop {loop_count} ---")

        # Call Claude
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            tools=tools,
            messages=messages,
        )

        print(f"stop_reason: {response.stop_reason}")

        # Add response to history
        messages.append({"role": "assistant", "content": response.content})

        # Check if done
        if response.stop_reason == "end_turn":
            print("\nClaude finished responding")
            for block in response.content:
                if hasattr(block, "text"):
                    print(f"\nFinal response: {block.text}")
            break

        # Process tool calls
        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"Executing tool: {block.name}({block.input})")
                    result = execute_tool(block.name, block.input)
                    print(f"Result: {result}")
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )

            # Add tool results to history
            messages.append({"role": "user", "content": tool_results})

    print("\n" + "=" * 40)
    print("Agent Loop Ended")
    print("=" * 40)


if __name__ == "__main__":
    simple_agent_loop_example()
