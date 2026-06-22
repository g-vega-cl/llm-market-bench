---
tags: [rag, retrieval, context, embeddings]
category: concept
---

# RAG Strategy

A tiered context injection system that gives different pipeline stages different
levels of retrieval depth.

## Tier 1: Analysis Hot Path & Dynamic Retrieval

Rather than statically injecting massive chunks of raw emails and background data (which dilutes prompts and inflates costs), Tier 1 implements a hybrid summary-and-tool strategy:
1. **Pre-Filtered Menu**: Financial newsletters are pre-summarized into 1-2 sentence summaries using `deepseek-v4-flash` via Instructor. A concise "Newsletter Summary & Menu" is injected into the Analysis Agent prompt instead of the full raw emails.
2. **On-Demand Content Fetching**: The Analysis Agent has access to `fetch_newsletter_content` to retrieve the full de-advertised text of target newsletters from the database when a summary warrants deeper investigation.
3. **On-Demand Vector RAG**: The Analysis Agent can call `search_past_memories` to perform semantic vector searches (pgvector) against past events and historical trade lessons learned.
4. **General Context**: Lightweight static context via `retrieve_top_memories(5)` (no-embedding active memories SQL query) and top trending concepts is still injected to maintain baseline market awareness.

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
