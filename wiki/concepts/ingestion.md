---
tags: [ingestion, newsletters, calendar, government]
category: concept
---

# Ingestion

Three parallel ingestion streams that feed the pipeline:

- **Newsletters**: Gmail API → HTML parsing (BeautifulSoup) → ad removal
  (Gemini Flash, parallel via `asyncio.gather` running asynchronously via non-blocking `asyncio.to_thread` client calls) → deterministic hashing → single-transaction bulk `UPSERT` into `newsletter_snapshots` (with automated sequential fallback on failure).
  Source IDs use the `news_{sender_clean}_{MD5[:8]}` pattern for idempotency; chunk hashes are SHA-256.
- **Economic Calendar**: Periodic cron fetches global macro catalysts →
  `CALENDAR_EVENT` memories with `is_future_catalyst=true`.
- **Government Tracking**: Scans for policy bills, subsidies, regulatory changes
  across G7 and major G20 economies. Stores as `GOVERNMENT_INCENTIVE` memories.
- **Prediction Markets (Hybrid)**: Periodically fetches active, high-volume sentiment data from Polymarket and Kalshi APIs, filtered via a lightweight LLM classifier, and upserts them to `prediction_market_snapshots`. Also exposed as real-time tools for active agent queries.

## Key Design

Deterministic `source_id = news_{sender_clean}_{MD5[:8]}` (where `sender_clean` is the sender's email address slugified, and the `MD5[:8]` hash is derived from `date_str + sender + subject`) means re-ingesting the same email produces the same ID. UPSERTs are idempotent. If a sender re-sends an article under a new subject, the chunk hash changes and it's treated as new.

## Sequential Decoupling (Consensus-First Trading)


The ingestion analysis phase utilizes a **sequential two-pass decoupling** model to maximize LLM performance by providing single-objective tasks:

1. **Pass 1: Macro Extraction & Synthesis**: LLMs receive newsletter chunks and extract macro-economic events (`MacroEventsResponse`). These events are then clustered and promoted via the Event Consensus Protocol.
2. **Pass 2: Trading Decisions**: LLMs receive the newsletter summaries/menus along with the synthesized consensus events context (`TradingDecisionsResponse`). The models analyze the consensus events and generate trading decisions.

This separates the broad consensus reasoning from specific asset trading logic, ensuring higher focus and better adherence to trading rules.

## Related

- [[entities/pipeline]]
- [[concepts/reasoning]]
- [[concepts/consensus]]

