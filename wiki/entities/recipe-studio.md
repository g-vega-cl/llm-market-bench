---
tags: [recipes, push-v2, trading, backtest, news-corpus, voxel, studio]
category: entity
---

# Recipe Studio

The **Recipe Studio** (`/recipes`) is a 5-block push-based strategy builder where each strategy makes one LLM call. Inspired by Unsloth Studio Data Recipes, it lets researchers compose prompts, point-in-time news filters, historical memories filters, technical criteria, and immutable trade-signal schemas into that call, then backtest them over random 2-week point-in-time windows or schedule hourly live runs.

## Architecture

1. **Storage & Corpus (`supabase/migrations/20261112103000_create_recipe_studio_v2.sql`, `supabase/migrations/20261114000000_create_recipe_intraday_bars.sql`, `supabase/migrations/20261116000000_recipe_beta_quotas_and_dual_lane.sql`, `supabase/migrations/20261116010000_strip_recipe_stage_title.sql`)**
   - `public.recipe_news_corpus`: Point-in-time news articles imported from `stock-news-scraper` shards and synced from live market wires + `newsletter_snapshots`, tagged across canonical buckets with `search_tsv` and GIN indexes on `tickers`, `buckets`, and `search_tsv`.
   - `public.strategy_recipes`: Push v2 strategy configurations (`graph_json` with `version: "2.0-push"` and a one-item `stages` list), cadence (`5m`, `3h`, or `1d`, defaulting to `3h` for 3x/day ET runs at `09:30`, `12:30`, `15:30`), concurrency limits (`max_open_trades: 4`, `max_equity_pct_per_trade: 25.0`), and isolated paper ledgers (`paper_cash`, `paper_positions`, `paper_trades`, `paper_equity_curve`). Starter templates live in `packages/config/starter-recipes.json` and are seeded into `strategy_recipes`.
   - `public.recipe_intraday_bars`: Cached intraday bars (`(ticker, bar_time_utc)` PK) populated from `FMPProvider.get_hourly_history`, Alpaca IEX hourly bars, and live slot snapshots (`snapshot_live_intraday_bars`). `FMPProvider._has_hourly_range_coverage()` and `_ensure_slot_prices()` in `push_runner.py` validate weekday/slot coverage so partial SQLite slices never shadow full-window intraday bars with prior-day daily closes.
   - `public.recipe_execution_queue`: Priority queue with `heartbeat_at` lease tracking, `cancelled` status support, and dual-lane atomic dequeue RPC `pop_next_recipe_job(target_mode TEXT DEFAULT NULL)` (10-minute `COALESCE(heartbeat_at, started_at)` stale recovery and strict 1-at-a-time active `backtest` serialization without blocking `live_turn` jobs).
   - `public.recipe_user_quotas`: Per-user starter/tier quota overrides (`max_concurrent_backtests: 1`, `daily_backtest_limit: 2`, `daily_live_turn_limit: 3`, `max_live_recipes: 1`).
   - `public.recipe_alerts_inbox`: In-app trade alert delivery table.
   - `public.recipe_waitlist_pledges`: Early supporter pledges for future dedicated GPU compute tiers.
   - **Stage-title cleanup (`20261116010000_strip_recipe_stage_title.sql`)**: removes the obsolete per-stage `title` key from stored `graph_json` for single-stage graphs. The migration is scoped with `CASE`-gated `jsonb_typeof`/`jsonb_array_length` checks (boolean subexpressions are not evaluated left to right, and `strategy_recipes_single_stage_check` was added `NOT VALID`, so a row whose `stages` is an object or scalar was never scanned and must not abort the migration). The legacy unpublished two-stage row cannot be updated at all — the single-stage CHECK rejects any update that leaves two stages in place — so its inert title is left as audit history. `recipe_execution_queue.result_json` rows are historical run telemetry and are intentionally untouched. No RLS or GRANT changes.

2. **Engine Processing (`apps/engine/recipes/`)**
   - `push_schema.py`: Pydantic models for Push v2 (`PushStrategy`, `StrategyStage`, `PromptBlock`, `NewsBlock`, `MemoriesBlock`, `TechnicalsBlock`, `OutputFormatBlock`). `PushStrategy` requires exactly one stage and defaults to `cadence: "3h"`. `StrategyStage` carries only `id`, `blocks`, and `selected_tools` — the per-stage `title` field has been removed, so stages render as a fixed "LLM Call" badge. Recipe naming is governed by a shared contract in `packages/config/recipe-naming.json` (`defaultName`, `nameMaxLength`), loaded once via the `lru_cache`-memoized `recipe_naming()` helper (raising `RuntimeError` when the file is missing or invalid) and exposed as `DEFAULT_STRATEGY_NAME` / `RECIPE_NAME_MAX_LENGTH`. `PushStrategy.name` is `Field(default=DEFAULT_STRATEGY_NAME, max_length=RECIPE_NAME_MAX_LENGTH)` with a `mode="before"` `normalize_name` validator that strips and caps the value and falls back to the default for blank or non-string input — `strategy_recipes.name` is `TEXT NOT NULL` and `graph_json` is free-form JSON, so a stored `name: null` must normalize instead of failing worker validation. The web layer mirrors the same contract via `recipes-validators.ts`.
   - `push_hydrator.py`: Point-in-time filtering and stage prompt hydration (`fetch_push_context_batch`, `hydrate_stage_prompt`, `build_news_excerpt`), injecting `[Current Portfolio State]` immediately before the Long-Only `OutputFormatBlock`.
   - `portfolio_engine.py`: Shared Long-Only stateful portfolio simulator (`DEFAULT_CONCURRENCY_CONFIG = {"max_open_trades": 4, "max_equity_pct_per_trade": 25.0}`, `PortfolioState`, `apply_portfolio_step`, `enrich_open_positions`, `format_portfolio_prompt_block`) used symmetrically by live turns and backtests. Positions hold across sessions and days until an explicit `EXIT` (or `SELL` on a held LONG) or `END_OF_WINDOW`. `enrich_open_positions(state, prices, slippage_bps=...)` attaches `current_price`, `market_value`, `unrealized_pnl_net` (net of round-trip slippage), and `unrealized_return_pct` to every open position so both the live and backtest payloads carry mark-to-market telemetry.
   - `intraday_bars.py`: 3x/day ET slot expansion (`TRADING_SLOTS_ET = ((9, 30), (12, 30), (15, 30))`, `CORPUS_MIN_DATE = "2026-02-09"`), multi-source hourly bar resolution (`recipe_intraday_bars` -> `FMPProvider.get_hourly_history` -> Alpaca IEX hourly -> `price_history` fallback), upsert caching, and live slot bar capture (`snapshot_live_intraday_bars`).
   - `pit_tools.py`: Strict point-in-time tool dispatcher invoked by `core/llm/handlers/base.py` only when `pit_mode=True` or `as_of_utc` is set (so standalone historical analysis passing `cutoff_date` alone stays on `tools.py`), enforcing `<= as_of_utc` / strict `< cutoff_day` daily bar bounds, `recipe_news_corpus` article fallback in `_pit_fetch_newsletter`, existing-column `market_feeling` reads (`primary_concern, secondary_concern`), and `strict_pit=True` fail-closed `tools/technicals.py` execution (zero `MarketDataManager.get_history` fallback). Exports `PIT_SAFE_TOOL_NAMES` matching `_build_pit_dispatch`; live-only tools (`web_search`, `run_stock_screener`, option chains, etc.) fail closed.
   - `llm_caller.py`: Extracted LLM failover caller (`default_llm_caller`, `llm_endpoints`, `run_tool_loop`, `invoke_llm`, `filter_recipe_tool_names`). Routes `auto-go` strictly to `FREE_LLM_PROXY_URL` (`https://llm.clvg.uk/v1`, excluding raw local Strata so live runs never contend with backtests), routes proxy router aliases (`strata-auto-go`, `auto-strata-go`) through `FREE_LLM_PROXY_URL` first, forwards per-job `model` cleanly through `invoke_llm`, and propagates `cutoff_date`, `as_of_utc`, and `pit_mode=bool(cutoff_date or as_of_utc)` inside `async with AsyncOpenAI(...)` contexts. Enforces `RECIPE_DISABLED_TOOLS` (`web_search`) and PIT/stage allowlists (`allowed_tools`) both in schemas and at dispatch time in `_execute_round_tools` (rejecting non-dict JSON args safely). Runs up to `MAX_TOOL_ROUNDS = 5` tool iterations followed by 1 forced tool-free `_run_final_synthesis` pass if exhausted, separating `thinking`/`reasoning_content` cleanly from `output` (never falling back to raw `thinking` blocks) while capturing `trace` (`rounds`, tool call args + results, `forced_final_synthesis`).
   - `push_runner.py` & `backtest_accounting.py`: Single-call live execution (`run_push_live`, propagating `prompt`, `trace`, and `enrich_open_positions`-enriched `paper_positions`; each stage result carries `stage_id`, `prompt`, `output`, and `tool_calls` — no `title`) and 3x/day ET point-in-time backtesting (`run_push_backtest`) across 10 trading days (30 ET slots) sampled from `>= CORPUS_MIN_DATE`. `BacktestAccumulator` wraps `PortfolioState` + `enrich_open_positions`, tracks `refreshed_bar_days` to backfill partial intraday bar arrays cleanly, persists `prompt`, `trace`, and unclipped `full_output` on `day_steps`, honors mid-run `is_cancelled()` checks, and streams slot-by-slot snapshots via `on_progress`.
   - `worker.py`: `async_process_next_recipe_job(target_mode=...)` / `process_next_recipe_job(target_mode=...)` returning `JobOutcome` (`"EMPTY"`, `"COMPLETED"`, `"FAILED"`, `"CANCELLED"`), updating `heartbeat_at` on each slot, forwarding `job_model` (`auto-go` for `live_turn`, `strata-auto-go` for `backtest`), skipping completion writes if cancelled mid-run, persisting live portfolio state + `trial_count` under optimistic CAS, and depositing alerts into `recipe_alerts_inbox` strictly for filled `executed_signals`.
   - `runner.py`: MiniPC dual-lane daemon (`python3 -m recipes.runner --loop`) running `_live_lane_loop` (scheduled 3x/day ET `09:30`, `12:30`, `15:30 ET` cycles + concurrent `live_turn` draining on `auto-go`) alongside `_backtest_lane_loop` (`max_jobs=1` serialized `strata-auto-go` backtests) so 2-hour backtests never block live execution.
   - `news_corpus.py` & `import_news_cli.py`: Bucket derivation (`derive_article_buckets`), JSONL shard importer, and `sync_live_news_to_corpus()` reusing `analysis/intraday_news_aggregator.py` + `newsletter_snapshots`.

3. **Presentation & Studio UI (`apps/web/src/features/recipes/` & `_authed/recipes/`)**
   - Auth-gated under `/_authed` (`apps/web/src/routes/_authed/recipes/index.tsx` and `_authed/recipes/backtest/$jobId.tsx`, preserving return redirect paths through `shared/auth/redirect.ts` and `routes/auth.callback.tsx`), paired with a public read-only showcase preview route (`/recipes-demo`, linked from `/lab`).
   - Built with Cheddar Voxel tokens (`bg-boxel-canvas`, `bg-boxel-surface`, 0px corners, 2px directional bevels, recessed `.voxel-trough` slots).
   - Studio (`/recipes`): `RecipeGuideAndQuotaBlock.tsx` (`FREE BETA STARTER` quota strip + in-flow backtest/live guides + `SavedRecipesStrip`, plus the top alert slot and `RecentBacktestsStrip`), `RecipeNameField.tsx`, `StudioActionBar.tsx`, `StageBuilder.tsx`, `BlockEditors.tsx`, `ToolPicker.tsx` (`web_search` removed from `CURATED_TOOLS`; `run_stock_screener` tagged `Live only`), `PromptVisualizer.tsx`, `RecipePortfolioBlock.tsx`, `TraceInspectorBlock.tsx`, `LiveRunsBlock.tsx`, `RecipeAlertsInbox.tsx`, `WaitlistPledgeModal.tsx`, `api/recipes-api.ts`, `api/recipes-quota-api.ts`, and `api/recipes-studio-api.ts`. Supports `Schedule Live (3x/d)` toggle (`max 1` active) and `auto-go` / `strata-auto-go` model dispatch.
   - **Recipe name field (`Recipe Name`) + explicit save**: `RecipeNameField.tsx` renders the `Label` + `Input` pair plus a `Save Recipe` button, and saving is never implicit — the button only enables while the name or graph differs from what the server holds (`persistedName` / `isGraphDirty`), shows `Saving...`, then settles on `Saved` with the server-returned name, and surfaces a save failure inline via `role="alert"` (with `aria-invalid` / `aria-describedby` wiring on the input and an `aria-live` status region for screen readers). Run Live, Backtest, and Schedule Live still persist through the shared `persistActiveStrategy`, which adopts `saved.name` from the response. The studio action row lives in `StudioActionBar.tsx` (Waitlist, Alerts with unread count, Schedule Live toggle, Run Live, Backtest — all run actions disabled while `isBusy`). `packages/config/recipe-naming.json` (`defaultName`, `nameMaxLength`) is the shared contract for both sides: `normalizeRecipeName()` in `api/recipes-validators.ts` and the `mode="before"` `field_validator("name")` in `push_schema.py` both read it, trimming, capping, and falling back to `Untitled Strategy` because `strategy_recipes.name` is `TEXT NOT NULL` and `graph_json` may hold a null name. `saveRecipe` applies `normalizeRecipeName(recipe.name)` before the insert. Running a recipe still persists the current draft as a side effect of queueing the job; the header button is the explicit path. `saveRecipe` also deletes only the obsolete `title` key from `stages[0]` (preserving any future stage field) so a stale client cannot copy it back into `graph_json`. Selecting a starter template resets the field to that template's name. There is no per-stage title field: the single stage is labelled `LLM Call` in `StageBuilder.tsx`, `PromptVisualizer.tsx`, and live run traces, and `supabase/migrations/20261116010000_strip_recipe_stage_title.sql` removes the leftover `title` key from stored `graph_json` stages (`recipe_execution_queue.result_json` is left as historical telemetry).
   - **Single top alert slot (`StudioAlertSlot`)**: Rendered once between the action row and the quota strip, backed by the pure `RecipeExecutionAlert` block (danger-bordered, `role="alert"`). It surfaces at most one failure at a time — an `ExecutionState` error takes precedence over a `scheduleError` — and offers an `Open Backtest Run →` link when a backtest job id is available, plus a `Request Capacity` button (opens the `WaitlistPledgeModal`) when the failure is quota-related. Because both `handleExecute` and `handleToggleScheduledLive` funnel errors through this single slot, a stale execution error is cleared before a schedule toggle, and a schedule failure never leaves a stale backtest error visible. A failed *save* is deliberately excluded: `RecipeSaveError` is reported inline next to the name field instead, so the same failure is never shown twice.
   - `resolveBacktestButtonLabel(isStarting, quotaStatus)` derives the backtest button caption from live quota state: `Starting Backtest...` while starting, `Backtest (N Active)` when concurrent backtests are maxed, `Backtest (0/N Left)` when the 24h limit is exhausted, else `▶ Backtest (Random 2W)`.
   - `RecentBacktestsStrip` renders up to 5 recent runs as `voxel-btn` links to `/recipes/backtest/$jobId`, labeling completed backtests with their net return (`+1.80%`) or `<STATUS> (<progress>%)` otherwise (ignoring `live_turn` payloads).
   - Live Backtest View (`/recipes/backtest/$jobId`): `RecipeBacktestPage.tsx` (with `QUEUED #N`, `Cancel Run`, `CANCELLED` status, `BacktestMethodologyBlock`, and `readOnlyShowcase` mode), `BacktestTimelineBlock.tsx` (with `SelectedSlotBar`), `BacktestSessionTraceBlock.tsx` (`#session-trace`), `BacktestTelemetryBlock.tsx`, `RecipePortfolioBlock.tsx`, and `BacktestTradesBlock.tsx`.
   - `prompt-builder.ts` owns the pure prompt-assembly helpers: `buildStagePromptPreview()` (unhydrated preview with `<Matching news headlines injected at run time>` placeholders) plus `hydrateNewsBlockText()` and `hydrateMemoriesBlockText()`, which apply recency windows, keyword `contains` matching, memory `category`, and `min_importance` filters to at most 15 rows. These hydration helpers were extracted out of the server API module so the Studio preview and the server function share one implementation.

## 5-Block Push-Based Model (`version: "2.0-push"`)

- **Single LLM Call (MVP)**: A strategy contains exactly one `StrategyStage`, which is one LLM call. The `stages` list shape stays so multi-stage chaining via `{{prev_output}}` can return later. See the Single LLM Call Limit section below.
- **5 Push Blocks**:
  - `output_format`: Immutable output-format contract locked to Long-Only decisions (`[{"action": "BUY"|"EXIT", "ticker": "..."}]` or `[]` to HOLD). Rendered **last** in the assembled stage prompt regardless of its block order, right after `[Current Portfolio State]`.
  - `prompt`: Free-text prompt instructions.
  - `news`: Keyword `contains` + `recency_hours` filter over `recipe_news_corpus`. Each hit renders its headline plus a ~300-char body excerpt (`build_news_excerpt` in `apps/engine/recipes/push_hydrator.py`, mirrored in `apps/web/src/features/recipes/news-excerpt.ts`, asserted against `packages/config/news-excerpt-cases.json`).
  - `memories`: Keyword `contains` + `recency_hours` + `category` (`memory_type`) + `min_importance` filter over `memories` (explicitly projecting columns without `embedding` vectors).
  - `technicals`: Company rules (`P/E`, `FCF`, `VWAP`, `RSI`, `MACD`, `price_52w_pct`, etc.) serialized as prompt criteria.

## Draft & Explicit Save State Machine (`useRecipeDraft`)

`apps/web/src/features/recipes/utils/use-recipe-draft.ts` owns the studio's draft and explicit-save lifecycle. It exposes `strategy`, `isDirty`, `isSaving`, `saveState` (`RecipeSaveState`), `saveError`, `setName`, `setStage`, `resetTo`, and `save(persist)`.

Three invariants keep edits from being lost or misattributed:

1. **Revision guard** — `draftRev` advances on every edit (`setName`, `setStage`, `resetTo`). A response that lands against a newer revision adopts the saved row `id` but never overwrites the local draft, and `saveState` settles to `idle` rather than `saved` so the field still reads as dirty.
2. **Flight-scoped `isSaving`** — cleared only when the request settles, never by an edit, so `isBusy` keeps Run Live, Backtest, and Schedule Live disabled for the whole flight.
3. **Generation guard** — `generation` advances when the draft is replaced by a template (`resetTo`). A response from an older generation is ignored entirely, so it cannot stamp the old row id onto a fresh template.

`save(persist)` shares the in-flight promise when the draft revision is unchanged, so a duplicate click cannot insert the recipe twice. When the draft advanced mid-flight, it chains a second persist after the first settles, so a queued run always enqueues the edited graph rather than the pre-edit snapshot. Failures are rethrown as `RecipeSaveError`, which `RecipeStudioPage` uses to route the message to the inline `RecipeNameField` alert instead of the top `StudioAlertSlot`.

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
- **`BacktestTimelineBlock`** — fluid grid of session tiles (`S<n> • <YYYY-MM-DD HH:MM ET>`), net P&L delta, and signal badges (`BUY` success, `EXIT` warning, `SELL`/`ERROR` danger, `HOLD`/`QUEUED` neutral, `RUNNING` accent), followed by a compact `SelectedSlotBar` with a `Jump to Trace ↓` anchor link to `#session-trace`.
- **`BacktestTelemetryBlock`** — `MetricTile`s and `Equity Progression` bars with `Spread & Slippage Net` vs `Midpoint (Zero-Cost)` toggle.
- **`RecipePortfolioBlock`** — displays `Cash Available`, `Open Market Value`, `Total Equity`, `Open Positions` (`n / 4`), and the open-positions mark-to-market table on both Backtest (`Current Portfolio & Open Positions`) and Live Studio (`Live Paper Portfolio`).
- **`BacktestTradesBlock`** — executed trades combining open `BUY` fills (`OpenTradeRow` with `OPEN` badge from `open_positions`) and closed trades (`Action`, `Entry Session`, `Exit Session`, `Entry`, `Exit`, `Exit Reason` badge `SIGNAL_EXIT` / `END_OF_WINDOW`, `Net Return`, `Net P&L`), plus skipped counterfactual signals (`SHORT_NOT_ALLOWED`, `MAX_OPEN_TRADES`, `NO_PRICE_DATA`).
- **`BacktestSessionTraceBlock`** (`#session-trace`) — sits below `BacktestTradesBlock` so Telemetry, Portfolio, and Trades remain immediately visible below the 30-slot indicator; provides `‹ Prev` / `Next ›` session stepping, an `↑ Timeline` anchor link back to `#simulation-timeline`, `Hold decision` summaries, and `TraceInspectorBlock` in exact LLM order (`Hydrated Prompt` → `LLM Execution Rounds` → `Final Output`).

A `live_turn` job opened on this route renders an `Incompatible Job Mode` error card instead of backtest telemetry.

## Studio Recent Backtests

`/recipes` loads `fetchRecentBacktestJobsFn()` alongside the optional `?recipeId=` recipe and passes the results to `RecentBacktestsStrip`, which renders a `Recent Backtests:` trough of up to five `voxel-btn` links to `/recipes/backtest/$jobId`. Each link is labeled with the short job id and either the net return (`+1.80%`) or `<STATUS> (<progress>%)`.

## Studio Live Paper Portfolio & Run Traces (`LiveRunsBlock`)

The `/recipes` route loader resolves `initialLiveState` through `fetchLivePortfolioAndRunsFn({ data: { recipeId } })` (failing soft to `null`) whenever `?recipeId=` is present, and `RecipeStudioPage` seeds `liveState` from it. `LiveRunsBlock` renders two stacked islands:

- **`Live Paper Portfolio`** — a `RecipePortfolioBlock` fed by the persisted `paper_cash` / `paper_positions` / `paper_trades`, with every open position enriched by the latest mark price.
- **`Live Run Traces`** — a `RunSelectorBar` of `Latest Turn` plus the last 10 persisted `live_turn` jobs (labeled by their `created_at` stamp), each rendering its stage prompt, per-round reasoning, tool calls & results, and full output through `TraceInspectorBlock`. Each stage header renders the fixed `LLM Call` label rather than a per-stage title.

When a live turn completes inline, `applyCompletedLiveRun()` first sets an optimistic portfolio built from the run's `updated_portfolio` + `signal_prices` (so the UI updates even if the refresh fails), then replaces it with the server-refreshed `LivePortfolioAndRuns` payload when that call succeeds.

## LLM Endpoint Failover (`apps/engine/recipes/llm_caller.py`)

Every LLM call in `push_runner.py` goes through `invoke_llm()` -> `default_llm_caller()` in `apps/engine/recipes/llm_caller.py`:

- **`llm_endpoints(openrouter_key, model)`** builds the ordered chain: OpenRouter (`https://openrouter.ai/api/v1`) when an explicit `openrouter_key` is supplied, otherwise `STRATA_BASE_URL` followed by `FREE_LLM_PROXY_URL` (`https://llm.clvg.uk/v1`).
- **`filter_recipe_tool_names(selected_tools, *, pit_mode)`** drops `RECIPE_DISABLED_TOOLS` (`web_search`), any name absent from `CANONICAL_TOOLS_REGISTRY`, and — when `pit_mode` is true — any name outside `PIT_SAFE_TOOL_NAMES`. The filtered list drives both the emitted `tool_schemas` and the runtime `allowed_tools` allowlist.
- **`run_tool_loop(client, model_id, prompt, tool_schemas, cutoff_date, as_of_utc=None, allowed_tools=None)`** runs up to `MAX_TOOL_ROUNDS = 5` Long-Only OpenAI-compatible tool-calling iterations followed by 1 forced tool-free synthesis turn (`_run_final_synthesis`) if the model did not emit a final answer, forwarding `cutoff_date` and `as_of_utc` into `core/llm/handlers/base.py:execute_tool()` and stripping `web_search` unconditionally (`filter_recipe_tool_names`) plus non-PIT tools when `pit_mode=True`. Captures `trace` (`rounds`, per-round `reasoning` / `thinking` text, `tool_calls` with args & results, and `forced_final_synthesis`).
- **`default_llm_caller(...)`** fails over across endpoints inside `async with AsyncOpenAI(...)` contexts (so the HTTP client is always closed) and re-raises if every endpoint fails.

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

- The Studio UI (`apps/web/src/features/recipes/pages/RecipeStudioPage.tsx`) shows one `LLM Call` card with no add or remove stage controls and no stage-title input. `PushStrategy.stages` is typed as the one-element tuple `[StrategyStage]`, and `starter-templates.ts` validates the imported JSON at load time.
- The engine schema (`apps/engine/recipes/push_schema.py`) is the source of truth. `PushStrategy.stages` is a required field with `min_length=1, max_length=1`; the `validate_exactly_one_llm_stage` validator raises `Push strategies must contain exactly one LLM stage for the MVP`, and `reject_prev_output_placeholder` rejects a `{{prev_output}}` prompt because a single-stage strategy has no previous output to reference.
- The scheduler (`apps/engine/recipes/runner.py`) uses `_is_valid_single_stage_graph()` in `enqueue_live_recipes()`. It validates with the same schema the worker uses, so a malformed or multi-stage live recipe is skipped with a `logger.warning` instead of being queued. Queueing it would leave a failed row behind on every hourly cycle.
- The save API (`apps/web/src/features/recipes/api/recipes-api.ts`) calls `assertSingleLlmStage()` and `assertNoPrevOutputPlaceholder()` inside `saveRecipe()` before any write.
- The enqueue API rejects a recipe the caller neither owns nor may see, rejects a multi-stage or malformed `graph_json` before it reaches the queue, and caps the number of open jobs per user.
- The database enforces it too. The `strategy_recipes_single_stage_check` constraint (`supabase/migrations/20261113190000_unpublish_legacy_multistage_recipe_template.sql`) rejects a `graph_json` whose `stages` array is not exactly one element on insert and update. It was added `NOT VALID` so the legacy row did not block it.

`{{prev_output}}` is rejected rather than left in place. The hydrator substituted it with an empty string, so a single-stage prompt that referenced a previous output silently reached the model truncated, and the Studio preview showed a token the run would not contain.

The legacy `2-Stage Research -> Trade Decision` template was unpublished by the same migration (`is_public = FALSE`, `is_template = FALSE`). It was removed from `packages/config/starter-recipes.json`, so the seeder never recreates it. The row is kept for auditability and is no longer publicly readable.

To bring multi-stage back, drop the `{{prev_output}}` rejection, relax the schema cardinality and the DB constraint, restore the stage controls in the UI, and re-add the second stage to the enqueue and scheduler guards.

## API Module Split & Fail-Closed Authorization

The Studio runs against the archive DB (`strategy_recipes` is publicly readable only for templates and public recipes while `recipe_execution_queue`, `recipe_user_quotas`, and `recipe_alerts_inbox` are service-role only). Server functions sit behind `/_authed` routes and fail closed (`Unauthorized`) when `user?.id` is absent (`ANONYMOUS_USER_ID` removed from user endpoints):

- **`api/recipes-api.ts`** — recipe persistence and job lifecycle: `saveRecipe` / `saveRecipeFn`, `enqueueRecipeJob` / `enqueueRecipeJobFn` (enforcing `assertQuotaAllowsJob` and dispatching `auto-go` / `strata-auto-go` via `free-llm-proxy`), `getRecipeJobStatus` / `getRecipeJobStatusFn`, `fetchRecipeRunDetail` / `fetchRecipeRunDetailFn` (including `queuePosition` and `globalActiveBacktests` for pending backtests), `fetchRecipeById` / `fetchRecipeByIdFn`, `fetchRecentBacktestJobs` / `fetchRecentBacktestJobsFn`, and `fetchPublicRecipes`.
- **`api/recipes-quota-api.ts`** — starter beta quotas (`1` concurrent backtest, `2` backtests/24h, `3` live turns/24h, `1` active `is_live` recipe, global queue cap `20`), `recipe_user_quotas` DB overrides, `cancelRecipeJob`, `toggleLiveSchedule`, `fetchUserRecipes`, and `fetchPublicShowcaseBacktest` (read-only `/recipes-demo` preview).
- **`api/recipes-studio-api.ts`** — alerts (`fetchRecipeAlerts`, `markAlertRead`), waitlist pledges (`submitWaitlistPledge`), `fetchLivePortfolioAndRuns` (hydrating `paper_cash`, `paper_positions` with latest mark prices from live runs/`recipe_intraday_bars`, `paper_trades`, and the last 10 `live_turn` jobs for `LiveRunsBlock`), and `previewStrategyPrompt` (via `prompt-builder.ts`).
- `RecipeJobStatus` includes `'pending' | 'processing' | 'completed' | 'failed' | 'cancelled'`.

## Client Types (`apps/web/src/features/recipes/types.ts`)

- `StrategyStage` — `{ id, blocks, selected_tools }`. The per-stage `title` field is gone; stages render as a fixed `LLM Call` label.
- `LLMExecutionTrace` — `{ forced_final_synthesis, rounds: [{ round, reasoning, assistant_text, tool_calls: [{ name, args, result }] }] }`.
- `LiveStageOutput` — `{ stage_id, prompt, output, tool_calls, ... }` (no `title`).
- `OpenPositionRecord` — `{ ticker, side?, shares, entry_price, entry_time, cost_basis?, current_price?, market_value?, unrealized_pnl_net?, unrealized_return_pct? }`, the enriched open-position shape shared by backtest snapshots, live paper portfolios, and `RecipePortfolioBlock`.
- `BacktestDayStep` — `{ day, day_index, status, signals, tool_calls, output_excerpt, full_output?, prompt?, trace?, day_pnl_net, trades_executed, trades_skipped }`, the per-slot trace rendered by `TraceInspectorBlock`.
- `BacktestResultData` — the accumulator snapshot shape, extended with `mode`, `days_completed`, `total_days`, `current_day`, `cash?`, `total_equity?`, `open_positions?`, and `day_steps` so a partial in-flight payload is a valid `BacktestResultData`. Note: `window_dates`, `days_completed`, and `total_days` intentionally retain their existing JSON keys while holding ET slot labels and slot counts (`30` slots for 10 trading days) for backwards schema compatibility across stored `result_json` rows, alongside preserving the `'5m' | '3h' | '1d'` `cadence` union on `PushStrategy`.
- `LiveRunResult` — `{ mode: 'live_turn', as_of_utc, slot_label?, stages, final_output, signals, executed_signals?, signal_prices?, updated_portfolio? }`.
- `LivePortfolioSnapshot` — `{ cash, total_equity, open_positions, trades }`.
- `LivePortfolioAndRuns` — `{ portfolio: LivePortfolioSnapshot, recentLiveRuns: RecipeJobRecord[] }`.
- `RecipeJobStatus` — `'pending' | 'processing' | 'completed' | 'failed' | 'cancelled'`.
- `RecipeJobRecord` — the queue row projection (`id`, `recipe_id`, `mode`, `status`, `progress_pct`, `provider`, `model`, `result_json`, `error_message`, timestamps).
- `RecipeRunDetail` — `{ job, recipeName, recipeCadence, queuePosition?, globalActiveBacktests? }`.
- `RecipeUserQuotaStatus` & `RecipeSummaryItem` — per-user beta starter/override limits (`maxConcurrentBacktests`, `dailyBacktestLimit`, `dailyLiveTurnLimit`, `maxLiveRecipes`, `globalPendingBacktests`, `globalQueueCap`) and owned recipe list projections.
- `RecipeSaveState` — `'idle' | 'saving' | 'saved' | 'error'`, exported from `RecipeNameField.tsx` and owned by `useRecipeDraft`.
- `ExecutionState` — a discriminated union of `idle` → `running` (`live_turn` | `backtest`) → `live_done` | `error`. The `error` variant now carries a `kind`:
  - `kind: 'navigation'` — the enqueue succeeded but router navigation to `/recipes/backtest/$jobId` rejected; carries a required `backtestJobId` so the alert can offer an `Open Backtest Run →` fallback link.
  - `kind: 'quota'` — the failure message matches a quota/limit guard (`isQuotaLimitMessage` matches `/limit reached|queue is currently full/i`); carries an optional `backtestJobId` (preserved from the current run or the prior backtest job) and surfaces a `Request Capacity` action.
  - `kind: 'execution'` — any other failure (e.g. a live-turn poll failure, `cancelled`/`failed` job, worker timeout); carries no `backtestJobId` so no backtest link is ever attached.

  `buildExecutionErrorState()` (`utils/live-studio-helpers.ts`) classifies the caught error, `resolvePreviousBacktestJobId()` recovers a prior backtest link from an existing navigation/quota error so a retry does not lose it, and `resolveBacktestButtonLabel()` derives the backtest caption from live quota. An `isBusy = isRunning || isTogglingLive || draft.isSaving` mutual-exclusion lock disables the execute, live-schedule toggle, and template-switch controls while any action is in flight. The former `backtest_done` state was removed because a backtest now navigates to its own route instead of rendering inline. See [[concepts/state-machines]].

## Related Pages

- [[entities/database]] — `recipe_*` / `strategy_recipes` tables, `price_history`, and `pop_next_recipe_job()`
- [[entities/secondary-minipc-edge]] — hosts the `recipe-worker` container in `docker/archive/docker-compose.secondary.yml`
- [[entities/free-llm-proxy]]
- [[entities/design-system]]
- [[concepts/zero-frontend-compute]]
- [[concepts/zero-lookahead-materialization]]
- [[concepts/state-machines]] — `RecipeJobStatus`, `RecipeSaveState`, and `ExecutionState` lifecycle registry
- `packages/config/recipe-naming.json` — shared naming contract (`defaultName`, `nameMaxLength`) between engine and web
