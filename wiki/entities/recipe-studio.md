---
tags: [recipes, push-v2, trading, backtest, news-corpus, voxel, studio]
category: entity
---

# Recipe Studio

The **Recipe Studio** (`/recipes`) is a 5-block push-based strategy builder where each strategy makes one LLM call. Inspired by Unsloth Studio Data Recipes, it lets researchers compose prompts, point-in-time news filters, historical memories filters, technical criteria, and immutable trade-signal schemas into that call, then backtest them over random 2-week point-in-time windows or schedule hourly live runs.

## Architecture

1. **Storage & Corpus (`supabase/migrations/20261112103000_create_recipe_studio_v2.sql`, `supabase/migrations/20261114000000_create_recipe_intraday_bars.sql`)**:
   - `public.recipe_news_corpus`: Point-in-time news articles imported from `stock-news-scraper` shards and synced from live market wires + `newsletter_snapshots`, tagged across canonical buckets with `search_tsv` and GIN indexes on `tickers`, `buckets`, and `search_tsv`.
   - `public.strategy_recipes`: Push v2 strategy configurations (`graph_json` with `version: "2.0-push"` and a one-item `stages` list), cadence (`5m`, `3h`, or `1d`, defaulting to `3h` for 3x/day ET runs at `09:30`, `12:30`, `15:30`), concurrency limits (`max_open_trades: 4`, `max_equity_pct_per_trade: 25.0`), and isolated paper ledgers (`paper_cash`, `paper_positions`, `paper_trades`, `paper_equity_curve`). Starter templates live in `packages/config/starter-recipes.json` and are seeded into `strategy_recipes`.
   - `public.recipe_intraday_bars`: Cached intraday bars (`(ticker, bar_time_utc)` PK) populated from `FMPProvider.get_hourly_history`, Alpaca IEX hourly bars, and live slot snapshots (`snapshot_live_intraday_bars`).
   - `public.recipe_execution_queue`: Priority queue for backtests (priority 10) and live turns (priority 1) with atomic dequeue RPC `pop_next_recipe_job()`.
   - `public.recipe_alerts_inbox`: In-app trade alert delivery table.
   - `public.recipe_waitlist_pledges`: Early supporter pledges for future dedicated GPU compute tiers.

2. **Engine Processing (`apps/engine/recipes/`)**:
   - `push_schema.py`: Pydantic models for Push v2 (`PushStrategy`, `StrategyStage`, `PromptBlock`, `NewsBlock`, `MemoriesBlock`, `TechnicalsBlock`, `OutputFormatBlock`). `PushStrategy` requires exactly one stage and defaults to `cadence: "3h"`.
   - `push_hydrator.py`: Point-in-time filtering and stage prompt hydration (`fetch_push_context_batch`, `hydrate_stage_prompt`, `build_news_excerpt`), injecting `[Current Portfolio State]` immediately before the Long-Only `OutputFormatBlock`.
   - `portfolio_engine.py`: Shared Long-Only stateful portfolio simulator (`DEFAULT_CONCURRENCY_CONFIG = {"max_open_trades": 4, "max_equity_pct_per_trade": 25.0}`, `PortfolioState`, `apply_portfolio_step`, `format_portfolio_prompt_block`) used symmetrically by live turns and backtests. Positions hold across sessions and days until an explicit `EXIT` (or `SELL` on a held LONG) or `END_OF_WINDOW`.
   - `intraday_bars.py`: 3x/day ET slot expansion (`TRADING_SLOTS_ET = ((9, 30), (12, 30), (15, 30))`, `CORPUS_MIN_DATE = "2026-02-09"`), multi-source hourly bar resolution (`recipe_intraday_bars` -> `FMPProvider.get_hourly_history` -> Alpaca IEX hourly -> `price_history` fallback), upsert caching, and live slot bar capture (`snapshot_live_intraday_bars`).
   - `pit_tools.py`: Strict point-in-time tool dispatcher invoked by `core/llm/handlers/base.py` only when `pit_mode=True` or `as_of_utc` is set (so standalone historical analysis passing `cutoff_date` alone stays on `tools.py`), enforcing `<= as_of_utc` / strict `< cutoff_day` daily bar bounds, `recipe_news_corpus` article fallback in `_pit_fetch_newsletter`, and `strict_pit=True` fail-closed `tools/technicals.py` execution (zero `MarketDataManager.get_history` fallback). Live-only tools (`web_search`, option chains, etc.) fail closed.
   - `llm_caller.py`: Extracted LLM failover caller (`default_llm_caller`, `llm_endpoints`, `run_tool_loop`, `invoke_llm`) routing `STRATA_BASE_URL` -> `FREE_LLM_PROXY_URL` and propagating `cutoff_date`, `as_of_utc`, and `pit_mode=bool(cutoff_date or as_of_utc)`.
   - `push_runner.py` & `backtest_accounting.py`: Single-call live execution (`run_push_live`) and 3x/day ET point-in-time backtesting (`run_push_backtest`) across 10 trading days (30 ET slots) sampled from `>= CORPUS_MIN_DATE`. `BacktestAccumulator` wraps `PortfolioState` (including open-position midpoint mark-to-market in `ending_capital_midpoint`) and streams slot-by-slot snapshots via `on_progress`.
   - `worker.py`: `async_process_next_recipe_job()` / `process_next_recipe_job()` returning `JobOutcome` (`"EMPTY"`, `"COMPLETED"`, `"FAILED"`), persisting live portfolio state (`paper_cash`, `paper_positions`, `paper_trades`, `paper_equity_curve`) and `trial_count` back onto `strategy_recipes` under an optimistic `.eq("trial_count", current_trials)` CAS guard, and depositing alerts into `recipe_alerts_inbox` strictly for filled `executed_signals` (omitting skipped/rejected signals).
   - `runner.py`: MiniPC daemon (`python3 -m recipes.runner --loop`) running 3x/day ET trading slots (`due_trading_slot` at `09:30`, `12:30`, `15:30 ET` Mon-Fri with a 20-minute window, canonical UTC slot timestamps via `_canonical_slot_utc`, and DB-backed `slot_start_utc` queue deduplication across daemon restarts), capturing live intraday snapshots (`snapshot_live_intraday_bars` in parallel via `asyncio.gather` + single batch upsert), syncing live news, enqueueing active live recipes, and polling the priority queue every 5s.
   - `news_corpus.py` & `import_news_cli.py`: Bucket derivation (`derive_article_buckets`), JSONL shard importer, and `sync_live_news_to_corpus()` reusing `analysis/intraday_news_aggregator.py` + `newsletter_snapshots`.

3. **Presentation & Studio UI (`apps/web/src/features/recipes/`)**:
   - Built with Cheddar Boxel (Voxel) tokens (`bg-boxel-canvas`, `bg-boxel-surface`, 0px corners, 2px directional bevels, recessed `.voxel-trough` slots).
   - Studio (`/recipes`): `StageBuilder.tsx`, `BlockEditors.tsx`, `ToolPicker.tsx`, `PromptVisualizer.tsx`, `RecipeBacktestResults.tsx`, `RecipeAlertsInbox.tsx`, `WaitlistPledgeModal.tsx`, `starter-templates.ts` (consuming `packages/config/starter-recipes.json`), `prompt-builder.ts`, `api/recipes-api.ts`, and `api/recipes-studio-api.ts`.
   - Live Backtest View (`/recipes/backtest/$jobId`): `RecipeBacktestPage.tsx`, `BacktestTimelineBlock.tsx`, `BacktestTelemetryBlock.tsx`, and `BacktestTradesBlock.tsx`. Clicking `Backtest (Random 2W)` saves and enqueues the job, then navigates straight to `/recipes/backtest/$jobId`, which polls `fetchRecipeRunDetailFn` every 1.5s while the job is `pending` or `processing`. Users watch the 10-day timeline, tool calls, model output excerpts, developing telemetry, equity progression, and executed/skipped trades stream in day by day.
   - `prompt-builder.ts` owns the pure prompt-assembly helpers: `buildStagePromptPreview()` (unhydrated preview with `<Matching news headlines injected at run time>` placeholders) plus `hydrateNewsBlockText()` and `hydrateMemoriesBlockText()`, which apply recency windows, keyword `contains` matching, memory `category`, and `min_importance` filters to at most 15 rows. These hydration helpers were extracted out of the server API module so the Studio preview and the server function share one implementation.

## 5-Block Push-Based Model (`version: "2.0-push"`)

- **Single LLM Call (MVP)**: A strategy contains exactly one `StrategyStage`, which is one LLM call. The `stages` list shape stays so multi-stage chaining via `{{prev_output}}` can return later. See the Single LLM Call Limit section below.
- **5 Push Blocks**:
  - `output_format`: Immutable output-format contract locked to Long-Only decisions (`[{"action": "BUY"|"EXIT", "ticker": "..."}]` or `[]` to HOLD). Rendered **last** in the assembled stage prompt regardless of its block order, right after `[Current Portfolio State]`.
  - `prompt`: Free-text prompt instructions.
  - `news`: Keyword `contains` + `recency_hours` filter over `recipe_news_corpus`. Each hit renders its headline plus a ~300-char body excerpt (`build_news_excerpt` in `apps/engine/recipes/push_hydrator.py`, mirrored in `apps/web/src/features/recipes/news-excerpt.ts`, asserted against `packages/config/news-excerpt-cases.json`).
  - `memories`: Keyword `contains` + `recency_hours` + `category` (`memory_type`) + `min_importance` filter over `memories` (explicitly projecting columns without `embedding` vectors).
  - `technicals`: Company rules (`P/E`, `FCF`, `VWAP`, `RSI`, `MACD`, `price_52w_pct`, etc.) serialized as prompt criteria.

## 3x/Day ET Runner Daemon (`apps/engine/recipes/runner.py`)

`recipes.runner` is the MiniPC-hosted scheduler and queue worker that keeps the corpus fresh, captures live intraday bars, and drains the execution queue. It is deployed as the `recipe-worker` container in `docker/archive/docker-compose.secondary.yml` (512M memory limit, with `ARCHIVE_DB_URL: http://archive-proxy:80` so `tool_audit.py` writes directly to `tool_execution_logs`; see [[entities/secondary-minipc-edge]]).

### Cycle Functions

- **`due_trading_slot(now_utc, last_slot_key)`** — aligns live cycles cleanly to `TRADING_SLOTS_ET` (`09:30`, `12:30`, `15:30` `America/New_York`, Monday–Friday) within a 20-minute window (`SLOT_WINDOW_SECONDS = 1200`) and deduplicates by `<YYYY-MM-DD HH:MM ET>` key.
- **`seed_starter_recipes(sb_client)`** — loads `packages/config/starter-recipes.json` and idempotently inserts any template whose `name` is not already present among `is_template = true` rows (`.limit(100)` capped existence check). Seeded rows carry `user_id = ANONYMOUS_USER_ID` (`00000000-0000-0000-0000-000000000000`), `is_public = true`, `is_template = true`, `is_live = false`, `cadence = '3h'`, and `DEFAULT_CONCURRENCY_CONFIG` (`max_open_trades: 4`, `max_equity_pct_per_trade: 25.0`). Returns the number inserted.
- **`enqueue_live_recipes(sb_client)`** — selects every `is_live = true` recipe (`.limit(500)`), skips any that already have a `pending`/`processing` queue row (`.limit(1000)` open-job scan), and validates each candidate through `_is_single_stage_push_v2_graph()`. Surviving jobs are inserted in a single batch (`priority = 1`).
- **`run_hourly_cycle(sb_client, as_of_utc=None, max_jobs=25)`** — runs `sync_live_news_to_corpus()`, then `enqueue_live_recipes()`, then drains up to `max_jobs` queue jobs via `await async_process_next_recipe_job(sb_client)`.
- **`_run_daemon_loop(sb_client)`** — seeds templates once, then whenever `due_trading_slot()` fires, snapshots live quotes into `recipe_intraday_bars` via `snapshot_live_intraday_bars()` for held/starter symbols and runs `run_hourly_cycle`; off-slot polls the queue every `POLL_INTERVAL_SECONDS` (5s) through `_drain_sync_queue`.

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

`run_push_backtest(strategy, sb_client, llm_caller=None, rng=None, slippage_bps=5.0, concurrency_config=None, on_progress=None)` simulates a random contiguous 10-trading-day window stepped 3x/day ET (`09:30`, `12:30`, `15:30 ET` = 30 sessions) using the shared Long-Only `PortfolioState` engine with zero forward leakage:

1. **Trading calendar & corpus floor** — `_load_window_dates(sb_client)` reads `SPY` dates from `price_history` filtered to `>= CORPUS_MIN_DATE` (`2026-02-09`, matching the earliest `memories` row), and `expand_dates_to_et_slots()` expands the 10-day window into 30 ET slot descriptors (`slot_label`, `cutoff_date`, `as_of_utc`).
2. **Initial progress** — `on_progress` receives `10%` immediately with all 30 slot labels so `/recipes/backtest/$jobId` renders the full grid before Slot 1 runs.
3. **Strict PIT context & tools** — `fetch_push_context_batch()` and `execute_pit_tool()` (`apps/engine/recipes/pit_tools.py`, routed automatically by `core/llm/handlers/base.py` when `cutoff_date` or `as_of_utc` is set) enforce temporal isolation for `get_stock_quote`, `get_price_history`, `get_technical_indicators`, `get_ticker_news`, `get_todays_news_menu`, `fetch_newsletter_content`, `search_past_memories`, `get_market_feeling`, `get_earnings_history`, and `get_key_metrics`, while failing closed on live-only tools (`web_search`, option chains, etc.).
4. **Intraday pricing (`apps/engine/recipes/intraday_bars.py`)** — `fetch_intraday_bars_for_ticker()` resolves hourly/intraday bars from `recipe_intraday_bars` -> `FMPProvider.get_hourly_history` -> Alpaca IEX hourly -> `price_history` fallback, upserting fetched bars back to Postgres, and `resolve_slot_price()` picks the bar at or before each `as_of_utc`.
5. **Long-Only portfolio accounting (`BacktestAccumulator` & `PortfolioState`)** — positions remain open across sessions and overnight until explicit `EXIT` (or `SELL` on a held LONG) or `END_OF_WINDOW` on Slot 30, obeying `max_open_trades = 4` and `max_equity_pct_per_trade = 25.0%` (`SELL` when flat is skipped as `SHORT_NOT_ALLOWED`). Net P&L models `2 × slippage_bps` round-trip friction.

In `apps/engine/recipes/worker.py`, `on_progress` persists `progress_pct` (`10` -> `95`) and `result_json` to `recipe_execution_queue` on every settled slot.

## Live Backtest View (`/recipes/backtest/$jobId`)

Clicking **Backtest (Random 2W)** saves the recipe, enqueues a `backtest` job, and navigates to `/recipes/backtest/$jobId`, polling `fetchRecipeRunDetailFn` every 1.5s while `pending` or `processing`.

- **`BacktestHeader`** — displays `Edit in Studio`, recipe name, solid badge (`QUEUED` / `SLOT n / N` / `COMPLETED` / `FAILED`), `progress_pct`, `Re-run Backtest`, and progress bar.
- **`BacktestTimelineBlock`** — fluid grid of session tiles (`S<n> • <YYYY-MM-DD HH:MM ET>`), net P&L delta, and signal badges (`BUY` success, `EXIT` warning, `SELL`/`ERROR` danger, `HOLD`/`QUEUED` neutral, `RUNNING` accent), plus the in-flow `DayInspector` trough showing open-position counts, tool traces, and model output.
- **`BacktestTelemetryBlock`** — `MetricTile`s and `Equity Progression` bars with `Spread & Slippage Net` vs `Midpoint (Zero-Cost)` toggle.
- **`BacktestTradesBlock`** — executed closed trades with `Action`, `Entry Session`, `Exit Session`, `Entry`, `Exit`, `Exit Reason` badge (`SIGNAL_EXIT` / `END_OF_WINDOW`), `Net Return`, `Net P&L`, and skipped counterfactual signals (`SHORT_NOT_ALLOWED`, `MAX_OPEN_TRADES`, `NO_PRICE_DATA`).

A `live_turn` job opened on this route renders an `Incompatible Job Mode` error card instead of backtest telemetry.

### Studio Recent Backtests

`/recipes` loads `fetchRecentBacktestJobsFn()` alongside the optional `?recipeId=` recipe and renders a `Recent Backtests:` trough of up to five `voxel-btn` links to `/recipes/backtest/$jobId`, each labeled with the short job id and either the net return (`+1.80%`) or `<STATUS> (<progress>%)`.

## LLM Endpoint Failover (`apps/engine/recipes/llm_caller.py`)

Every LLM call in `push_runner.py` goes through `invoke_llm()` -> `default_llm_caller()` in `apps/engine/recipes/llm_caller.py`:

- **`llm_endpoints(openrouter_key, model)`** builds the ordered chain: OpenRouter (`https://openrouter.ai/api/v1`) when an explicit `openrouter_key` is supplied, otherwise `STRATA_BASE_URL` followed by `FREE_LLM_PROXY_URL` (`https://llm.clvg.uk/v1`).
- **`run_tool_loop(client, model_id, prompt, tool_schemas, cutoff_date, as_of_utc=None)`** runs up to 4 Long-Only OpenAI-compatible tool-calling iterations, forwarding both `cutoff_date` and `as_of_utc` into `core/llm/handlers/base.py:execute_tool()` so backtests enforce strict PIT bounds.
- **`default_llm_caller(...)`** fails over across endpoints and re-raises if every endpoint fails.

## Worker Modes, Outcomes & Event-Loop Safety (`apps/engine/recipes/worker.py`)

- **`JobOutcome = Literal["EMPTY", "COMPLETED", "FAILED"]`** — the tri-state return distinguishes "queue was empty" from "job ran" and "job errored". Callers drain until `"EMPTY"` and count `"FAILED"` separately (`run_hourly_cycle` reports `jobs_processed` vs `jobs_failed`).
- **`SUPPORTED_JOB_MODES = ("backtest", "live_turn")`** — the popped `job_mode` is validated immediately after dequeue; an unrecognized mode raises `ValueError("Unsupported recipe execution mode: <mode>")`, which is caught, persisted to `recipe_execution_queue.error_message` on the `failed` row, and returned as `"FAILED"`. A missing `job_mode` defaults to `backtest`. The `preview` mode was removed: it had no implementation and fell through to the backtest branch, so a preview job spent ten LLM calls.
- **No nested event loop** — `async_process_next_recipe_job()` `await`s `run_push_live()` / `run_push_backtest()` directly, so it is safe to call from an already-running loop (e.g. inside `async run_hourly_cycle`). The legacy `asyncio.run(...)` nesting that raised `RuntimeError: asyncio.run() cannot be called from a running event loop` is confined to the synchronous wrapper `process_next_recipe_job()`.
- **`process_next_recipe_job(client=None)`** — thin synchronous wrapper (`return asyncio.run(async_process_next_recipe_job(client))`) preserved for non-async callers and the off-hour daemon drain path.
- Successful jobs still write `result_json`, `status = 'completed'`, increment `strategy_recipes.trial_count`, and deposit `live_turn` signals into `recipe_alerts_inbox`.

## Legacy DAG Removal

The former `RecipeGraph` DAG pipeline (`schema.py`, `validator.py`, `indicators.py`, `backtester.py`, `backtest_models.py`) and its `recipe_intraday_bars` 5-minute candle cache have been removed. `async_process_next_recipe_job()` rejects any `graph_json` that lacks a `stages` list with `ValueError("Recipe must use Push v2 format with a 'stages' list (legacy DAG format is removed).")`, marking the queue row `failed` with that message in `error_message`. `enqueue_live_recipes()` applies the same Push v2 shape check, plus the one-stage limit, before a live recipe may enter the queue.

## Single LLM Call Limit (MVP)

Each strategy makes one LLM call per live run or per backtest day. Multi-stage chaining is off for the MVP. The limit is enforced at every boundary a strategy can cross, so a stale client, an old queued row, or a hand-written API call cannot bypass it.

- The Studio UI (`apps/web/src/features/recipes/pages/RecipeStudioPage.tsx`) shows one `LLM Call` card with no add or remove stage controls. `PushStrategy.stages` is typed as the one-element tuple `[StrategyStage]`, and `starter-templates.ts` validates the imported JSON at load time.
- The engine schema (`apps/engine/recipes/push_schema.py`) is the source of truth. `PushStrategy.stages` is a required field with `min_length=1, max_length=1`; the `validate_exactly_one_llm_stage` validator raises `Push strategies must contain exactly one LLM stage for the MVP`, and `reject_prev_output_placeholder` rejects a `{{prev_output}}` prompt because a single-stage strategy has no previous output to reference.
- The scheduler (`apps/engine/recipes/runner.py`) uses `_is_valid_single_stage_graph()` in `enqueue_live_recipes()`. It validates with the same schema the worker uses, so a malformed or multi-stage live recipe is skipped with a `logger.warning` instead of being queued. Queueing it would leave a failed row behind on every hourly cycle.
- The save API (`apps/web/src/features/recipes/api/recipes-api.ts`) calls `assertSingleLlmStage()` and `assertNoPrevOutputPlaceholder()` inside `saveRecipe()` before any write.
- The enqueue API rejects a recipe the caller neither owns nor may see, rejects a multi-stage or malformed `graph_json` before it reaches the queue, and caps the number of open jobs per user.
- The database enforces it too. The `strategy_recipes_single_stage_check` constraint (`supabase/migrations/20261113190000_unpublish_legacy_multistage_recipe_template.sql`) rejects a `graph_json` whose `stages` array is not exactly one element on insert and update. It was added `NOT VALID` so the legacy row did not block it.

`{{prev_output}}` is rejected rather than left in place. The hydrator substituted it with an empty string, so a single-stage prompt that referenced a previous output silently reached the model truncated, and the Studio preview showed a token the run would not contain.

The legacy `2-Stage Research -> Trade Decision` template was unpublished by the same migration (`is_public = FALSE`, `is_template = FALSE`). It was removed from `packages/config/starter-recipes.json`, so the seeder never recreates it. The row is kept for auditability and is no longer publicly readable.

To bring multi-stage back, drop the `{{prev_output}}` rejection, relax the schema cardinality and the DB constraint, restore the stage controls in the UI, and re-add the second stage to the enqueue and scheduler guards.

## API Module Split

The Studio's server functions are split across two modules by concern, both keeping the logic in plain exported functions with the `createServerFn` wrappers as thin shells so each rule is unit tested:

- **`api/recipes-api.ts`** — recipe persistence and job lifecycle: `saveRecipe` / `saveRecipeFn`, `enqueueRecipeJob` / `enqueueRecipeJobFn`, `getRecipeJobStatus` / `getRecipeJobStatusFn`, `fetchRecipeRunDetail` / `fetchRecipeRunDetailFn`, `fetchRecipeById` / `fetchRecipeByIdFn`, `fetchRecentBacktestJobs` / `fetchRecentBacktestJobsFn`, and `fetchPublicRecipes`.
- **`api/recipes-studio-api.ts`** — Studio-side utilities that are not part of the job lifecycle: `fetchRecipeAlerts` / `fetchRecipeAlertsFn`, `markAlertRead` / `markAlertReadFn`, `submitWaitlistPledge` / `submitWaitlistPledgeFn`, and `previewStrategyPrompt` / `previewStrategyPromptFn` (which hydrates news and memories blocks through `prompt-builder.ts` without ever selecting `embedding` vectors).

`RecipeStudioPage` imports the job functions from `recipes-api` and the alerts/waitlist/preview functions from `recipes-studio-api`; the split keeps the job module free of alert-inbox and waitlist concerns.

## Recipe API Authorization

The Studio runs against the archive DB, where `strategy_recipes` is publicly readable for templates and public recipes while `recipe_execution_queue` and `recipe_alerts_inbox` are service-role only. The API in `apps/web/src/features/recipes/api/recipes-api.ts` keeps the logic in plain exported functions and the server functions as thin wrappers, so each rule is unit tested.

- `saveRecipe()` fails closed. It reads the existing row first, rejects a row owned by another user, and never transfers ownership or clobbers customized slot/sizing limits: `user_id` is absent from `update`, `concurrency_config` defaults (`max_open_trades: 4`, `max_equity_pct_per_trade: 25.0`) apply only on `insert`, and the update is scoped with `.eq('user_id', userId)`.
- `enqueueRecipeJob()` requires the caller to own the recipe or to be allowed to see it (`is_public` or `is_template`), validates the recipe's `graph_json` before it reaches the queue, and caps the number of open jobs per user so one caller cannot flood the queue with LLM runs.
- `getRecipeJobStatus()` and `fetchRecipeRunDetail()` read the service-role-only queue with the admin client and scope the row to the requesting user's `user_id`, so one caller cannot read another caller's job result. `fetchRecipeRunDetail()` additionally joins `strategy_recipes` for `name` and `cadence`, returning `{ job, recipeName, recipeCadence }` and degrading to nulls when `recipe_id` is absent. `fetchRecentBacktestJobs()` surfaces the caller's recent backtests in the Studio.
- `fetchRecipeById()` allows the Studio (`/recipes?recipeId=<id>`) to reload a saved recipe when returning from `/recipes/backtest/$jobId` ("Edit in Studio"). It authorizes on ownership, `is_public`, or `is_template`, and drops `id` when loading another user's public/template recipe so edits fork into a new row instead of hitting an ownership error on save.
- Anonymous visitors share the `00000000-0000-0000-0000-000000000000` user id, so ownership only separates signed-in users. By default `/recipes` starts from a local starter template unless `?recipeId=` is specified.

## Client Types (`apps/web/src/features/recipes/types.ts`)

- `BacktestDayStep` — `{ day, day_index, status, signals, tool_calls, output_excerpt, day_pnl_net, trades_executed, trades_skipped }`, the per-day trace rendered by the timeline inspector.
- `BacktestResultData` — the accumulator snapshot shape, extended with `mode`, `days_completed`, `total_days`, `current_day`, and `day_steps` so a partial in-flight payload is a valid `BacktestResultData`. Note: `window_dates`, `days_completed`, and `total_days` intentionally retain their existing JSON keys while holding ET slot labels and slot counts (`30` slots for 10 trading days) for backwards schema compatibility across stored `result_json` rows, alongside preserving the `'5m' | '3h' | '1d'` `cadence` union on `PushStrategy`.
- `RecipeJobStatus` — `'pending' | 'processing' | 'completed' | 'failed'`.
- `RecipeJobRecord` — the queue row projection (`id`, `recipe_id`, `mode`, `status`, `progress_pct`, `provider`, `model`, `result_json`, `error_message`, timestamps).
- `RecipeRunDetail` — `{ job, recipeName, recipeCadence }`.
- `ExecutionState` — `idle` → `running` (`live_turn` | `backtest`) → `live_done` | `error`. The former `backtest_done` state was removed because a backtest now navigates to its own route instead of rendering inline.

## Related Pages

- [[entities/database]] — `recipe_*` / `strategy_recipes` tables, `price_history`, and `pop_next_recipe_job()`
- [[entities/secondary-minipc-edge]] — hosts the `recipe-worker` container in `docker/archive/docker-compose.secondary.yml`
- [[entities/free-llm-proxy]]
- [[entities/design-system]]
- [[concepts/zero-frontend-compute]]
- [[concepts/zero-lookahead-materialization]]
- [[concepts/state-machines]] — `RecipeJobStatus` and `ExecutionState` lifecycle registry
