"""Simplified FreshRSS API client using Google Reader API.

This is a learning-focused implementation that covers the core concepts:
- Authentication with Google Reader API
- Fetching unread articles
- Marking articles as read

Reference: https://freshrss.github.io/FreshRSS/en/developers/06_GoogleReader_API.html
"""

from dataclasses import dataclass

import httpx


@dataclass
class Article:
    """Represents an RSS article."""

    id: str
    title: str
    url: str
    feed_title: str
    author: str
    content: str
    published: int  # Unix timestamp


class FreshRSSClient:
    """Simple FreshRSS client using Google Reader API."""

    def __init__(self, api_url: str, username: str, password: str):
        """Initialize the client.

        Args:
            api_url: FreshRSS API URL (e.g., https://freshrss.example.com/api/greader.php)
            username: FreshRSS username
            password: API password (set in FreshRSS settings)
        """
        self.api_url = api_url.rstrip("/")
        self.username = username
        self.password = password
        self._auth_token: str | None = None
        self._client = httpx.Client(timeout=30.0)

    def login(self) -> str:
        """Authenticate and get auth token.

        Returns:
            Auth token string

        Raises:
            Exception: If authentication fails
        """
        response = self._client.post(
            f"{self.api_url}/accounts/ClientLogin",
            data={
                "Email": self.username,
                "Passwd": self.password,
            },
        )
        response.raise_for_status()

        # Parse response: Auth=xxx\nSID=xxx\n...
        for line in response.text.strip().split("\n"):
            if line.startswith("Auth="):
                self._auth_token = line[5:]
                return self._auth_token

        raise Exception("Failed to get auth token from response")

    def _ensure_auth(self) -> None:
        """Ensure we have a valid auth token."""
        if not self._auth_token:
            self.login()

    def _get_headers(self) -> dict[str, str]:
        """Get headers with auth token."""
        self._ensure_auth()
        return {"Authorization": f"GoogleLogin auth={self._auth_token}"}

    def get_unread_articles(self, limit: int = 20) -> list[Article]:
        """Get unread articles.

        Args:
            limit: Maximum number of articles to fetch

        Returns:
            List of Article objects
        """
        response = self._client.get(
            f"{self.api_url}/reader/api/0/stream/contents/user/-/state/com.google/reading-list",
            params={
                "xt": "user/-/state/com.google/read",  # Exclude read items
                "n": limit,
                "output": "json",
            },
            headers=self._get_headers(),
        )
        response.raise_for_status()

        data = response.json()
        articles = []

        for item in data.get("items", []):
            articles.append(
                Article(
                    id=item.get("id", ""),
                    title=item.get("title", ""),
                    url=item.get("canonical", [{}])[0].get("href", "")
                    if item.get("canonical")
                    else item.get("alternate", [{}])[0].get("href", ""),
                    feed_title=item.get("origin", {}).get("title", ""),
                    author=item.get("author", ""),
                    content=item.get("summary", {}).get("content", ""),
                    published=item.get("published", 0),
                )
            )

        return articles

    def mark_as_read(self, article_ids: list[str]) -> bool:
        """Mark articles as read.

        Args:
            article_ids: List of article IDs to mark as read

        Returns:
            True if successful
        """
        if not article_ids:
            return True

        # Need to get edit token first
        token_response = self._client.get(
            f"{self.api_url}/reader/api/0/token",
            headers=self._get_headers(),
        )
        token_response.raise_for_status()
        edit_token = token_response.text.strip()

        # Mark as read
        response = self._client.post(
            f"{self.api_url}/reader/api/0/edit-tag",
            data={
                "i": article_ids,
                "a": "user/-/state/com.google/read",
                "T": edit_token,
            },
            headers=self._get_headers(),
        )
        response.raise_for_status()

        return response.text.strip() == "OK"

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
