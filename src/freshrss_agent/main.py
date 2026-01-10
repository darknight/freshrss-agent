"""CLI entry point for FreshRSS Agent.

Supports two modes:
1. Interactive chat mode
2. Single command execution (e.g., daily digest)
"""

import argparse
import sys

from .agent import FreshRSSAgent
from .config import get_settings


def interactive_mode(agent: FreshRSSAgent) -> None:
    """Run the agent in interactive chat mode.

    Args:
        agent: Configured FreshRSSAgent instance
    """
    print("FreshRSS Agent Interactive Mode")
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


def daily_digest(agent: FreshRSSAgent, output_format: str = "text") -> None:
    """Generate a daily digest of unread articles.

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


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="FreshRSS Agent - AI-powered RSS reader assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  freshrss-agent                    # Start interactive mode
  freshrss-agent chat               # Start interactive mode
  freshrss-agent digest             # Generate daily digest
  freshrss-agent digest --markdown  # Generate Markdown format digest
""",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Chat command (default)
    subparsers.add_parser("chat", help="Interactive chat mode")

    # Digest command
    digest_parser = subparsers.add_parser("digest", help="Generate daily digest")
    digest_parser.add_argument(
        "--markdown", "-m",
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

    # Create and run agent
    with FreshRSSAgent(settings) as agent:
        if args.command == "digest":
            output_format = "markdown" if args.markdown else "text"
            daily_digest(agent, output_format)
        else:
            # Default to interactive mode
            interactive_mode(agent)


if __name__ == "__main__":
    main()
