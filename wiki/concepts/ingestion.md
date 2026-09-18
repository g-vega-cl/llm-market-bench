---
tags: [ingestion, newsletter, scraping, pipeline]
category: concept
---

# Ingestion

Ingestion is the first phase of the daily pipeline. It fetches raw data from multiple sources: financial newsletters, economic calendars, and government data feeds. The data is stored in Supabase and later consumed by analysis agents.

## Newsletter Scraping

- **Newsletter Snapshots**: Ingested newsletters are stored in the `newsletter_snapshots` table with a `date` field indicating their publication time.
- **Dual Authentication Modes (App Password vs OAuth 2.0)**: Ingestion supports two authentication mechanisms, controlled via environment variables:
  - **Google App Password (Preferred)**: When `GMAIL_EMAIL` and `GMAIL_APP_PASSWORD` are defined, ingestion connects directly to `imap.gmail.com:993` via SSL using Python's built-in `imaplib`. It leverages Gmail's `X-GM-RAW` search extension to run standard Gmail query filters (`from:(...) newer_than:1d`) with zero Google Cloud OAuth red tape, eliminating 7-day token expirations, consent screen redirects, and public domain verification requirements.
  - **OAuth 2.0 (Fallback)**: When `GMAIL_CREDENTIALS_JSON` and `GMAIL_TOKEN_JSON` are provided, ingestion falls back to the Google Cloud REST API (`build('gmail', 'v1', ...)`), using resilient parsing (`_parse_json_secret`) and automatic retries on transient errors (`502`, `429`).
- **Thread-Safe Gmail API Fetching**: For OAuth REST queries, message retrieval uses `asyncio.to_thread` protected by an `asyncio.Lock` to serialize calls on the shared, non-thread-safe `googleapiclient.discovery.Resource` instance (`service`). This prevents socket/SSL data races and C-level memory corruption (`Segmentation fault`) during batch message fetching, while keeping Phase 2 LLM advertisement cleaning fully concurrent via `asyncio.gather()`.
- **LLM De-Advertisement & Pure Ad Filtering**: Before storage, raw newsletter text passes through a concurrent `gemini-3.5-flash-lite` cleaning pass (`clean_newsletter_content`). It strips commercial sponsors, referral links, and unsubscribe boilerplate while preserving all market data verbatim. Pure marketing emails (`is_pure_ad = true`) and empty bodies are automatically discarded to prevent inserting zero-length snapshots into Supabase. Catastrophic over-stripping fallback protects newsletters against accidental truncation. See [[concepts/ad-stripping-audit]].
- **Daily Newsletter Generation**: A separate step (see [[entities/generated-newsletters]]) generates a digest newsletter using DeepSeek V4 Flash. It queries newsletters published within the last **12 hours** (based on the `date` column), not the `ingested_at` timestamp. This rolling window ensures overnight and early-morning editions are captured for the morning session.
- **Lookback Window**: The 12-hour window is measured from the current Eastern Time to the `date` field of each snapshot. The switch from `ingested_at` to `date` improved alignment with actual publication times.

## Economic Calendar & Macro Releases

The economic calendar pipeline incorporates two complementary mechanisms:
- **Semi-Weekly Forward Calendar Scraping (`apps/engine/ingest/calendar.py`)**: Runs via GitHub Actions (`.github/workflows/calendar.yml`) on Sunday and Wednesday at 00:00 UTC, scraping upcoming events from Trading Economics and saving high-importance future catalysts to Supabase `memories` (`memory_type = 'CALENDAR_EVENT'`).
- **Live Morning Economic Releases (`apps/engine/core/economic_releases.py`)**: Queries Financial Modeling Prep (`/stable/economic-calendar`) for real-time indicator prints released at 8:30 AM ET and throughout the trading session (CPI, PPI, Nonfarm Payrolls, Retail Sales, Unemployment, GDP). Computes consensus surprise deltas (`actual - estimate`) and partitions events into `RELEASED` vs `PENDING` with a 30-minute in-memory cache (`ttl = 1800s`). Injected directly into `daily_predictor.py` and `newsletter_generator.py`, and available as canonical agent tool `get_today_economic_releases`.
- **Target Date & Catalyst Storage**: Resolves event date and time deterministically in $O(1)$ from the source table, storing high-importance records in Supabase `memories` with `memory_type = 'CALENDAR_EVENT'`, `is_future_catalyst = true`, and `target_date = YYYY-MM-DD`.
- **Frontend Integration**: Displayed on the Today dashboard in the **Horizon Watch** timeline (`FutureCatalysts.tsx`) with dynamic Critical/High badges and chronological sequencing.

## Government Data

… (existing content)

## Related

- [[concepts/ad-stripping-audit]]
- [[entities/generated-newsletters]]
- [[entities/pipeline]]
- [[concepts/ingestion]]
