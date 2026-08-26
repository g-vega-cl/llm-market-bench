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

… (existing content)

## Government Data

… (existing content)

## Related

- [[entities/generated-newsletters]]
- [[entities/pipeline]]
- [[concepts/ingestion]]
