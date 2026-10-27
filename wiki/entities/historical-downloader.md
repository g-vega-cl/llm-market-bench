---
tags: [autoresearch, data-ingestion, historical-data, rate-limiting, sqlite]
category: entity
---

# Historical Downloader

`apps/engine/local_autoresearch/historical_downloader.py` bulk-fetches multi-year historical market data into a local raw SQLite vault (`.historical_raw.db`), so local autoresearch iterations can run entirely offline with no live network calls or rate limits. It is the raw-data counterpart to the Supabase-backed cache path in [[entities/local-autoresearch]].

## Data Sources

| Source | Content | Notes |
| :--- | :--- | :--- |
| FMP | Daily EOD bars | SPY plus 8 macro proxies (`QQQ`, `DIA`, `IWM`, `TLT`, `IEF`, `GLD`, `USO`, `UUP`) |
| Polygon | 5-minute bars | Pre-market tape for `SPY`, `QQQ`, `IWM`, `TLT`; fetched in monthly chunks to avoid result-set truncation |
| Polygon | Reference news | Point-in-time news via `published_utc.gte/lte` |
| Gmail (IMAP SSL) | Financial newsletters | Uses `NEWSLETTER_SENDERS`, `extract_email_message_body`, `clean_text` from `ingest.newsletter` |
| FRED | Macro series | `DGS10`, `DGS2`, `T10Y2Y`, `FEDFUNDS`, `UNRATE`, `ICSA` via `fredgraph.csv` |

## Rate Limiting

`TokenBucketLimiter` is a synchronous token-bucket limiter used to pace external APIs:

- Polygon: 1 request / 12.5s (~4.8 req/min) with 65s backoff and up to 3 retries on `429` responses.
- FMP: 1 request / 2.0s.

Polygon bar downloads are idempotent per month — a month with more than 100 already-cached bars is skipped.

## Raw Vault Schema

`init_raw_db` creates the following SQLite tables (with supporting indexes):

- `eod_bars` — daily OHLCV + VWAP, keyed by `(ticker, date)`
- `premarket_bars` — 5-minute intraday bars keyed by `(ticker, bar_time_utc)`
- `raw_newsletters` — cleaned Gmail newsletters, keyed by `source_id`
- `market_news` — Polygon reference news, keyed by `id`
- `macro_series` — FRED observations keyed by `(series_id, date)`

## Postgres Sync

`sync_to_local_postgres` mirrors the raw tables into the local Docker PostgreSQL container `market-bench-archive-db` (`market_bench_archive` database) under `historical_*` tables, batching inserts of 500 rows via `docker exec ... psql`.

## CLI

The module is runnable standalone:

```sh
PYTHONPATH=apps/engine ./apps/engine/.venv/bin/python3 -m local_autoresearch.historical_downloader \
  --start-date 2024-10-01 --end-date 2026-10-10 --include-news --include-newsletters --sync-postgres
```

The same flow is also reachable through the runner via `--download-raw`.

## Related

- [[entities/local-autoresearch]] — orchestrates the research loop that consumes this vault
- [[concepts/zero-lookahead-materialization]] — how raw rows become point-in-time features
- [[concepts/regime-vault]] — held-out out-of-distribution evaluation built on this data
