"""CLI entry point for FreshRSS Agent.

Supports two modes:
1. Interactive chat mode
2. Single command execution (e.g., daily digest)

Phase 2: Added MCP support via --mcp flag or USE_MCP env var.
"""

import argparse
import asyncio
import sys

from .agent import FreshRSSAgent
from .config import get_settings


def interactive_mode(agent: FreshRSSAgent) -> None:
    """Run the agent in interactive chat mode (sync version).

    Args:
        agent: Configured FreshRSSAgent instance
    """
    mode_label = "MCP Mode" if agent.use_mcp else "Direct API Mode"
    print(f"FreshRSS Agent Interactive Mode ({mode_label})")
    print("=" * 40)
    print("Enter your question. Type 'quit' or 'exit' to quit.")
    print("Type 'reset' to reset conversation history.")
    print("=" * 40)
    print()

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break

            if user_input.lower() == "reset":
                agent.reset()
                print("[Conversation history reset]\n")
                continue

            # Get response from agent
            response = agent.chat(user_input)
            print(f"\nAssistant: {response}\n")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\n[Error: {e}]\n")


async def interactive_mode_async(agent: FreshRSSAgent) -> None:
    """Run the agent in interactive chat mode (async version for MCP).

    Args:
        agent: Configured FreshRSSAgent instance
    """
    mode_label = "MCP Mode" if agent.use_mcp else "Direct API Mode"
    print(f"FreshRSS Agent Interactive Mode ({mode_label})")
    print("=" * 40)
    print("Enter your question. Type 'quit' or 'exit' to quit.")
    print("Type 'reset' to reset conversation history.")
    print("=" * 40)
    print()

    while True:
        try:
            user_input = await asyncio.get_event_loop().run_in_executor(
                None, lambda: input("You: ").strip()
            )

            if not user_input:
                continue

            if user_input.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break

            if user_input.lower() == "reset":
                agent.reset()
                print("[Conversation history reset]\n")
                continue

            # Get response from agent
            response = await agent.chat_async(user_input)
            print(f"\nAssistant: {response}\n")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\n[Error: {e}]\n")


def daily_digest(agent: FreshRSSAgent, output_format: str = "text") -> None:
    """Generate a daily digest of unread articles (sync version).

    Args:
        agent: Configured FreshRSSAgent instance
        output_format: Output format (text, markdown)
    """
    print("Generating daily digest...\n")

    prompt = """Please generate today's RSS reading digest:
1. First get all unread articles
2. Categorize by source, provide a brief summary for each article
3. Finally recommend the top 3 most worth reading articles for today"""

    if output_format == "markdown":
        prompt += "\n\nPlease output in Markdown format."

    response = agent.chat(prompt)
    print(response)


async def daily_digest_async(agent: FreshRSSAgent, output_format: str = "text") -> None:
    """Generate a daily digest of unread articles (async version for MCP).

    Args:
        agent: Configured FreshRSSAgent instance
        output_format: Output format (text, markdown)
    """
    print("Generating daily digest...\n")

    prompt = """Please generate today's RSS reading digest:
1. First get all unread articles
2. Categorize by source, provide a brief summary for each article
3. Finally recommend the top 3 most worth reading articles for today"""

    if output_format == "markdown":
        prompt += "\n\nPlease output in Markdown format."

    response = await agent.chat_async(prompt)
    print(response)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="FreshRSS Agent - AI-powered RSS reader assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  freshrss-agent                    # Start interactive mode (Direct API)
  freshrss-agent --mcp              # Start interactive mode (MCP)
  freshrss-agent chat               # Start interactive mode
  freshrss-agent digest             # Generate daily digest
  freshrss-agent digest --markdown  # Generate Markdown format digest

Environment Variables:
  USE_MCP=true                      # Enable MCP mode by default
  MCP_SERVER_URL=http://...         # MCP server URL
""",
    )

    # Global arguments
    parser.add_argument(
        "--mcp",
        action="store_true",
        help="Use MCP mode instead of direct API",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Chat command (default)
    subparsers.add_parser("chat", help="Interactive chat mode")

    # Digest command
    digest_parser = subparsers.add_parser("digest", help="Generate daily digest")
    digest_parser.add_argument(
        "--markdown",
        "-m",
        action="store_true",
        help="Output in Markdown format",
    )

    args = parser.parse_args()

    # Load settings
    try:
        settings = get_settings()
    except Exception as e:
        print(f"Configuration error: {e}")
        print("Please ensure .env file is created with required environment variables")
        sys.exit(1)

    # Determine MCP mode
    use_mcp = args.mcp or settings.use_mcp

    if use_mcp:
        # Run async main for MCP mode
        asyncio.run(main_async(args, settings))
    else:
        # Run sync main for Direct API mode
        with FreshRSSAgent(settings, verbose=True, use_mcp=False) as agent:
            if args.command == "digest":
                output_format = "markdown" if args.markdown else "text"
                daily_digest(agent, output_format)
            else:
                # Default to interactive mode
                interactive_mode(agent)


async def main_async(args, settings) -> None:
    """Async main for MCP mode."""
    async with FreshRSSAgent(settings, verbose=True, use_mcp=True) as agent:
        if args.command == "digest":
            output_format = "markdown" if getattr(args, "markdown", False) else "text"
            await daily_digest_async(agent, output_format)
        else:
            # Default to interactive mode
            await interactive_mode_async(agent)


if __name__ == "__main__":
    main()
