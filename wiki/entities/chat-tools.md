---
tags: [chat, tools, investment-chat-gateway]
category: entity
---

# Chat Tools

Server-side tool definitions and handlers for the Investment Chat Gateway. These tools enable the conversational agent to query memories, theses, and causal chains.

## Tools

### search_memories_and_theses

Searches past agent market memories, lessons learned, historical parallels, causal chains (cause_and_effect), and scenario analyses by ticker or thematic query.

**Parameters:**
- `ticker` (optional): Stock ticker symbol
- `query` (optional): Thematic search string

**Returns:** Structured results with:
- `memories`: Array of memory objects, each now including a `historical_parallel` field (structured object with title, timeframe, precedent, market_reaction, takeaway, affected_assets) when the memory has an associated historical parallel stored in metadata.
- `causalRecords`: Array of cause-and-effect records.

The tool fetches memories from the `memories` table including the `metadata` column, then extracts `historical_parallel` from metadata into a top-level field for easy consumption by the LLM and UI.

## Related

- [[entities/investment-chat-gateway]]
- [[concepts/memory-feedback]]
- [[entities/web-app]]
