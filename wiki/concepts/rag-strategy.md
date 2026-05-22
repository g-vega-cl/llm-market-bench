---
tags: [rag, retrieval, context, embeddings]
category: concept
---

# RAG Strategy

A tiered context injection system that gives different pipeline stages different
levels of retrieval depth.

## Tier 1: Analysis Hot Path

Lightweight context via `retrieve_top_memories(5)` — a simple SQL query for the
top-5 highest-importance active memories. No embedding calls, no pgvector.
Augmented with top trending concepts for broad market awareness.

## Tier 2: Verifier Path

Targeted per-trade RAG via `retrieve_for_decision()`:
- Past decisions scoped to the current agent's `model_name` (prevents
  cross-contamination)
- Shared memories (market events, lessons) remain cross-agent
- Empirical foundational knowledge seeded as high-importance `LESSON_LEARNED` memories (e.g., Fama-French factor models, behavioral anomalies).
- Content sanitized (HTML stripped) before prompt injection
- Items ranked by importance × similarity, capped at token budget

## Tier 3: Contrarian Path

Batch pgvector search via `retrieve_context_batch()` for non-time-critical deep
analysis.

| Type | Source | Table | Scope | Decay Rate |
|------|--------|-------|-------|------------|
| MARKET_EVENT | Consensus synthesis | `memories` | Cross-agent | Standard (50% per half-life) |
| GOVERNMENT_INCENTIVE | Gov tracking | `memories` | Cross-agent | Mild (25% per half-life) |
| LESSON_LEARNED | Manager Agent | `memories` | Cross-agent | Persistent (0% decay) |
| UNCROWDED_TRADE | Discovery Agent | `memories` | Cross-agent | Persistent (0% decay) |
| PAST_REASONING | Agent decisions | `decisions` | Per-agent | N/A |


## Related

- [[entities/pipeline]]
- [[entities/database]]
- [[concepts/memory-feedback]]
- [[concepts/reasoning]]
