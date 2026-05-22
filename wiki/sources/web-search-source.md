---
tags: [engine, search, providers]
category: source
---

# Source: Web Search Configuration

Synthesized from `raw/docs/engine/WEB_SEARCH.md`.

## Takeaways

- **Provider Patterns**: Different models use different search mechanisms (Anthropic server-tools vs Gemini Google Search grounding).
- **Multi-Tool Integration**: On Gemini, custom client-side function tools and Google Search grounding can be active simultaneously by enabling `include_server_side_tool_invocations` (supported in Gemini 3). The engine automatically falls back to disabling automatic function calling on older SDK/model versions that do not support tool integration.
- **Cost Controls**: Web search is restricted to the Analysis phase; it is disabled during Verification to manage costs and ensure focus.

## Related

- [[entities/engine]]
- [[concepts/reasoning]]
