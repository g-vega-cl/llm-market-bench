---
tags: [engine, search, providers]
category: source
---

# Source: Web Search Configuration

Synthesized from `raw/docs/engine/WEB_SEARCH.md`.

## Takeaways

- **Provider Patterns**: Different models use different search mechanisms (Anthropic server-tools vs Gemini Google Search grounding).
- **Mutual Exclusivity**: On Gemini, search grounding is automatically disabled if function tools are present to avoid conflicts.
- **Cost Controls**: Web search is restricted to the Analysis phase; it is disabled during Verification to manage costs and ensure focus.

## Related

- [[entities/engine]]
- [[concepts/reasoning]]
