# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Language Preferences

- **Source code, comments, and documentation**: English only
- **Conversation with user**: Simplified Chinese

## Build & Run Commands

```bash
# Install dependencies
uv sync

# Run the agent (interactive mode)
uv run freshrss-agent

# Run the agent (daily digest)
uv run freshrss-agent digest

# Run learning examples
uv run python examples/01_basic_tool_use.py
uv run python examples/02_simple_agent_loop.py

# Lint
uv run ruff check src/

# Type check (if needed)
uv run python -m py_compile src/freshrss_agent/*.py
```

## Architecture

This is a learning project demonstrating AI Agent patterns with FreshRSS integration.

**Core Flow:**
```
User Input → FreshRSSAgent.chat() → Agent Loop → Claude API
                                        ↓
                              Tool execution (if tool_use)
                                        ↓
                              Response to user
```

**Key Components:**

- `agent.py`: Implements the Agent Loop - the core pattern that loops calling Claude until `stop_reason == "end_turn"`, executing tools when `stop_reason == "tool_use"`
- `tools.py`: Defines tool schemas (JSON Schema format) and `ToolExecutor` class that dispatches tool calls to `freshrss_client.py`
- `freshrss_client.py`: HTTP client for FreshRSS Google Reader API (login, get_unread_articles, mark_as_read)
- `config.py`: Uses pydantic-settings to load configuration from `.env`

**Learning Examples in `examples/`:**
- `01_basic_tool_use.py`: Demonstrates single/multiple tool calls without agent loop
- `02_simple_agent_loop.py`: Standalone agent loop example without FreshRSS dependency

## Project Status

- Phase 1 (current): Direct FreshRSS API integration
- Phase 2 (planned): MCP client integration
- Phase 3 (planned): Daily digest automation with scheduling
