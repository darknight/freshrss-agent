"""CLI entry point for FreshRSS Agent.

Supports multiple modes:
1. Interactive chat mode
2. Single command execution (e.g., daily digest)

Backend options:
- Direct API mode (default)
- MCP mode (--mcp flag or USE_MCP env var)
- Agent SDK mode (--sdk flag) - uses Claude Agent SDK

Phase 2: Added MCP support via --mcp flag or USE_MCP env var.
Step 4: Added Agent SDK support via --sdk flag.
Phase 3: Added daily digest with Slack integration.
"""

import argparse
import asyncio
import sys
from pathlib import Path

from .agent import FreshRSSAgent
from .config import Settings, get_settings

# =============================================================================
# Digest Prompt (Phase 3)
# =============================================================================

DIGEST_PROMPT = """Please generate today's RSS reading digest:

1. First get ALL unread articles (use limit=100 or higher to get all)
2. Generate a statistics summary at the top:
   - Total unread count
   - Count breakdown by source/feed
3. Group articles by RSS source (feed name)
4. For each article include:
   - Title as a clickable Markdown link: [Title](URL)
   - One-sentence summary of the content

Output in Markdown format with proper headers and lists.
"""


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


async def daily_digest_async(
    agent: FreshRSSAgent,
    settings: Settings,
    send_slack: bool = False,
    output_file: str | None = None,
    quiet: bool = False,
) -> str:
    """Generate a daily digest of unread articles (async version for MCP).

    Args:
        agent: Configured FreshRSSAgent instance
        settings: Application settings
        send_slack: If True, send digest to Slack webhook
        output_file: If set, save digest to this file path
        quiet: If True, suppress terminal output

    Returns:
        The generated digest text
    """
    if not quiet:
        print("Generating daily digest...\n")

    digest = await agent.chat_async(DIGEST_PROMPT)

    # Output to terminal
    if not quiet:
        print(digest)

    # Save to file
    if output_file:
        Path(output_file).write_text(digest, encoding="utf-8")
        if not quiet:
            print(f"\nDigest saved to: {output_file}")

    # Send to Slack
    if send_slack:
        if not settings.slack_webhook_url:
            print("\nError: SLACK_WEBHOOK_URL not configured in .env")
        else:
            from .slack_client import SlackClient

            client = SlackClient(settings.slack_webhook_url)
            slack_text = client.format_for_slack(digest)
            success = await client.send_message(slack_text)
            if not quiet:
                if success:
                    print("\nDigest sent to Slack successfully!")
                else:
                    print("\nFailed to send digest to Slack")

    return digest


# =============================================================================
# Agent SDK Mode Functions
# =============================================================================


async def interactive_mode_sdk(settings) -> None:
    """Run the agent in interactive chat mode using Agent SDK.

    Args:
        settings: Application settings
    """
    from .agent_sdk import FreshRSSAgentSDK

    print("FreshRSS Agent Interactive Mode (Agent SDK)")
    print("=" * 40)
    print("Enter your question. Type 'quit' or 'exit' to quit.")
    print("=" * 40)
    print()

    async with FreshRSSAgentSDK(settings, verbose=True) as agent:
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

                # Get response from agent
                response = await agent.chat(user_input)
                print(f"\nAssistant: {response}\n")

            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"\n[Error: {e}]\n")


async def daily_digest_sdk(
    settings: Settings,
    send_slack: bool = False,
    output_file: str | None = None,
    quiet: bool = False,
) -> str:
    """Generate a daily digest using Agent SDK.

    Args:
        settings: Application settings
        send_slack: If True, send digest to Slack webhook
        output_file: If set, save digest to this file path
        quiet: If True, suppress terminal output

    Returns:
        The generated digest text
    """
    from .agent_sdk import FreshRSSAgentSDK

    if not quiet:
        print("Generating daily digest (Agent SDK)...\n")

    async with FreshRSSAgentSDK(settings, verbose=not quiet) as agent:
        digest = await agent.chat(DIGEST_PROMPT)

    # Output to terminal
    if not quiet:
        print(digest)

    # Save to file
    if output_file:
        Path(output_file).write_text(digest, encoding="utf-8")
        if not quiet:
            print(f"\nDigest saved to: {output_file}")

    # Send to Slack
    if send_slack:
        if not settings.slack_webhook_url:
            print("\nError: SLACK_WEBHOOK_URL not configured in .env")
        else:
            from .slack_client import SlackClient

            client = SlackClient(settings.slack_webhook_url)
            slack_text = client.format_for_slack(digest)
            success = await client.send_message(slack_text)
            if not quiet:
                if success:
                    print("\nDigest sent to Slack successfully!")
                else:
                    print("\nFailed to send digest to Slack")

    return digest


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="FreshRSS Agent - AI-powered RSS reader assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  freshrss-agent                    # Start interactive mode (Direct API)
  freshrss-agent --mcp              # Start interactive mode (MCP)
  freshrss-agent --sdk              # Start interactive mode (Agent SDK)
  freshrss-agent chat               # Start interactive mode
  freshrss-agent digest             # Generate daily digest
  freshrss-agent digest --slack     # Generate and send to Slack
  freshrss-agent digest --slack -q  # Send to Slack (quiet mode for cron)
  freshrss-agent digest -o out.md   # Save digest to file

Backend Modes:
  (default)   Direct API - Hand-written agent loop (agent.py)
  --mcp       MCP Mode - Uses MCP protocol for tool execution
  --sdk       Agent SDK - Uses Claude Agent SDK (agent_sdk.py)

Environment Variables:
  USE_MCP=true                      # Enable MCP mode by default
  MCP_SERVER_URL=http://...         # MCP server URL
  SLACK_WEBHOOK_URL=https://...     # Slack Incoming Webhook URL
""",
    )

    # Global arguments
    parser.add_argument(
        "--mcp",
        action="store_true",
        help="Use MCP mode instead of direct API",
    )
    parser.add_argument(
        "--sdk",
        action="store_true",
        help="Use Claude Agent SDK (requires: pip install claude-agent-sdk)",
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
        help="Output in Markdown format (legacy, now default)",
    )
    digest_parser.add_argument(
        "--slack",
        action="store_true",
        help="Send digest to Slack (requires SLACK_WEBHOOK_URL in .env)",
    )
    digest_parser.add_argument(
        "--output",
        "-o",
        type=str,
        metavar="FILE",
        help="Save digest to file",
    )
    digest_parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress terminal output (useful for cron jobs)",
    )

    args = parser.parse_args()

    # Load settings
    try:
        settings = get_settings()
    except Exception as e:
        print(f"Configuration error: {e}")
        print("Please ensure .env file is created with required environment variables")
        sys.exit(1)

    # Determine mode
    if args.sdk:
        # Agent SDK mode
        asyncio.run(main_sdk(args, settings))
    elif args.mcp or settings.use_mcp:
        # MCP mode
        asyncio.run(main_async(args, settings))
    else:
        # Direct API mode (default)
        with FreshRSSAgent(settings, verbose=True, use_mcp=False) as agent:
            if args.command == "digest":
                output_format = "markdown" if args.markdown else "text"
                daily_digest(agent, output_format)
            else:
                # Default to interactive mode
                interactive_mode(agent)


async def main_async(args, settings) -> None:
    """Async main for MCP mode."""
    quiet = getattr(args, "quiet", False)
    async with FreshRSSAgent(settings, verbose=not quiet, use_mcp=True) as agent:
        if args.command == "digest":
            await daily_digest_async(
                agent,
                settings,
                send_slack=getattr(args, "slack", False),
                output_file=getattr(args, "output", None),
                quiet=quiet,
            )
        else:
            # Default to interactive mode
            await interactive_mode_async(agent)


async def main_sdk(args, settings) -> None:
    """Async main for Agent SDK mode."""
    try:
        from .agent_sdk import check_sdk_available

        check_sdk_available()
    except ImportError as e:
        print(f"Error: {e}")
        print("\nTo use Agent SDK mode, install the SDK:")
        print("  pip install claude-agent-sdk")
        print("  or: uv sync --extra agent-sdk")
        sys.exit(1)

    if args.command == "digest":
        await daily_digest_sdk(
            settings,
            send_slack=getattr(args, "slack", False),
            output_file=getattr(args, "output", None),
            quiet=getattr(args, "quiet", False),
        )
    else:
        # Default to interactive mode
        await interactive_mode_sdk(settings)


if __name__ == "__main__":
    main()
