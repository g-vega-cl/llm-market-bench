---
tags: [concept, historical-parallel, synthesis, memory, ui]
category: concept
---

# Structured Historical Parallel

A structured data pattern for capturing, persisting, and surfacing historical precedents identified during consensus synthesis. This replaces the previous plain-string `historical_parallel` field with a rich object containing timeframe, market reaction, and asset-level detail.

## Data Model

Defined in `core/llm/events.py` as a Pydantic `BaseModel`:

```python
class HistoricalParallelDetail(BaseModel):
    title: str                              # e.g. "2024 Red Sea Tanker Disruptions"
    timeframe: str                           # e.g. "Jan - Mar 2024"
    precedent: str                           # What happened historically
    market_reaction: str                     # Price and sector reactions
    takeaway: str                            # Actionable lesson for today
    affected_assets: list[str]               # e.g. ["USO", "FRO"]
```

## Flow

1. **Candidate Collection** — During consensus grouping, individual model observations with `historical_parallel` fields (plain strings) are collected into a `candidate_parallels` list.
2. **LLM Synthesis** — The `synthesize_event` function receives `candidate_parallels` (formatted as a bullet list in the prompt via `PromptFactory.build_synthesis_messages`). The LLM Arbiter selects the single best parallel and enriches it with structured fields, returning a `HistoricalParallelDetail` object.
3. **Fallback Handling** — If no parallel is identified, the field is `null`. If the LLM returns a plain string (legacy), it is normalized into a minimal structured object with placeholder values.
4. **Memory Persistence** — The structured parallel is stored in `metadata.historical_parallel` when promoted to long-term memory. The memory content string includes a formatted tag like `[Historical Parallel: Title (Timeframe)]`.
5. **UI Rendering** — `MemoryCard.tsx` renders a dedicated panel under "Show Analysis" with:
   - Title and timeframe badge
   - Precedent narrative
   - Market reaction in a monospaced block
   - Key takeaway/playbook
   - Affected assets as clickable badges
   - Deep link to `/chat` with pre-populated query to interrogate the parallel
6. **Chat Tool Exposure** — The `search_memories_and_theses` tool fetches the `metadata` column and extracts `historical_parallel` into a top-level field in the returned memory objects, making it available to the conversational agent.

## Edge Cases

- **Legacy string parallels**: Rendered as plain text without structured sections.
- **Missing fields**: The UI renders only available sections; missing `market_reaction` or `affected_assets` are simply absent.
- **No parallel identified**: The `historical_parallel` field is `null` throughout the pipeline; no panel is rendered.

## Testing

Unit tests cover:
- `test_historical_parallel_synthesis.py` — prompt factory inclusion, structured parsing, null handling, consensus-level propagation and memory persistence
- `MemoryCard.test.tsx` — collapsed hidden state, structured panel rendering, legacy string rendering, deep link generation
- `chat-memories-server.test.ts` — structured `historical_parallel` in search results

## Related

- [[concepts/consensus]] — Consensus flow that feeds candidate parallels
- [[concepts/memory-feedback]] — Memory persistence and scenario analysis
- [[entities/chat-tools]] — Tool exposing historical parallels to chat
- [[entities/engine]] — Engine synthesis logic and prompt factory
