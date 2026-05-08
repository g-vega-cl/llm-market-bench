---
tags: [source, web-search, provider]
category: source
source: docs/engine/WEB_SEARCH.md
---

# Source: Web Search Configuration

Anthropic, Gemini, OpenAI web search patterns. DeepSeek has no web search
(endpoint limitation).

Key details:

- Anthropic: server-side tool, no client-side `tool_result` handling, server `tool_use` blocks excluded from message history to prevent 400 errors
- Gemini: Google Search grounding, mutually exclusive with function calling
- OpenAI: search-enabled model variants only
- PromptFactory dynamically injects/strips search instructions per provider
- Web search disabled in verification pipeline for cost control
