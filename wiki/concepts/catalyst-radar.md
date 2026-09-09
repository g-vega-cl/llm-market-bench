---
tags: [concepts, calendar, catalysts, digestion, radar, tools]
category: concept
---

# Catalyst Radar (Keep an Eye)

The Catalyst Radar represents the architectural convergence between high-velocity narrative concepts (`concept_metrics`) and scheduled market calendar events (`memories`).

Separately, concepts lack dates and calendars lack narrative conviction. By pairing them via pgvector cosine similarity and a 4-stage market digestion lifecycle, the system exposes an actionable radar for human traders and autonomous agents.

## 4-Stage Digestion Lifecycle

Price discovery does not finish at the moment an event occurs. The market requires 1 to 3 trading days to absorb commentary, process revisions, and resolve post-announcement drift.

| Stage | Date Offset | User-Facing Display | Context |
| :--- | :--- | :--- | :--- |
| **Upcoming** | $+1$ to $+14$ days | `Sep 16, 2026 (1 week from now)` <br> `Sep 10, 2026 (tomorrow)` | Narrative anticipation and pre-positioning. |
| **Active / Today** | $0$ days | `Sep 09, 2026 (today)` | Live event release day with peak intraday volatility. |
| **Digesting** | $-1$ to $-3$ days | `Sep 08, 2026 (digesting, 1 day ago)` <br> `Sep 06, 2026 (digesting, 3 days ago)` | Post-event settlement, analyst revisions, and drift. |
| **Expired** | $\le -4$ days | Archived | Historical post-mortem phase. Removed from active radar. |

## Zero-LLM Vector Matching

Matching is computed deterministically in memory or database using vector math:
1. **Concept Filtering**: Filters concepts with `velocity_score >= 1.0` (or `1.2` for agent queries) and valid `concept_vector`.
2. **Calendar Memory Filtering**: Filters active calendar memories with `importance_score >= 7` within `[Now - 3 days, Now + 14 days]`.
3. **Cosine Similarity**: Computes cosine similarity between `concept_vector` and memory `embedding`.
4. **Keyword Boost**: Adds $+0.15$ match boost when a ticker or keyword overlaps between the concept name and event metadata.
5. **Threshold Gate**: Requires overall similarity $\ge 0.35$.

## Agent Tooling & Autoresearch

Under Principle 8 in [[concepts/agent-workflow]], catalyst intelligence is delivered as a lean callable tool:
- **Tool**: `get_catalyst_radar(days_ahead=7, include_digesting=True, min_velocity=1.2, detail=False)`
- **Registry**: Documented in `packages/config/tools.json` and registered in `CANONICAL_TOOLS_REGISTRY`.
- **Modular Block**: `catalyst_radar_discipline` in `apps/engine/autoresearch/prompt_blocks.py` allows the Auto-Researcher to test whether catalyst awareness improves backtest Sharpe ratios.

## UI Surface

On the web dashboard, the radar appears as the **⚡ Keep an Eye** tab in the Concept Tracker (`/concepts`):
- Displays active concept-catalyst collisions sorted by date proximity.
- Features concrete date labels (`1 week from now`, `in 2 days`, `digesting, 1 day ago`).
- Shows status badges (`Upcoming`, `Today`, `Digesting`).
- Expands inline to reveal exact memory quotes, similarity scores, and related tickers.

## Pre-Computed Pipeline Architecture

To prevent heavy vector payload transfers (6MB+) and redundant CPU dot-product calculations on user page views, the Catalyst Radar operates on a **pre-computed materialized pipeline** (mirroring [[entities/market-barometer-audit]] and [[entities/earnings-alpha]]):

1. **Pipeline Triggers (`apps/engine/scripts/update_catalyst_radar.py`)**:
   - **Calendar Ingestion** (`.github/workflows/calendar.yml`): Runs twice weekly (Sunday & Wednesday at 00:00 UTC). After ingesting new events, it triggers `update_catalyst_radar.py`.
   - **Daily Momentum Pipeline** (`main.py`): Step 9 runs `analyze_momentum` and `decay_stale_concepts`, then immediately re-computes `compute_and_store_catalyst_radar()`.
2. **Database Storage (`public.catalyst_radar`)**:
   - Stores pre-matched pairs (`concept_id`, `catalyst_id`, `target_date`, `similarity`, `impact`, `related_tickers`).
   - Automatically prunes expired records older than 3 days past during pipeline runs.
3. **Sub-30ms Zero-Vector Consumption & Tiered Caching**:
   - **Web App** (`apps/web/src/features/concepts/api/fetch-concepts.ts`): Queries `concept_metrics` without downloading 768-dimensional `concept_vector` embeddings over HTTP. In parallel, it fetches `catalyst_radar` rows and calculates dynamic date offsets (`target_date - today`) on the fly.
   - **Tiered 5-Minute Caching**: The backend server function retains a 5-minute shared in-memory cache (`CONCEPTS_CACHE_TTL = 300000`), while TanStack Query maintains a synchronized 5-minute `staleTime` in the client browser, providing instant (<0.1ms) tab switching while automatically revalidating in the background.
   - **Autonomous Agents** (`get_catalyst_radar`): Reads directly from `catalyst_radar` with standard relational filters, formatting results into lean tables or detailed scenario reports.

## Related

- [[entities/tool-registry]]
- [[entities/engine]]
- [[entities/pipeline]]
- [[concepts/memory-feedback]]
- [[concepts/visual-planning]]
