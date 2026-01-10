# FreshRSS Agent

A learning project for understanding AI Agent concepts through FreshRSS integration.

## Learning Path

```
Step 1: Understand Tool Use principles
        ↓
Step 2: Hand-write Agent Loop (using Anthropic SDK)
        ↓
Step 3: Understand MCP protocol
        ↓
Step 4: Use Claude Agent SDK (understand what it does for you)
```

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
```

### Run Agent

```bash
# Interactive mode
uv run freshrss-agent

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
│   ├── agent.py             # Agent loop core implementation
│   ├── tools.py             # Tool definitions and execution logic
│   ├── freshrss_client.py   # FreshRSS API client
│   └── config.py            # Configuration management
└── examples/
    ├── 01_basic_tool_use.py     # Learn Tool Use basics
    └── 02_simple_agent_loop.py  # Learn Agent Loop
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

## Implementation Phases

- [x] Phase 1: Basic Agent (direct FreshRSS API calls)
- [ ] Phase 2: MCP client integration
- [ ] Phase 3: Daily digest automation

## License

MIT
