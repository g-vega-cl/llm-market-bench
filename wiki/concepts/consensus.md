---
tags: [consensus, synthesis, events, momentum]
category: concept
---

# Consensus & Synthesis

Transforms individual LLM decisions into coherent market events.

## Event Consensus Protocol

1. **Semantic Grouping**: Embeddings cluster events by cosine similarity across LLMs
2. **Weighted Consensus**: Cumulative model weight must exceed promotion threshold
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
- PCA reduces embedding vectors to 2D for concept map

## Horizon Watch

Only high-importance future catalysts with specific ISO 8601 dates appear on the
dashboard. Vague timeframes excluded.

## Related

- [[entities/pipeline]]
- [[concepts/reasoning]]
- [[concepts/execution]]
