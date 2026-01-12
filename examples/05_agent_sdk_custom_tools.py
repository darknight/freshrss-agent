"""Claude Agent SDK Custom Tools and Hooks.

This example demonstrates advanced Agent SDK features:
- Custom tools using @tool decorator (in-process MCP servers)
- Hooks for validation, logging, and control flow
- ClaudeSDKClient for bidirectional conversations

Key learning points:
- Custom tools run in-process (no subprocess management)
- Hooks execute at key points in the agent lifecycle
- ClaudeSDKClient enables multi-turn conversations with custom tools

Prerequisites:
    pip install claude-agent-sdk

Usage:
    uv run python examples/05_agent_sdk_custom_tools.py
"""

import asyncio
import json
from datetime import datetime

# Check if claude-agent-sdk is installed
try:
    from claude_agent_sdk import (
        ClaudeAgentOptions,
        ClaudeSDKClient,
        HookMatcher,
        create_sdk_mcp_server,
        tool,
    )
except ImportError:
    print("=" * 60)
    print("Claude Agent SDK not installed!")
    print("Install with: pip install claude-agent-sdk")
    print("=" * 60)
    exit(1)


# =============================================================================
# Custom Tools (In-Process MCP Servers)
# =============================================================================


@tool(
    name="get_current_time",
    description="Get the current date and time",
    parameters={},  # No parameters needed
)
async def get_current_time(args: dict) -> dict:
    """Return current time.

    This is a simple tool that demonstrates the @tool decorator.
    The tool runs in-process, no subprocess needed!
    """
    now = datetime.now()
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(
                    {
                        "date": now.strftime("%Y-%m-%d"),
                        "time": now.strftime("%H:%M:%S"),
                        "timezone": "local",
                    }
                ),
            }
        ]
    }


@tool(
    name="calculate",
    description="Perform basic arithmetic calculations",
    parameters={
        "operation": str,  # add, subtract, multiply, divide
        "a": float,
        "b": float,
    },
)
async def calculate(args: dict) -> dict:
    """Perform arithmetic calculation.

    Demonstrates a tool with typed parameters.
    """
    op = args.get("operation", "add")
    a = args.get("a", 0)
    b = args.get("b", 0)

    operations = {
        "add": lambda x, y: x + y,
        "subtract": lambda x, y: x - y,
        "multiply": lambda x, y: x * y,
        "divide": lambda x, y: x / y if y != 0 else "Error: division by zero",
    }

    if op not in operations:
        result = f"Unknown operation: {op}"
    else:
        result = operations[op](a, b)

    return {"content": [{"type": "text", "text": str(result)}]}


@tool(
    name="mock_get_articles",
    description="Get a list of RSS articles (mock data for demo)",
    parameters={"limit": int},
)
async def mock_get_articles(args: dict) -> dict:
    """Mock article fetcher.

    In a real application, this would call the FreshRSS API.
    This demonstrates how to integrate our FreshRSS functionality
    as a custom tool in the Agent SDK.
    """
    limit = args.get("limit", 5)

    # Mock data
    articles = [
        {
            "id": f"article_{i}",
            "title": f"Article {i}: Example News",
            "feed": "Tech News",
            "summary": f"This is a summary of article {i}...",
        }
        for i in range(1, min(limit + 1, 6))
    ]

    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps({"count": len(articles), "articles": articles}),
            }
        ]
    }


# =============================================================================
# Hooks
# =============================================================================


async def log_tool_use(input_data: dict, tool_use_id: str, context: dict) -> dict:
    """Hook: Log every tool invocation.

    This hook runs BEFORE a tool is executed (PreToolUse).
    Useful for audit logging, monitoring, etc.
    """
    tool_name = input_data.get("tool_name", "unknown")
    tool_input = input_data.get("tool_input", {})

    print(f"  [Hook] Tool called: {tool_name}")
    print(f"  [Hook] Input: {json.dumps(tool_input, indent=2)}")

    # Return empty dict to allow the tool to proceed
    return {}


async def validate_calculation(input_data: dict, tool_use_id: str, context: dict) -> dict:
    """Hook: Validate calculation inputs.

    This hook demonstrates how to BLOCK a tool call.
    If division by zero is attempted, we deny the request.
    """
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    if tool_name != "mcp__my-tools__calculate":
        return {}

    operation = tool_input.get("operation", "")
    b = tool_input.get("b", 1)

    if operation == "divide" and b == 0:
        print("  [Hook] Blocking division by zero!")
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "Division by zero is not allowed",
            }
        }

    return {}


# =============================================================================
# Demos
# =============================================================================


async def demo_custom_tools():
    """Demo 1: Using custom tools.

    Shows how to create in-process MCP tools and use them with the SDK.
    """
    print("\n" + "=" * 60)
    print("Demo 1: Custom Tools (In-Process MCP Server)")
    print("=" * 60)

    # Create an SDK MCP server with our tools
    my_server = create_sdk_mcp_server(
        name="my-tools",
        version="1.0.0",
        tools=[get_current_time, calculate, mock_get_articles],
    )

    # Configure options
    options = ClaudeAgentOptions(
        system_prompt="You are a helpful assistant with access to time, calculator, and article tools.",
        mcp_servers={"my-tools": my_server},
        allowed_tools=[
            "mcp__my-tools__get_current_time",
            "mcp__my-tools__calculate",
            "mcp__my-tools__mock_get_articles",
        ],
        max_turns=3,
    )

    print("\nPrompt: What time is it, and calculate 42 * 17 for me\n")

    async with ClaudeSDKClient(options=options) as client:
        await client.query("What time is it, and calculate 42 * 17 for me")
        async for message in client.receive_response():
            if hasattr(message, "content"):
                for block in message.content:
                    if hasattr(block, "text"):
                        print(f"Claude: {block.text}")
            elif hasattr(message, "result"):
                print(f"\n[Result]: {message.result}")


async def demo_hooks():
    """Demo 2: Using hooks for logging and validation.

    Shows how to intercept tool calls for logging and validation.
    """
    print("\n" + "=" * 60)
    print("Demo 2: Hooks for Logging and Validation")
    print("=" * 60)

    my_server = create_sdk_mcp_server(
        name="my-tools",
        version="1.0.0",
        tools=[calculate],
    )

    options = ClaudeAgentOptions(
        system_prompt="You are a calculator assistant.",
        mcp_servers={"my-tools": my_server},
        allowed_tools=["mcp__my-tools__calculate"],
        max_turns=3,
        hooks={
            "PreToolUse": [
                # Log all tool calls
                HookMatcher(matcher=".*", hooks=[log_tool_use]),
                # Validate calculations
                HookMatcher(matcher="calculate", hooks=[validate_calculation]),
            ],
        },
    )

    print("\nPrompt: Calculate 100 / 5, then try 100 / 0\n")

    async with ClaudeSDKClient(options=options) as client:
        await client.query("First calculate 100 / 5, then calculate 100 / 0")
        async for message in client.receive_response():
            if hasattr(message, "content"):
                for block in message.content:
                    if hasattr(block, "text"):
                        print(f"Claude: {block.text}")


async def demo_multi_turn():
    """Demo 3: Multi-turn conversation with ClaudeSDKClient.

    Shows how to maintain context across multiple exchanges.
    """
    print("\n" + "=" * 60)
    print("Demo 3: Multi-turn Conversation")
    print("=" * 60)

    my_server = create_sdk_mcp_server(
        name="my-tools",
        version="1.0.0",
        tools=[mock_get_articles],
    )

    options = ClaudeAgentOptions(
        system_prompt="You are an RSS reading assistant. Help users manage their articles.",
        mcp_servers={"my-tools": my_server},
        allowed_tools=["mcp__my-tools__mock_get_articles"],
        max_turns=3,
    )

    async with ClaudeSDKClient(options=options) as client:
        # First turn
        print("\n[Turn 1] User: Show me 3 articles")
        await client.query("Show me 3 articles")
        async for message in client.receive_response():
            if hasattr(message, "content"):
                for block in message.content:
                    if hasattr(block, "text"):
                        print(f"Claude: {block.text}")

        # Second turn - context is maintained
        print("\n[Turn 2] User: Summarize them briefly")
        await client.query("Summarize them briefly")
        async for message in client.receive_response():
            if hasattr(message, "content"):
                for block in message.content:
                    if hasattr(block, "text"):
                        print(f"Claude: {block.text}")


def show_architecture():
    """Show the architecture of custom tools."""
    print("\n" + "=" * 60)
    print("Custom Tools Architecture")
    print("=" * 60)

    architecture = """
┌─────────────────────────────────────────────────────────────────────────┐
│                        In-Process MCP Server                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   @tool("get_time", ...)        @tool("calculate", ...)                │
│   async def get_time():          async def calculate(args):             │
│       return {...}                   return {...}                       │
│           │                              │                              │
│           └──────────────┬───────────────┘                              │
│                          ▼                                              │
│               create_sdk_mcp_server(                                    │
│                   name="my-tools",                                      │
│                   tools=[get_time, calculate]                           │
│               )                                                         │
│                          │                                              │
│                          ▼                                              │
│               ClaudeAgentOptions(                                       │
│                   mcp_servers={"my-tools": server},                     │
│                   allowed_tools=["mcp__my-tools__get_time", ...]        │
│               )                                                         │
│                          │                                              │
│                          ▼                                              │
│               ┌─────────────────────┐                                   │
│               │   Claude Agent SDK  │                                   │
│               │   (Agent Loop)      │◄── Handles everything!            │
│               └─────────────────────┘                                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

Benefits of In-Process Tools:
  ✓ No subprocess management
  ✓ Better performance (no IPC overhead)
  ✓ Easier debugging
  ✓ Type safety with Python functions
  ✓ Can still use external MCP servers when needed

Comparison with Phase 2 (External MCP Server):
┌────────────────────────────┬───────────────────────────────────────────┐
│ Phase 2: External MCP      │ Agent SDK: In-Process MCP                 │
├────────────────────────────┼───────────────────────────────────────────┤
│ mcp_client.call_tool()     │ @tool decorator                           │
│ Separate server process    │ Same process                              │
│ Network communication      │ Direct function call                      │
│ Manual connection mgmt     │ SDK handles it                            │
└────────────────────────────┴───────────────────────────────────────────┘
"""
    print(architecture)


async def main():
    """Run all demos."""
    print("=" * 60)
    print("Claude Agent SDK: Custom Tools and Hooks")
    print("=" * 60)

    show_architecture()

    try:
        await demo_custom_tools()
        await demo_hooks()
        await demo_multi_turn()
    except Exception as e:
        print(f"\nError running demos: {e}")
        print("Make sure you have ANTHROPIC_API_KEY set and claude-agent-sdk installed.")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 60)
    print("Learning Complete!")
    print("=" * 60)
    print("\nKey takeaways:")
    print("  1. @tool decorator creates in-process MCP tools")
    print("  2. Hooks intercept tool calls for logging/validation")
    print("  3. ClaudeSDKClient enables multi-turn conversations")
    print("  4. SDK handles agent loop - you focus on business logic")


if __name__ == "__main__":
    asyncio.run(main())
