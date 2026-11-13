---
tags: [recipes, push-v2, trading, backtest, news-corpus, voxel, studio]
category: entity
---

# Recipe Studio

The **Recipe Studio** (`/recipes`) is a 5-block push-based multi-stage LLM strategy builder. Inspired by Unsloth Studio Data Recipes, it lets researchers compose ordered stages of prompts, point-in-time news filters, historical memories filters, technical criteria, and immutable trade-signal schemas, then backtest them over random 2-week point-in-time windows or schedule hourly live runs.

## Architecture

1. **Storage & Corpus (`supabase/migrations/20261112103000_create_recipe_studio_v2.sql`, `supabase/migrations/20261113112000_drop_recipe_intraday_bars.sql`)**:
   - `public.recipe_news_corpus`: Point-in-time news articles imported from `stock-news-scraper` shards and synced hourly from live market wires + `newsletter_snapshots`, tagged across canonical buckets with `search_tsv` and GIN indexes on `tickers`, `buckets`, and `search_tsv`.
   - `public.strategy_recipes`: Push v2 strategy configurations (`graph_json` with `version: "2.0-push"` and `stages`), cadence (`5m` or `1d`), concurrency limits, and isolated paper ledgers. Starter templates live in `packages/config/starter-recipes.json` and are seeded into `strategy_recipes`.
   - `public.recipe_execution_queue`: Priority queue for backtests (priority 10) and live turns (priority 1) with atomic dequeue RPC `pop_next_recipe_job()`.
   - `public.recipe_alerts_inbox`: In-app trade alert delivery table.
   - `public.recipe_waitlist_pledges`: Early supporter pledges for future dedicated GPU compute tiers.

2. **Engine Processing (`apps/engine/recipes/`)**:
   - `push_schema.py`: Pydantic models for Push v2 (`PushStrategy`, `StrategyStage`, `PromptBlock`, `NewsBlock`, `MemoriesBlock`, `TechnicalsBlock`, `OutputFormatBlock`).
   - `push_hydrator.py`: Point-in-time filtering and stage prompt hydration (`fetch_push_context_batch`, `hydrate_stage_prompt`, `build_news_excerpt`).
   - `push_runner.py`: Sequential stage execution (`run_push_live`) and random 10-trading-day point-in-time backtesting (`run_push_backtest`) backed by `public.price_history` and `STRATA_BASE_URL` / `FREE_LLM_PROXY_URL` (`https://llm.clvg.uk/v1`).
   - `worker.py`: `process_next_recipe_job()` / `async_process_next_recipe_job()` returning a `JobOutcome` (`"EMPTY"`, `"COMPLETED"`, `"FAILED"`) — pops one Push v2 job from `recipe_execution_queue`, rejects legacy/unsupported payloads, executes `run_push_live` or `run_push_backtest`, and deposits `live_turn` signals into `recipe_alerts_inbox`.
   - `runner.py`: MiniPC daemon (`python3 -m recipes.runner --loop`) running hourly `sync_live_news_to_corpus()` + `enqueue_live_recipes()` and polling the priority queue every 5s via `async_process_next_recipe_job` / `_drain_sync_queue`.
   - `news_corpus.py` & `import_news_cli.py`: Bucket derivation (`derive_article_buckets`), JSONL shard importer, and `sync_live_news_to_corpus()` reusing `analysis/intraday_news_aggregator.py` + `newsletter_snapshots`.

3. **Presentation & Studio UI (`apps/web/src/features/recipes/`)**:
   - Built with Cheddar Boxel (Voxel) tokens (`bg-boxel-canvas`, `bg-boxel-surface`, 0px corners, 2px directional bevels, recessed `.voxel-trough` slots).
   - `StageBuilder.tsx`, `BlockEditors.tsx`, `ToolPicker.tsx`, `PromptVisualizer.tsx`, `RecipeBacktestResults.tsx`, `RecipeAlertsInbox.tsx`, `WaitlistPledgeModal.tsx`, `starter-templates.ts` (consuming `packages/config/starter-recipes.json`), and `api/recipes-api.ts`.

## 5-Block Push-Based Model (`version: "2.0-push"`)

- **Multi-Stage Sequential Chaining**: A strategy contains 1 or more ordered `StrategyStage` items (`Stage 1..N`), where Stage $N$'s output is passed into Stage $N+1$ via `{{prev_output}}`.
- **5 Push Blocks**:
  - `output_format`: Immutable output-format contract locked to `[{"action": "BUY"|"SELL", "ticker": "..."}]`. Rendered **last** in the assembled stage prompt regardless of its block order.
  - `prompt`: Free-text prompt instructions.
  - `news`: Keyword `contains` + `recency_hours` filter over `recipe_news_corpus`. Each hit renders its headline plus a ~300-char body excerpt (`build_news_excerpt` in `apps/engine/recipes/push_hydrator.py`, mirrored in `apps/web/src/features/recipes/news-excerpt.ts`, asserted against `packages/config/news-excerpt-cases.json`).
  - `memories`: Keyword `contains` + `recency_hours` + `category` (`memory_type`) + `min_importance` filter over `memories` (explicitly projecting columns without `embedding` vectors).
  - `technicals`: Company rules (`P/E`, `FCF`, `VWAP`, `RSI`, `MACD`, `price_52w_pct`, etc.) serialized as prompt criteria.

## Hourly Runner Daemon (`apps/engine/recipes/runner.py`)

`recipes.runner` is the MiniPC-hosted scheduler and queue worker that keeps the corpus fresh and drains the execution queue. It is deployed as the `recipe-worker` container in `docker/archive/docker-compose.secondary.yml` (see [[entities/secondary-minipc-edge]]).

### Cycle Functions

- **`seed_starter_recipes(sb_client)`** — loads `packages/config/starter-recipes.json` and idempotently inserts any template whose `name` is not already present among `is_template = true` rows. Seeded rows carry `user_id = ANONYMOUS_USER_ID` (`00000000-0000-0000-0000-000000000000`), `is_public = true`, `is_template = true`, `is_live = false`, and the default concurrency config (`max_open_trades: 3`, `max_equity_pct_per_trade: 33.3`). Returns the number inserted.
- **`enqueue_live_recipes(sb_client)`** — selects every `is_live = true` recipe and inserts a `live_turn` job (priority `1`, provider `auto-strata`, model `strata`) for each one that does not already have a `pending`/`processing` queue row. Returns the number enqueued.
- **`run_hourly_cycle(sb_client, as_of_utc=None, max_jobs=25)`** — runs `sync_live_news_to_corpus()`, then `enqueue_live_recipes()`, then drains up to `max_jobs` queue jobs via `process_next_recipe_job()`. Returns `{news_synced, live_enqueued, jobs_processed}`.
- **`_run_daemon_loop(sb_client)`** — seeds templates once, then runs `run_hourly_cycle` every `HOURLY_INTERVAL_SECONDS` (3600s) and otherwise polls the queue every `POLL_INTERVAL_SECONDS` (5s), draining up to `MAX_JOBS_PER_CYCLE` (25) jobs per pass. Cycle failures are logged via `logger.exception` and never terminate the loop.

### CLI

```sh
# Continuous daemon (hourly sync + 5s queue polling)
python3 -m recipes.runner --loop

# One hourly sync + enqueue + queue drain
python3 -m recipes.runner --once

# Seed starter templates only
python3 -m recipes.runner --seed-only

# Sync live news into recipe_news_corpus only
python3 -m recipes.runner --sync-news-only
```

Running with no flags seeds templates and executes a single `run_hourly_cycle`.

## Live News Sync (`sync_live_news_to_corpus`)

`apps/engine/recipes/news_corpus.py` exposes `sync_live_news_to_corpus(sb_client, as_of_utc=None, symbols="SPY,QQQ,NVDA,AMD,AAPL,MSFT,AMZN,META,GOOGL,TSLA", lookback_hours=48, batch_size=50)`, which keeps `recipe_news_corpus` current with the live tape:

1. **Market wire ingestion** — calls `aggregate_intraday_news()` (Alpaca Benzinga wire, Polygon reference news, FMP stable stock news) with `limit_per_source=25`. Each item is normalized through `parse_and_normalize_article()` using its `source_id_hash` as `article_id`, `source_family = "market_wire"`, and `date_precision = "wire_timestamp"`.
2. **Newsletter snapshots** — queries `newsletter_snapshots` for rows newer than `as_of_utc - lookback_hours` (max 50) and normalizes each as `article_id = "nl_<source_id>"`, `source_family = "newsletter"`, `date_precision = "newsletter_date"`.
3. **Idempotent upsert** — batches records (`batch_size`, default 50) into `recipe_news_corpus` with `on_conflict="article_id"`.

Both source fetches are individually wrapped in `try/except` with `logger.exception`, so a single upstream outage still persists whatever succeeded. Returns `{"fetched": N, "inserted": M}`.

## Point-in-Time Backtesting (`run_push_backtest`)

`run_push_backtest(strategy, sb_client, llm_caller=None, rng=None, slippage_bps=5.0)` simulates a random contiguous 10-trading-day window with zero forward leakage:

1. **Trading calendar** — `_load_window_dates(sb_client)` reads the most recent 120 `price_history` rows for `SPY` and derives the distinct trading dates; when the table is empty or the query fails it falls back to the last 20 weekdays.
2. **Window selection** — `pick_random_two_week_window()` picks a seeded random contiguous slice of up to 10 trading days.
3. **Point-in-time hydration** — `fetch_push_context_batch()` gathers news and memories bounded by each simulated day's cutoff (lookback extended by 20 days for the news window).
4. **Signal generation** — every stage is executed per day and `parse_trade_signals()` extracts `{action, ticker}` picks; the union of traded tickers is collected.
5. **Pricing** — `_load_daily_closes(sb_client, tickers, start_day, end_day)` batch-fetches `price_history` rows (`ticker, fetched_at, close, price`) for exactly those tickers, preferring `close` and falling back to `price`.
6. **Accounting** — trades are closed against the next day's close with `slippage_bps` friction, producing the dual Midpoint / Net P&L result payload.

Because pricing is resolved after all signals are known, the backtest issues exactly one batched price query per run instead of per-day lookups.

## Legacy DAG Removal

The former `RecipeGraph` DAG pipeline (`schema.py`, `validator.py`, `indicators.py`, `backtester.py`, `backtest_models.py`) and its `recipe_intraday_bars` 5-minute candle cache have been removed. `process_next_recipe_job()` now rejects any `graph_json` that lacks a `stages` list with `ValueError("Recipe must use Push v2 format with a 'stages' list (legacy DAG format is removed).")`, marking the queue row `failed` with that message in `error_message`.

## Related Pages

- [[entities/database]] — `recipe_*` / `strategy_recipes` tables, `price_history`, and `pop_next_recipe_job()`
- [[entities/secondary-minipc-edge]] — hosts the `recipe-worker` container in `docker/archive/docker-compose.secondary.yml`
- [[entities/free-llm-proxy]]
- [[entities/design-system]]
- [[concepts/zero-frontend-compute]]
- [[concepts/zero-lookahead-materialization]]
