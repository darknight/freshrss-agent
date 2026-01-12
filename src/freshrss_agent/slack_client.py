"""Slack Incoming Webhook client for sending digest notifications.

This module provides a simple client for sending messages to Slack
via Incoming Webhooks. No additional dependencies needed - uses httpx.

Usage:
    client = SlackClient(webhook_url)
    await client.send_message("Hello from FreshRSS Agent!")
"""

import re

import httpx


class SlackClient:
    """Slack Incoming Webhook client.

    Sends messages to a Slack channel via Incoming Webhook URL.
    Supports converting standard Markdown to Slack's mrkdwn format.
    """

    def __init__(self, webhook_url: str):
        """Initialize the Slack client.

        Args:
            webhook_url: Slack Incoming Webhook URL
                         (e.g., https://hooks.slack.com/services/T.../B.../xxx)
        """
        self.webhook_url = webhook_url

    async def send_message(self, text: str) -> bool:
        """Send a message to Slack.

        Args:
            text: Message text (supports mrkdwn format)

        Returns:
            True if successful, False otherwise
        """
        payload = {
            "text": text,
            "mrkdwn": True,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    timeout=30.0,
                )
                return response.status_code == 200
            except httpx.HTTPError as e:
                print(f"Failed to send Slack message: {e}")
                return False

    def format_for_slack(self, markdown_text: str) -> str:
        """Convert standard Markdown to Slack mrkdwn format.

        Slack's mrkdwn is similar to Markdown but has some differences:
        - Links: [text](url) -> <url|text>
        - Bold: **text** -> *text*
        - Headers: # Header -> *Header*

        Args:
            markdown_text: Standard Markdown text

        Returns:
            Slack mrkdwn formatted text
        """
        text = markdown_text

        # Convert Markdown links to Slack format: [text](url) -> <url|text>
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"<\2|\1>", text)

        # Convert bold: **text** -> *text*
        text = re.sub(r"\*\*([^*]+)\*\*", r"*\1*", text)

        # Convert headers: ## Header -> *Header*
        text = re.sub(r"^#{1,6}\s+(.+)$", r"*\1*", text, flags=re.MULTILINE)

        return text


async def send_test_message(webhook_url: str) -> None:
    """Send a test message to verify webhook configuration.

    Args:
        webhook_url: Slack Incoming Webhook URL
    """
    client = SlackClient(webhook_url)
    test_message = (
        "*FreshRSS Agent* - Test message\n\n"
        "If you see this, Slack integration is working!"
    )

    success = await client.send_message(test_message)
    if success:
        print("Test message sent successfully!")
    else:
        print("Failed to send test message. Please check your webhook URL.")
