# FreshRSS Agent

A learning project for understanding AI Agent concepts through FreshRSS integration.

## Learning Path

```
Step 1: Understand Tool Use principles           ✅
        ↓
Step 2: Hand-write Agent Loop (Anthropic SDK)    ✅
        ↓
Step 3: Understand MCP protocol                  ✅
        ↓
Step 4: Use Claude Agent SDK                     ✅
```

The goal is to understand HOW agents work by building one from scratch,
then use the Agent SDK for production applications.

## Quick Start

### Installation

```bash
# Clone the project
git clone https://github.com/yourusername/freshrss-agent.git
cd freshrss-agent

# Install dependencies
uv sync

# Configure environment variables
cp .env.example .env
# Edit .env and fill in your configuration
```

### Run Learning Examples

```bash
# Example 1: Tool Use basics
uv run python examples/01_basic_tool_use.py

# Example 2: Agent Loop
uv run python examples/02_simple_agent_loop.py

# Example 3: MCP client integration
uv run python examples/03_mcp_client.py

# Example 4-5: Claude Agent SDK (requires extra dependency)
uv sync --extra agent-sdk
uv run python examples/04_agent_sdk_basics.py
uv run python examples/05_agent_sdk_custom_tools.py
```

### Run Agent

```bash
# Interactive mode (Direct API - hand-written agent loop)
uv run freshrss-agent

# Interactive mode (MCP - uses MCP protocol)
uv run freshrss-agent --mcp

# Interactive mode (Agent SDK - uses Claude Agent SDK)
uv sync --extra agent-sdk  # Install SDK first
uv run freshrss-agent --sdk

# Generate daily digest
uv run freshrss-agent digest

# Markdown format digest
uv run freshrss-agent digest --markdown
```

## Project Structure

```
freshrss-agent/
├── pyproject.toml
├── .env.example
├── README.md
├── src/freshrss_agent/
│   ├── __init__.py
│   ├── main.py              # CLI entry point
│   ├── agent.py             # Hand-written agent loop (Phase 1-2)
│   ├── agent_sdk.py         # Agent SDK implementation (Step 4)
│   ├── tools.py             # Tool definitions and execution logic
│   ├── freshrss_client.py   # FreshRSS API client
│   ├── mcp_client.py        # MCP protocol client (Phase 2)
│   └── config.py            # Configuration management
├── examples/
│   ├── 01_basic_tool_use.py         # Learn Tool Use basics
│   ├── 02_simple_agent_loop.py      # Learn Agent Loop
│   ├── 03_mcp_client.py             # Learn MCP client integration
│   ├── 04_agent_sdk_basics.py       # Learn Claude Agent SDK basics
│   └── 05_agent_sdk_custom_tools.py # Learn custom tools and hooks
└── docs/
    ├── mcp-agent-architecture.md    # Phase 2: MCP architecture deep dive
    └── agent-sdk-architecture.md    # Step 4: Agent SDK architecture deep dive
```

## Core Concepts

### Tool Use

Claude can call external functions through Tool Use. The flow:

1. Define tool schema (JSON Schema format)
2. Claude returns `tool_use` block
3. Execute tool, send result back as `tool_result`

### Agent Loop

The core pattern of Agents:

```python
while True:
    response = call_claude(messages)

    if response.stop_reason == "end_turn":
        return extract_text(response)

    if response.stop_reason == "tool_use":
        results = execute_tools(response)
        messages.append(results)
        continue
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Claude API key |
| `FRESHRSS_API_URL` | FreshRSS API URL |
| `FRESHRSS_USERNAME` | FreshRSS username |
| `FRESHRSS_API_PASSWORD` | FreshRSS API password |
| `MCP_SERVER_URL` | MCP server URL (Phase 2) |
| `MCP_AUTH_TOKEN` | MCP authentication token (optional) |
| `USE_MCP` | Enable MCP mode (true/false) |

## Implementation Phases

- [x] Phase 1: Basic Agent (direct FreshRSS API calls)
- [x] Phase 2: MCP client integration
- [ ] Phase 3: Daily digest automation

## License

MIT
