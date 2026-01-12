# MCP Agent Architecture Deep Dive

This document provides a top-down analysis of the MCP-based agent implementation in the FreshRSS Agent project.

## 1. High-Level Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Input                              │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FreshRSSAgent.chat()                         │
│                         Agent Loop                              │
└─────────────────────────────────────────────────────────────────┘
                               │
              ┌────────────────┴────────────────┐
              ▼                                 ▼
┌──────────────────────┐           ┌──────────────────────────────┐
│   Direct API Mode    │           │         MCP Mode             │
│   (use_mcp=False)    │           │       (use_mcp=True)         │
├──────────────────────┤           ├──────────────────────────────┤
│ FreshRSSClient       │           │ FreshRSSMCPClient            │
│ ToolExecutor         │           │ MCPToolExecutor              │
│ Static tool defs     │           │ Dynamic tool discovery       │
└──────────────────────┘           └──────────────────────────────┘
```

**Key Difference**: Direct API mode calls FreshRSS API directly; MCP mode communicates with an MCP Server through a standardized protocol.

## 2. Agent Core (agent.py)

### 2.1 Initialization (`__init__`)

```python
# agent.py:39-68
def __init__(self, settings: Settings, verbose: bool = False, use_mcp: bool | None = None):
    self.use_mcp = use_mcp if use_mcp is not None else settings.use_mcp

    if not self.use_mcp:
        # Direct API mode: initialize client directly
        self.freshrss_client = FreshRSSClient(...)
        self.tool_executor = ToolExecutor(self.freshrss_client)
    else:
        # MCP mode: deferred initialization, wait for connect_mcp()
        self.freshrss_client = None
        self.tool_executor = None
```

Key points:
- Mode selection based on `use_mcp` flag
- MCP mode requires async connection, so initialization is deferred

### 2.2 MCP Connection (`connect_mcp`)

```python
# agent.py:90-109
async def connect_mcp(self) -> None:
    # 1. Create MCP client
    self._mcp_client = FreshRSSMCPClient(
        self.settings.mcp_server_url,
        auth_token=self.settings.mcp_auth_token,
    )

    # 2. Establish connection
    await self._mcp_client.connect()

    # 3. Create tool executor
    self._mcp_tool_executor = MCPToolExecutor(self._mcp_client)

    # 4. Dynamic tool discovery (core MCP advantage!)
    self._tools = await get_tools_from_mcp(self._mcp_client)
```

**Dynamic tool discovery** is the most important feature of MCP: the Agent doesn't need hardcoded tool definitions; it fetches them from the Server.

### 2.3 Agent Loop (Core!)

```python
# agent.py:170-213
async def chat_async(self, user_message: str) -> str:
    # 1. Add user message to history
    self.messages.append({"role": "user", "content": user_message})

    # Agent Loop - the core loop
    while True:
        # 2. Call Claude
        response = self._call_claude()

        # 3. Save assistant response to history
        self.messages.append({"role": "assistant", "content": response.content})

        # 4. Check stop reason
        if response.stop_reason == "end_turn":
            # Claude is done, return text
            return self._extract_text(response.content)

        elif response.stop_reason == "tool_use":
            # Claude wants to use tools
            if self.use_mcp:
                # MCP mode: async execution
                tool_results = await self._process_tool_calls_async(response.content)
            else:
                # Direct API mode: sync execution
                tool_results = self._process_tool_calls(response.content)

            # 5. Add tool results to history, continue loop
            self.messages.append({"role": "user", "content": tool_results})
```

Agent Loop Flowchart:

```
           ┌──────────────────────────┐
           │  User message → History  │
           └────────────┬─────────────┘
                        ▼
           ┌──────────────────────────┐
           │    Call Claude API       │◄─────────┐
           └────────────┬─────────────┘          │
                        ▼                        │
              ┌─────────────────────┐            │
              │ What is stop_reason? │            │
              └─────────┬───────────┘            │
          ┌─────────────┼─────────────┐          │
          ▼             ▼             ▼          │
     "end_turn"    "tool_use"      other         │
          │             │             │          │
          ▼             ▼             ▼          │
     Return text   Execute tool   Return error   │
                        │                        │
                        ▼                        │
               Add tool_result ──────────────────┘
```

## 3. MCP Client (mcp_client.py)

### 3.1 Connection Establishment

```python
# mcp_client.py:52-75
async def connect(self) -> None:
    # 1. Build authentication headers
    headers = {}
    if self.auth_token:
        headers["Authorization"] = f"Bearer {self.auth_token}"

    # 2. Create Streamable HTTP transport
    self._context_manager = streamablehttp_client(
        self.server_url,
        headers=headers if headers else None,
    )

    # 3. Get read/write streams
    self._streams = await self._context_manager.__aenter__()
    read_stream, write_stream, _ = self._streams

    # 4. Create MCP session and initialize
    self._session = ClientSession(read_stream, write_stream)
    await self._session.__aenter__()
    await self._session.initialize()
```

MCP uses **Streamable HTTP** transport, an HTTP extension that supports bidirectional streaming.

### 3.2 Tool Discovery

```python
# mcp_client.py:77-95
async def list_tools(self) -> list[dict]:
    result = await self._session.list_tools()
    return [
        {
            "name": tool.name,
            "description": tool.description or "",
            "inputSchema": tool.inputSchema,  # Note: MCP format
        }
        for tool in result.tools
    ]
```

### 3.3 Tool Invocation

```python
# mcp_client.py:97-122
async def call_tool(self, name: str, arguments: dict) -> str:
    result = await self._session.call_tool(name, arguments or {})

    # MCP returns a list of content blocks
    if result.content:
        texts = []
        for content in result.content:
            if hasattr(content, "text"):
                texts.append(content.text)
        return "\n".join(texts)
```

### 3.4 Format Conversion (Important!)

```python
# mcp_client.py:144-166
def convert_mcp_tools_to_anthropic(mcp_tools: list[dict]) -> list[dict]:
    """
    MCP format:      {"inputSchema": {...}}
    Anthropic format: {"input_schema": {...}}
    """
    return [
        {
            "name": tool["name"],
            "description": tool["description"],
            "input_schema": tool["inputSchema"],  # Key conversion!
        }
        for tool in mcp_tools
    ]
```

This conversion function is the bridge between MCP and Claude integration: MCP uses camelCase (`inputSchema`), Anthropic uses snake_case (`input_schema`).

## 4. Tool Executors (tools.py)

### 4.1 MCPToolExecutor

```python
# tools.py:215-255
class MCPToolExecutor:
    def __init__(self, mcp_client):
        self.mcp_client = mcp_client
        self._cached_articles: list[dict] = []

    async def execute_async(self, tool_name: str, tool_input: dict) -> str:
        # Delegate directly to MCP client
        result = await self.mcp_client.call_tool(tool_name, tool_input)

        # Cache articles for summarization support
        if tool_name == "get_unread_articles":
            data = json.loads(result)
            self._cached_articles = data.get("articles", [])

        return result
```

In MCP mode, tool execution is very simple: just call `mcp_client.call_tool()`, all business logic is on the MCP Server side.

### 4.2 Comparison: ToolExecutor (Direct API Mode)

```python
# tools.py:81-113
class ToolExecutor:
    def execute(self, tool_name: str, tool_input: dict) -> str:
        if tool_name == "get_unread_articles":
            return self._get_unread_articles(tool_input)
        elif tool_name == "mark_articles_read":
            return self._mark_articles_read(tool_input)
        # ... need to implement all tool logic yourself
```

Direct API mode requires implementing all tool logic inside the Agent, while MCP mode moves this logic to the Server side.

## 5. Complete Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MCP Agent Complete Data Flow                      │
└─────────────────────────────────────────────────────────────────────┘

1. Initialization Phase:
   Agent ──connect_mcp()──> MCP Server
                  │
                  └──list_tools()──> Get tool definitions
                                          │
                                          ▼
                               convert_mcp_tools_to_anthropic()
                                          │
                                          ▼
                               self._tools (Anthropic format)

2. Conversation Phase:
   User ──"Show me my articles"──> Agent
                                    │
                                    ▼
                         Claude API (with tools)
                                    │
                                    ▼
                         stop_reason = "tool_use"
                         tool = "get_unread_articles"
                                    │
                                    ▼
                    MCPToolExecutor.execute_async()
                                    │
                                    ▼
                    MCP Client ──call_tool──> MCP Server
                                                  │
                                                  ▼
                                           FreshRSS API
                                                  │
                                    <─────────────┘
                                    │
                                    ▼
                         tool_result added to message history
                                    │
                                    ▼
                         Continue Agent Loop...
                                    │
                                    ▼
                         stop_reason = "end_turn"
                                    │
                                    ▼
                         Return final response to user
```

## 6. MCP Architecture Advantages

| Feature | Direct API Mode | MCP Mode |
|---------|-----------------|----------|
| Tool definitions | Hardcoded in Agent | Dynamically discovered from Server |
| Business logic | Implemented inside Agent | Implemented on Server side |
| Reusability | Single Agent | Multiple Agents share one Server |
| Extensibility | Modify Agent code | Only modify Server |
| Protocol standard | No standard | MCP standard protocol |

MCP essentially **decouples "tool implementation"** from the Agent, allowing any MCP-compatible Agent to use tools provided by the same Server through a standard protocol.

## 7. Key Files Reference

| File | Purpose | Key Classes/Functions |
|------|---------|----------------------|
| `agent.py` | Agent core + sync/async support | `FreshRSSAgent`, `chat()`, `chat_async()` |
| `mcp_client.py` | MCP protocol client | `FreshRSSMCPClient`, `convert_mcp_tools_to_anthropic()` |
| `tools.py` | Tool definitions and execution | `TOOLS`, `ToolExecutor`, `MCPToolExecutor` |
| `config.py` | Configuration management | `Settings` |

## 8. Learning Takeaways

1. **Agent Loop Pattern**: `while True: call_claude() → check_stop_reason() → execute_tools() → continue`

2. **Tool Execution Flow**:
   - Define tool schema (JSON Schema)
   - Claude returns tool_use block
   - Execute tool to get result
   - Construct tool_result message
   - Continue Agent Loop

3. **MCP Protocol**:
   - Client-Server architecture
   - Dynamic tool discovery
   - Unified tool execution interface

4. **Async Design**:
   - MCP uses async/await
   - Support for both sync and async modes
   - Context managers for resource management

5. **Architecture Flexibility**:
   - Switchable between Direct API and MCP modes
   - Unified tool executor interface
   - Same Agent supports multiple backends
