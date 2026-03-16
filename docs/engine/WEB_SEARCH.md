# Web Search Implementation

This document describes the web search integration for the AI Wall Street engine, enabling LLM agents to access real-time information from the internet.

## Overview

The engine now supports native web search tools for:
- **Anthropic Claude** (`web_search_20250305` and `web_search_20260209`)
- **Google Gemini** (`google_search` grounding)
- **OpenAI** (limited support in Chat API, full support in Responses API)

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Enable/disable web search for each provider
ENABLE_ANTHROPIC_WEB_SEARCH=true
ENABLE_GEMINI_WEB_SEARCH=true
ENABLE_OPENAI_WEB_SEARCH=false  # Limited support in Chat API

# Anthropic web search tool version
# Use 'web_search_20250305' for ZDR compliance (basic search)
# Use 'web_search_20260209' for dynamic filtering (Opus 4.6 / Sonnet 4.6 only)
ANTHROPIC_WEB_SEARCH_VERSION="web_search_20250305"

# Maximum web searches per Anthropic request (default: 3)
ANTHROPIC_MAX_WEB_SEARCHES=3
```

### Model Compatibility

| Provider | Tool Version | Models | ZDR Eligible | Notes |
|----------|-------------|--------|--------------|-------|
| Anthropic | `web_search_20250305` | Opus 4.6, Sonnet 4.6, Haiku 4.5 | ✅ Yes | Basic search |
| Anthropic | `web_search_20260209` | Opus 4.6, Sonnet 4.6 | ❌ No | Dynamic filtering |
| Gemini | `google_search` | Gemini 3.x, 2.5.x | N/A | Grounding with citations |
| OpenAI | `web_search` | `gpt-5-search-api`, `gpt-4o-search-preview` | ✅ Yes | **Requires search-enabled model** or Responses API |

## Usage

### In Analysis Pipeline

Web search is **enabled by default** for Anthropic and Gemini in the analysis pipeline (`core/llm/analysis.py`):

```python
# Anthropic (web search enabled)
await anthropic.run_tool_loop(
    raw_client, model_name, messages, 
    enable_web_search=True
)

# Gemini (Google search enabled)
await gemini.run_tool_loop(
    raw_client, model_name, messages, 
    enable_google_search=True
)

# OpenAI/DeepSeek (web search disabled - limited Chat API support)
await openai.run_tool_loop(
    raw_client, model_name, messages, provider,
    enable_web_search=False
)
```

### In Verification Pipeline

Web search is **disabled by default** for verification to keep the second-step focused on validation:

```python
await anthropic.run_tool_loop(
    raw_client, model_name, messages, 
    enable_web_search=False  # Focused validation
)
```

### Custom Tool Configuration

You can override the default tools list:

```python
from core.llm import tools

custom_tools = [
    tools.STOCK_TOOL_DEFINITION_ANTHROPIC,
    tools.WEB_SEARCH_TOOL_DEFINITION_ANTHROPIC,
]

await anthropic.run_tool_loop(
    raw_client, model_name, messages,
    override_tools=custom_tools
)
```

## How It Works

### Anthropic

Anthropic's web search is a **native server tool** (not a function tool). When enabled:

1. The model decides when to search based on the prompt
2. The API executes searches **server-side** and automatically incorporates results
3. Results include `url`, `title`, `page_age`, and `encrypted_content`
4. Citations are automatically added to the response text

**How Server Tools Work:**

Unlike function tools (e.g., `get_stock_quote`), server tools are executed entirely on Anthropic's servers. The handler:
- **Does NOT** need to execute anything client-side
- **Does NOT** need to send `tool_result` blocks back
- **Does NOT** record `server_tool_use` blocks in message history (they're internal to Anthropic)

This is handled automatically in `apps/engine/core/llm/handlers/anthropic.py`:

```python
# Check for server tool calls (web_search - executed server-side by Anthropic)
server_tool_uses = [c for c in resp.content if c.type == "server_tool_use"]

# Log server tool usage for visibility
for server_tool in server_tool_uses:
    logger.info(f"Server tool executed by Anthropic: {server_tool.name}")

# Build assistant message content
# IMPORTANT: Do NOT include server_tool_use blocks in message history
# Anthropic executes these server-side and they don't need tool_result blocks
assistant_content = []
for content_block in resp.content:
    if content_block.type == "text":
        assistant_content.append({"type": "text", "text": content_block.text})
    elif content_block.type == "tool_use":
        # Only include function tool calls (client-side tools)
        assistant_content.append({
            "type": "tool_use",
            "id": content_block.id,
            "name": content_block.name,
            "input": content_block.input,
        })
    # Skip server_tool_use blocks - they are internal to Anthropic's server
```

**Response Structure:**
```json
{
  "type": "server_tool_use",
  "id": "srvtoolu_xyz",
  "name": "web_search",
  "input": {"query": "AAPL stock price today"}
}
```

The search results appear as text content with citations in the same response.

### Gemini

Gemini's Google Search grounding provides:

1. `groundingMetadata` with search queries used
2. `groundingChunks` with source URLs and titles
3. `groundingSupports` linking text segments to sources

**Response Metadata:**
```json
{
  "groundingMetadata": {
    "webSearchQueries": ["AAPL stock price"],
    "groundingChunks": [
      {"web": {"uri": "https://...", "title": "..."}}
    ],
    "groundingSupports": [
      {"segment": {...}, "groundingChunkIndices": [0]}
    ]
  }
}
```

### OpenAI

OpenAI web search is available in the **Responses API** as a native tool. In the Chat Completions API, you must use **search-enabled model variants**:

- `gpt-5-search-api`
- `gpt-4o-search-preview`
- `gpt-4o-mini-search-preview`

Standard models like `gpt-5-mini` do **not** support web search in the Chat Completions API.

**To enable OpenAI web search:**

1. Update your `.env`:
```bash
OPENAI_MODEL="gpt-5-search-api"  # or gpt-4o-search-preview
ENABLE_OPENAI_WEB_SEARCH=true
```

2. The handler will automatically include the `web_search` tool when enabled.

## Prompt Engineering

The system prompt has been updated to inform agents about web search capability:

```
You are a hedge fund trading algorithm with access to real-time web search.
Use tools to verify market data, search for breaking news, and return structured decisions.
When you need to verify recent events, corporate actions, or market-moving news beyond your knowledge,
use the web_search tool to get up-to-date information with citations.
```

### Best Practices for Agents

Agents are instructed to use web search for:
1. Verifying breaking news mentioned in snippets
2. Checking corporate actions (earnings, splits, M&A)
3. Confirming government policy announcements
4. Fact-checking claims before trading

**Important:** Agents should use web search strategically, not for every query.

## Testing

Run the test script to verify web search integration:

```bash
cd apps/engine
python test_web_search.py
```

This tests:
- Anthropic web search with basic queries
- Gemini Google Search grounding
- Citation handling and metadata extraction

## Attribution & Audit Trail

Web search usage is logged for attribution:

```python
logger.info(f"Server tool invoked: {server_tool.name}")
```

Search results and citations are preserved in the message history, allowing you to trace:
- Which searches were performed
- What sources were consulted
- How information influenced the trading decision

## Troubleshooting

### "Tool execution failed" warnings

Check:
1. API key has web search permissions enabled
2. Organization admin has enabled web search (Anthropic Console)
3. Model supports web search (see compatibility table)

### "tool_use without tool_result" Error (Anthropic)

**Error Message:**
```
Error code: 400 - {'type': 'invalid_request_error', 'message': 'messages.3: `tool_use` ids were found without `tool_result` blocks immediately after: srvtoolu_...'}
```

**Cause:** The handler was incorrectly recording `server_tool_use` blocks in message history. Since server tools are executed server-side by Anthropic, they don't require (or expect) `tool_result` blocks from the client.

**Solution:** The handler now:
- Excludes `server_tool_use` blocks from message history entirely
- Only tracks client-side function tool calls (`tool_use`)
- Only sends `tool_result` blocks for function tools that require client execution

If you see this error, ensure you're using the updated `apps/engine/core/llm/handlers/anthropic.py` that properly handles server tools.

### No search results in response

Verify:
1. `enable_web_search=True` is passed to `run_tool_loop`
2. The model decided a search was necessary (it's autonomous)
3. For Anthropic, check `ENABLE_ANTHROPIC_WEB_SEARCH` config

### Citation handling issues

For multi-turn conversations:
- Preserve `encrypted_content` (Anthropic) and `encrypted_index` in message history
- Pass native response objects (Gemini `Content`) to maintain metadata

## Cost Considerations

Web search incurs additional costs:
- **Anthropic**: Charged per search request (see pricing)
- **Gemini**: Billed per search query executed
- **OpenAI**: Tiered rate limits based on model

Use `ANTHROPIC_MAX_WEB_SEARCHES` to limit searches per request.

## Future Enhancements

Potential improvements:
1. Domain filtering (`allowed_domains`, `blocked_domains`)
2. Location-based search (`user_location`)
3. Search result caching for repeated queries
4. Web search attribution dashboard in the frontend
