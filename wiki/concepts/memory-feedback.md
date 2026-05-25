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

Decoupled vector storage: `memories` table for market context (`MARKET_EVENT`, `GOVERNMENT_INCENTIVE`, `LESSON_LEARNED`, `UNCROWDED_TRADE`), `decisions` table for past trade reasoning. Retrieval is scoped: cross-agent for memories, per-agent for decisions (prevents cross-contamination in verification).

### Frontend UI Filtering, Caching & Delta-Sync Strategy

To achieve a modern, instant (0ms) user experience while minimizing server load and database queries, the `/memories` dashboard implements a **Hybrid Local Cache + Progressive Background Fill** architecture powered by TanStack Query:

1. **Immediate Initial Render (0ms)**: On client mount, TanStack Query is bootstrapped with `initialData` loaded from a browser cache stored in `localStorage` (`benchify_memories_v1`, capped at 500 items). The interface renders instantly with no spinners.
2. **Self-Healing Reset Detection**: Before entering delta-sync, the client runs a lightweight `validateCacheState(cachedId)` check — two parallel Supabase queries:
   - Query 1: Fetch the newest `created_at` timestamp in the database.
   - Query 2: Check whether the newest cached memory's `id` still exists in the database.
   - **If any anomaly is detected** (ID missing, DB timestamp is older than cache's newest timestamp, or database is empty), the stale cache is wiped completely and a progressive backfill is triggered. This automatically self-heals after database resets, re-seeds, or historical imports — with no user intervention required.
3. **Background Sync & Progressive Fill**: Once validated, `initialDataUpdatedAt: 1` treats the initial cache as stale, prompting a background `queryFn` to run:
   - **Delta Sync (Cache Full)**: If the local cache is fully populated (`cached.length >= 500`), the client requests only memories created *after* the latest cached timestamp (`fetchNewMemories`), keeping network overhead minimal.
   - **Progressive Backfill (Cache Empty or Partial)**: If the local cache is empty or has fewer than 500 items, the client runs a multi-page progressive fill:
     1. `performFullBackfill` fetches the first page (50 items) immediately via `fetchFn` and returns it to the UI — the list is visible with no loading state.
     2. The `queryFn` stores the `nextCursor` as `pendingCursor` state, which triggers a `useEffect`.
     3. `runProgressiveFill` walks subsequent cursor pages in the background, calling `queryClient.setQueryData` after each page so the list silently grows in place — no spinner, no flash.
     4. Pages continue until the cache reaches 500 items or the DB returns no more records.
   - The fetched payload is merged with the cache, deduplicated by unique ID, sorted chronologically descending, capped at 500 entries, and written back to `localStorage`.
4. **100% In-Memory Filtering**: All category tabs filter the local array completely in-memory in the browser. Transitioning between tabs is instantaneous (0ms) and dispatches zero server requests — including during and after background fill.
5. **Client-Side Pagination**: Scrolling and loading more data is driven by a local `displayLimit` state (in increments of 50) on the pre-loaded cache pool, eliminating network hops during pagination.

**Implementation**: The `queryFn` delegates to focused helper functions in `MemoriesPage.tsx` — `syncMemoriesCache`, `performFullBackfill`, and `runProgressiveFill` — keeping cognitive complexity within Biome's strict limits. The `fetchFn` interface `(cursor, category)` is shared between the route's TanStack Start server wrapper and the progressive fill loop; `pageSize` is intentionally not part of the interface, so bulk fetching is achieved via cursor-paged iteration rather than a single large request.

To maintain consistency, the database `memory_type` values and Frontend UI selectors remain **fully unified** as first-class discriminators. The client-side classifier `getMemoryCategory(m)` categorizes memories in-memory and applies dynamic brand-color badge styles:

- **Events (`MARKET_EVENT`)**: (displayed as "Events").
- **Calendar Events (`CALENDAR_EVENT`)**: (displayed as "Calendar Events").
- **Principles (`ACADEMIC_PAPER`)**: (displayed as "Principles").
- **Post-Mortems (`POST_MORTEM`)**: (displayed as "Post-Mortems").
- **Lessons (`LESSON_LEARNED`)**: (retained for generic legacy lessons).

*Note: The empty Decisions (`decision_reasoning`) and redundant, permanently empty Lessons (`lesson_learned`) filters are completely removed. Decisions are managed under the specialized **Reasoning** page rather than the memories table. Post-mortem lessons and academic principles fully cover all lessons learned, so a dedicated empty general lessons tab is unnecessary.*




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
