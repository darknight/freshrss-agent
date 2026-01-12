# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Language Preferences

- **Source code, comments, and documentation**: English only
- **Conversation with user**: Simplified Chinese

## Build & Run Commands

```bash
# Install dependencies
uv sync

# Run the agent (interactive mode - Direct API)
uv run freshrss-agent

# Run the agent (interactive mode - Agent SDK)
uv sync --extra agent-sdk
uv run freshrss-agent --sdk

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

- `agent.py`: Hand-written Agent Loop - loops calling Claude until `stop_reason == "end_turn"`, executing tools when `stop_reason == "tool_use"`. Supports Direct API and MCP modes.
- `agent_sdk.py`: Agent SDK implementation - same functionality using Claude Agent SDK with in-process MCP tools
- `tools.py`: Defines tool schemas (JSON Schema format) and `ToolExecutor`/`MCPToolExecutor` classes for tool execution
- `freshrss_client.py`: HTTP client for FreshRSS Google Reader API (login, get_unread_articles, mark_as_read)
- `mcp_client.py`: MCP protocol client using Streamable HTTP transport, with dynamic tool discovery
- `config.py`: Uses pydantic-settings to load configuration from `.env`

**Learning Examples in `examples/`:**
- `01_basic_tool_use.py`: Demonstrates single/multiple tool calls without agent loop
- `02_simple_agent_loop.py`: Standalone agent loop example without FreshRSS dependency
- `03_mcp_client.py`: MCP client integration example
- `04_agent_sdk_basics.py`: Claude Agent SDK basics and comparison
- `05_agent_sdk_custom_tools.py`: Custom tools and hooks with Agent SDK

**Documentation in `docs/`:**
- `mcp-agent-architecture.md`: Phase 2 - MCP-based agent architecture deep dive
- `agent-sdk-architecture.md`: Step 4 - Agent SDK architecture deep dive

## Project Status

- Phase 1 (completed): Direct FreshRSS API integration
- Phase 2 (completed): MCP client integration
- Phase 3 (planned): Daily digest automation with scheduling
