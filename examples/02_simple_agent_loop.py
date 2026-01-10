#!/usr/bin/env python3
"""
Learning Point 2: Agent Loop

This example demonstrates the core Agent Loop pattern:
1. Loop calling Claude until the task is complete
2. Decide next action based on stop_reason
3. Maintain conversation history

Agent Loop is the foundational architecture of all AI Agents.

Run with:
    uv run python examples/02_simple_agent_loop.py
"""

from anthropic import Anthropic

client = Anthropic()

# =============================================================================
# Tool Definitions
# =============================================================================

TOOLS = [
    {
        "name": "search_knowledge",
        "description": "Search knowledge base for information",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "send_email",
        "description": "Send an email",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient"},
                "subject": {"type": "string", "description": "Subject"},
                "body": {"type": "string", "description": "Body"},
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "create_task",
        "description": "Create a todo task",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Task title"},
                "due_date": {"type": "string", "description": "Due date"},
            },
            "required": ["title"],
        },
    },
]


# =============================================================================
# Tool Execution
# =============================================================================

def execute_tool(name: str, input: dict) -> str:
    """Simulate tool execution."""
    print(f"  Executing tool: {name}")
    print(f"     Input: {input}")

    if name == "search_knowledge":
        query = input["query"]
        # Simulated search results
        return (
            f"Search results: Found 3 items about '{query}':\n"
            "1. Python is a programming language\n"
            "2. AI Agent is an autonomous AI system\n"
            "3. Tool Use allows LLMs to call external functions"
        )

    elif name == "send_email":
        return f"Email sent to {input['to']}, subject: {input['subject']}"

    elif name == "create_task":
        return f"Task created: {input['title']}"

    return "Unknown tool"


# =============================================================================
# Agent Loop Implementation
# =============================================================================

def agent_loop(user_request: str, max_iterations: int = 10) -> str:
    """
    Core implementation of Agent Loop.

    Args:
        user_request: User's request
        max_iterations: Maximum iterations (prevent infinite loops)

    Returns:
        Agent's final response
    """
    print("=" * 60)
    print("Agent Loop Started")
    print("=" * 60)
    print(f"\nUser request: {user_request}\n")

    # Initialize conversation history
    messages = [{"role": "user", "content": user_request}]

    # System prompt
    system = """You are an intelligent assistant that helps users complete various tasks.
You can search knowledge base, send emails, and create tasks.
Complete user requests step by step, using multiple tools when necessary."""

    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        print(f"\n--- Iteration {iteration} ---")

        # Call Claude
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system,
            tools=TOOLS,
            messages=messages,
        )

        print(f"stop_reason: {response.stop_reason}")

        # Add response to conversation history
        messages.append({"role": "assistant", "content": response.content})

        # Check response content
        text_parts = []
        tool_uses = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
                preview = block.text[:100] + "..." if len(block.text) > 100 else block.text
                print(f"  Claude: {preview}")
            elif block.type == "tool_use":
                tool_uses.append(block)

        # Decide next action based on stop_reason
        if response.stop_reason == "end_turn":
            # Claude completed the task
            print("\nAgent completed task")
            return "\n".join(text_parts)

        elif response.stop_reason == "tool_use":
            # Claude wants to use tools
            tool_results = []

            for tool_use in tool_uses:
                result = execute_tool(tool_use.name, tool_use.input)
                print(f"     Result: {result}")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result,
                })

            # Add tool results to conversation history
            messages.append({"role": "user", "content": tool_results})

        elif response.stop_reason == "max_tokens":
            print("\nReached token limit")
            return "\n".join(text_parts) + "\n[Response truncated]"

        else:
            print(f"\nUnknown stop_reason: {response.stop_reason}")
            return "\n".join(text_parts)

    print("\nReached maximum iterations")
    return "Agent timeout"


# =============================================================================
# Demos
# =============================================================================

def demo_simple_task():
    """Demonstrate simple task (may not need tools)."""
    print("\n" + "=" * 60)
    print("Demo 1: Simple Q&A")
    print("=" * 60)

    result = agent_loop("Hello, who are you?")
    print(f"\nFinal result: {result}")


def demo_single_tool():
    """Demonstrate single tool task."""
    print("\n" + "=" * 60)
    print("Demo 2: Single Tool Call")
    print("=" * 60)

    result = agent_loop("Search for information about Python")
    print(f"\nFinal result: {result}")


def demo_multi_tool():
    """Demonstrate multi-tool task."""
    print("\n" + "=" * 60)
    print("Demo 3: Multiple Tool Calls")
    print("=" * 60)

    result = agent_loop(
        "Please complete the following tasks:\n"
        "1. Search for information about AI Agent\n"
        "2. Create a task: Learn AI Agent development\n"
        "3. Send email to team@example.com with subject 'AI Agent Learning Plan'"
    )
    print(f"\nFinal result: {result}")


if __name__ == "__main__":
    print("""
+==============================================================+
|                   Agent Loop Learning Example                 |
+==============================================================+
|                                                              |
|  Core flow of Agent Loop:                                    |
|                                                              |
|  +----------------------------------------------------------+|
|  |                                                          ||
|  |   User Request --> Call Claude --> Check stop_reason     ||
|  |                        ^               |                 ||
|  |                        |               v                 ||
|  |                        |    +---------------------+      ||
|  |                        |    | end_turn?  --> Return|     ||
|  |                        |    | tool_use? --> Execute|     ||
|  |                        |    +---------------------+      ||
|  |                        |               |                 ||
|  |                        +-- Tool Result <+                ||
|  |                                                          ||
|  +----------------------------------------------------------+|
|                                                              |
+==============================================================+
""")

    demo_simple_task()
    demo_single_tool()
    demo_multi_tool()
