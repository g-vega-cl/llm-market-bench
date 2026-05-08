---
tags: [pipeline, data-flow, phases]
category: entity
---

# Pipeline

The daily pipeline runs on a cron schedule during US market hours
(`.github/workflows/ingest.yml`). Six phases from ingestion to feedback.

## Phase 1: Ingestion

Gmail API fetches unread newsletters → BeautifulSoup HTML parsing → Gemini Flash
removes ads → deterministic source_id + chunk_hash → UPSERT into
`newsletter_snapshots`. Parallel fetching of economic calendar and government
data.

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

Pre-market validation (existence, liquidity, staleness ≤2%, buying power, min
value, SMA floor) → Reg T margin check → "Commit at the End" settlement
(decision_id → position UPSERT → trade INSERT → cash/save) → Alpaca paper
mirror. Attribution locking creates bidirectional Decision ↔ Trade links.

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
