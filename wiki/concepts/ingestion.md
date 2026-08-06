---
tags: [ingestion, newsletters, calendar, government]
category: concept
---

# Ingestion

Three parallel ingestion streams that feed the pipeline:

- **Newsletters**: Gmail API (parallel fetches via `asyncio.gather` for senders in `NEWSLETTER_SENDERS`, including Morning Brew, Bloomberg, Axios, and Substack) → HTML parsing (BeautifulSoup) → ad removal
  (Gemini Flash, parallel via `asyncio.gather` running asynchronously via non-blocking `asyncio.to_thread` client calls) → deterministic hashing → single-transaction bulk `UPSERT` into `newsletter_snapshots` (with automated sequential fallback on failure).
  Source IDs use the `news_{sender_clean}_{MD5[:8]}` pattern for idempotency; chunk hashes are SHA-256.
- **Economic Calendar**: Periodic cron fetches global macro catalysts →
  `CALENDAR_EVENT` memories with `is_future_catalyst=true`.
- **Government Tracking**: Scans for policy bills, subsidies, regulatory changes
  across G7 and major G20 economies. Stores as `GOVERNMENT_INCENTIVE` memories.
- **Prediction Markets (Hybrid)**: Periodically fetches active, high-volume sentiment data from Polymarket and Kalshi APIs, filtered via a lightweight LLM classifier, and upserts them to `prediction_market_snapshots`. Also exposed as real-time tools for active agent queries.

## Performance Optimizations

*   **Parallel Gmail API Fetching**: Payloads for all matching emails are retrieved concurrently via `asyncio.gather` with bounded concurrency (`asyncio.Semaphore(5)`) and 3-attempt exponential backoff retries. Bounded concurrency prevents socket collisions and SSL protocol errors on the underlying `httplib2` transport while maintaining high throughput.
*   **Batched Cache Lookups**: When checking the local ticker price cache in `MarketDataManager.get_quotes`, a single batched query is sent to Supabase using `.in_("ticker", tickers)` instead of executing sequential, individual cache check queries for each symbol.

## Key Design

Deterministic `source_id = news_{sender_clean}_{MD5[:8]}` (where `sender_clean` is the sender's email address slugified, and the `MD5[:8]` hash is derived from `date_str + sender + subject`) means re-ingesting the same email produces the same ID. UPSERTs are idempotent. If a sender re-sends an article under a new subject, the chunk hash changes and it's treated as new.

## Sequential Decoupling (Consensus-First Trading)


The ingestion analysis phase utilizes a **sequential two-pass decoupling** model to maximize LLM performance by providing single-objective tasks:

1. **Pass 1: Macro Extraction & Synthesis**: LLMs receive newsletter chunks and extract macro-economic events (`MacroEventsResponse`). These events are then clustered and promoted via the Event Consensus Protocol. In the LLM audit trace (`llm_reasoning_logs`), these steps are explicitly tagged with `task_type="MACRO_EXTRACTION"`.
2. **Pass 2: Trading Decisions**: LLMs receive the newsletter summaries/menus along with the synthesized consensus events context (`TradingDecisionsResponse`). The models analyze the consensus events and generate trading decisions. In the LLM audit trace (`llm_reasoning_logs`), these steps are tagged with `task_type="INGESTION"`.

This separates the broad consensus reasoning from specific asset trading logic, ensuring higher focus and better adherence to trading rules.

*   **Workflow Schedule**: Triggered via high-precision Cloudflare Worker Cron Dispatcher (`apps/cron-dispatcher`) at 9:35 AM, 10:35 AM, 11:35 AM, and 2:00 PM EDT (`ingest.yml`).
*   **Market Failsafe**: Runs prior to US market open (e.g. 8:35 AM EST / 13:35 UTC in winter) are skipped via `is_market_open_with_logging()` in `apps/engine/core/utils.py`.
*   **High-Precision Dispatch**: Managed via Cloudflare Edge Worker (`apps/cron-dispatcher`) firing `workflow_dispatch` requests to GitHub's REST API, eliminating GitHub Actions native schedule queue delays (< 5s dispatch latency).

## Related

- [[entities/pipeline]]
- [[concepts/reasoning]]
- [[concepts/consensus]]


