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

## Multi-Source Aggregator (`intraday_news_aggregator.py`)

`apps/engine/analysis/intraday_news_aggregator.py` provides the shared aggregation primitives used by both the scheduled ingest path and the continuous edge daemon:

- **`generate_source_id_hash(headline, source, event_timestamp)`** — deterministic SHA-256 hash of `headline|source|event_timestamp[:19]` (lowercased, stripped). Every provider attaches this hash to each item so downstream upserts are idempotent.
- **`normalize_headline(headline)`** — lowercases, strips punctuation, drops stopwords and tokens of length ≤ 2.
- **`deduplicate_news(items, similarity_threshold=0.5)`** — drops any article whose Jaccard word overlap with an already-seen headline is ≥ the threshold.
- **`fetch_alpaca_news(alpaca_news_client=None, limit=10, symbols="SPY", api_key=None, secret_key=None)`** — fetches the Alpaca Benzinga wire. When no client is passed (or it lacks `get_news`), it lazily constructs a `NewsClient` from the supplied keys or the ambient `ALPACA_API_KEY`/`ALPACA_SECRET_KEY`. Each article carries `url`, `tickers` (from `item.symbols`), and `source_id_hash`.
- **`fetch_polygon_news(http_client, api_key, limit)`** — Polygon reference news; each article carries `url` (`article_url`), `tickers`, and `source_id_hash`.
- **`fetch_fmp_news(http_client, api_key, symbols, limit)`** — FMP stable stock news; normalizes `publishedDate` (space-separated → ISO `T…Z`), and attaches `url`, `tickers` (parsed from `symbols`), and `source_id_hash`.
- **`aggregate_intraday_news(..., alpaca_api_key="", alpaca_secret_key="", ...)`** — fans the three providers out with `asyncio.gather(..., return_exceptions=True)`, keeps only list results, deduplicates, and backfills `source_id_hash` on any item missing one. Each provider fails soft on missing keys, non-200 responses, or exceptions.

## Deduplication

Every event gets a deterministic SHA-256 `source_id_hash` derived from `headline|source|event_timestamp[:19]` (lowercased, stripped). `fetch_raw_intraday_events()` collapses duplicates within a batch, and `sync_intraday_market_news()` queries existing hashes in Supabase to skip already-stored items. The hash is the table's unique key, so upserts are idempotent.

## Jev Relevance Sieve

Each new candidate is evaluated by `evaluate_news_with_jev()` against the OpenRouter Decisions API (`https://openrouter.ai/api/alpha/decisions`) using the `JEV_MODEL`. The single `market_relevance` question classifies the headline as `MARKET_MOVING` or `NOISE` with a confidence score. See [[concepts/jev-news-sieve]] for the classification criteria and threshold logic.

Evaluation runs concurrently under an `asyncio.Semaphore(3)` and only the first 10 new candidates per sync are screened. Items classified `MARKET_MOVING` with confidence ≥ 70 are persisted to the `intraday_market_news` table (see [[entities/database]]).

## Sync & Caching

`sync_intraday_market_news(force=False)` is the entry point. It enforces a 15-minute freshness guard (`DEFAULT_SYNC_COOLDOWN_SECONDS = 900`): if the newest stored record is younger than the cooldown, it returns the cached rows without re-fetching. `force=True` bypasses the guard. If no `OPENROUTER_API_KEY` is configured, evaluation defaults to `NOISE` and nothing is stored.

## Agent Tool

`execute_get_market_moving_news_tool(limit=8, force_refresh=False)` formats the vetted records into a markdown briefing (timestamp in ET, impact choice + confidence, source, tickers, context). The limit is clamped to 1–20. It is registered as the `get_market_moving_news` tool in the canonical registry and dispatched through `TOOL_DISPATCH_TABLE`; the thin wrapper lives in `tools/news_memories.py`. See [[entities/tool-registry]].

## Pipeline Integration & Continuous Edge Ingestion

- **Scheduled Ingest Runs**: `run_ingest()` in `apps/engine/pipeline/runner.py` calls `sync_intraday_market_news(force=False)` after dust cleanup and before the ingest/snapshot stage. Failures are logged as warnings and do not abort the pipeline. See [[entities/pipeline]].
- **Continuous 5-Minute Edge Ingestion**: The 24/7 `live-spy-trader` daemon calls `aggregate_intraday_news()` every 5 minutes across Alpaca Benzinga wire, Polygon reference news, and FMP stable stock news. Deduplicated items are persisted to `intraday_market_news` with `source_id_hash` conflict guards via `persist_intraday_news()` (see [[entities/live-agent-trader]]).
- **30-Minute AI News Synthesis**: `run_news_synthesis_worker_loop()` in `apps/engine/trading/runner.py` periodically gathers recent breaking news and prompts the local Strata / free proxy cascade (`query_multi_tier_llm`) to generate a 2-3 sentence institutional market summary, saving it into `market_feeling.news_summary` to feed the Today page briefing.

## Related

- [[concepts/jev-news-sieve]]
- [[entities/intraday-news-wire]]
- [[entities/live-agent-trader]]
- [[entities/database]]
- [[entities/tool-registry]]
- [[entities/pipeline]]
- [[entities/economic-releases]]
