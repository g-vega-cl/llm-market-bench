---
tags: [memory, feedback, rag, learning]
category: concept
---

# Memory & Feedback Loops

Three feedback mechanisms that make the system improve over time.

## Manager Agent (Post-Mortem)

At configured intervals after trade execution (short, medium, long horizon):
1. Fetch current price for each traded ticker
2. Send original reasoning + actual outcome to LLM
3. Generate `LESSON_LEARNED` memories in pgvector
4. Future RAG retrievals include these lessons, preventing repeated mistakes

## Contrarian Agent

Runs after primary agents. Identifies crowded trades and missed risks. Executes
counter-trades in a dedicated portfolio. Uses fresh market prices
(`force_refresh=True`), not cached data.

## Cause & Effect Analysis

Periodic retrospective audit that:
1. Deduplicates against prior analyses
2. Identifies most-affected companies per event (Gemini)
3. Compares scenario analysis against actual price data
4. Creates a searchable playbook of what narratives actually moved markets

## Market Feeling

After each pipeline run, an LLM generates "How I'm feeling and why" sentiment
based on the day's trades, lessons, and market events. Displayed on Today
dashboard with confidence bar and direction badge.

## Memory Architecture

Decoupled vector storage: `memories` table for market context (`MARKET_EVENT`, `GOVERNMENT_INCENTIVE`, `LESSON_LEARNED`, `UNCROWDED_TRADE`), `decisions` table for past trade reasoning. Retrieval is scoped: cross-agent for memories, per-agent for decisions (prevents cross-contamination in verification).

### Memory Reinforcement & Duplicate Bumping
When a new memory is ingested with `check_similarity=True`, the system performs a semantic similarity search. If a duplicate or highly similar entry is found:
- Instead of creating a redundant record or silently skipping it, the system **bumps** the existing memory.
- Bumping resets the `relevance_score` to `1.0` and updates the `created_at` timestamp to the current UTC time, keeping high-signal recurring concepts fresh in the retrieval window.
- The duplicate check utilizes an extended **168-hour (7 days) lookback window** to prevent redundant database inserts across weekends and weekly schedules.

### Tiered Memory Decay
To prevent context window pollution and reasoning degradation while retaining key long-term lessons, the system applies adaptive tiered decay rates during weekly cleanups:
- **Market Events (`MARKET_EVENT`)**: Decays standardly (relevance reduced by 50% after half-life threshold).
- **Government Incentives (`GOVERNMENT_INCENTIVE`)**: Decays mildly (relevance reduced by 25% after half-life threshold).
- **Lessons Learned (`LESSON_LEARNED`) & Uncrowded Trades (`UNCROWDED_TRADE`)**: Never decay (relevance score remains permanently at `1.0` to preserve core trading insights).
- **Superseded Pruning**: To prevent pgvector storage bloat, `SUPERSEDED` memories older than **180 days** are hard-deleted during weekly cleanups, ensuring that historical trace records are kept lean.

### The "Sleep Cycle" (Weekly Memory Consolidation)
An offline weekly consolidation pipeline groups overlapping memories to compound knowledge and reduce redundancy:
1. **Clustering**: Active memories are retrieved (capped at the **500 most recent active memories** for scaling safety), and an adjacency graph is built by mapping pairs with a cosine similarity metric `>= 0.85`. Connected components are identified using depth-first search (DFS).
2. **Synthesis**: For clusters of 2 or more overlapping memories, the system invokes DeepSeek (`DEEPSEEK_MODEL` from `core.config`) using `instructor` to guarantee a structured Pydantic schema response.
3. **Canonical Record Creation**: A single canonical consolidated memory is inserted with `status='ACTIVE'`, `relationship_type='UPDATE'`, and `parent_id` pointing to the primary parent.
4. **Supersedence**: The original memories in the cluster are updated to `status='SUPERSEDED'`, maintaining reference links while removing them from the active analysis hot path.


## Related

- [[entities/pipeline]]
- [[entities/database]]
- [[concepts/rag-strategy]]
- [[concepts/auto-research-prompt-improver]]
- [[entities/autoresearch]]
