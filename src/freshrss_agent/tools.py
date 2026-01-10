"""Tool definitions and execution logic for FreshRSS Agent.

This module defines the tools available to the Agent and provides
the execution logic for each tool.
"""

import json
from typing import Any

from .freshrss_client import Article, FreshRSSClient

# =============================================================================
# Tool Definitions (JSON Schema format for Claude)
# =============================================================================

TOOLS = [
    {
        "name": "get_unread_articles",
        "description": (
            "Get unread articles from FreshRSS. "
            "Returns article title, source, author, and content preview."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of articles to return, defaults to 20",
                    "default": 20,
                }
            },
            "required": [],
        },
    },
    {
        "name": "mark_articles_read",
        "description": "Mark specified articles as read",
        "input_schema": {
            "type": "object",
            "properties": {
                "article_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of article IDs to mark as read",
                }
            },
            "required": ["article_ids"],
        },
    },
    {
        "name": "summarize_articles",
        "description": (
            "Request article summarization. "
            "This is an instructional tool that tells the Agent the user wants summaries."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "style": {
                    "type": "string",
                    "enum": ["brief", "detailed", "bullet_points"],
                    "description": "Summary style: brief, detailed, or bullet_points",
                    "default": "brief",
                }
            },
            "required": [],
        },
    },
]


# =============================================================================
# Tool Executor
# =============================================================================

class ToolExecutor:
    """Executes tools with FreshRSS client."""

    def __init__(self, client: FreshRSSClient):
        """Initialize with FreshRSS client.

        Args:
            client: Configured FreshRSS client instance
        """
        self.client = client
        self._cached_articles: list[Article] = []

    def execute(self, tool_name: str, tool_input: dict[str, Any]) -> str:
        """Execute a tool and return the result.

        Args:
            tool_name: Name of the tool to execute
            tool_input: Tool input parameters

        Returns:
            JSON string with the result
        """
        try:
            if tool_name == "get_unread_articles":
                return self._get_unread_articles(tool_input)
            elif tool_name == "mark_articles_read":
                return self._mark_articles_read(tool_input)
            elif tool_name == "summarize_articles":
                return self._summarize_articles(tool_input)
            else:
                return json.dumps({"error": f"Unknown tool: {tool_name}"})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _get_unread_articles(self, tool_input: dict[str, Any]) -> str:
        """Get unread articles from FreshRSS."""
        limit = tool_input.get("limit", 20)
        articles = self.client.get_unread_articles(limit=limit)

        # Cache articles for later reference
        self._cached_articles = articles

        # Format for Claude
        result = []
        for article in articles:
            result.append({
                "id": article.id,
                "title": article.title,
                "feed": article.feed_title,
                "author": article.author,
                "url": article.url,
                "content_preview": article.content[:500] + "..."
                if len(article.content) > 500
                else article.content,
            })

        return json.dumps({
            "count": len(result),
            "articles": result,
        }, ensure_ascii=False, indent=2)

    def _mark_articles_read(self, tool_input: dict[str, Any]) -> str:
        """Mark articles as read."""
        article_ids = tool_input.get("article_ids", [])
        if not article_ids:
            return json.dumps({"success": False, "error": "No article IDs provided"})

        success = self.client.mark_as_read(article_ids)
        return json.dumps({
            "success": success,
            "marked_count": len(article_ids) if success else 0,
        })

    def _summarize_articles(self, tool_input: dict[str, Any]) -> str:
        """Return cached articles for summarization.

        This tool doesn't actually summarize - it returns the articles
        so Claude can generate the summary.
        """
        style = tool_input.get("style", "brief")

        if not self._cached_articles:
            return json.dumps({
                "error": "No articles cached. Please call get_unread_articles first."
            })

        # Return full content for summarization
        articles_data = []
        for article in self._cached_articles:
            articles_data.append({
                "title": article.title,
                "feed": article.feed_title,
                "content": article.content,
            })

        instruction = f"Please summarize these {len(articles_data)} articles in {style} style."
        return json.dumps({
            "style": style,
            "articles": articles_data,
            "instruction": instruction,
        }, ensure_ascii=False)
