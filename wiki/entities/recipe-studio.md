---
tags: [recipes, push-v2, trading, backtest, news-corpus, voxel, studio]
category: entity
---

# Recipe Studio

The **Recipe Studio** (`/recipes`) is a 5-block push-based strategy builder where each strategy makes one LLM call. Inspired by Unsloth Studio Data Recipes, it lets researchers compose prompts, point-in-time news filters, historical memories filters, technical criteria, and immutable trade-signal schemas into that call, then backtest them over random 2-week point-in-time windows or schedule hourly live runs.

## Architecture

1. **Storage & Corpus (`supabase/migrations/20261112103000_create_recipe_studio_v2.sql`, `supabase/migrations/20261113112000_drop_recipe_intraday_bars.sql`)**:
   - `public.recipe_news_corpus`: Point-in-time news articles imported from `stock-news-scraper` shards and synced hourly from live market wires + `newsletter_snapshots`, tagged across canonical buckets with `search_tsv` and GIN indexes on `tickers`, `buckets`, and `search_tsv`.
   - `public.strategy_recipes`: Push v2 strategy configurations (`graph_json` with `version: "2.0-push"` and a one-item `stages` list), cadence (`5m` or `1d`), concurrency limits, and isolated paper ledgers. Starter templates live in `packages/config/starter-recipes.json` and are seeded into `strategy_recipes`.
   - `public.recipe_execution_queue`: Priority queue for backtests (priority 10) and live turns (priority 1) with atomic dequeue RPC `pop_next_recipe_job()`.
   - `public.recipe_alerts_inbox`: In-app trade alert delivery table.
   - `public.recipe_waitlist_pledges`: Early supporter pledges for future dedicated GPU compute tiers.

2. **Engine Processing (`apps/engine/recipes/`)**:
   - `push_schema.py`: Pydantic models for Push v2 (`PushStrategy`, `StrategyStage`, `PromptBlock`, `NewsBlock`, `MemoriesBlock`, `TechnicalsBlock`, `OutputFormatBlock`). `PushStrategy` rejects more than one stage.
   - `push_hydrator.py`: Point-in-time filtering and stage prompt hydration (`fetch_push_context_batch`, `hydrate_stage_prompt`, `build_news_excerpt`).
   - `push_runner.py`: Single-call execution (`run_push_live`) and random 10-trading-day point-in-time backtesting (`run_push_backtest`) backed by `public.price_history` and `STRATA_BASE_URL` / `FREE_LLM_PROXY_URL` (`https://llm.clvg.uk/v1`). The LLM call goes through a local-first endpoint failover chain (see below).
   - `worker.py`: `async_process_next_recipe_job()` (canonical) and the sync wrapper `process_next_recipe_job()` returning a `JobOutcome` (`"EMPTY"`, `"COMPLETED"`, `"FAILED"`) — pops one Push v2 job from `recipe_execution_queue`, rejects legacy/unsupported payloads and unsupported execution modes, executes `run_push_live` or `run_push_backtest`, and deposits `live_turn` signals into `recipe_alerts_inbox`.
   - `runner.py`: MiniPC daemon (`python3 -m recipes.runner --loop`) running hourly `sync_live_news_to_corpus()` + `enqueue_live_recipes()` and polling the priority queue every 5s via `async_process_next_recipe_job` / `_drain_sync_queue`.
   - `news_corpus.py` & `import_news_cli.py`: Bucket derivation (`derive_article_buckets`), JSONL shard importer, and `sync_live_news_to_corpus()` reusing `analysis/intraday_news_aggregator.py` + `newsletter_snapshots`.

3. **Presentation & Studio UI (`apps/web/src/features/recipes/`)**:
   - Built with Cheddar Boxel (Voxel) tokens (`bg-boxel-canvas`, `bg-boxel-surface`, 0px corners, 2px directional bevels, recessed `.voxel-trough` slots).
   - `StageBuilder.tsx`, `BlockEditors.tsx`, `ToolPicker.tsx`, `PromptVisualizer.tsx`, `RecipeBacktestResults.tsx`, `RecipeAlertsInbox.tsx`, `WaitlistPledgeModal.tsx`, `starter-templates.ts` (consuming `packages/config/starter-recipes.json`), and `api/recipes-api.ts`.

## 5-Block Push-Based Model (`version: "2.0-push"`)

- **Single LLM Call (MVP)**: A strategy contains exactly one `StrategyStage`, which is one LLM call. The `stages` list shape stays so multi-stage chaining via `{{prev_output}}` can return later. See the Single LLM Call Limit section below.
- **5 Push Blocks**:
  - `output_format`: Immutable output-format contract locked to `[{"action": "BUY"|"SELL", "ticker": "..."}]`. Rendered **last** in the assembled stage prompt regardless of its block order.
  - `prompt`: Free-text prompt instructions.
  - `news`: Keyword `contains` + `recency_hours` filter over `recipe_news_corpus`. Each hit renders its headline plus a ~300-char body excerpt (`build_news_excerpt` in `apps/engine/recipes/push_hydrator.py`, mirrored in `apps/web/src/features/recipes/news-excerpt.ts`, asserted against `packages/config/news-excerpt-cases.json`).
  - `memories`: Keyword `contains` + `recency_hours` + `category` (`memory_type`) + `min_importance` filter over `memories` (explicitly projecting columns without `embedding` vectors).
  - `technicals`: Company rules (`P/E`, `FCF`, `VWAP`, `RSI`, `MACD`, `price_52w_pct`, etc.) serialized as prompt criteria.

## Hourly Runner Daemon (`apps/engine/recipes/runner.py`)

`recipes.runner` is the MiniPC-hosted scheduler and queue worker that keeps the corpus fresh and drains the execution queue. It is deployed as the `recipe-worker` container in `docker/archive/docker-compose.secondary.yml` (512M memory limit, see [[entities/secondary-minipc-edge]]).

### Cycle Functions

- **`seed_starter_recipes(sb_client)`** — loads `packages/config/starter-recipes.json` and idempotently inserts any template whose `name` is not already present among `is_template = true` rows (`.limit(100)` capped existence check). Seeded rows carry `user_id = ANONYMOUS_USER_ID` (`00000000-0000-0000-0000-000000000000`), `is_public = true`, `is_template = true`, `is_live = false`, and the default concurrency config (`max_open_trades: 3`, `max_equity_pct_per_trade: 33.3`). Returns the number inserted. A seeding failure is logged via `logger.exception` and never prevents the cycle from running.
- **`enqueue_live_recipes(sb_client)`** — selects every `is_live = true` recipe (`.limit(500)`, selecting `id, user_id, name, graph_json`), skips any that already have a `pending`/`processing` queue row (`.limit(1000)` open-job scan), and validates each candidate through `_is_single_stage_push_v2_graph()`: a recipe whose `graph_json` is not a dict carrying a `stages` list of exactly one item (legacy DAG `nodes`/`edges` payloads, or any multi-stage strategy) is skipped with a `logger.warning` and never queued. All surviving jobs are inserted in a **single batched `.insert([...])`** rather than one round-trip per recipe. Returns the number enqueued.
- **`run_hourly_cycle(sb_client, as_of_utc=None, max_jobs=25)`** — runs `sync_live_news_to_corpus()`, then `enqueue_live_recipes()`, then drains up to `max_jobs` queue jobs via `await async_process_next_recipe_job(sb_client)`. Draining stops only on `"EMPTY"`; `"FAILED"` outcomes increment `jobs_failed` and the loop continues, so one poisoned job can never starve the rest of the queue. Returns `{news_synced, live_enqueued, jobs_processed, jobs_failed}`.
- **`_drain_sync_queue(sb_client, max_jobs=MAX_JOBS_PER_CYCLE)`** — the off-hour drain path used by the daemon loop; calls the synchronous `process_next_recipe_job()` until `"EMPTY"` or the job budget is exhausted.
- **`_run_daemon_loop(sb_client)`** — seeds templates once inside a `try/except` (startup seeding failure is logged and the loop still starts), then runs `run_hourly_cycle` every `HOURLY_INTERVAL_SECONDS` (3600s) and otherwise polls the queue every `POLL_INTERVAL_SECONDS` (5s) through `_drain_sync_queue`, draining up to `MAX_JOBS_PER_CYCLE` (25) jobs per pass. Cycle failures are logged via `logger.exception` and never terminate the loop.

### CLI

```sh
# Continuous daemon (hourly sync + 5s queue polling)
python3 -m recipes.runner --loop

# One hourly sync + enqueue + queue drain (default action)
python3 -m recipes.runner --once

# Seed starter templates only
python3 -m recipes.runner --seed-only

# Sync live news into recipe_news_corpus only
python3 -m recipes.runner --sync-news-only
```

Running with no flags behaves like `--once`: it seeds templates (failing soft) and executes a single `run_hourly_cycle`.

## Live News Sync (`sync_live_news_to_corpus`)

`apps/engine/recipes/news_corpus.py` exposes `sync_live_news_to_corpus(sb_client, as_of_utc=None, symbols="SPY,QQQ,NVDA,AMD,AAPL,MSFT,AMZN,META,GOOGL,TSLA", lookback_hours=48, batch_size=50)`, which keeps `recipe_news_corpus` current with the live tape. It is composed of two independently fail-soft collectors, `_collect_wire_records()` and `_collect_newsletter_records()`:

1. **Market wire ingestion (`_collect_wire_records`)** — calls `aggregate_intraday_news()` (Alpaca Benzinga wire, Polygon reference news, FMP stable stock news) with `limit_per_source=25`. Each item is normalized through `parse_and_normalize_article()` using its `source_id_hash` as `article_id`, `source_family = "market_wire"`, and `date_precision = "wire_timestamp"`.
2. **Newsletter snapshots (`_collect_newsletter_records`)** — queries `newsletter_snapshots` for rows newer than `as_of_utc - lookback_hours` (max 50) and normalizes each as `article_id = "nl_<clean_source_id>_<YYYY-MM-DD>"`, `source_family = "newsletter"`, `date_precision = "newsletter_date"`. Any pre-existing `nl_` prefix on the snapshot `source_id` is stripped (`removeprefix("nl_")`) before composing the id and the archive URL (`https://benchify.app/newsletters/<clean_source_id>`), so a snapshot that was itself generated from the corpus cannot accumulate repeated `nl_nl_…` prefixes. The publication day is appended to the article id, making each newsletter-day pair a distinct corpus row (the same newsletter re-observed on a later sync of a later day is a new, correctly dated article) while keeping the upsert idempotent for repeats within a day.
3. **Idempotent upsert** — batches records (`batch_size`, default 50) into `recipe_news_corpus` with `on_conflict="article_id"`.

Both source fetches are individually wrapped in `try/except` with `logger.exception`, so a single upstream outage still persists whatever succeeded. Returns `{"fetched": N, "inserted": M}`.

## Point-in-Time Backtesting (`run_push_backtest`)

`run_push_backtest(strategy, sb_client, llm_caller=None, rng=None, slippage_bps=5.0)` simulates a random contiguous 10-trading-day window with zero forward leakage:

1. **Trading calendar** — `_load_window_dates(sb_client)` reads the most recent 1,000 `price_history` rows for `SPY` (`.limit(1000)`) and derives the distinct trading dates; when the table is empty or the query fails it falls back to the last 20 weekdays.
2. **Window selection** — `pick_random_two_week_window()` picks a seeded random contiguous slice of up to 10 trading days.
3. **Point-in-time hydration** — `fetch_push_context_batch()` gathers news and memories bounded by each simulated day's cutoff (lookback extended by 20 days for the news window).
4. **Signal generation** — the single LLM call runs once per day and `parse_trade_signals()` extracts `{action, ticker}` picks; the union of traded tickers is collected.
5. **Pricing** — `_load_daily_closes(sb_client, tickers, start_day, end_day)` batch-fetches `price_history` rows (`ticker, fetched_at, close, price`) for exactly those tickers with `.limit(10000)` (raised from 5,000 so wide multi-ticker windows are never truncated), preferring `close` and falling back to `price`.
6. **Accounting** — trades are closed against the next day's close with `slippage_bps` friction, producing the dual Midpoint / Net P&L result payload (`midpoint` / `net` returns, `win_rate_pct`, `llm_calls_made`, `trades`, `skipped_trades`, `equity_curve`). The payload no longer carries a `weeks_breakdown` key — the random-window backtest reports a flat trade list and equity curve only.

Because pricing is resolved after all signals are known, the backtest issues exactly one batched price query per run instead of per-day lookups.

## LLM Endpoint Failover (`_llm_endpoints` / `_run_tool_loop`)

Every LLM call in `push_runner.py` is executed through a small, ordered endpoint chain rather than a single hardcoded base URL:

- **`_llm_endpoints(openrouter_key, model)`** builds the chain:
  - With an explicit `openrouter_key`, a single OpenRouter endpoint (`https://openrouter.ai/api/v1`) is used, and `model == "auto-strata"` is remapped to `deepseek/deepseek-chat`.
  - Otherwise the chain is local-first: `STRATA_BASE_URL` (if set) followed by `FREE_LLM_PROXY_URL` (default `https://llm.clvg.uk/v1`) when it differs from the Strata URL, both authenticated with `FREE_PROXY_MASTER_KEY` (falling back to `STRATA_API_KEY`, then `local`). If neither resolves, the centralized CLVG proxy is the sole endpoint.
- **`_run_tool_loop(client, model_id, prompt, tool_schemas, cutoff_date)`** holds the OpenAI-compatible tool-calling loop (system prompt with immutable output contract, canonical tool schemas, cutoff-date enforcement) and is unchanged in behavior.
- **`default_llm_caller(...)`** iterates the chain: a failing endpoint logs `Recipe LLM endpoint <url> failed (<exc>); failing over to next endpoint` and the next endpoint is attempted; if every endpoint fails the final exception is re-raised so the queue job is marked `failed` with the real error.

## Worker Modes, Outcomes & Event-Loop Safety (`apps/engine/recipes/worker.py`)

- **`JobOutcome = Literal["EMPTY", "COMPLETED", "FAILED"]`** — the tri-state return distinguishes "queue was empty" from "job ran" and "job errored". Callers drain until `"EMPTY"` and count `"FAILED"` separately (`run_hourly_cycle` reports `jobs_processed` vs `jobs_failed`).
- **`SUPPORTED_JOB_MODES = ("backtest", "preview", "live_turn")`** — the popped `job_mode` is validated immediately after dequeue; an unrecognized mode raises `ValueError("Unsupported recipe execution mode: <mode>")`, which is caught, persisted to `recipe_execution_queue.error_message` on the `failed` row, and returned as `"FAILED"`. A missing `job_mode` defaults to `backtest`.
- **No nested event loop** — `async_process_next_recipe_job()` `await`s `run_push_live()` / `run_push_backtest()` directly, so it is safe to call from an already-running loop (e.g. inside `async run_hourly_cycle`). The legacy `asyncio.run(...)` nesting that raised `RuntimeError: asyncio.run() cannot be called from a running event loop` is confined to the synchronous wrapper `process_next_recipe_job()`.
- **`process_next_recipe_job(client=None)`** — thin synchronous wrapper (`return asyncio.run(async_process_next_recipe_job(client))`) preserved for non-async callers and the off-hour daemon drain path.
- Successful jobs still write `output_json`, `status = 'completed'`, increment `strategy_recipes.trial_count`, and deposit `live_turn` signals into `recipe_alerts_inbox`.

## Legacy DAG Removal

The former `RecipeGraph` DAG pipeline (`schema.py`, `validator.py`, `indicators.py`, `backtester.py`, `backtest_models.py`) and its `recipe_intraday_bars` 5-minute candle cache have been removed. `async_process_next_recipe_job()` rejects any `graph_json` that lacks a `stages` list with `ValueError("Recipe must use Push v2 format with a 'stages' list (legacy DAG format is removed).")`, marking the queue row `failed` with that message in `error_message`. `enqueue_live_recipes()` applies the same Push v2 shape check, plus the one-stage limit, before a live recipe may enter the queue.

## Single LLM Call Limit (MVP)

Each strategy makes one LLM call per live run or per backtest day. Multi-stage chaining is off for the MVP. The limit is enforced in four places, so a stale client or an old queued row cannot bypass it.

- The Studio UI (`apps/web/src/features/recipes/pages/RecipeStudioPage.tsx`) shows one `LLM Call` card with no add or remove stage controls. The starter templates are single-stage (`packages/config/starter-recipes.json`).
- The save API (`apps/web/src/features/recipes/api/recipes-api.ts`) calls `assertSingleLlmStage()` inside `saveRecipeFn` and throws `Invalid strategy: must contain exactly one LLM stage`.
- The scheduler (`apps/engine/recipes/runner.py`) uses `_is_single_stage_push_v2_graph()` in `enqueue_live_recipes()`. A multi-stage live recipe is skipped with a `logger.warning`, so no queue row is written.
- The engine schema (`apps/engine/recipes/push_schema.py`) runs the `PushStrategy` validator `validate_single_llm_stage`, which raises `Push strategies are limited to one LLM stage for the MVP`. The worker stores that message in `recipe_execution_queue.error_message` and returns `FAILED`.

Existing data stays in place. The seeder only inserts missing template names, so the former `2-Stage Research -> Trade Decision` row remains in `strategy_recipes`. No UI path reads DB templates (`fetchPublicRecipes` has no callers), and a multi-stage row that runs fails with the validator message. The `stages` list shape and the `{{prev_output}}` hydrator path are kept inert. To bring multi-stage back, relax the validator and the three checks above, then restore the stage controls in the UI.

## Related Pages

- [[entities/database]] — `recipe_*` / `strategy_recipes` tables, `price_history`, and `pop_next_recipe_job()`
- [[entities/secondary-minipc-edge]] — hosts the `recipe-worker` container in `docker/archive/docker-compose.secondary.yml`
- [[entities/free-llm-proxy]]
- [[entities/design-system]]
- [[concepts/zero-frontend-compute]]
- [[concepts/zero-lookahead-materialization]]
