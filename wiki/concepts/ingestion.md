---
tags: [ingestion, newsletter, scraping, pipeline]
category: concept
---

# Ingestion

Ingestion is the first phase of the daily pipeline. It fetches raw data from multiple sources: financial newsletters, economic calendars, and government data feeds. The data is stored in Supabase and later consumed by analysis agents.

## Newsletter Scraping

- **Newsletter Snapshots**: Ingested newsletters are stored in the `newsletter_snapshots` table with a `date` field indicating their publication time.
- **Resilient Credential Parsing & API Retry**: Ingestion supports robust parsing of `GMAIL_CREDENTIALS_JSON` and `GMAIL_TOKEN_JSON` via `_parse_json_secret`, automatically stripping outer quotes, handling unescaped control characters (such as raw line breaks from environment formatting via `strict=False`), and providing diagnostic logging per secret key. Both query search listing and raw message fetching use asynchronous retry loops with backoff to withstand transient upstream Google errors (such as `502 Bad Gateway` or `429`).
- **Thread-Safe Gmail API Fetching**: Message retrieval uses `asyncio.to_thread` protected by an `asyncio.Lock` to serialize calls on the shared, non-thread-safe `googleapiclient.discovery.Resource` instance (`service`). This prevents socket/SSL data races and C-level memory corruption (`Segmentation fault`) during batch message fetching, while keeping Phase 2 LLM advertisement cleaning fully concurrent via `asyncio.gather()`.
- **Daily Newsletter Generation**: A separate step (see [[entities/generated-newsletters]]) generates a digest newsletter using DeepSeek V4 Flash. It queries newsletters published within the last **12 hours** (based on the `date` column), not the `ingested_at` timestamp. This rolling window ensures overnight and early-morning editions are captured for the morning session.
- **Lookback Window**: The 12-hour window is measured from the current Eastern Time to the `date` field of each snapshot. The switch from `ingested_at` to `date` improved alignment with actual publication times.

## Economic Calendar

The economic calendar ingestion pipeline (`apps/engine/ingest/calendar.py`) runs semi-weekly via GitHub Actions (`.github/workflows/calendar.yml`) on Sunday and Wednesday at 00:00 UTC:
- **Scraping**: Fetches upcoming macro events from Trading Economics using non-recursive top-level table cell parsing to capture 7 structured columns (`Time`, `Country`, `Event`, `Actual`, `Previous`, `Consensus`, and `Forecast`).
- **Deterministic Tag Indexing**: Ingested events are formatted with numerical index tags (`[#N]`). DeepSeek Flash analyzes the batch to identify high-importance events ($\ge 8/10$) or calendar anomalies (Pre-ECB/Fed Drift, Pre-Holiday Effect, Payday/Turn-of-the-Month), setting `source_id = "[#N]"`.
- **Target Date & Catalyst Storage**: Resolves event date and time deterministically in $O(1)$ from the source table, storing high-importance records in Supabase `memories` with `memory_type = 'CALENDAR_EVENT'`, `is_future_catalyst = true`, and `target_date = YYYY-MM-DD`.
- **Frontend Integration**: Displayed on the Today dashboard in the **Horizon Watch** timeline (`FutureCatalysts.tsx`) with dynamic Critical/High badges and chronological sequencing.

## Government Data

… (existing content)

## Related

- [[entities/generated-newsletters]]
- [[entities/pipeline]]
- [[concepts/ingestion]]
