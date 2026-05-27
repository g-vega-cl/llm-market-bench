---
tags: [pipeline, data-flow, phases]
category: entity
---

# Pipeline

The daily pipeline runs on a cron schedule during US market hours
(`.github/workflows/ingest.yml`). Six phases from ingestion to feedback.

## Phase 1: Ingestion

Feeds the platform's multi-agent decision path through three concurrent, idempotent pipelines:
1. **Newsletters**: Gmail API fetches unread newsletters → sanitizes layout and content using BeautifulSoup → parallel ad removal and text cleaning via Gemini Flash under `asyncio.gather` → computes deterministic `source_id` (`news_{sender_clean}_{MD5[:8]}`) and SHA-256 `chunk_hash` → idempotent single-transaction bulk `UPSERT` into the `newsletter_snapshots` database (with automatic sequential fallback on failure). This deterministic hashing prevents duplicate ingestion on rerun.
2. **Economic Calendar**: Periodic schedules scan and fetch macro events, injecting them as `CALENDAR_EVENT` memories marked with `is_future_catalyst = true` for high-importance horizons.
3. **Government Tracking**: Continuously monitors G7/G20 governmental policy announcements, subsidy bills, and regulatory shifts, persisting them as high-importance `GOVERNMENT_INCENTIVE` memories.

For more details on ingestion mechanics, see [[concepts/ingestion]].

## Phase 2: Pre-Analysis

Market hours check (holiday-aware, class-level caching) → price history cache
validation → dust cleanup (auto-sell negligible positions) → Global Macro
Tracker (σ-based regime detection) → portfolio initialization with lightweight
historical context (top-5 importance memories, no embedding calls).

## Phase 3: Analysis

News chunks split into batches. Each batch receives portfolio summary + market
data + context. All batches run in parallel via `asyncio.gather`. LLMs invoke
tools (stock quote, price history, quantity calculators, web search, stock
screener, uncorrelated assets). Discovery Agent identifies thematic assets
before main analysis. Structured extraction via Instructor + Pydantic with
3-attempt retry.

## Phase 4: Consensus

Semantic clustering (cosine similarity) → weighted voting → temporal
dedup → relationship analysis (REVERSAL/RESOLUTION/UPDATE) → LLM synthesis →
scenario analysis → alpha discovery via DiscoveryAgent. Trend/momentum tracking
with concept velocity (intensity × growth), PCA visualization, half-life decay.

## Phase 5: Execution

Settles trades in the market using a multi-layered verification and database preservation process:
1. **Pre-Market Validation**: Before placement, trades must pass rigorous checks:
   - **Existence**: Ticker is validated and resolved via FMP.
   - **Liquidity**: Verifies the asset's market cap exceeds the minimum floor.
   - **Staleness**: Ensures JIT (Just-In-Time) quote prices do not deviate by > 2% compared to model prompt prices.
   - **SMA Floor**: Checks if projected 50-day/200-day SMA is above safety parameters.
2. **Reg T Margin Checks**: Validates Initial Margin, Maintenance Margin, and active Buying Power under a 10% minimum position constraint.
3. **Commit at the End**: Settles trades in the database using an atomic two-phase write (`decision_id` saved → position `UPSERT` → trade `INSERT` → updates cash/SMA balances). This prevents phantom balance deductions in the event of query failure.
4. **Alpaca Broker Mirroring**: Executes paper-trading limit orders via the Alpaca API. Statuses are decoupled and tracked dynamically via the daily cron sync script.
5. **Performance Snapshots**: Compiles daily equity curves for all active portfolios (cash-only, inactive portfolios are skipped), fetching market data in a single optimized batch `get_quotes()` call.

For more details on execution safeguards and order settlement, see [[concepts/execution]].

After execution, a daily performance snapshot records equity curves for all
active portfolios (those holding positions — empty cash-only portfolios are
skipped). Market data is fetched in batch via `get_quotes()` rather than
individual sequential `get_quote()` calls.

## Phase 6: Feedback

Manager Agent post-mortem (multi-horizon → LESSON_LEARNED memories) →
Contrarian Agent (crowded trade detection → counter-trades) → Cause & Effect
audit (retrospective vs actual price data) → Market Feeling sentiment.

## Related

- [[entities/engine]]
- [[concepts/ingestion]]
- [[concepts/reasoning]]
- [[concepts/consensus]]
- [[concepts/execution]]
- [[concepts/memory-feedback]]
