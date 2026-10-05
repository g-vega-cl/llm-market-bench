---
tags: [engine, news, intraday, jev, ingestion, catalysts]
category: entity
---

# Intraday News

The intraday news subsystem (`apps/engine/analysis/intraday_news.py`) aggregates live market-moving catalysts during the trading day, screens them through the TypeSafe Jev relevance sieve, persists the survivors, and exposes them to analysis agents via the `get_market_moving_news` tool. It is the real-time counterpart to the scheduled newsletter ingestion — capturing breaking macro prints, Fed remarks, and wire headlines as they happen.

## Event Aggregation

`fetch_raw_intraday_events()` pulls from three sources and normalizes them into a common event shape (`headline`, `summary`, `source`, `url`, `tickers`, `event_timestamp`, `source_id_hash`, `context`):

- **FMP Macro Calendar** — today's economic releases with `High`/`Medium` impact or `RELEASED` status, formatted with actual/estimate/previous/surprise values. Tagged with `SPY`, `QQQ`, `TLT`.
- **Alpaca Benzinga Wire** — real-time news via `NewsClient` (last 24h, requires `ALPACA_API_KEY`/`ALPACA_SECRET_KEY`).
- **Polygon Wire** — recent reference news via the Polygon `/v2/reference/news` endpoint (requires `MASSIVE_API_KEY`).

## Deduplication

Every event gets a deterministic SHA-256 `source_id_hash` derived from `headline|source|event_timestamp[:19]` (lowercased, stripped). `fetch_raw_intraday_events()` collapses duplicates within a batch, and `sync_intraday_market_news()` queries existing hashes in Supabase to skip already-stored items. The hash is the table's unique key, so upserts are idempotent.

## Jev Relevance Sieve

Each new candidate is evaluated by `evaluate_news_with_jev()` against the OpenRouter Decisions API (`https://openrouter.ai/api/alpha/decisions`) using the `JEV_MODEL`. The single `market_relevance` question classifies the headline as `MARKET_MOVING` or `NOISE` with a confidence score. See [[concepts/jev-news-sieve]] for the classification criteria and threshold logic.

Evaluation runs concurrently under an `asyncio.Semaphore(3)` and only the first 10 new candidates per sync are screened. Items classified `MARKET_MOVING` with confidence ≥ 70 are persisted to the `intraday_market_news` table (see [[entities/database]]).

## Sync & Caching

`sync_intraday_market_news(force=False)` is the entry point. It enforces a 15-minute freshness guard (`DEFAULT_SYNC_COOLDOWN_SECONDS = 900`): if the newest stored record is younger than the cooldown, it returns the cached rows without re-fetching. `force=True` bypasses the guard. If no `OPENROUTER_API_KEY` is configured, evaluation defaults to `NOISE` and nothing is stored.

## Agent Tool

`execute_get_market_moving_news_tool(limit=8, force_refresh=False)` formats the vetted records into a markdown briefing (timestamp in ET, impact choice + confidence, source, tickers, context). The limit is clamped to 1–20. It is registered as the `get_market_moving_news` tool in the canonical registry and dispatched through `TOOL_DISPATCH_TABLE`; the thin wrapper lives in `tools/news_memories.py`. See [[entities/tool-registry]].

## Pipeline Integration

`run_ingest()` in `apps/engine/pipeline/runner.py` calls `sync_intraday_market_news(force=False)` after dust cleanup and before the ingest/snapshot stage. Failures are logged as warnings and do not abort the pipeline. See [[entities/pipeline]].

## Related

- [[concepts/jev-news-sieve]]
- [[entities/intraday-news-wire]]
- [[entities/database]]
- [[entities/tool-registry]]
- [[entities/pipeline]]
- [[entities/economic-releases]]
