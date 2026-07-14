---
tags: [consensus, synthesis, events, momentum]
category: concept
---

# Consensus & Synthesis

Transforms individual LLM decisions into coherent market events.

## Event Consensus Protocol

The Event Consensus Protocol is executed between the two analysis passes of the daily pipeline. The macro events extracted by individual models in **Pass 1** are grouped, promoted, and synthesized. The resulting promoted consensus events are then formatted and injected as today's macro context (`{consensus_context}`) into **Pass 2** to drive informed asset-level trading decisions.

1. **Semantic Grouping**: Embeddings cluster events by cosine similarity across LLMs (threshold 0.75).

   * **API Rate-Limit Resilience**: Uses `tenacity` exponential backoff retries (3 max attempts) to absorb transient errors like `429 RESOURCE_EXHAUSTED`.
   * **Exact-Match Fallback**: If the embedding API fails or mismatches, the engine gracefully falls back to exact string-based grouping to prevent pipeline crashes.
2. **Weighted Consensus**: Cumulative model weight must exceed promotion threshold (default 2.0)
3. **Temporal Deduplication**: New events checked against `memories` table within recency window
4. **Relationship Analysis**: Links to ancestor events as REVERSAL, RESOLUTION, or UPDATE
5. **LLM Synthesis**: Unifies naming, extracts catalyst dates and historical parallels
6. **Scenario Analysis**: Requires ≥2 distinct outcomes with specific trading plans
7. **Alpha Discovery**: Promoted events trigger DiscoveryAgent for investable assets

## Trend & Momentum

Concept velocity tracked via hybrid formula: `Momentum = Intensity × Growth`.
- Intensity: log-scaled mention count
- Growth: short-vs-long window mention rate
- Stale concepts decay via half-life
- **PCA Dimensionality Reduction**: PCA reduces embedding vectors to 2D coordinates for semantic tracking (viewable in narrative details). The coordinate calculation ensures vector parsing alignment to prevent index-shifting/data-corruption if a concept vector is malformed or skipped.

## Horizon Watch

Only high-importance future catalysts with specific ISO 8601 dates appear on the
dashboard. Vague timeframes excluded.

## Metadata & UI Representation

Promoted consensus events (`MARKET_EVENT` memory type) store the models that reached agreement inside their database metadata:
* **`participating_agents`**: A list of strings matching the participating models (e.g. `["openai_gpt-5.4-nano", "anthropic_claude-haiku-4-5"]`). This is consumed by the web app to render agent avatars.
* **`models_involved`**: A list of strings matching unique models involved.

The UI displays the avatars of these models directly on the market consensus cards to indicate consensus visually. The old overall "Consensus" percentage bar has been removed to avoid confusion.

## Performance & Execution Optimizations

*   **Single-Consensus Invocation Architecture**: Resolved the double-consensus bug where `process_consensus` was executed twice. A global memory cache (`_last_consensus_events` / `get_last_consensus_events`) in `consensus.py` allows the synchronously-derived consensus events from Pass 1 to be reused during the background momentum/decay processing stage, preventing redundant LLM and database executions.
*   **Parallel Scenario Asset Discovery**: In `_synthesize_and_promote_group`, asset discovery tasks for all scenarios under a promoted consensus event are processed concurrently using `asyncio.gather`, improving throughput.
*   **Parallel Screener History Enrichment**: The stock screening tool (`execute_stock_screener_tool`) enriches screened tickers in parallel using `asyncio.gather` for price history lookups, preventing sequential database request bottlenecks.

## Related

- [[entities/pipeline]]
- [[concepts/reasoning]]
- [[concepts/execution]]
- [[concepts/memory-feedback]]
