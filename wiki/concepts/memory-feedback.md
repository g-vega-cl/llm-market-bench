---
tags: [memory, feedback, rag, learning]
category: concept
---

# Memory & Feedback Loops

Two primary feedback mechanisms make the system improve over time.

## Manager Agent (Post-Mortem)

At configured intervals after trade execution (short, medium, long horizons):
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

## Structured Scenarios, Adversarial Debate & Ticker Mapping

To make scenario analysis and consensus memories highly actionable and stress-tested, memories support a strict **Gold Standard** structured scenarios and debate schema inside their database `metadata`:
1. **Two-Stage Adversarial Debate (`gpt-5.6-luna`)**: Before final synthesis, `gpt-5.6-luna` runs as an Adversarial Red-Team Challenger to discover counter-theses, pre-mortem failure modes, and unaddressed risks. The Arbiter then synthesizes hedged scenarios and trading plans addressing these failure modes. The resulting critique is stored in `metadata.debate` and rendered with a `🛡️ Stress-Tested` badge.
2. **Pydantic Scenarios List**: The synthesis returns a typed `scenarios` array containing individual scenario objects (`cleanHeader`, `percentage`, `outcome`, `tradingPlan`).
3. **Targeted Ticker Discovery**: For each synthesized scenario, the consensus engine runs the `DiscoveryService` specifically against that scenario's individual `tradingPlan` context (invoking FMP company screeners and web search). Verified tickers are tagged by scenario and saved directly inside the respective scenario object (`scenarios.assets`).
4. **Structured UI Rendering**: The frontend memories UI (`MemoryCard.tsx`) renders the Adversarial Red-Team Stress-Test panel alongside the structured scenarios and nested ticker pills. Clicking nested scenario tickers selects and launches the FMP asset details modal. In addition, the "Other Investable Assets" section is cleanly hidden if all discovered assets are already mapped directly to scenarios (resulting in 0 remaining global assets).
5. **Resilient Fallback**: The backend continues to populate a unified flat string `scenario_analysis` fallback in the database to ensure legacy consumer pages (e.g. `FutureCatalysts.tsx` timeline) remain fully operational.
6. **Structured Historical Parallel & Chat Gateway Interrogation**: If model observations or news cite historical precedent, the Arbiter synthesizes a structured `HistoricalParallelDetail` object (`title`, `timeframe`, `precedent`, `market_reaction`, `takeaway`, `affected_assets`) stored in `metadata.historical_parallel`. The frontend (`MemoryCard.tsx`) renders this panel inside "Show Analysis" with the precedent narrative, asset reaction, and an interactive deep link to `/chat` ("Interrogate Parallel in AI Chat →").

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
3. **Server-Side Merge & Deduplication**: The loader combines the parallel results, deduplicates them by unique ID, and sorts them chronologically descending (newest first). This unified list is sent to the browser. The loader additionally returns an `initialByCategory` map (`Record<string, PaginatedMemories>`) keyed by category name, holding each category's own page payload (`data`, `hasMore`, `nextCursor`) so per-category pagination cursors survive hydration.
4. **Hydrated TanStack Query State**: The `MemoriesPage` component is initialized with this server-fetched list via React Query's `initialData`. Because it's hydrated instantly on mount, `isPending` is false, and the memories are rendered immediately with zero flicker. `initialData` is a function that selects the right seed per active filter: the matching `initialByCategory[category]` slice when available, otherwise an in-memory filter of `initialMemories` by `getMemoryCategory(m) === category`, otherwise the full `initialMemories` list for the `All` tab. The infinite query sets `initialDataUpdatedAt: 0` so the SSR slice is treated as immediately stale and expands to a full page on mount; page flattening is null-safe (`page?.data || []`) and `getNextPageParam` guards `lastPage?.hasMore`.
5. **Category-Scoped Query Keys**: The infinite query is keyed as `['benchify', 'memories', 'list', categoryKey]`, where `categoryKey` is the active filter (`'all'` for the `All` tab and for `RESOLVED`, otherwise the memory type). Each tab therefore owns an independent infinite-query cache entry, so switching tabs is instantaneous (served from the hydrated seed) and never mixes pagination state across categories. The `RESOLVED` filter is a status filter rather than a memory type, so it maps to the unscoped `all` key.
6. **Category-Aware Cursor Pagination**: When the user clicks "Load More", `fetchNextPage` calls the server fetcher with both the page cursor and the active category (`fetchFn(cursor, category)`), so subsequent pages are fetched from the database already scoped to the selected tab and continue from that category's own `nextCursor`. Newly fetched pages are appended seamlessly to the category's cache entry.
7. **No Empty-State Flash During Expansion**: While the background expansion is in flight (`isFetching`), `MemoriesPage` passes `isLoading` to `MemoriesList`, which renders `Loading memories…` instead of the `No memories found in this category` empty state. A filter that has no match in the 2-item SSR slice therefore never claims the category is empty before the full page arrives.

**Implementation**: The data fetching is configured cleanly at the routing layer in `routes/memories/index.tsx` using a route `loader` and a server function wrapper (`getMemories`). The `MemoriesPage` component utilizes `useInfiniteQuery` for bulletproof, prop-driven cursor-based pagination, while all old client-side local storage caching libraries (`cache.ts`), progressive fills, and self-healing validation endpoints are completely deleted, reducing codebase footprint and complexity.

To maintain consistency, the database `memory_type` values and Frontend UI selectors remain **fully unified** as first-class discriminators. The client-side classifier `getMemoryCategory(m)` categorizes memories in-memory and applies dynamic brand-color badge styles:

- **Events (`MARKET_EVENT`)**: (displayed as "Events").
- **Calendar Events (`CALENDAR_EVENT`)**: (displayed as "Calendar Events").
- **Principles (`ACADEMIC_PAPER`)**: (displayed as "Principles").
- **Post-Mortems (`POST_MORTEM`)**: (displayed as "Post-Mortems").
- **Resolved Events (`status === 'RESOLVED'`)**: (displayed as "Resolved", filtering memories by resolved status).
- **Lessons (`LESSON_LEARNED`)**: (retained for generic legacy lessons).

### Sorting, Date Presets & Smart Caching
To navigate large historical memory corpuses efficiently, the Memories page features:
1. **Importance Sorting**: Dropdown selector supporting `Newest First` (default), `Highest Importance` (orders by `importance_score` descending 10→1, tiebreak `created_at` desc), `Lowest Importance`, and `Oldest First`.
2. **Date Presets**: Fast client-side filter pills (`All Time`, `7D`, `30D`, `90D`) evaluating memory `created_at` against sliding time windows.
3. **High Impact (8+) Toggle**: One-click filter isolating critical macro events, Horizon Watch catalysts, and key trade post-mortems with `importance_score >= 8`.
4. **4-Hour Caching with Mount Delta-Sync**: TanStack Query caches the memory list with a 4-hour `staleTime` (`1000 * 60 * 60 * 4`). On mount, a lightweight check calls `syncMemories` to inspect whether any new records arrived since the newest cached memory, prepending newly ingested deltas without full-table reloads. The delta-sync write targets the currently active category-scoped query key (`['benchify', 'memories', 'list', categoryKey]`) and re-runs when the active category changes.
5. **PostHog Analytics**: Tracks `memories_sort_changed`, `memories_date_preset_changed`, and `memories_high_impact_toggled` along with result counts to observe how users explore historical market theses.

*Note: The empty Decisions (`decision_reasoning`) and redundant, permanently empty Lessons (`lesson_learned`) filters are completely removed. Decisions are managed under the specialized **Reasoning** page rather than the memories table. Post-mortem lessons and academic principles fully cover all lessons learned, so a dedicated empty general lessons tab is unnecessary.*




### Zero-Compute Database Full-Text Search
To search historical events without serialization bloat or edge worker timeouts:
1. **Database-Level Full-Text Search**: Replaces legacy in-memory full-table downloads (3,144 rows + 768-dim float vectors = 18.8 MB) and quadratic Levenshtein loops with PostgreSQL `to_tsvector('english', content)` and `websearch_to_tsquery` via PostgREST `.textSearch('content', query, { type: 'websearch' })`.
2. **Dedicated GIN Index**: Supported by `memories_content_fts_idx` GIN index for sub-10ms English text search execution.
3. **Scalar Column Projection**: Restricts database select queries to scalar metadata columns (`MEMORY_SCALAR_COLUMNS`), permanently preventing high-dimensional embedding vector leakage across the web read path.
4. **TanStack Query Caching**: Search queries are managed with a 5-minute `staleTime` via `memoriesQueries.search` to eliminate redundant server trips when re-inspecting terms.

### Memory Reinforcement & Duplicate Bumping
When a new memory is ingested with `check_similarity=True`, the system performs a semantic similarity search. If a duplicate or highly similar entry is found:
- Instead of creating a redundant record or silently skipping it, the system **bumps** the existing memory.
- Bumping resets the `relevance_score` to `1.0` and updates the `created_at` timestamp to the current UTC time, keeping high-signal recurring concepts fresh in the retrieval window.
- The duplicate check utilizes an extended **168-hour (7 days) lookback window** to prevent redundant database inserts across weekends and weekly schedules.
- **Consensus promotion exception (fix 2026-08-27):** the consensus pipeline (`analysis/consensus.py`) uses a stricter `168h→24h` lookback with `MEMORY_DEDUP_THRESHOLD=0.90` (`core/config.py`), **decoupled** from semantic grouping `0.75`. The previous coupling at `0.75` caused false dedup at Sim `0.77-0.80` (IDs `4685e74f`, `b2174ca9` collisions on 2026-08-27). General `memory/store.add_memory` default remains `0.90`/`168h`.

### Tiered Memory Decay
To prevent context window pollution and reasoning degradation while retaining key long-term lessons, the system applies adaptive tiered decay rates during weekly cleanups:
- **Market Events (`MARKET_EVENT`)**: Decays standardly (relevance reduced by 50% after half-life threshold).
- **Government Incentives (`GOVERNMENT_INCENTIVE`)**: Decays mildly (relevance reduced by 25% after half-life threshold).
- **Lessons Learned (`LESSON_LEARNED`) & Post-Mortems (`POST_MORTEM`) & Academic Papers (`ACADEMIC_PAPER`)**: Never decay (relevance score remains permanently at `1.0` to preserve core trading insights and immutable trade outcomes).
- **Autoresearch Insights (`AUTORESEARCH_INSIGHT`)**: Conditional decay. Baseline-beating insights (`metadata.is_baseline_beat = true` or `importance_score >= 8`) never decay (relevance remains `1.0`) to retain permanent algorithmic breakthroughs. Exploratory or non-winning insights decay at **0.50× per 30-day half-life** to prevent hypothesis clutter. Track-isolated by `metadata.track_id` and `metadata.scope`, and capped at `limit=5` on retrieval.
- **Uncrowded Trades (`UNCROWDED_TRADE`)**: Slow decay at **0.72× per 30-day half-life** (~28%/month). Stays meaningful for ~2 months, falls below the 0.05 retrieval threshold by month 12. This models cycle-specific theses (e.g. "AI infrastructure is the adjacent play") that are valid for one market cycle but become noise once the cycle turns.
- **Superseded Pruning**: To prevent pgvector storage bloat, `SUPERSEDED` memories older than **180 days** are hard-deleted during weekly cleanups, ensuring that historical trace records are kept lean.

### The "Sleep Cycle" (Weekly Memory Consolidation)
An offline weekly consolidation pipeline groups overlapping memories to compound knowledge and reduce redundancy:
1. **Clustering**: Active memories are retrieved (capped at the **500 most recent active memories** for scaling safety), and an adjacency graph is built by mapping pairs with a cosine similarity metric `>= 0.85`. Connected components are identified using depth-first search (DFS).
2. **Synthesis**: For clusters of 2 or more overlapping memories, the system invokes DeepSeek Flash (`DEEPSEEK_FLASH_MODEL` from `core.config`) using `instructor` to guarantee a structured Pydantic schema response.
3. **Canonical Record Creation**: A single canonical consolidated memory is inserted with `status='ACTIVE'`, `relationship_type='UPDATE'`, and `parent_id` pointing to the primary parent.
4. **Supersedence**: The original memories in the cluster are updated to `status='SUPERSEDED'`, maintaining reference links while removing them from the active analysis hot path.
5. **Execution Environment**: Runs every Friday at 16:00 EST (21:00 UTC) via `.github/workflows/audit.yml` (`python main.py cleanup`), requiring `DEEPSEEK_API_KEY` for synthesis and `GEMINI_API_KEY` for vector embedding generation.


### Event Chain Graph Traversal & Thought Journey Timeline

The Event Chain feature visualizes the full geopolitical timeline of a memory by reconstructing its causal tree. When displaying an event chain for a specific memory:
1. **Database Traversal (RPC)**: Rather than executing slow client-side pagination loops, the system invokes the database function `get_memory_chain` via the Supabase API.
2. **Recursive CTE Engine**: Inside the database, a recursive SQL Common Table Expression (CTE) traverses backward via `parent_id` foreign keys to locate the absolute root node (the originating event), and then recursively gathers all child descendants and sibling branches.
3. **Chronological Assembly & Pre-Formatting**: The resulting subset of connected memories is sorted chronologically by `created_at` in the server loader via `buildChain`. To satisfy the **Zero-Date Frontend Architecture**, dates are pre-formatted on the server using centralized timezone-locked helper utilities (`formatEasternDateTimeWithYear`) to lock the timezone output (Eastern Time `America/New_York`) and normalize whitespaces.
4. **Hydration-Safe Rendering**: The client component (`EventChainPage`) renders the static pre-formatted date string directly without executing any runtime browser-side Date parses, preventing client-server timezone disparities and narrow non-breaking space warnings (React Error #418).

#### Chain Annotation (`buildChain`)

`buildChain(memoryId, memories)` in `apps/web/src/features/memories/utils/build-chain.ts` returns `{ chain, targetMemory }` where each `ChainMemory` node is annotated for timeline rendering. `ChainMemory` is a standalone interface (it no longer extends the database `Memory` type) carrying `id`, `content`, `created_at`, `formattedDate`, `isRoot`, `elapsedFromRoot`, `elapsedFromPreceding`, `modelsInvolved`, `directPredecessorId`, `directSuccessorIds`, plus the passthrough `status`, `parent_id`, `relationship_type`, `relevance_score`, `memory_type`, `importance_score`, `target_date`, and `metadata` fields.

- **Elapsed durations** — `formatElapsedDuration(diffMs)` renders `0m later`, `<1m later`, `+Nm later`, `+Nh Nm later`, or `+Nd Nh later`. The root node is stamped `Origin Catalyst` for `elapsedFromRoot` and `Origin` for `elapsedFromPreceding`; every other node gets the delta from the root and from its immediately preceding chain node.
- **Model attribution** — `extractModelsInvolved(metadata)` unions `metadata.models_involved`, `metadata.participating_agents`, `metadata.model_name`, `metadata.debate.adversary_model`, and `metadata.debate.arbiter_model` into a deduplicated string list, so the red-team challenger appears alongside the synthesizing models.
- **Graph edges** — `directPredecessorId` is the node's `parent_id`; `directSuccessorIds` lists every chain node whose `parent_id` points at it.
- **Target resolution** — `targetMemory` is the annotated node from the chain when the selected id is present, otherwise a synthesized annotation of the raw row (root-stamped, empty successors).

#### Thought Journey Timeline UI

`EventChainPage` (`apps/web/src/features/memories/pages/EventChainPage.tsx`) renders the chain as a vertical **Thought Journey & Event Chain** timeline rather than a flat list:

- **Step headers** — each card carries a solid monospace step chip: `STEP 1 • CATALYST ORIGIN` for the root, `STEP n • RESOLUTION` for the final node of a multi-node chain, and `STEP n` otherwise.
- **Directional connectors** — between consecutive steps a centered connector renders a `↓` glyph, a solid relationship badge colored by `getRelationshipColor` (`RESOLUTION` → success, `REVERSAL` → warning, `UPDATE` → info, default neutral), and the `elapsedFromPreceding` duration.
- **Metadata ribbon** — type badge (`getTypeBadgeColor`), `$TICKER` badge, impact badge (`getImpactBadgeColor`), and an `★ N/10` importance score, with the pre-formatted Eastern date and `elapsedFromRoot` on the right.
- **Focus banner** — the selected memory renders an emerald `← You selected this event` strip and a ringed card border.
- **Model process section** — `Models Involved:` renders one `🤖 <model>` outline badge per attributed model; `metadata.debate` renders a `🛡️ Red-Team Stress-Test` panel with the challenger model, counter-thesis, pre-mortem failure mode, and key risks list; `metadata.scenarios` renders a two-column `Probability Scenarios:` grid of header/percentage/outcome tiles.
- **Chain switcher** — a `Card variant="glass"` bar above the timeline hosts `ChainMemorySwitcher`.
- **Chat interrogation footer** — an `💬 Interrogate Chain in AI Chat →` button deep-links to `/chat` with a pre-composed `q` search param summarizing the first and last chain events plus the primary ticker, alongside the `Back to All Memories` action.

#### Chain Switcher (`ChainMemorySwitcher`)

`apps/web/src/features/memories/components/ChainMemorySwitcher.tsx` lets a viewer jump between causal chains without returning to the memories index:

- **Featured ticker pills** — `$TSLA`, `$NVDA`, `$SPY`, `$AAPL`, `$Macro` ghost buttons that seed the search box and immediately run the query.
- **Search input** — debounce-free `onChange` search with a leading magnifier icon and a trailing `LoadingSpinner` while in flight; the `searchFn` prop is injected (the page passes `searchMemories`), keeping the component hermetic for tests.
- **Results dropdown** — an absolutely positioned panel listing up to 10 matches, each showing the `$TICKER` badge, the memory date, a two-line clamped content preview, and a `CURRENT` marker for the active chain. Outside `mousedown` closes the panel.
- **Navigation** — selecting a result calls `navigate({ to: '/memories/chain/$memoryId', params: { memoryId } })`, skipping navigation when the selected id is already current.


### Memory-to-Source Citations (Lazy Newsletter Snapshots Fetching)

To verify the origins and context behind a promoted memory (e.g. why an LLM prioritized a specific event or geopolitical shift), the system supports tracing memories back to the raw source newsletter snapshots:
1. **Source IDs Storage**: When memories are created, the list of original database `newsletter_snapshots` IDs is stored within the memory's `metadata` JSONB column as `source_ids` (an array of strings) or `source_id` (a single string).
2. **Secure RPC Gatekeeper**: A secure PostgreSQL RPC function `get_referenced_newsletter_snapshots(target_source_ids TEXT[])` is exposed to lazy-load newsletter context specifically linked to a memory, running with `SECURITY DEFINER` privileges. Note that while `newsletter_snapshots` originally blocked all public direct `SELECT` queries via RLS policies, `SELECT` access was later granted to the public/anonymous client to support the Today page's Daily Intelligence Briefing.
3. **On-Demand Client Fetching**: When a memory card is expanded in the UI (`MemoryCard.tsx`), TanStack Query `useQuery` fetches the referenced source snapshots using the RPC client fetcher `fetchReferencedNewsletters`.
4. **Cache & Performance**: The query uses a `staleTime` of 5 minutes to avoid redundant RPC roundtrips during collapse/expand toggles, ensuring the page's initial loader remains lightweight and high-performance.


## Related

- [[entities/gainers-postmortem]]
- [[entities/pipeline]]
- [[entities/database]]
- [[concepts/rag-strategy]]
- [[concepts/auto-research-prompt-improver]]
- [[entities/autoresearch]]
- [[concepts/consensus]]
- [[concepts/rendering-strategies]]
- [[concepts/tanstack-query]]
