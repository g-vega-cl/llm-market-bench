---
tags: [memory, feedback, rag, learning]
category: concept
---

# Memory & Feedback Loops

Two primary feedback mechanisms make the system improve over time.

## Manager Agent (Post-Mortem)

At configured intervals after trade execution (short, medium, long horizon):
1. Fetch current price for each traded ticker
2. Send original reasoning + actual outcome to LLM
3. Generate `LESSON_LEARNED` memories in pgvector
4. Future RAG retrievals include these lessons, preventing repeated mistakes

## Cause & Effect Analysis

Periodic retrospective audit that:
1. Deduplicates against prior analyses.
2. Identifies most-affected companies per event (Gemini).
3. Compares scenario analysis against actual price data.
4. Creates a searchable playbook of what narratives actually moved markets.

### Resolution Memory Chains & Performance Integration

To close the loop on historical predictions and learn from resolved market events, the system links active memories with their eventual resolutions and causal outcomes:

1. **Resolution Linkage**: When a target event is resolved, its status in the `memories` table is updated to `RESOLVED`. A child memory of type `RESOLUTION` is created, referencing the parent via `parent_id` and setting `relationship_type = 'RESOLUTION'`.
2. **Causal Data Retrieval (`cause_and_effect` table)**: Causal metrics (actual outcomes, confidence scores, playbooks) are stored in the `cause_and_effect` table. Because mature cause-and-effect results might be saved under the parent event or the child resolution event, the frontend queries both (`fetchCauseAndEffectByEventId`) and merges the outcomes.
3. **Consolidated UI Panel**: The memories dashboard (`MemoryCard.tsx`) renders a dedicated **Resolution & Market Performance** section for resolved events, featuring:
   - **Header Badge**: A prominent `🏆 Winning Scenario: [Header]` badge on the unexpanded card header.
   - **What Resolved**: Clearly displays the original event summary and a clickable link to the child resolution event in the Event Chain view (`Resolved by:`).
   - **Winning Scenario Callout & Highlighting**: Identifies and highlights the winning scenario with a `🏆 WINNING SCENARIO` badge and emerald container styling, while non-winning scenarios are dimmed (`opacity-60`) with a `Did Not Occur` badge.
   - **Why It Resolved**: The actual market price outcome (with classification confidence rating) and full causal analysis playbook.
   - **Performance Tags**: Categorized tags (e.g. `energy-prices`, `geopolitics`) associated with the causal playbook.

## Structured Scenarios & Ticker Mapping

To make scenario analysis highly actionable, memories support a strict **Gold Standard** structured scenarios schema inside their database `metadata`:
1. **Pydantic Scenarios List**: Instead of a flat markdown string, the backend Gemini synthesis returns a structured `scenarios` array containing individual scenario objects (`cleanHeader`, `percentage`, `outcome`, `tradingPlan`).
2. **Targeted Ticker Discovery**: For each synthesized scenario, the consensus engine runs the `DiscoveryService` specifically against that scenario's individual `tradingPlan` context (invoking FMP company screeners and web search). Verified tickers are tagged by scenario and saved directly inside the respective scenario object (`scenarios.assets`).
3. **Structured UI Rendering**: The frontend memories UI (`MemoryCard.tsx`) bypasses all regex text parsing and fuzzy asset-matching loops, standardizing 100% on rendering this structured typed list. Clicking nested scenario tickers selects and launches the FMP asset details modal. In addition, to prevent redundant layout boxes, the "Other Investable Assets" section is cleanly hidden if all discovered assets are already mapped directly to scenarios (resulting in 0 remaining global assets).
4. **Resilient Fallback**: The backend continues to populate a unified flat string `scenario_analysis` fallback in the database to ensure legacy consumer pages (e.g. `FutureCatalysts.tsx` timeline) remain fully operational.
5. **Consensus Persistence Fix (2026-06-03)**: Resolved a bug where the `scenarios` structured array was omitted from the `metadata` dict passed to `add_memory` in the consensus promotion logic, causing the UI to show an empty Scenario Analysis. The pipeline now correctly persists both the legacy `scenario_analysis` text fallback and the structured `scenarios` array. All historical entries since the initial schema rollout have been retroactively repaired.

## Market Feeling


After each pipeline run, an LLM generates "How I'm feeling and why" sentiment
based on the day's trades, lessons, and market events. Displayed on Today
dashboard with confidence bar and direction badge.

Decoupled vector storage: `memories` table for market context (`MARKET_EVENT`, `GOVERNMENT_INCENTIVE`, `LESSON_LEARNED`, `UNCROWDED_TRADE`), `decisions` table for past trade reasoning. Retrieval is scoped: cross-agent for memories, per-agent for decisions (prevents cross-contamination in verification).

### SSR-First Loading & Parallel Category Prefetching Strategy

To achieve a modern, instant (0ms) user experience with absolutely zero loader flashes—on both page navigation and hard browser reloads—the `/memories` dashboard implements an **SSR-First + Parallel Category Prefetching** architecture powered by TanStack Start and TanStack Query:

1. **True Server-Side Rendering (SSR)**: On a hard browser reload, the route loader fetches the first page of memories on the server, pre-rendering the memories directly into the static HTML. The user immediately receives the fully populated page with **zero loader flash**.
2. **Parallel Category Prefetching (The Sparse Tab Fix)**: To ensure that client-side category filtering doesn't result in nearly empty tabs on load, the route loader runs parallel queries on the server (using a single `Promise.all` scan) to fetch:
   - The first 50 memories for the main feed (`All` / `category: undefined`).
   - The first 50 memories for each specific category: `MARKET_EVENT` (Events), `CALENDAR_EVENT` (Calendar Events), `POST_MORTEM` (Post-Mortems), and `ACADEMIC_PAPER` (Principles).
3. **Server-Side Merge & Deduplication**: The loader combines the parallel results, deduplicates them by unique ID, and sorts them chronologically descending (newest first). This unified list is sent to the browser.
4. **Hydrated TanStack Query State**: The `MemoriesPage` component is initialized with this server-fetched list via React Query's `initialData`. Because it's hydrated instantly on mount, `isPending` is false, and the memories are rendered immediately with zero flicker.
5. **100% In-Memory Filtering**: All category tabs filter the local query array completely in-memory in the browser. Transitioning between tabs is instantaneous (0ms) and dispatches zero server requests. Because we pre-fetched 50 of each type, every single tab is guaranteed to show a rich pool of data instantly on mount.
6. **Dynamic Cursor-Based Pagination**: When the user clicks "Load More", the page displays additional locally loaded items. If more items are required from the database, it utilizes TanStack Query's `useInfiniteQuery` to fetch subsequent pages from the server in the background, appending them seamlessly.

**Implementation**: The data fetching is configured cleanly at the routing layer in `routes/memories/index.tsx` using a route `loader` and a server function wrapper (`getMemories`). The `MemoriesPage` component utilizes `useInfiniteQuery` for bulletproof, prop-driven cursor-based pagination, while all old client-side local storage caching libraries (`cache.ts`), progressive fills, and self-healing validation endpoints are completely deleted, reducing codebase footprint and complexity.

To maintain consistency, the database `memory_type` values and Frontend UI selectors remain **fully unified** as first-class discriminators. The client-side classifier `getMemoryCategory(m)` categorizes memories in-memory and applies dynamic brand-color badge styles:

- **Events (`MARKET_EVENT`)**: (displayed as "Events").
- **Calendar Events (`CALENDAR_EVENT`)**: (displayed as "Calendar Events").
- **Principles (`ACADEMIC_PAPER`)**: (displayed as "Principles").
- **Post-Mortems (`POST_MORTEM`)**: (displayed as "Post-Mortems").
- **Resolved Events (`status === 'RESOLVED'`)**: (displayed as "Resolved", filtering memories by resolved status).
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
- **Lessons Learned (`LESSON_LEARNED`) & Post-Mortems (`POST_MORTEM`) & Academic Papers (`ACADEMIC_PAPER`)**: Never decay (relevance score remains permanently at `1.0` to preserve core trading insights and immutable trade outcomes).
- **Uncrowded Trades (`UNCROWDED_TRADE`)**: Slow decay at **0.72× per 30-day half-life** (~28%/month). Stays meaningful for ~2 months, falls below the 0.05 retrieval threshold by month 12. This models cycle-specific theses (e.g. "AI infrastructure is the adjacent play") that are valid for one market cycle but become noise once the cycle turns.
- **Superseded Pruning**: To prevent pgvector storage bloat, `SUPERSEDED` memories older than **180 days** are hard-deleted during weekly cleanups, ensuring that historical trace records are kept lean.

### The "Sleep Cycle" (Weekly Memory Consolidation)
An offline weekly consolidation pipeline groups overlapping memories to compound knowledge and reduce redundancy:
1. **Clustering**: Active memories are retrieved (capped at the **500 most recent active memories** for scaling safety), and an adjacency graph is built by mapping pairs with a cosine similarity metric `>= 0.85`. Connected components are identified using depth-first search (DFS).
2. **Synthesis**: For clusters of 2 or more overlapping memories, the system invokes DeepSeek (`DEEPSEEK_MODEL` from `core.config`) using `instructor` to guarantee a structured Pydantic schema response.
3. **Canonical Record Creation**: A single canonical consolidated memory is inserted with `status='ACTIVE'`, `relationship_type='UPDATE'`, and `parent_id` pointing to the primary parent.
4. **Supersedence**: The original memories in the cluster are updated to `status='SUPERSEDED'`, maintaining reference links while removing them from the active analysis hot path.


### Event Chain Graph Traversal

The Event Chain feature visualizes the full geopolitical timeline of a memory by reconstructing its causal tree. When displaying an event chain for a specific memory:
1. **Database Traversal (RPC)**: Rather than executing slow client-side pagination loops, the system invokes the database function `get_memory_chain` via the Supabase API.
2. **Recursive CTE Engine**: Inside the database, a recursive SQL Common Table Expression (CTE) traverses backward via `parent_id` foreign keys to locate the absolute root node (the originating event), and then recursively gathers all child descendants and sibling branches.
3. **Chronological Assembly & Pre-Formatting**: The resulting subset of connected memories is sorted chronologically by `created_at` in the server loader via `buildChain`. To satisfy the **Zero-Date Frontend Architecture**, dates are pre-formatted on the server using centralized timezone-locked helper utilities (`formatEasternDateTimeWithYear`) to lock the timezone output (Eastern Time `America/New_York`) and normalize whitespaces.
4. **Hydration-Safe Rendering**: The client component (`EventChainPage`) renders the static pre-formatted date string directly without executing any runtime browser-side Date parses, preventing client-server timezone disparities and narrow non-breaking space warnings (React Error #418).

This architecture ensures optimal edge serverless TTFB (<5ms database select) and guarantees 100% flawless SSR hydration performance.


### Memory-to-Source Citations (Lazy Newsletter Snapshots Fetching)

To verify the origins and context behind a promoted memory (e.g. why an LLM prioritized a specific event or geopolitical shift), the system supports tracing memories back to the raw source newsletter snapshots:
1. **Source IDs Storage**: When memories are created, the list of original database `newsletter_snapshots` IDs is stored within the memory's `metadata` JSONB column as `source_ids` (an array of strings) or `source_id` (a single string).
2. **Secure RPC Gatekeeper**: A secure PostgreSQL RPC function `get_referenced_newsletter_snapshots(target_source_ids TEXT[])` is exposed to lazy-load newsletter context specifically linked to a memory, running with `SECURITY DEFINER` privileges. Note that while `newsletter_snapshots` originally blocked all public direct `SELECT` queries via RLS policies, `SELECT` access was later granted to the public/anonymous client to support the Today page's Daily Intelligence Briefing.
3. **On-Demand Client Fetching**: When a memory card is expanded in the UI (`MemoryCard.tsx`), TanStack Query `useQuery` fetches the referenced source snapshots using the RPC client fetcher `fetchReferencedNewsletters`.
4. **Cache & Performance**: The query uses a `staleTime` of 5 minutes to avoid redundant RPC roundtrips during collapse/expand toggles, ensuring the page's initial loader remains lightweight and high-performance.


## Related

- [[entities/pipeline]]
- [[entities/database]]
- [[concepts/rag-strategy]]
- [[concepts/auto-research-prompt-improver]]
- [[entities/autoresearch]]
- [[concepts/consensus]]
