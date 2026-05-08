# Web Search Configuration

Active provider list: see [`packages/config/models.json`](../../packages/config/models.json). This document describes the web search architecture per provider pattern.

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `ENABLE_ANTHROPIC_WEB_SEARCH` | Toggle Anthropic native web search |
| `ENABLE_GEMINI_WEB_SEARCH` | Toggle Gemini Google Search grounding |
| `ENABLE_OPENAI_WEB_SEARCH` | Toggle OpenAI web search (only with search-enabled models) |
| `ANTHROPIC_WEB_SEARCH_VERSION` | Anthropic web search tool version string |
| `ANTHROPIC_MAX_WEB_SEARCHES` | Per-request search budget for Anthropic |

Defaults and current valid values: see [`apps/engine/.env.example`](../../apps/engine/.env.example) and the handler files referenced below.

## How It Works

- **Anthropic**: Server-side tool — Anthropic's servers execute searches and incorporate results. No client-side `tool_result` handling. Server `tool_use` blocks are excluded from message history to prevent 400 errors.
- **Gemini**: Google Search grounding provides citations in `groundingMetadata`. Disabled automatically when custom function tools are present (Gemini's grounding tool is mutually exclusive with function calling).
- **OpenAI**: Available only with search-enabled model variants. Standard chat models don't support it. Compatible model list: OpenAI docs.
- **DeepSeek**: Disabled — handler calls an OpenAI-compatible endpoint without web search support.

## Prompt Management

The `PromptFactory` dynamically manages web search instructions:
- Injects search-capability instructions when enabled for the provider
- Strips them when a provider can't use search (prevents "tool hallucination")
- Strips for Gemini when function tools are present
- Strips for DeepSeek (no support on the endpoint)

## Pipeline Usage

- **Analysis**: Enabled for Anthropic and Gemini.
- **Verification**: Disabled — focused validation only, cost-controlled.

## Key Files

- `core/llm/handlers/anthropic.py` — Server tool handling, `enable_web_search` parameter, Anthropic web search tool definitions
- `core/llm/handlers/gemini.py` — Google Search grounding integration (built inline via `types.Tool(google_search={})`)
- `core/llm/prompt_factory.py` — Dynamic prompt assembly
- `core/llm/tools.py` — Canonical function-tool definitions (non-web-search) and `to_anthropic` / `to_gemini` adapters
