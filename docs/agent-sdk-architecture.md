# Agent SDK Architecture Deep Dive

This document compares the hand-written MCP mode (Phase 2) with the Claude Agent SDK mode (Learning Step 4), explaining what the SDK handles for you and what remains your responsibility.

> **Note on terminology:**
> - **Phase 1-3**: Implementation phases (features being built)
> - **Step 1-4**: Learning path (concepts being learned)
>
> Agent SDK is **Step 4** of the learning path, not a new implementation phase.
> Phase 3 (Daily digest automation) is still planned for future implementation.

## 1. High-Level Architecture Comparison

### Phase 2: Hand-Written MCP Mode (agent.py + mcp_client.py)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              User Input                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         FreshRSSAgent                                    │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    YOU implement all of this:                      │  │
│  │                                                                    │  │
│  │  1. MCP Connection Management                                     │  │
│  │     └── connect_mcp() / disconnect_mcp()                          │  │
│  │                                                                    │  │
│  │  2. Tool Discovery                                                 │  │
│  │     └── list_tools() → convert_mcp_tools_to_anthropic()           │  │
│  │                                                                    │  │
│  │  3. Agent Loop                                                     │  │
│  │     └── while True: call_claude() → check_stop_reason()           │  │
│  │                                                                    │  │
│  │  4. Tool Execution                                                 │  │
│  │     └── MCPToolExecutor.execute_async()                           │  │
│  │                                                                    │  │
│  │  5. Message History Management                                     │  │
│  │     └── self.messages.append(...)                                 │  │
│  │                                                                    │  │
│  │  6. Error Handling & Cleanup                                       │  │
│  │     └── try/finally, context managers                             │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         FreshRSSMCPClient                                │
│                    (mcp_client.py - YOU implement)                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           MCP Server                                     │
│                    (External - 5 tools available)                        │
└─────────────────────────────────────────────────────────────────────────┘
```

### Agent SDK: Agent SDK Mode (agent_sdk.py)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              User Input                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        FreshRSSAgentSDK                                  │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    YOU only need to:                               │  │
│  │                                                                    │  │
│  │  1. Provide MCP Server configuration                              │  │
│  │     └── {"url": "http://..."} or {"command": "..."}               │  │
│  │                                                                    │  │
│  │  2. Set system prompt (optional)                                   │  │
│  │     └── ClaudeAgentOptions(system_prompt="...")                   │  │
│  │                                                                    │  │
│  │  3. Process response messages                                      │  │
│  │     └── async for msg in client.receive_response()                │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Claude Agent SDK                                  │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    SDK handles all of this:                        │  │
│  │                                                                    │  │
│  │  ✓ MCP Connection Management (auto connect/disconnect)            │  │
│  │  ✓ Tool Discovery (auto list_tools from Server)                   │  │
│  │  ✓ Format Conversion (MCP → Anthropic format)                     │  │
│  │  ✓ Agent Loop (no while True needed)                              │  │
│  │  ✓ Tool Execution (auto call_tool)                                │  │
│  │  ✓ Message History (auto managed)                                 │  │
│  │  ✓ Error Handling & Cleanup                                       │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           MCP Server                                     │
│                    (External - 5 tools discovered automatically)         │
└─────────────────────────────────────────────────────────────────────────┘
```

## 2. What Changed vs What Stayed the Same

### What CHANGED (SDK handles now)

| Aspect | Phase 2 (Hand-Written) | Agent SDK (Agent SDK) |
|--------|------------------------|---------------------|
| **MCP Connection** | Manual `connect()`/`close()` | Automatic |
| **Tool Discovery** | Manual `list_tools()` call | Automatic |
| **Format Conversion** | Manual `convert_mcp_tools_to_anthropic()` | Automatic |
| **Agent Loop** | Manual `while True` loop | Built-in |
| **Tool Execution** | Manual `call_tool()` dispatch | Automatic |
| **Message History** | Manual `messages.append()` | Automatic |
| **Error Handling** | Manual try/except/finally | Built-in |
| **Context Management** | Manual `__aenter__`/`__aexit__` | Built-in |

### What STAYED THE SAME

| Aspect | Description |
|--------|-------------|
| **MCP Server** | Same external MCP Server, no changes needed |
| **Tool Definitions** | Still defined on MCP Server side |
| **Dynamic Discovery** | Tools still discovered from Server (not hardcoded) |
| **FreshRSS API** | Still called by MCP Server, not by Agent |
| **System Prompt** | Still your responsibility to define |
| **Response Processing** | Still need to handle response messages |

## 3. What SDK Implements vs What You Implement

### SDK Implements (You DON'T write this code)

```python
# ═══════════════════════════════════════════════════════════════════════
# ALL OF THIS IS HANDLED BY THE SDK - YOU DON'T WRITE ANY OF IT
# ═══════════════════════════════════════════════════════════════════════

# 1. MCP Connection (mcp_client.py equivalent)
class InternalMCPClient:
    async def connect(self):
        self._context_manager = streamablehttp_client(url, headers)
        self._streams = await self._context_manager.__aenter__()
        self._session = ClientSession(read_stream, write_stream)
        await self._session.initialize()

    async def list_tools(self) -> list[Tool]:
        return await self._session.list_tools()

    async def call_tool(self, name: str, args: dict) -> Result:
        return await self._session.call_tool(name, args)

    async def close(self):
        await self._session.__aexit__(None, None, None)
        await self._context_manager.__aexit__(None, None, None)

# 2. Format Conversion
def convert_mcp_to_anthropic(mcp_tools):
    return [{"name": t.name, "input_schema": t.inputSchema, ...} for t in mcp_tools]

# 3. Agent Loop (agent.py equivalent)
async def run_agent_loop(prompt, tools, messages):
    while True:
        response = await call_claude(tools=tools, messages=messages)
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            return extract_text(response)

        elif response.stop_reason == "tool_use":
            for block in response.content:
                if isinstance(block, ToolUseBlock):
                    result = await mcp_client.call_tool(block.name, block.input)
                    messages.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

# 4. Resource Management
async def __aenter__(self):
    await self.mcp_client.connect()
    self.tools = await self.mcp_client.list_tools()
    return self

async def __aexit__(self, *args):
    await self.mcp_client.close()
```

### You Implement (Your responsibility)

```python
# ═══════════════════════════════════════════════════════════════════════
# THIS IS WHAT YOU WRITE - MINIMAL CODE
# ═══════════════════════════════════════════════════════════════════════

# 1. Configuration
options = ClaudeAgentOptions(
    system_prompt="You are an RSS reading assistant...",
    mcp_servers={
        "freshrss": {"url": "http://localhost:8080/mcp"}
        # OR
        # "freshrss": {"command": "freshrss-mcp-server", "args": [...]}
    },
    max_turns=10,
)

# 2. Client Usage
async with ClaudeSDKClient(options) as client:
    await client.query("Show me my articles")

    # 3. Response Processing
    async for message in client.receive_response():
        if hasattr(message, "content"):
            for block in message.content:
                if hasattr(block, "text"):
                    print(block.text)
```

## 4. Core Code Comparison

### Phase 2: agent.py (~150 lines of agent logic)

```python
class FreshRSSAgent:
    def __init__(self, settings, use_mcp=True):
        # Initialize MCP client
        self._mcp_client = None
        self._tools = []
        self.messages = []

    async def connect_mcp(self):
        # 1. Create client
        self._mcp_client = FreshRSSMCPClient(url, token)

        # 2. Connect
        await self._mcp_client.connect()

        # 3. Discover tools
        mcp_tools = await self._mcp_client.list_tools()

        # 4. Convert format
        self._tools = convert_mcp_tools_to_anthropic(mcp_tools)

    async def chat_async(self, user_message):
        self.messages.append({"role": "user", "content": user_message})

        # Manual agent loop
        while True:
            response = self._call_claude()
            self.messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                return self._extract_text(response.content)

            elif response.stop_reason == "tool_use":
                # Manual tool execution
                results = await self._process_tool_calls_async(response.content)
                self.messages.append({"role": "user", "content": results})

    async def _process_tool_calls_async(self, content):
        results = []
        for block in content:
            if isinstance(block, ToolUseBlock):
                # Manual MCP call
                result = await self._mcp_client.call_tool(block.name, block.input)
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })
        return results

    async def disconnect_mcp(self):
        if self._mcp_client:
            await self._mcp_client.close()
```

### Agent SDK: agent_sdk.py (~50 lines of agent logic)

```python
class FreshRSSAgentSDK:
    def __init__(self, settings):
        # Just configuration - no MCP client code!
        self._options = ClaudeAgentOptions(
            system_prompt="You are an RSS reading assistant...",
            mcp_servers={
                "freshrss": {"url": settings.mcp_server_url}
            },
            max_turns=10,
        )
        self._client = None

    async def chat(self, user_message):
        await self._client.query(user_message)

        result_text = ""
        async for message in self._client.receive_response():
            if hasattr(message, "content"):
                for block in message.content:
                    if hasattr(block, "text"):
                        result_text = block.text
            elif isinstance(message, ResultMessage):
                result_text = message.result

        return result_text

    async def __aenter__(self):
        self._client = ClaudeSDKClient(options=self._options)
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.__aexit__(*args)
```

### Code Reduction Summary

| Component | Phase 2 | Agent SDK | Reduction |
|-----------|---------|---------|-----------|
| MCP Client | ~100 lines (mcp_client.py) | 0 lines | 100% |
| Agent Loop | ~50 lines | 0 lines | 100% |
| Tool Execution | ~30 lines | 0 lines | 100% |
| Configuration | ~20 lines | ~15 lines | 25% |
| Response Handling | ~20 lines | ~15 lines | 25% |
| **Total** | **~220 lines** | **~30 lines** | **~85%** |

## 5. Data Flow Comparison

### Phase 2: Manual Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Phase 2 Data Flow                                │
│                    (Every arrow is YOUR code)                            │
└─────────────────────────────────────────────────────────────────────────┘

User: "Show me my articles"
         │
         ▼
┌─────────────────┐
│ messages.append │ ◄── YOU write this
└────────┬────────┘
         ▼
┌─────────────────┐     ┌─────────────────┐
│  _call_claude() │────▶│   Claude API    │
└────────┬────────┘     └────────┬────────┘
         │                       │
         │◄──────────────────────┘
         ▼
┌─────────────────────────┐
│ if stop_reason ==       │ ◄── YOU write this
│   "tool_use":           │
│     _process_tool_calls │
└────────┬────────────────┘
         ▼
┌─────────────────────────┐
│ mcp_client.call_tool()  │ ◄── YOU write this
└────────┬────────────────┘
         ▼
┌─────────────────┐     ┌─────────────────┐
│   MCP Client    │────▶│   MCP Server    │
│   (YOUR code)   │     │                 │
└────────┬────────┘     └────────┬────────┘
         │                       │
         │◄──────────────────────┘
         ▼
┌─────────────────────────┐
│ messages.append(        │ ◄── YOU write this
│   tool_result)          │
└────────┬────────────────┘
         ▼
┌─────────────────────────┐
│ continue while loop     │ ◄── YOU write this
└─────────────────────────┘
```

### Agent SDK: SDK Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Agent SDK Data Flow                                │
│                    (Only dotted arrows are YOUR code)                    │
└─────────────────────────────────────────────────────────────────────────┘

User: "Show me my articles"
         ┊
         ▼
┌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌┐
┊ client.query()   ┊ ◄╌╌ YOU write this (1 line)
└╌╌╌╌╌╌╌╌┬╌╌╌╌╌╌╌╌╌┘
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         CLAUDE AGENT SDK                                 │
│                    (All of this is automatic)                            │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  messages.append(user_message)                                      │ │
│  │           │                                                         │ │
│  │           ▼                                                         │ │
│  │  ┌─────────────────┐     ┌─────────────────┐                       │ │
│  │  │  call_claude()  │────▶│   Claude API    │                       │ │
│  │  └────────┬────────┘     └────────┬────────┘                       │ │
│  │           │◄──────────────────────┘                                 │ │
│  │           ▼                                                         │ │
│  │  if stop_reason == "tool_use":                                      │ │
│  │           │                                                         │ │
│  │           ▼                                                         │ │
│  │  ┌─────────────────┐     ┌─────────────────┐                       │ │
│  │  │   call_tool()   │────▶│   MCP Server    │                       │ │
│  │  └────────┬────────┘     └────────┬────────┘                       │ │
│  │           │◄──────────────────────┘                                 │ │
│  │           ▼                                                         │ │
│  │  messages.append(tool_result)                                       │ │
│  │           │                                                         │ │
│  │           ▼                                                         │ │
│  │  continue loop until stop_reason == "end_turn"                      │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
         ┊
         ▼
┌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌┐
┊ async for msg in       ┊
┊   receive_response():  ┊ ◄╌╌ YOU write this (handle results)
┊     print(msg)         ┊
└╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌┘
```

## 6. MCP Server Configuration

### Phase 2: Manual Connection Code

```python
# YOU write all of this in mcp_client.py

class FreshRSSMCPClient:
    def __init__(self, server_url, auth_token=None):
        self.server_url = server_url
        self.auth_token = auth_token
        self._session = None
        self._streams = None

    async def connect(self):
        headers = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        self._context_manager = streamablehttp_client(
            self.server_url,
            headers=headers,
        )
        self._streams = await self._context_manager.__aenter__()
        read_stream, write_stream, _ = self._streams

        self._session = ClientSession(read_stream, write_stream)
        await self._session.__aenter__()
        await self._session.initialize()
```

### Agent SDK: Just Configuration

```python
# YOU only provide configuration - SDK does the rest

# Option 1: HTTP/SSE URL (connect to running server)
options = ClaudeAgentOptions(
    mcp_servers={
        "freshrss": {
            "url": "http://localhost:8080/mcp",
            "headers": {"Authorization": "Bearer token"}  # Optional
        }
    }
)

# Option 2: stdio command (SDK launches subprocess)
options = ClaudeAgentOptions(
    mcp_servers={
        "freshrss": {
            "command": "freshrss-mcp-server",
            "args": ["--url", "http://freshrss.example.com"]
        }
    }
)
```

## 7. Tool Discovery Comparison

### Phase 2: Manual Discovery

```python
# 1. Call list_tools
mcp_tools = await self._mcp_client.list_tools()
# Returns: [{"name": "get_unread_articles", "inputSchema": {...}}, ...]

# 2. Convert format (MCP uses camelCase, Anthropic uses snake_case)
def convert_mcp_tools_to_anthropic(mcp_tools):
    return [
        {
            "name": tool["name"],
            "description": tool["description"],
            "input_schema": tool["inputSchema"],  # Key conversion!
        }
        for tool in mcp_tools
    ]

anthropic_tools = convert_mcp_tools_to_anthropic(mcp_tools)

# 3. Pass to Claude
response = client.messages.create(tools=anthropic_tools, ...)
```

### Agent SDK: Automatic Discovery

```python
# Just specify MCP server - SDK discovers and converts tools automatically
options = ClaudeAgentOptions(
    mcp_servers={"freshrss": {"url": "http://..."}}
    # No allowed_tools needed - SDK discovers all 5 tools from server:
    # - get_unread_articles
    # - get_article_content
    # - mark_as_read
    # - get_subscriptions
    # - fetch_full_article
)
```

## 8. Key Files Reference

### Phase 2 Files

| File | Lines | Purpose |
|------|-------|---------|
| `agent.py` | ~200 | Agent loop, tool execution, MCP integration |
| `mcp_client.py` | ~100 | MCP protocol client, connection management |
| `tools.py` | ~150 | Tool definitions, executors |
| **Total** | **~450** | |

### Agent SDK Files

| File | Lines | Purpose |
|------|-------|---------|
| `agent_sdk.py` | ~100 | Configuration, response handling |
| **Total** | **~100** | **~80% reduction** |

## 9. When to Use Which Approach

### Use Phase 2 (Hand-Written) When:

- **Learning**: Understanding how agents work at the protocol level
- **Full Control**: Need to customize every aspect of the agent loop
- **No SDK Dependency**: Want to avoid the claude-agent-sdk package
- **Custom MCP Transport**: Using non-standard MCP transport
- **Debugging**: Need to trace every step of tool execution

### Use Agent SDK (Agent SDK) When:

- **Production**: Building production-ready agents quickly
- **Standard MCP**: Using stdio or HTTP MCP transports
- **Less Code**: Want minimal boilerplate
- **Best Practices**: SDK implements battle-tested patterns
- **Future Features**: SDK updates bring new capabilities automatically

## 10. Learning Takeaways

### What Phase 2 Taught Us

1. **Agent Loop Pattern**: The core `while True → call_claude → check_stop_reason → execute_tools` pattern
2. **MCP Protocol**: How to connect, discover tools, call tools, handle responses
3. **Format Bridging**: Converting between MCP format and Anthropic format
4. **Async Patterns**: Managing async connections and context managers

### What Agent SDK Teaches Us

1. **Abstraction Value**: Understanding what the SDK abstracts away
2. **Configuration Over Code**: Declarative MCP server configuration
3. **SDK Patterns**: How to use ClaudeAgentOptions and ClaudeSDKClient
4. **Minimal Interface**: The smallest possible agent implementation

### The Complete Picture

```
Phase 1: Direct API
    └── Learn: Tool Use basics, no MCP

Phase 2: MCP Mode (Hand-Written)
    └── Learn: MCP protocol, agent loop, tool discovery

Agent SDK: Agent SDK
    └── Learn: What SDK automates, production patterns

Result: You understand BOTH how it works AND how to use it efficiently
```

## 11. Summary Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Evolution of Agent Implementation                     │
└─────────────────────────────────────────────────────────────────────────┘

Phase 1: Direct API          Phase 2: MCP Mode           Agent SDK: Agent SDK
─────────────────────────────────────────────────────────────────────────────

┌─────────────────┐        ┌─────────────────┐        ┌─────────────────┐
│   Your Code     │        │   Your Code     │        │   Your Code     │
│                 │        │                 │        │                 │
│ • Agent Loop    │        │ • Agent Loop    │        │ • Config only   │
│ • Tool Defs     │        │ • MCP Client    │        │ • Response      │
│ • Tool Executor │        │ • Tool Discovery│        │   handling      │
│ • FreshRSS API  │        │ • Format Convert│        │                 │
│                 │        │                 │        │                 │
│   ~300 lines    │        │   ~450 lines    │        │   ~100 lines    │
└────────┬────────┘        └────────┬────────┘        └────────┬────────┘
         │                          │                          │
         ▼                          ▼                          ▼
┌─────────────────┐        ┌─────────────────┐        ┌─────────────────┐
│  FreshRSS API   │        │   MCP Server    │        │ Claude Agent SDK│
│  (direct call)  │        │  (5 tools)      │        │  (built-in)     │
└─────────────────┘        └─────────────────┘        │                 │
                                                      │ • Agent Loop    │
                                                      │ • MCP Client    │
                                                      │ • Tool Discovery│
                                                      │ • Format Convert│
                                                      └────────┬────────┘
                                                               │
                                                               ▼
                                                      ┌─────────────────┐
                                                      │   MCP Server    │
                                                      │  (5 tools)      │
                                                      └─────────────────┘

Key Insight:
─────────────────────────────────────────────────────────────────────────────
The MCP Server stays the same across Phase 2 and Agent SDK.
The difference is WHO implements the agent logic:
  • Phase 2: YOU implement everything
  • Agent SDK: SDK implements everything, you just configure
```
