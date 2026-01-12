"""Claude Agent SDK Basics.

This example demonstrates the Claude Agent SDK - a high-level SDK that provides
the same agent loop, tools, and context management as Claude Code.

Key learning points:
- Agent SDK handles the agent loop for you (no more while True loop!)
- Built-in tools: Read, Write, Edit, Bash, Glob, Grep, WebSearch, etc.
- Simple async API with query() function
- ClaudeSDKClient for custom tools and hooks

Comparison with our hand-written agent:
┌─────────────────────────────────────────────────────────────────────────┐
│                    Hand-written Agent (Phase 1-2)                        │
├─────────────────────────────────────────────────────────────────────────┤
│  while True:                                                            │
│      response = client.messages.create(tools=TOOLS, ...)                │
│      if response.stop_reason == "end_turn":                             │
│          return extract_text(response)                                  │
│      elif response.stop_reason == "tool_use":                           │
│          results = execute_tools(response)  # YOU implement this        │
│          messages.append(results)                                       │
└─────────────────────────────────────────────────────────────────────────┘
                              vs
┌─────────────────────────────────────────────────────────────────────────┐
│                       Claude Agent SDK                                   │
├─────────────────────────────────────────────────────────────────────────┤
│  async for message in query(prompt="...", options=...):                 │
│      print(message)  # That's it! SDK handles everything                │
└─────────────────────────────────────────────────────────────────────────┘

Prerequisites:
    pip install claude-agent-sdk

Usage:
    uv run python examples/04_agent_sdk_basics.py
"""

import asyncio

# Check if claude-agent-sdk is installed
try:
    from claude_agent_sdk import (
        ClaudeAgentOptions,
        AssistantMessage,
        ResultMessage,
        TextBlock,
        query,
    )
except ImportError:
    print("=" * 60)
    print("Claude Agent SDK not installed!")
    print("Install with: pip install claude-agent-sdk")
    print("=" * 60)
    exit(1)


async def demo_simple_query():
    """Demo 1: Simple query with no tools.

    The simplest usage - just ask a question and get an answer.
    """
    print("\n" + "=" * 60)
    print("Demo 1: Simple Query (No Tools)")
    print("=" * 60)

    async for message in query(prompt="What is 2 + 2? Reply in one word."):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"Response: {block.text}")
        elif isinstance(message, ResultMessage):
            print(f"Final result: {message.result}")


async def demo_with_tools():
    """Demo 2: Query with built-in tools.

    The SDK has built-in tools that Claude can use autonomously:
    - Read: Read files
    - Write: Create files
    - Edit: Modify files
    - Bash: Run commands
    - Glob: Find files by pattern
    - Grep: Search file contents
    """
    print("\n" + "=" * 60)
    print("Demo 2: Query with Built-in Tools")
    print("=" * 60)

    options = ClaudeAgentOptions(
        allowed_tools=["Glob", "Read"],
        max_turns=3,  # Limit agent loop iterations
    )

    print("Prompt: List all Python files in the examples directory\n")

    async for message in query(
        prompt="List all Python files in the examples directory and briefly describe each",
        options=options,
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(block.text)
        elif isinstance(message, ResultMessage):
            print(f"\n[Agent completed with result]")


async def demo_system_prompt():
    """Demo 3: Custom system prompt.

    You can customize the agent's behavior with a system prompt.
    By default, the SDK doesn't include Claude Code's system prompt,
    giving you full control.
    """
    print("\n" + "=" * 60)
    print("Demo 3: Custom System Prompt")
    print("=" * 60)

    options = ClaudeAgentOptions(
        system_prompt="You are a helpful RSS reading assistant. Be concise.",
        max_turns=1,
    )

    async for message in query(
        prompt="What can you help me with?",
        options=options,
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"Response: {block.text}")


async def demo_working_directory():
    """Demo 4: Working directory and file operations.

    You can specify a working directory for file operations.
    This is useful for limiting the agent's scope.
    """
    print("\n" + "=" * 60)
    print("Demo 4: Working Directory")
    print("=" * 60)

    from pathlib import Path

    options = ClaudeAgentOptions(
        cwd=Path.cwd() / "src" / "freshrss_agent",
        allowed_tools=["Glob"],
        max_turns=2,
    )

    async for message in query(
        prompt="What Python files are in this directory?",
        options=options,
    ):
        if isinstance(message, ResultMessage):
            print(f"Result: {message.result}")


def compare_with_handwritten():
    """Show the comparison between hand-written agent and SDK."""
    print("\n" + "=" * 60)
    print("Comparison: Hand-written Agent vs Agent SDK")
    print("=" * 60)

    comparison = """
┌────────────────────────────────────────────────────────────────────────────┐
│ What we built in Phase 1-2 (agent.py):                                     │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│   class FreshRSSAgent:                                                     │
│       def chat(self, user_message: str) -> str:                            │
│           self.messages.append({"role": "user", "content": user_message})  │
│                                                                            │
│           while True:  # <-- We implement the agent loop                   │
│               response = self._call_claude()                               │
│               self.messages.append(...)                                    │
│                                                                            │
│               if response.stop_reason == "end_turn":                       │
│                   return self._extract_text(response.content)              │
│                                                                            │
│               elif response.stop_reason == "tool_use":                     │
│                   results = self._process_tool_calls(response.content)     │
│                   self.messages.append({"role": "user", "content": results})│
│                                                                            │
├────────────────────────────────────────────────────────────────────────────┤
│ What we write with Agent SDK:                                              │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│   async for message in query(prompt="...", options=options):               │
│       print(message)  # Done! SDK handles the loop and tool execution     │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘

Key Differences:
┌──────────────────────────┬─────────────────────┬─────────────────────────┐
│ Aspect                   │ Hand-written        │ Agent SDK               │
├──────────────────────────┼─────────────────────┼─────────────────────────┤
│ Agent Loop               │ You implement       │ Built-in                │
│ Tool Definitions         │ You define          │ Built-in (Read, Bash..) │
│ Tool Execution           │ You implement       │ Built-in                │
│ Message History          │ You manage          │ Built-in                │
│ Error Handling           │ You implement       │ Built-in                │
│ Learning Value           │ High (understand)   │ Lower (just use)        │
│ Production Ready         │ Needs more work     │ Yes                     │
│ Customization            │ Full control        │ Via hooks/options       │
└──────────────────────────┴─────────────────────┴─────────────────────────┘

Why learn both?
1. Hand-written: Understand HOW agents work (agent loop, tool_use, tool_result)
2. Agent SDK: Build production agents quickly with battle-tested code
"""
    print(comparison)


async def main():
    """Run all demos."""
    print("=" * 60)
    print("Claude Agent SDK Learning Examples")
    print("=" * 60)
    print("\nThe Agent SDK provides the same capabilities as Claude Code,")
    print("but as a programmable Python/TypeScript library.")
    print("\nKey benefits:")
    print("  - Built-in tools (Read, Write, Edit, Bash, Glob, Grep, ...)")
    print("  - Built-in agent loop (no more while True!)")
    print("  - Hooks for custom logic at key points")
    print("  - MCP server integration")
    print("  - Subagents for specialized tasks")

    # Show comparison first
    compare_with_handwritten()

    # Run demos
    try:
        await demo_simple_query()
        await demo_system_prompt()
        # Uncomment these if you want to test file operations:
        # await demo_with_tools()
        # await demo_working_directory()
    except Exception as e:
        print(f"\nError running demos: {e}")
        print("Make sure you have ANTHROPIC_API_KEY set and claude-agent-sdk installed.")

    print("\n" + "=" * 60)
    print("Learning Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Try the demos with file tools (uncomment in main())")
    print("  2. Explore custom tools with @tool decorator")
    print("  3. Learn about hooks for validation and logging")
    print("  4. Check out: https://platform.claude.com/docs/en/agent-sdk/overview")


if __name__ == "__main__":
    asyncio.run(main())
