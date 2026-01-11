"""Configuration management using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Claude API
    anthropic_api_key: str

    # FreshRSS API (Phase 1: direct API calls)
    freshrss_api_url: str
    freshrss_username: str
    freshrss_api_password: str

    # MCP Server (Phase 2)
    mcp_server_url: str = "http://localhost:8080/mcp"
    mcp_auth_token: str | None = None
    use_mcp: bool = False

    # Agent settings
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
