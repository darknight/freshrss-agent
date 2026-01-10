#!/usr/bin/env python3
"""
Learning Point 1: Tool Use Basics

This example demonstrates the core concepts of Claude Tool Use:
1. How to define tool schemas (JSON Schema format)
2. How Claude returns tool_use (in response.content)
3. How to handle tool call results (construct tool_result messages)

Run with:
    uv run python examples/01_basic_tool_use.py
"""

from anthropic import Anthropic

# Initialize client
client = Anthropic()

# =============================================================================
# Step 1: Define Tool Schema
# =============================================================================
# Tool definitions use JSON Schema format to tell Claude what tools are available
# Each tool needs: name, description, input_schema

TOOLS = [
    {
        "name": "get_weather",
        "description": "Get weather information for a specified city",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "City name, e.g., 'Beijing' or 'New York'",
                }
            },
            "required": ["city"],
        },
    },
    {
        "name": "calculate",
        "description": "Perform mathematical calculations",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression, e.g., '2 + 3 * 4'",
                }
            },
            "required": ["expression"],
        },
    },
]


# =============================================================================
# Step 2: Implement Tool Execution Function
# =============================================================================
def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool and return the result.

    In real applications, this would call actual APIs or perform real operations.
    """
    if tool_name == "get_weather":
        city = tool_input["city"]
        # Simulated weather data
        return f"{city}: Sunny today, temperature 22°C, humidity 45%"

    elif tool_name == "calculate":
        expression = tool_input["expression"]
        try:
            # Note: eval should be used with caution in production
            result = eval(expression)
            return str(result)
        except Exception as e:
            return f"Calculation error: {e}"

    return f"Unknown tool: {tool_name}"


# =============================================================================
# Step 3: Interact with Claude
# =============================================================================
def demo_single_tool_call():
    """Demonstrate the complete flow of a single tool call."""
    print("=" * 60)
    print("Demo: Single Tool Call")
    print("=" * 60)

    # User message
    user_message = "What's the weather like in Beijing today?"
    print(f"\nUser: {user_message}\n")

    # Send request to Claude (with tool definitions)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        tools=TOOLS,
        messages=[{"role": "user", "content": user_message}],
    )

    print(f"Claude response (stop_reason={response.stop_reason}):")

    # Check Claude's response
    # response.content is a list that may contain TextBlock and ToolUseBlock
    for block in response.content:
        print(f"  - {block.type}: {block}")

    # If stop_reason is "tool_use", Claude wants to call a tool
    if response.stop_reason == "tool_use":
        print("\n--- Claude requests tool call ---")

        # Find the tool_use block
        tool_use_block = next(
            block for block in response.content if block.type == "tool_use"
        )

        print(f"Tool name: {tool_use_block.name}")
        print(f"Tool input: {tool_use_block.input}")
        print(f"Tool use ID: {tool_use_block.id}")

        # Execute the tool
        result = execute_tool(tool_use_block.name, tool_use_block.input)
        print(f"Tool execution result: {result}")

        # Send tool result back to Claude
        print("\n--- Sending tool result to Claude ---")

        # Construct conversation history: original user message + Claude's response + tool result
        messages = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": response.content},
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_block.id,
                        "content": result,
                    }
                ],
            },
        ]

        # Call Claude again
        final_response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            tools=TOOLS,
            messages=messages,
        )

        print(f"\nClaude final response (stop_reason={final_response.stop_reason}):")
        for block in final_response.content:
            if block.type == "text":
                print(f"  {block.text}")


def demo_multiple_tool_calls():
    """Demonstrate Claude requesting multiple tool calls at once."""
    print("\n" + "=" * 60)
    print("Demo: Multiple Tool Calls")
    print("=" * 60)

    user_message = "What's the weather in Beijing and Shanghai? Also calculate 123 * 456 for me."
    print(f"\nUser: {user_message}\n")

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        tools=TOOLS,
        messages=[{"role": "user", "content": user_message}],
    )

    print(f"Claude response (stop_reason={response.stop_reason}):")

    # Collect all tool calls
    tool_results = []

    for block in response.content:
        print(f"  - {block.type}")
        if block.type == "tool_use":
            print(f"    Tool: {block.name}, Input: {block.input}")
            result = execute_tool(block.name, block.input)
            print(f"    Result: {result}")
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                }
            )

    if tool_results:
        # Send all tool results
        messages = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": response.content},
            {"role": "user", "content": tool_results},
        ]

        final_response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            tools=TOOLS,
            messages=messages,
        )

        print("\nClaude final response:")
        for block in final_response.content:
            if block.type == "text":
                print(f"  {block.text}")


if __name__ == "__main__":
    print("Tool Use Basics Learning Example")
    print("=" * 60)
    print("""
Key Concepts:

1. tools parameter: Define available tools using JSON Schema format
2. stop_reason:
   - "end_turn" = Claude finished responding
   - "tool_use" = Claude wants to call a tool
3. response.content: May contain multiple blocks
   - TextBlock: Claude's text response
   - ToolUseBlock: Tool call request
4. tool_result: Send tool execution results back to Claude
""")

    demo_single_tool_call()
    demo_multiple_tool_calls()
