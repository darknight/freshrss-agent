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
"""

from anthropic import Anthropic
from anthropic.types import ContentBlock, Message, TextBlock, ToolUseBlock

from .config import Settings
from .freshrss_client import FreshRSSClient
from .tools import TOOLS, ToolExecutor


class FreshRSSAgent:
    """FreshRSS Agent with tool use capabilities."""

    def __init__(self, settings: Settings, verbose: bool = False):
        """Initialize the agent.

        Args:
            settings: Application settings
            verbose: If True, print status messages during processing
        """
        self.settings = settings
        self.verbose = verbose
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.freshrss_client = FreshRSSClient(
            api_url=settings.freshrss_api_url,
            username=settings.freshrss_username,
            password=settings.freshrss_api_password,
        )
        self.tool_executor = ToolExecutor(self.freshrss_client)

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

    def chat(self, user_message: str) -> str:
        """Process a user message and return the response.

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

    def _call_claude(self) -> Message:
        """Make an API call to Claude.

        Returns:
            Claude's response message
        """
        return self.client.messages.create(
            model=self.settings.model,
            max_tokens=self.settings.max_tokens,
            system=self.system_prompt,
            tools=TOOLS,
            messages=self.messages,
        )

    def _process_tool_calls(self, content: list[ContentBlock]) -> list[dict]:
        """Process tool use requests and return results.

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
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

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
        """Clean up resources."""
        self.freshrss_client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


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
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            # Add tool results to history
            messages.append({"role": "user", "content": tool_results})

    print("\n" + "=" * 40)
    print("Agent Loop Ended")
    print("=" * 40)


if __name__ == "__main__":
    simple_agent_loop_example()
