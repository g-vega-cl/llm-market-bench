---
tags: [recipes, push-v2, trading, backtest, news-corpus, voxel, studio]
category: entity
---

# Recipe Studio

The **Recipe Studio** (`/recipes`) is a 5-block push-based strategy builder where each strategy makes one LLM call. Inspired by Unsloth Studio Data Recipes, it lets researchers compose prompts, point-in-time news filters, historical memories filters, technical criteria, and immutable trade-signal schemas into that call, then backtest them over random 2-week point-in-time windows or run them live every 30 minutes during US market hours (09:30–16:00 ET), with an optional one-hour 5-minute **Turbo** boost once per ET trading day.

`/recipes` is **public**: a logged-out visitor gets `RecipeGalleryPage` (the template catalogue, block badges, prompt excerpts, and links to `/build` / `/recipes-demo`), while a signed-in visitor gets the full studio. Editors, saves, backtests, forks and live toggles stay auth-gated server-side. `/` is the public **recipe desk** (see [Public Recipe Surface & Homepage](#public-recipe-surface--homepage)), and the benchmark dashboard that used to be the homepage now lives at `/live-trader`.

## Architecture

1. **Storage & Corpus (`supabase/migrations/20261112103000_create_recipe_studio_v2.sql`, `supabase/migrations/20261114000000_create_recipe_intraday_bars.sql`, `supabase/migrations/20261116000000_recipe_beta_quotas_and_dual_lane.sql`, `supabase/migrations/20261116010000_strip_recipe_stage_title.sql`, `supabase/migrations/20261119000000_recipe_public_stats_and_concurrency.sql`, `supabase/migrations/20261119020000_recipe_desk_summary_feed_and_builder_usage.sql`, `supabase/migrations/20261120000000_add_recipe_turbo_mode.sql`)**
   - `public.recipe_news_corpus`: Point-in-time news articles imported from `stock-news-scraper` shards and synced from live market wires + `newsletter_snapshots`, tagged across canonical buckets with `search_tsv` and GIN indexes on `tickers`, `buckets`, and `search_tsv`.
   - `public.strategy_recipes`: Push v2 strategy configurations (`graph_json` with `version: "2.0-push"` and a one-item `stages` list), cadence (`5m`, `3h`, or `1d`, defaulting to `3h` for templates/backtests while live execution runs every 30m ET), the optional `turbo_expires_at` Turbo window (guarded by the `strategy_recipes_turbo_requires_live` CHECK so a paused or archived recipe can never hold one, and indexed by the partial `idx_strategy_recipes_turbo_active`), concurrency limits (`max_open_trades: 4`, `max_equity_pct_per_trade: 25.0`), and isolated paper ledgers (`paper_cash`, `paper_positions`, `paper_trades`, `paper_equity_curve`). Starter templates live in `packages/config/starter-recipes.json` and are seeded into `strategy_recipes`. `archived_at` (`supabase/migrations/20261117150000_add_recipe_archive.sql`) is the soft-hide marker used by "My Strategies" — see the soft-hide section below.
   - `public.recipe_intraday_bars`: Cached intraday bars (`(ticker, bar_time_utc)` PK) populated from `FMPProvider.get_hourly_history`, Alpaca IEX hourly bars, and live slot snapshots (`snapshot_live_intraday_bars`). `FMPProvider._has_hourly_range_coverage()` and `_ensure_slot_prices()` in `push_runner.py` validate weekday/slot coverage so partial SQLite slices never shadow full-window intraday bars with prior-day daily closes.
   - `public.recipe_execution_queue`: Priority queue with `heartbeat_at` lease tracking, `started_at`, `cancelled` status support, and a counted dual-lane atomic dequeue RPC `pop_next_recipe_job(target_mode TEXT DEFAULT NULL)` (10-minute `COALESCE(heartbeat_at, started_at)` stale recovery, `priority ASC` ordering of *pending* jobs only, and a counted guard that allows up to `c_max_processing_backtests = 3` concurrent backtests without blocking `live_turn` jobs). The Turbo migration adds the partial `idx_recipe_queue_live_turn_created` index and the unique partial `idx_recipe_one_open_live_turn_per_recipe`, which makes two open `live_turn` jobs for the same recipe unrepresentable (surplus pending rows are cancelled before the index is built).
   - `public.recipe_user_quotas`: Per-user starter/tier quota overrides (`max_concurrent_backtests: 1`, `daily_backtest_limit: 2`, `max_live_recipes: 3`, `last_turbo_et_date` enforcing 1 Turbo boost per ET trading day via `activate_recipe_turbo(p_user_id, p_recipe_id)`; the legacy `daily_live_turn_limit` column survives for old overrides but is no longer read, displayed, or enforced).
   - `public.recipe_alerts_inbox`: In-app trade alert delivery table.
   - `public.recipe_waitlist_pledges`: Early supporter pledges for future dedicated GPU compute tiers.
   - `public.recipe_public_stats` / `public.recipe_desk_summary` / `public.recipe_desk_feed`: Runner-materialised board, header, and same-day tape that the public desk reads (see [Public Recipe Surface & Homepage](#public-recipe-surface--homepage)).
   - `public.recipe_builder_usage` + `consume_builder_compile(p_user UUID)`: atomic per-user daily metering of `/build` compiles (25/day), service-role only. See [[concepts/recipe-builder-usage]].
   - `public.recipe_ops_events`: durable scheduler telemetry (enqueue counters, high-skip-ratio alarms, paid-provider fallbacks). See [[concepts/recipe-ops-telemetry]].
   - **Stage-title cleanup (`20261116010000_strip_recipe_stage_title.sql`)**: removes the obsolete per-stage `title` key from stored `graph_json` for single-stage graphs. The migration is scoped with `CASE`-gated `jsonb_typeof`/`jsonb_array_length` checks (boolean subexpressions are not evaluated left to right, and `strategy_recipes_single_stage_check` was added `NOT VALID`, so a row whose `stages` is an object or scalar was never scanned and must not abort the migration). The legacy unpublished two-stage row cannot be updated at all — the single-stage CHECK rejects any update that leaves two stages in place — so its inert title is left as audit history. `recipe_execution_queue.result_json` rows are historical run telemetry and are intentionally untouched. No RLS or GRANT changes.

2. **Engine Processing (`apps/engine/recipes/`)**
   - `push_schema.py`: Pydantic models for Push v2 (`PushStrategy`, `StrategyStage`, `PromptBlock`, `NewsBlock`, `MemoriesBlock`, `TechnicalsBlock`, `OutputFormatBlock`). `PushStrategy` requires exactly one stage and defaults to `cadence: "3h"`. `StrategyStage` carries only `id`, `blocks`, and `selected_tools` — the per-stage `title` field has been removed, so stages render as a fixed "LLM Call" badge. Recipe naming is governed by a shared contract in `packages/config/recipe-naming.json` (`defaultName`, `nameMaxLength`), loaded once via the `lru_cache`-memoized `recipe_naming()` helper (raising `RuntimeError` when the file is missing or invalid) and exposed as `DEFAULT_STRATEGY_NAME` / `RECIPE_NAME_MAX_LENGTH`. `PushStrategy.name` is `Field(default=DEFAULT_STRATEGY_NAME, max_length=RECIPE_NAME_MAX_LENGTH)` with a `mode="before"` `normalize_name` validator that strips and caps the value and falls back to the default for blank or non-string input — `strategy_recipes.name` is `TEXT NOT NULL` and `graph_json` is free-form JSON, so a stored `name: null` must normalize instead of failing worker validation. The web layer mirrors the same contract via `recipes-validators.ts` (`normalizeRecipeName`).
   - `push_hydrator.py`: Point-in-time filtering and stage prompt hydration (`fetch_push_context_batch`, `hydrate_stage_prompt`, `build_news_excerpt`), injecting `[Current Portfolio State]` immediately before the Long-Only `OutputFormatBlock`.
   - `portfolio_engine.py`: Shared Long-Only stateful portfolio simulator (`DEFAULT_CONCURRENCY_CONFIG = {"max_open_trades": 4, "max_equity_pct_per_trade": 25.0}`, `PortfolioState`, `apply_portfolio_step`, `enrich_open_positions`, `format_portfolio_prompt_block`) used symmetrically by live turns and backtests. Positions hold across sessions and days until an explicit `EXIT` (or `SELL` on a held LONG) or `END_OF_WINDOW`. Entries size to **whole shares only** (`shares = int(alloc // fill_px)`), charge the actual spend as `cost_basis` rather than the full notional allocation, and record an `ALLOCATION_BELOW_ONE_SHARE` skip when the allocation cannot buy a single share. `enrich_open_positions(state, prices, slippage_bps=...)` attaches `current_price`, `market_value`, `unrealized_pnl_net` (net of round-trip slippage), and `unrealized_return_pct` to every open position so both the live and backtest payloads carry mark-to-market telemetry. See [[concepts/recipe-portfolio-engine]].
   - `alpaca_mirror.py`: Fire-and-forget mirror of live-turn fills to the shared Alpaca paper account. `position_snapshot()` / `compute_fills()` diff the book before and after `apply_portfolio_step()`, `mirror_recipe_fills()` submits DAY market orders tagged `recipe-<id8>__<TICKER>__<BUY|SELL>__<slot UTC>`, and `record_mirror_status()` stamps `alpaca_status` / `alpaca_order_id` / `alpaca_submitted_at` onto the open position or closed trade dict. SELL legs are capped to the shares the broker actually holds and marked `SKIPPED_NO_POSITION` when flat; broker errors log and record `ERROR` without ever blocking the Supabase ledger write. `_build_client()` returns `None` when `ALPACA_ENABLED` is false or credentials are absent, so the mirror is inert in unconfigured environments. See [[concepts/recipe-portfolio-engine]].
   - `intraday_bars.py`: 3x/day ET slot expansion (`TRADING_SLOTS_ET = ((9, 30), (12, 30), (15, 30))`, used only for **backtest** slot stepping, `CORPUS_MIN_DATE = "2026-02-09"`), multi-source hourly bar resolution (`recipe_intraday_bars` -> `FMPProvider.get_hourly_history` -> Alpaca IEX hourly -> `price_history` fallback), upsert caching, and live slot bar capture (`snapshot_live_intraday_bars`). Live scheduling does **not** use `TRADING_SLOTS_ET` — it uses the runner's 14-slot `LIVE_SLOTS_ET`.
   - `pit_tools.py`: Strict point-in-time tool dispatcher invoked by `core/llm/handlers/base.py` only when `pit_mode=True` or `as_of_utc` is set (so standalone historical analysis passing `cutoff_date` alone stays on `tools.py`), enforcing `<= as_of_utc` / strict `< cutoff_day` daily bar bounds, `recipe_news_corpus` article fallback in `_pit_fetch_newsletter`, existing-column `market_feeling` reads (`primary_concern, secondary_concern`), and `strict_pit=True` fail-closed `tools/technicals.py` execution (zero `MarketDataManager.get_history` fallback). Exports `PIT_SAFE_TOOL_NAMES` matching `_build_pit_dispatch`; live-only tools (`web_search`, run_stock_screener, option chains, etc.) fail closed.
   - `llm_caller.py`: Extracted LLM failover caller (`default_llm_caller`, `llm_endpoints`, `run_tool_loop`, `invoke_llm`, `filter_recipe_tool_names`). Routes `auto-go` strictly to `FREE_LLM_PROXY_URL` (`https://llm.clvg.uk/v1`, excluding raw local Strata so live runs never contend with backtests), forwards per-job `model` cleanly through `invoke_llm`, and propagates `cutoff_date`, `as_of_utc`, and `pit_mode=bool(cutoff_date or as_of_utc)` inside `async with AsyncOpenAI(...)` contexts. Enforces `RECIPE_DISABLED_TOOLS` (`web_search`) and PIT/stage allowlists (`allowed_tools`) both in schemas and at dispatch time in `_execute_round_tools` (rejecting non-dict JSON args safely). Runs up to `MAX_TOOL_ROUNDS = 5` tool iterations followed by 1 forced tool-free `_run_final_synthesis` pass if exhausted, separating `thinking`/`reasoning_content` cleanly from `output` (never falling back to raw `thinking` blocks) while capturing `trace` (`rounds`, tool call args + results, `forced_final_synthesis`). The resolved provider model is persisted per run so the public board can state which model produced a result.
   - `push_runner.py` & `backtest_accounting.py`: Single-call live execution (`run_push_live`, propagating `prompt`, `trace`, and `enrich_open_positions`-enriched `paper_positions`; each stage result carries `stage_id`, `prompt`, `output`, and `tool_calls` — no `title`) and backtesting (`run_push_backtest`) across 10 trading days (30 ET slots) sampled from `>= CORPUS_MIN_DATE`. `run_push_live` snapshots positions before the step, mirrors the turn's fills through `mirror_recipe_fills()`, stamps the broker outcome via `record_mirror_status()`, and returns the per-fill outcome list as `alpaca_fills` alongside `executed_signals` and `updated_portfolio`. `BacktestAccumulator` wraps `PortfolioState` + `enrich_open_positions`, tracks `refreshed_bar_days` to backfill partial intraday bar arrays cleanly, persists `prompt`, `trace`, and unclipped `full_output` on `day_steps`, honors mid-run `is_cancelled()` checks, and streams slot-by-slot snapshots via `on_progress`. Backtests never mirror to Alpaca.
   - `worker.py`: `async_process_next_recipe_job(target_mode=...)` / `process_next_recipe_job(target_mode=...)` returning `JobOutcome` (`"EMPTY"`, `"COMPLETED"`, `"FAILED"`, `"CANCELLED"`), updating `heartbeat_at` on each slot, resolving `auto-go` for **both** lanes, skipping completion writes if cancelled mid-run, persisting live portfolio state + `trial_count` under optimistic CAS, and depositing alerts into `recipe_alerts_inbox` strictly for filled `executed_signals`.
   - `runner.py`: MiniPC dual-lane daemon (`python3 -m recipes.runner --loop`) running `_live_lane_loop` (a 5-second poll around `run_live_lane_tick`) alongside `_backtest_lane_loop` (counted guard, `RECIPE_BACKTEST_CONCURRENCY` default `3`, all on the free proxy's `auto-go`) so backtests never block live execution. The live lane evaluates, in order: a due 30-minute ET market slot (`LIVE_SLOTS_ET`, 14 slots `09:30`–`16:00`, Mon–Fri excluding US holidays including Good Friday) handled by `run_scheduled_slot`; the throttled 5-minute `enqueue_turbo_recipes` path (`TURBO_POLL_INTERVAL_SECONDS = 30`, `TURBO_INTERVAL_SECONDS = 300`) for bots with an unexpired `turbo_expires_at`; and an always-on `live_turn` drain. Per-tick throttles live in a `LiveLaneState` dataclass (`last_slot_key`, `last_news_sync_utc`, `last_turbo_poll_utc`, `last_stats_refresh_utc`), with `NEWS_SYNC_MIN_INTERVAL_SECONDS = 300` and `PUBLIC_STATS_MIN_INTERVAL_SECONDS = 60`. A failed scheduled slot is retried on the next tick instead of advancing `last_slot_key`. `drain_lane(sb_client, mode=..., max_jobs=..., concurrency=...)` processes jobs serially by default (`concurrency=1`) so tests and one-off drains never fan out accidentally; the daemon passes `concurrency=LIVE_TURN_CONCURRENCY` (`RECIPE_LIVE_CONCURRENCY` env var, default `10`) for the `live_turn` lane, running many users' recipes in parallel behind an `asyncio.Semaphore`. Exceptions raised by a concurrent task are logged via `logger.exception` and do not abort the remaining tasks. Live `live_turn` inserts go through `_insert_live_jobs_idempotent`, which tolerates `23505` duplicate-index errors under replica lag. See [[concepts/recipe-turbo-mode]] and [[concepts/recipe-backtest-concurrency]].
   - `public_stats.py`: `parse_equity_curve`, `return_pct`, `spy_return_pct`, `build_last_action`, `build_public_stats`, and `refresh_public_stats(client)` — rebuilds `recipe_public_stats`, `recipe_desk_summary`, and `recipe_desk_feed` after each lane drain. Its queue reads are paginated (`_fetch_last_results` in 500-row pages, `_count_runs_today` in 1,000-row pages) so PostgREST row caps can never silently truncate the board. See [[concepts/recipe-public-stats]].
   - `news_corpus.py` & `import_news_cli.py`: Bucket derivation (`derive_article_buckets`), JSONL shard importer, and `sync_live_news_to_corpus()` reusing `analysis/intraday_news_aggregator.py` + `newsletter_snapshots`.

3. **Presentation & Studio UI (`apps/web/src/features/recipes/` & `routes/recipes/`)**
   - `/recipes` itself is public (`apps/web/src/routes/recipes/index.tsx`): an anonymous visitor gets `RecipeGalleryPage`, a signed-in visitor gets the studio. The route loader short-circuits to empty loader data when `context?.user?.id` is absent, so three auth-gated server functions are never called for a guest. The run surfaces stay auth-gated under `/_authed` (`apps/web/src/routes/_authed/recipes/backtest/$jobId.tsx` and `apps/web/src/routes/_authed/recipes/live/$recipeId.tsx`) preserving return redirect paths through `shared/auth/redirect.ts` and `routes/auth.callback.tsx`, paired with a public read-only showcase preview route (`/recipes-demo`, linked from `/lab`).
   - Built with Cheddar Voxel tokens (`bg-voxel-canvas`, `bg-voxel-surface`, 0px corners, 2px directional bevels, recessed `.voxel-trough` slots).
   - Studio (`/recipes`): `RecipeGuideAndQuotaBlock.tsx` (`FREE BETA STARTER` quota strip + in-flow backtest/live guides + `SavedRecipesStrip`, plus the top alert slot and `RecentBacktestsStrip`), `RecipeNameField.tsx`, `StudioActionBar.tsx` (with shared `TurboButton.tsx`), `StageBuilder.tsx`, `BlockEditors.tsx`, `ToolPicker.tsx` (`web_search` removed from `CURATED_TOOLS`; `run_stock_screener` tagged `Live only`), `PromptVisualizer.tsx`, `RecipePortfolioBlock.tsx`, `TraceInspectorBlock.tsx`, `LiveSwitchConfirmation.tsx` (inline trough confirming a live-recipe switch), `RecipeAlertsInbox.tsx`, `WaitlistPledgeModal.tsx`, `StudioHeader.tsx` (heading + name field + save), `TemplatePickerBar.tsx` (template buttons + the selected template's description), `api/recipes-api.ts` (recipe lifecycle: public read, save, queue), `api/recipe-jobs-api.ts` (queue/run reads: status, run detail, recent jobs), `api/archive-recipe.ts` (soft-hide), `api/fork-recipe.ts` (fork), `api/recipes-quota-api.ts` (including `activateRecipeTurboFn`), `api/recipes-studio-api.ts`, and `utils/market-hours.ts`. Supports the `Enable Live (30m)` toggle, the 1x/day `⚡ Turbo (5m x 1h)` boost, and free-proxy `auto-go` dispatch for both backtests and live turns.
   - **Quota strip** (`RecipeGuideAndQuotaBlock.tsx`): renders `Backtests: N/2 left today`, `Live bots: N/3`, and `Global Backtest Queue: N/20`. The former `Live Turns: N/3 left today` line was removed — regular live turns are unbounded per user across the 30-minute market-hours slots (up to 3 live bots), and Turbo is capped at 1 activation per ET trading day per user. `SavedRecipesStrip` badges each live chip `LIVE 30m` (success) or `TURBO 5m` (accent) based on `isTurboActive(item.turbo_expires_at)`.
   - **Recipe name field (`Recipe Name`) + explicit save**: `RecipeNameField.tsx` renders the `Label` + `Input` pair plus a `Save Recipe` button, and saving is never implicit — the button only enables while the name or graph differs from what the server holds (`persistedName` / `isGraphDirty`), shows `Saving...`, then settles on `Saved` with the server-returned name, and surfaces a save failure inline via `role="alert"` (with `aria-invalid` / `aria-describedby` wiring on the input and an `aria-live` status region for screen readers). Backtest and Enable Live still persist through the shared `persistActiveStrategy`, which adopts `saved.name` from the response. The studio action row lives in `StudioActionBar.tsx` (Waitlist, Alerts with unread count, Enable Live (30m) toggle, `TurboButton` when live, Backtest — each button manages its own `isLoading` state; there is no global `isBusy` lock). When the open recipe is live, `StudioActionBar` also renders a `Live Status →` `Link` to `/recipes/live/$recipeId` and the Turbo control, wired to `RecipeStudioPage.handleActivateTurbo` (`activateRecipeTurboFn` → update `turbo_expires_at` on the local summary → `turboUsedToday: true` → `refreshQuota()`). `packages/config/recipe-naming.json` (`defaultName`, `nameMaxLength`) is the shared contract for both sides: `normalizeRecipeName()` in `api/recipes-validators.ts` and the `mode="before"` `field_validator("name")` in `push_schema.py` both read it, trimming, capping, and falling back to `Untitled Strategy` because `strategy_recipes.name` is `TEXT NOT NULL` and `graph_json` may hold a null name. `saveRecipe` applies `normalizeRecipeName(recipe.name)` before the insert. Running a recipe still persists the current draft as a side effect of queueing the job; the header button is the explicit path. `saveRecipe` also deletes only the obsolete `title` key from `stages[0]` (preserving any future stage field) so a stale client cannot copy it back into `graph_json`. Selecting a starter template resets the field to that template's name. There is no per-stage title field: the single stage is labelled `LLM Call` in `StageBuilder.tsx`, `PromptVisualizer.tsx`, and live run traces.
   - **Draft adoption from the builder**: `RecipeStudioPage` reads a browser-parked draft (`loadLocalDraft()`) inside a `useEffect` guarded by a `importedRef` and the presence of `initialStrategy`, calls `draft.resetTo(local.strategy)` and then `clearLocalDraft()`. Reading localStorage during render would make the first client paint differ from SSR, hence the effect.
   - **Single top alert slot (`StudioAlertSlot`)**: Rendered once between the action row and the quota strip, backed by the pure `RecipeExecutionAlert` block (danger-bordered, `role="alert"`). It surfaces at most one failure at a time — a `BacktestError` takes precedence over a `scheduleError` (a failed Turbo activation routes through `applyScheduleError`) — and offers an `Open Backtest Run →` link when a backtest job id is available (the link is preserved across retries: a later quota failure keeps the earlier job id visible), plus a `Request Capacity` button (opens the `WaitlistPledgeModal`) when the failure is quota-related. Because both `handleBacktest` and `handleToggleScheduledLive` funnel errors through this single slot, a stale backtest error is cleared before a schedule toggle, and a schedule failure never leaves a stale backtest error visible. A failed *save* is deliberately excluded: `RecipeSaveError` is reported inline next to the name field instead, so the same failure is never shown twice.
   - **Alerts inbox (`RecipeAlertsInbox.tsx`)**: Each alert renders as a `RecipeAlertCard` (extracted sub-component) with an `ACTION_COLOR_SCHEME` map — `BUY` → `success`, `EXIT` → `warning`, `SELL` → `danger`, `HOLD` → `danger`. The card shows the action/ticker badge, the recipe name, the timeframe, the created-at stamp, the entry price and optional target / stop levels, and the reason trough. When the alert carries a `recipe_id`, the recipe name is a `Link` to `/recipes/live/$recipeId` so a user can jump from an alert straight to that recipe's live status page; when `recipe_id` is absent it renders as plain text. Unread alerts keep a `Mark Read` button wired to `onMarkRead`.
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

## Starter Template Catalog

`packages/config/starter-recipes.json` holds five templates. The studio renders one button per template (`STARTER_RECIPES` in `apps/web/src/features/recipes/starter-templates.ts`) and prints the selected template's `description` on its own line beneath the row. `starter-templates.ts` throws on a duplicate `name` because `seed_starter_recipes` keys template identity on the name. The public gallery (`RecipeGalleryPage`) and the recipe desk render the same `STARTER_RECIPES` list.

| Template | Capability it demonstrates |
| --- | --- |
| `Trump & Chips News Momentum` (`3h`) | News keywords + memories category + P/E and RSI screens in one call — the canonical five-block recipe. |
| `Claude Agent Portfolio Mirror` (`3h`) | Mirrors the live Claude agent portfolio (`claude-haiku-5-5`, i.e. `MODELS.ANTHROPIC`; the retired `claude-haiku-4-5` rows are labelled "Claude Haiku 4.5"): tool-first research (`get_stock_quote` → `get_price_history` → `get_ticker_news` → `get_key_metrics` → `get_technical_indicators`), explicit thesis-intact/broken review of every open position, and the same Long-Only 4 × 25% sizing the agent portfolios trade. |
| `Quality Value Screener` (`3h`) | No news block at all — the technicals block alone drives selection (P/E, free cash flow, MACD, 52-week position), proving a fundamentals-only strategy is valid. |
| `Contrarian Sentiment Fader` (`3h`) | `get_market_feeling` barometer + oversold RSI mean reversion, with `POST_MORTEM` memories for how similar panics resolved. |
| `Earnings Catalyst Hunter` (`3h`) | `get_earnings_history` surprise streaks + per-ticker news, trading post-print drift instead of the headline spike. |

Every template declares `cadence: "3h"` on purpose: `enqueue_live_recipes` has no cadence predicate, so a scheduled recipe fires at every 30-minute ET market slot regardless of what `cadence` says. Publishing a `1d` template would advertise a schedule the runner does not honour. Each template must validate as a single-stage Push v2 graph (`PushStrategy.model_validate`), which `recipes/test_runner.py` asserts for all five. `RecipeGalleryPage` labels each card `Live: 30m · Backtest: <cadence> · one LLM call`.

Seeding is insert-only keyed on `name`, so a template whose text or cadence changes after seeding keeps its old row. After editing the JSON, diff the DB against the file and correct drift deliberately:

```sql
SELECT name, cadence, graph_json->>'cadence' AS g_cadence,
       description = graph_json->>'description' AS desc_ok
FROM strategy_recipes WHERE is_template ORDER BY name;
```

## My Strategies: Soft-Hide (Never Delete)

"My Strategies" (`SavedRecipesStrip` in `apps/web/src/features/recipes/components/RecipeGuideAndQuotaBlock.tsx`) lists every strategy the server returned (there is deliberately no display cap — a hidden seventh row would be unremovable), and every chip carries a remove control (`aria-label="Remove <name> from My Strategies"`) that shows `Button[isLoading]` while the request is in flight. A live strategy chip (`RecipeSummaryItem.is_live`) also renders a `Live Status →` `Link` to `/recipes/live/$recipeId`. Removal is driven by `useStrategyRemoval` (`apps/web/src/features/recipes/utils/use-strategy-removal.ts`): a confirmed mutation — no optimistic cache rewrite, no rollback machinery — that keeps the chip in place and surfaces a failure in-flow via `role="alert"`. Only one removal is in flight at a time.

Removal is a `strategy_recipes.archived_at` stamp, never a `DELETE`:

- `archiveRecipe` (`apps/web/src/features/recipes/api/archive-recipe.ts`) fails closed on an unreadable row, refuses a recipe owned by another user, then writes `archived_at`, `is_live = false`, and `turbo_expires_at = null` so the scheduler stops creating new turns and any Turbo window is cleared in the same update. `updated_at` is deliberately untouched — hiding is not a content edit and bumping it would trip the showcase publisher's graph-drift guard.
- The same call cancels the recipe's `pending`/`processing` queue rows (`status = 'cancelled'`, `cancelled_at`), so a queued turn cannot outlive the removal. A failed cancel is logged, never rolled back into an un-removal: the hide already stands. The worker's mid-run `is_cancelled()` check stops a turn that was already executing.
- `fetchUserRecipes` filters `.is('archived_at', null)`, so the chip disappears; the row, its paper ledger (`paper_cash` / `paper_positions` / `paper_trades` / `paper_equity_curve`), its `recipe_execution_queue` history, and its `recipe_alerts_inbox` rows all stay attached. `fetchPublicRecipes` and the showcase fallback in `fetchPublicShowcaseBacktest` apply the same filter, and `publish_showcase` refuses a run whose recipe carries `archived_at`.
- `enqueue_live_recipes` and `_fetch_active_turbo_recipes` in `apps/engine/recipes/runner.py` both select `.eq('is_live', True).is_('archived_at', 'null')`, so a hidden strategy can never re-enter the live or Turbo queue even if a stale `is_live` flag survives.
- **Restore is explicit.** `saveRecipe` only clears `archived_at` when the caller passes `{ restore: true }`, which only the header `Save Recipe` button does (`RecipeStudioPage` → `persistActiveStrategy({ restore: true })`). The persist that precedes Backtest or a schedule toggle never restores. `enqueueRecipeJob` and `toggleLiveSchedule` fail closed on an archived row with "removed from My Strategies; save it to restore".
- Removing the strategy that is currently open resets the draft to the first starter template, so no hidden row stays in the editor for a later persist to act on.
- Forking an archived recipe the caller owns is refused with the same "removed from My Strategies" message.

## Pausing a Live Schedule

`toggleLiveSchedule(recipeId, isLive, userId)` writes `is_live` plus `updated_at`, and on a **pause** (`isLive === false`) additionally clears `turbo_expires_at` and cancels that recipe's `pending` `live_turn` queue rows (`status = 'cancelled'`, `cancelled_at = now`). A cancel failure is logged with `console.error` and intentionally not rolled back — the pause already stands. The `strategy_recipes_turbo_requires_live` CHECK backstops any path that tries to leave a Turbo window on a paused recipe. `upsertSavedRecipeSummary` mirrors this locally by dropping `turbo_expires_at` whenever the summary stops being live.

## Fork (Copy a Recipe Into Your Account)

`forkRecipe(recipeId, userId)` in `apps/web/src/features/recipes/api/fork-recipe.ts` (exposed as `forkRecipeFn`, `POST`, auth-gated) is the cheapest path from "that looks interesting" to "this is mine": it copies a public, template, or own recipe into a new row owned by the caller, so the visitor lands in the studio with a working five-block graph and changes one thing.

- **Read** — selects `id, user_id, name, description, cadence, graph_json, is_public, is_template, archived_at` from `strategy_recipes`; a missing row throws `Recipe not found`.
- **Authorization** — allowed when the caller owns the row, or when `is_public` or `is_template` is true; otherwise `Unauthorized: cannot fork a private recipe`.
- **Archived** — an owned row carrying `archived_at` is refused (restore instead of forking).
- **Graph validation** — `assertSingleLlmStage()` and `assertNoPrevOutputPlaceholder()` run before any write, so a legacy or malformed public graph is never copied into a queue row that would burn a run attempt every slot.
- **Insert** — `name = normalizeRecipeName('Copy of ' + source.name)`, `user_id = caller`, `is_public: false`, `is_template: false`, `is_live: false`, `concurrency_config = { max_open_trades: 4, max_equity_pct_per_trade: 25.0 }`, `paper_cash: 10000`, and empty `paper_positions` / `paper_trades` / `paper_equity_curve`. A fork therefore **never** inherits live scheduling, publication state, or a Turbo window.
- **Callers** — the recipe desk `Fork` button (`handleFork` in `routes/index.tsx`) navigates to `/recipes?recipeId=<new id>` on success and redirects an unauthorized caller to `/login?redirect=/recipes`.

Regression coverage: `apps/web/src/features/recipes/api/fork-recipe.test.ts` asserts the `Copy of` name, caller ownership, `is_live`/`is_public` false, `paper_cash` 10000, refusal of a private foreign recipe, refusal of an archived own recipe, and rejection of a malformed graph with zero inserts.

## Draft & Explicit Save State Machine (`useRecipeDraft`)

`apps/web/src/features/recipes/utils/use-recipe-draft.ts` owns the studio's draft and explicit-save lifecycle. It exposes `strategy`, `isDirty`, `isSaving`, `saveState` (`RecipeSaveState`), `saveError`, `setName`, `setStage`, `resetTo`, and `save(persist)`.

Three invariants keep edits from being lost or misattributed:

1. **Revision guard** — `draftRev` advances on every edit (`setName`, `setStage`, `resetTo`). A response that lands against a newer revision adopts the saved row `id` but never overwrites the local draft, and `saveState` settles to `idle` rather than `saved` so the field still reads as dirty.
2. **Flight-scoped `isSaving`** — cleared only when the request settles, never by an edit, so the Save Recipe button stays disabled for the whole flight.
3. **Generation guard** — `generation` advances when the draft is replaced by a template or an imported local draft. A response from an older generation is ignored entirely, so it cannot stamp the old row id onto a fresh template.

`save(persist)` shares the in-flight promise when the draft revision is unchanged, so a duplicate click cannot insert the recipe twice. When the draft advanced mid-flight, it chains a second persist after the first settles, so a queued run always enqueues the edited graph rather than the pre-edit snapshot. Failures are rethrown as `RecipeSaveError`, which `RecipeStudioPage` uses to route the message to the inline `RecipeNameField` alert instead of the top `StudioAlertSlot`.

## 30-Minute Market-Hours Runner Daemon (`apps/engine/recipes/runner.py`)

`recipes.runner` is the MiniPC-hosted scheduler and queue worker that keeps the corpus fresh, captures live intraday bars, and drains the execution queue. It is deployed as the `recipe-worker` container in `docker/archive/docker-compose.secondary.yml` (512M memory limit, with `ARCHIVE_DB_URL: http://archive-proxy:80` so `tool_audit.py` writes directly to `tool_execution_logs`; see [[entities/secondary-minipc-edge]]).

### Cycle Functions

- **`due_trading_slot(now_utc, last_slot_key)`** — aligns live cycles cleanly to `LIVE_SLOTS_ET` (14 half-hour slots from `09:30` through `16:00` `America/New_York`, Monday–Friday, excluding the rule-based US holiday fallback **including Good Friday** computed via the Anonymous Gregorian Easter algorithm) within a 20-minute window (`SLOT_WINDOW_SECONDS = 1200`) and deduplicates by `<YYYY-MM-DDTHH:MM>` key. `is_us_market_hours_et(now_utc)` gates the Turbo path. `enqueue_turbo_recipes(sb_client, now_utc=...)` runs between slots during market hours for bots with `turbo_expires_at > now_utc` at 5-minute spacing (`TURBO_INTERVAL_SECONDS = 300`). See [[concepts/recipe-turbo-mode]].
- **`seed_starter_recipes(sb_client)`** — loads `packages/config/starter-recipes.json` and idempotently inserts any template whose `name` is not already present among `is_template = true` rows (`.limit(100)` capped existence check). Seeded rows carry `user_id = ANONYMOUS_USER_ID` (`00000000-0000-0000-0000-000000000000`), `is_public = true`, `is_template = true`, `is_live = false`, `cadence = '3h'`, and `DEFAULT_CONCURRENCY_CONFIG` (`max_open_trades: 4`, `max_equity_pct_per_trade: 25.0`). Returns the number inserted.
- **`enqueue_live_recipes_with_stats(sb_client, *, slot_start_utc=None, recent_turbo_cutoff_utc=None)`** — pages every `is_live = true` recipe, skips any that already have a `pending`/`processing` queue row, skips any that ran a Turbo turn inside the recent cutoff (counted as `skipped_recent_turbo`, not `skipped_open`), validates each candidate through `_is_single_stage_push_v2_graph()`, inserts surviving jobs in a batch through `_insert_live_jobs_idempotent` (`priority = 1`), and returns the counter dict (`seen`, `enqueued`, `skipped_open`, `skipped_invalid_graph`). See [[concepts/recipe-ops-telemetry]].
- **`run_live_lane_tick(sb_client, now_utc, state)`** — one poll tick over a `LiveLaneState` dataclass: a due 30-minute slot runs `run_scheduled_slot`; otherwise the Turbo enqueuer runs at most once per `TURBO_POLL_INTERVAL_SECONDS` (30s) during market hours, with a news sync only when at least one Turbo job was enqueued and `NEWS_SYNC_MIN_INTERVAL_SECONDS` (300s) has elapsed; the `live_turn` lane is always drained, refreshing public stats at most once per `PUBLIC_STATS_MIN_INTERVAL_SECONDS` (60s) when anything ran. A failed scheduled slot does not advance `last_slot_key`, so the next tick retries it.
- **`drain_lane(sb_client, mode, max_jobs=MAX_JOBS_PER_CYCLE, concurrency=None)`** — drains queued jobs for a single execution lane. Serial by default (`concurrency=1`) so tests and one-off drains never fan out accidentally. When `concurrency > 1`, it builds an `asyncio.Semaphore(concurrency)` and `asyncio.gather`s `max_jobs` `_process_one()` tasks, logging any per-task exception via `logger.exception` without aborting the remaining tasks. The daemon passes `concurrency=LIVE_TURN_CONCURRENCY` for the `live_turn` lane and `RECIPE_BACKTEST_CONCURRENCY` (default `3`) for the backtest lane.
- **`run_hourly_cycle(sb_client, as_of_utc=None, max_jobs=25)`** — runs `sync_live_news_to_corpus()`, rebuilds the public stats tables via `refresh_public_stats()`, then `enqueue_live_recipes()`, then drains queue jobs. A stats-refresh failure is caught and logged — a board write must never abort the trading cycle.
- **`_run_daemon_loop(sb_client)`** — seeds templates once, then runs the live and backtest lanes concurrently; the live lane snapshots live quotes into `recipe_intraday_bars` via `snapshot_live_intraday_bars()` on each scheduled slot and polls the queue every `POLL_INTERVAL_SECONDS` (5s).

### Concurrency Configuration

| Setting | Source | Default | Meaning |
| :--- | :--- | :--- | :--- |
| `LIVE_TURN_CONCURRENCY` | `RECIPE_LIVE_CONCURRENCY` env var | `10` | Bounded parallelism for the `live_turn` lane. Passed as `concurrency=` into `drain_lane` by `_live_lane_loop`. |
| `RECIPE_BACKTEST_CONCURRENCY` | env var | `3` | Bounded parallelism for the `backtest` lane; matches the database's counted guard (`c_max_processing_backtests = 3`). |
| `TURBO_INTERVAL_SECONDS` | module constant | `300` | Minimum spacing between Turbo turns for one bot. |
| `TURBO_POLL_INTERVAL_SECONDS` | module constant | `30` | How often the live lane polls active Turbo bots. |
| `MAX_JOBS_PER_CYCLE` | module constant | `25` | Upper bound on jobs drained per lane per cycle. |
| `POLL_INTERVAL_SECONDS` | module constant | `5` | Off-slot queue poll cadence. |

Three concurrent backtests are allowed by the counted guard inside `pop_next_recipe_job` (replacing the old single-`processing` unique index), and the lane passes `max_jobs=3`. A recipe's `live_turn` lane is separately capped at one open job by the unique partial index `idx_recipe_one_open_live_turn_per_recipe`. See [[concepts/recipe-backtest-concurrency]] and [[concepts/recipe-turbo-mode]].

### CLI

```sh
# Continuous daemon (30m slots + 5m Turbo + 5s queue polling)
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
2. **Newsletter snapshots (`_collect_newsletter_records`)** — queries `newsletter_snapshots` for rows newer than `as_of_utc - lookback_hours` (max 50) and normalizes each as `article_id = "nl_<clean_source_id>_<YYYY-MM-DD>"`, `source_family = "newsletter"`, `date_precision = "newsletter_date"`. Any pre-existing `nl_` prefix on the snapshot `source_id` is stripped (`removeprefix("nl_")`) before composing the id and the archive URL (`https://benchify.app/newsletters/<clean_source_id>`), so a snapshot that was itself generated from the corpus cannot accumulate repeated `nl_nl_…` prefixes. The publication day is appended to the article id, making each newsletter-day pair a distinct corpus row while keeping the upsert idempotent for repeats within a day.
3. **Idempotent upsert** — batches records (`batch_size`, default 50) into `recipe_news_corpus` with `on_conflict="article_id"`.

Both source fetches are individually wrapped in `try/except` with `logger.exception`, so a single upstream outage still persists whatever succeeded. Returns `{"fetched": N, "inserted": M}`. The daemon throttles this to `NEWS_SYNC_MIN_INTERVAL_SECONDS` (300s) on Turbo-driven ticks and runs it unconditionally on each scheduled 30-minute slot.

## Point-in-Time Backtesting (`run_push_backtest`)

`run_push_backtest(strategy, sb_client, llm_caller=None, rng=None, slippage_bps=5.0, concurrency_config=None, on_progress=None)` simulates a random contiguous 10-trading-day window stepped 3x/day ET (`09:30`, `12:30`, `15:30 ET` = 30 sessions) using the shared Long-Only `PortfolioState` engine with zero forward leakage:

1. **Trading calendar & corpus floor** — `_load_window_dates(sb_client)` reads `SPY` dates from `price_history` filtered to `>= CORPUS_MIN_DATE` (`2026-02-09`, matching the earliest `memories` row), and `expand_dates_to_et_slots()` expands the 10-day window into 30 ET slot descriptors (`slot_label`, `cutoff_date`, `as_of_utc`).
2. **Initial progress** — `on_progress` receives `10%` immediately with all 30 slot labels so `/recipes/backtest/$jobId` renders the full grid before Slot 1 runs.
3. **Strict PIT context & tools** — `fetch_push_context_batch()` and `execute_pit_tool()` (`apps/engine/recipes/pit_tools.py`, routed automatically by `core/llm/handlers/base.py` when `cutoff_date` or `as_of_utc` is set) enforce temporal isolation for `get_stock_quote`, `get_price_history`, `get_technical_indicators`, `get_ticker_news`, `get_todays_news_menu`, `fetch_newsletter_content`, `search_past_memories`, `get_market_feeling`, `get_earnings_history`, and `get_key_metrics`, while failing closed on live-only tools (`web_search`, option chains, etc.).
4. **Intraday pricing (`apps/engine/recipes/intraday_bars.py`)** — `fetch_intraday_bars_for_ticker()` resolves hourly/intraday bars from `recipe_intraday_bars` -> `FMPProvider.get_hourly_history` -> Alpaca IEX hourly -> `price_history` fallback, upserting fetched bars back to Postgres, and `resolve_slot_price()` picks the bar at or before each `as_of_utc`.
5. **Long-Only portfolio accounting (`BacktestAccumulator` & `PortfolioState`)** — positions remain open across sessions and overnight until explicit `EXIT` (or `SELL` on a held LONG) or `END_OF_WINDOW` on Slot 30, obeying `max_open_trades = 4` and `max_equity_pct_per_trade = 25.0%` (`SELL` when flat is skipped as `SHORT_NOT_ALLOWED`). Entries are whole-share only and charge the actual spend as `cost_basis`. Net P&L models `2 × slippage_bps` round-trip friction.

In `apps/engine/recipes/worker.py`, `on_progress` persists `progress_pct` (`10` -> `95`) and `result_json` to `recipe_execution_queue` on every settled slot.

## Live Backtest View (`/recipes/backtest/$jobId`)

Clicking **Backtest (Random 2W)** saves the recipe, enqueues a `backtest` job, and navigates to `/recipes/backtest/$jobId`, polling `fetchRecipeRunDetailFn` every 1.5s while `pending` or `processing`.

- **`BacktestHeader`** — displays `Edit in Studio`, recipe name, solid badge (`QUEUED` / `SLOT n / N` / `COMPLETED` / `FAILED`), `progress_pct`, `Re-run Backtest`, and progress bar.
- **`BacktestTimelineBlock`** — fluid grid of session tiles (`S<n> • <YYYY-MM-DD HH:MM ET>`), net P&L delta, and signal badges (`BUY` success, `EXIT` warning, `SELL`/`ERROR` danger, `HOLD`/`QUEUED` neutral, `RUNNING` accent), followed by a compact `SelectedSlotBar` with a `Jump to Trace ↓` anchor link to `#session-trace`.
- **`BacktestTelemetryBlock`** — `MetricTile`s and `Equity Progression` bars with `Spread & Slippage Net` vs `Midpoint (Zero-Cost)` toggle.
- **`RecipePortfolioBlock`** — displays `Cash Available`, `Open Market Value`, `Total Equity`, `Open Positions` (`n / 4`), and the open-positions mark-to-market table on both Backtest (`Current Portfolio & Open Positions`) and Live Studio (`Live Paper Portfolio`). The share column renders through `formatShares()` (`Number(value).toLocaleString('en-US', { maximumFractionDigits: 4 })`), so whole-share positions show as bare integers (`25`) and legacy fractional rows stay readable at up to 4dp (`20.4748`).
- **`BacktestTradesBlock`** — executed trades combining open `BUY` fills (`OpenTradeRow` with `OPEN` badge from `open_positions`) and closed trades (`Action`, `Entry Session`, `Exit Session`, `Entry`, `Exit`, `Exit Reason` badge `SIGNAL_EXIT` / `END_OF_WINDOW`, `Net Return`, `Net P&L`), plus skipped counterfactual signals (`SHORT_NOT_ALLOWED`, `MAX_OPEN_TRADES`, `NO_PRICE_DATA`, `ALLOCATION_BELOW_ONE_SHARE`).
- **`BacktestSessionTraceBlock`** (`#session-trace`) — sits below `BacktestTradesBlock` so Telemetry, Portfolio, and Trades remain immediately visible below the 30-slot indicator; provides `‹ Prev` / `Next ›` session stepping, an `↑ Timeline` anchor link back to `#simulation-timeline`, `Hold decision` summaries, and `TraceInspectorBlock` in exact LLM order (`Hydrated Prompt` → `LLM Execution Rounds` → `Final Output`).

A `live_turn` job opened on this route renders an `Incompatible Job Mode` error card instead of backtest telemetry.

## Public Showcase Pin (`/recipes-demo`)

`/recipes-demo` is a public read-only walkthrough of one published backtest (`RecipeBacktestPage` with `readOnlyShowcase`, which hides `Re-run`/`Cancel` and swaps `Edit in Studio` for `Sign In Free to Build & Run`). `fetchPublicShowcaseBacktest` resolves what it renders in two steps:

1. **Pin first** — `public.recipe_showcase` holds a single row (`id = 1`) with `job_id` (nullable, `ON DELETE SET NULL`), `recipe_id`, `headline`, `recipe_name`, and `published_at` (`supabase/migrations/20261117000000_create_recipe_showcase.sql`). The row is service-role only (RLS + `REVOKE` from `anon`/`authenticated`) because the page reads it through `getDbAdminClient`. The pinned job must be `mode = 'backtest'`, `status = 'completed'`, and carry `result_json`; `headline` overrides the recipe name as the page title and `recipe_name` is frozen at publish time. A `NULL` `job_id` (a future queue-retention prune) degrades to the heuristic instead of deleting the pin.
2. **Fallback heuristic** — if the pin is missing, stale, or unreadable, the original path still applies: public recipes (`is_public = true`, newest `completed_at` first, top 5) and the newest completed backtest with `result_json`. Every read in this path destructures `error` and logs, so a silent `PGRST205` or revoked grant cannot masquerade as "nothing published yet".

Publishing is an explicit editorial act:

```sh
# validate against the live run without writing
python3 -m recipes.publish_showcase --job <job-id> --dry-run

# pin it (also sets strategy_recipes.is_public = true on the owning recipe)
python3 -m recipes.publish_showcase --job <job-id> --headline "Trump & Chips News Momentum — 2-week point-in-time run"
```

`apps/engine/recipes/publish_showcase.py` fails closed with `ShowcasePublishError`:

- the job must be a completed backtest carrying the full `30` `day_steps`;
- the recipe graph must validate through `push_schema.is_valid_single_stage_graph`;
- a recipe edited more than `GRAPH_EDIT_GRACE` (10 minutes) after the run completed is refused, since the queue does not snapshot the graph;
- `_build_client` requires `ARCHIVE_DB_URL` + `ARCHIVE_DB_SERVICE_ROLE_KEY` and refuses any host that is not the archive database (or localhost).

Write order matters: the pin upsert runs **before** `is_public` is flipped, and the flag is read back afterwards. Publishing deliberately does not touch `strategy_recipes.updated_at`.

`saveRecipe` takes an explicit `publication: 'preserve' | 'publish' | 'unpublish'` (default `'preserve'`) and only writes `is_public` when it is not `'preserve'`, so an ordinary studio save cannot silently unpublish a pinned showcase. `saveRecipeFn` does not accept `isPublic` from the browser at all — publication is CLI-only.

### Caching (`apps/web/src/lib/showcase-cache.ts`)

A published showcase changes only when someone publishes again, so the document is served from the shared CDN cache instead of running SSR (and its `~1 MB` `result_json` read) for every visitor:

- `cache-control: public, max-age=0, s-maxage=259200, must-revalidate` — browsers revalidate, shared caches keep it for 72 hours.
- `netlify-cdn-cache-control: public, s-maxage=259200` — Netlify's edge honours this on function responses.
- The headers are applied in `start.ts` `requestMiddleware` (not `netlify.toml`, whose header rules do not cover function-backed paths). Only a `200` on exactly `/recipes-demo` is touched.
- `hasPublishedShowcase()` probes the pin (one small read, only on a cache miss). No pin, a read error, or a non-200 response all yield `cache-control: no-store`.

## Studio Recent Backtests

`/recipes` loads `fetchRecentBacktestJobsFn()` alongside the optional `?recipeId=` recipe and passes the results to `RecentBacktestsStrip`, which renders a `Recent Backtests:` trough of up to five `voxel-btn` links to `/recipes/backtest/$jobId`.

## Live Status Page (`/recipes/live/$recipeId`)

Live paper portfolio and run history moved from the studio to a dedicated SSR page (`[[entities/recipe-live-status]]`). `/recipes/live/$recipeId` loads through `RecipeLivePage` with `useLoaderData`, seeded by the route loader calling `fetchLivePortfolioAndRunsFn({ data: { recipeId } })` (failing soft to `null`). The page renders `Live Paper Portfolio` (a `RecipePortfolioBlock` fed by the persisted `paper_cash` / `paper_positions` / `paper_trades`, enriched by the latest mark price) and `Live Run Traces` (a `RunSelectorBar` of the last 10 persisted `live_turn` jobs, each rendering its stage prompt, per-round reasoning, tool calls & results, and full output through `TraceInspectorBlock`).

The page header renders a `← Back to Studio` link, the `Live Status` heading, the short recipe id, a `Live: ON (30m)` success badge (or `Live: PAUSED`, or `Turbo: <N>m left (5m)` while active), a `Next run: <slot>` label computed by `getNextLiveSlotLabel` from `apps/web/src/features/recipes/utils/market-hours.ts`, and the `TurboButton` control for the recipe owner. The page is reachable from the `StudioActionBar` `Live Status →` link, the `SavedRecipesStrip` `Live Status →` chip link, and the recipe name link inside each `RecipeAlertsInbox` card. There is no client-side polling.

### Live-recipe switching (`LiveSwitchConfirmation.tsx`)

Enabling `Enable Live (30m)` on a recipe while another recipe already holds `is_live = true` shows an inline `voxel-trough` confirmation (not a modal) reading "`<name>` is currently live (30m)" with `Switch to This` (disable the old recipe, clearing its `turbo_expires_at`, enable the new one, navigate to its live page) and `Keep <Old Recipe>` (cancel). The scheduled-live cap is **three bots per user** (`maxLiveRecipes: 3`); enabling a fourth fails with `Scheduled live limit reached (3/3)`.

## LLM Endpoint Failover (`apps/engine/recipes/llm_caller.py`)

Every LLM call in `push_runner.py` goes through `invoke_llm()` -> `default_llm_caller()` in `apps/engine/recipes/llm_caller.py`:

- **`llm_endpoints(openrouter_key, model)`** builds the ordered chain: OpenRouter (`https://openrouter.ai/api/v1`) when an explicit `openrouter_key` is supplied, otherwise `STRATA_BASE_URL` followed by `FREE_LLM_PROXY_URL` (`https://llm.clvg.uk/v1`).
- **`filter_recipe_tool_names(selected_tools, *, pit_mode)`** drops `RECIPE_DISABLED_TOOLS` (`web_search`), any name absent from `CANONICAL_TOOLS_REGISTRY`, and — when `pit_mode` is true — any name outside `PIT_SAFE_TOOL_NAMES`.
- **`run_tool_loop(client, model_id, prompt, tool_schemas, cutoff_date, as_of_utc=None, allowed_tools=None)`** runs up to `MAX_TOOL_ROUNDS = 5` Long-Only OpenAI-compatible tool-calling iterations followed by 1 forced tool-free synthesis turn (`_run_final_synthesis`) if the model did not emit a final answer, forwarding `cutoff_date` and `as_of_utc` into `core/llm/handlers/base.py:execute_tool()`. Captures `trace` (`rounds`, per-round `reasoning` / `thinking` text, `tool_calls` with args & results, and `forced_final_synthesis`).
- **`default_llm_caller(...)`** fails over across endpoints inside `async with AsyncOpenAI(...)` contexts (so the HTTP client is always closed) and re-raises if every endpoint fails.

Both worker lanes resolve `auto-go`, so backtests, scheduled live turns, and Turbo turns share one free-proxy routing path and cannot contend with local Strata.

## Worker Modes, Outcomes & Event-Loop Safety (`apps/engine/recipes/worker.py`)

- **`JobOutcome = Literal["EMPTY", "COMPLETED", "FAILED"]`** — the tri-state return distinguishes "queue was empty" from "job ran" and "job errored". Callers drain until `"EMPTY"` and count `"FAILED"` separately.
- **`SUPPORTED_JOB_MODES = ("backtest", "live_turn")`** — the popped `job_mode` is validated immediately after dequeue; an unrecognized mode raises `ValueError("Unsupported recipe execution mode: <mode>")`, which is caught, persisted to `recipe_execution_queue.error_message` on the `failed` row, and returned as `"FAILED"`. A missing `job_mode` defaults to `backtest`.
- **No nested event loop** — `async_process_next_recipe_job()` `await`s `run_push_live()` / `run_push_backtest()` directly, so it is safe to call from an already-running loop.
- **`process_next_recipe_job(client=None)`** — thin synchronous wrapper (`return asyncio.run(async_process_next_recipe_job(client))`).
- Successful jobs still write `result_json`, `status = 'completed'`, increment `strategy_recipes.trial_count`, and deposit `live_turn` signals into `recipe_alerts_inbox`.

## Legacy DAG Removal

The former `RecipeGraph` DAG pipeline (`schema.py`, `validator.py`, `indicators.py`, `backtester.py`, `backtest_models.py`) and its `recipe_intraday_bars` 5-minute candle cache have been removed. `async_process_next_recipe_job()` rejects any `graph_json` that lacks a `stages` list with `ValueError("Recipe must use Push v2 format with a 'stages' list (legacy DAG format is removed).")`, marking the queue row `failed`. `enqueue_live_recipes()` applies the same Push v2 shape check, plus the one-stage limit, before a live recipe may enter the queue; `enqueue_turbo_recipes()` applies it before a Turbo job may enter the queue.

## Single LLM Call Limit (MVP)

Each strategy makes one LLM call per live run or per backtest day. Multi-stage chaining is off for the MVP. The limit is enforced at every boundary a strategy can cross, so a stale client, an old queued row, or a hand-written API call cannot bypass it.

- The Studio UI (`apps/web/src/features/recipes/pages/RecipeStudioPage.tsx`) shows one `LLM Call` card with no add or remove stage controls and no stage-title input. `PushStrategy.stages` is typed as the one-element tuple `[StrategyStage]`, and `starter-templates.ts` validates the imported JSON at load time.
- The engine schema (`apps/engine/recipes/push_schema.py`) is the source of truth. `PushStrategy.stages` is a required field with `min_length=1, max_length=1`; the `validate_exactly_one_llm_stage` validator raises `Push strategies must contain exactly one LLM stage for the MVP`, and `reject_prev_output_placeholder` rejects a `{{prev_output}}` prompt.
- The scheduler (`apps/engine/recipes/runner.py`) uses `_is_valid_single_stage_graph()` in `enqueue_live_recipes()` and `enqueue_turbo_recipes()`. A malformed or multi-stage live recipe is skipped with a `logger.warning` instead of being queued.
- The save API (`apps/web/src/features/recipes/api/recipes-api.ts`) calls `assertSingleLlmStage()` and `assertNoPrevOutputPlaceholder()` inside `saveRecipe()` before any write.
- The fork API and the builder compiler run the same two assertions before writing a row.
- The database enforces it too. The `strategy_recipes_single_stage_check` constraint (`supabase/migrations/20261113190000_unpublish_legacy_multistage_recipe_template.sql`) rejects a `graph_json` whose `stages` array is not exactly one element on insert and update. It was added `NOT VALID` so the legacy row did not block it.

The legacy `2-Stage Research -> Trade Decision` template was unpublished by the same migration (`is_public = FALSE`, `is_template = FALSE`). It was removed from `packages/config/starter-recipes.json`, so the seeder never recreates it.

## API Module Split & Fail-Closed Authorization

The Studio runs against the archive DB (`strategy_recipes` is publicly readable only for templates and public recipes while `recipe_execution_queue`, `recipe_user_quotas`, `recipe_alerts_inbox`, `recipe_builder_usage`, and the desk tables are service-role only). Server functions sit behind auth checks and fail closed (`Unauthorized`) when `user?.id` is absent:

- **`api/recipes-api.ts`** — recipe persistence and job lifecycle: `saveRecipe` / `saveRecipeFn`, `enqueueRecipeJob` / `enqueueRecipeJobFn`, `getRecipeJobStatus` / `getRecipeJobStatusFn`, `fetchRecipeRunDetail` / `fetchRecipeRunDetailFn` (including `queuePosition` and `globalActiveBacktests`), `fetchRecipeById` / `fetchRecipeByIdFn`, `fetchRecentBacktestJobs` / `fetchRecentBacktestJobsFn`, and `fetchPublicRecipes`. `enqueueRecipeJob` types `mode` as `'backtest'` (live turns are enqueued exclusively by the daemon and the Turbo RPC), always sets `provider: 'free-llm-proxy'` and `model: 'auto-go'`, and derives `priority`: it counts the caller's `completed` backtests and stamps **`priority: 0` for their first-ever backtest**, otherwise `priority: 10`. Priority only reorders *pending* jobs (`pop_next_recipe_job` orders `priority ASC`), so a beginner's first run jumps the queue without preempting a running backtest.
- **`api/recipes-quota-api.ts`** — starter beta quotas (`maxConcurrentBacktests: 1`, `dailyBacktestLimit: 2`, `dailyLiveTurnLimit: Number.POSITIVE_INFINITY`, `maxLiveRecipes: 3`, global queue cap `20`), `recipe_user_quotas` DB overrides, `cancelRecipeJob`, `toggleLiveSchedule`, `activateRecipeTurbo` / `activateRecipeTurboFn`, `fetchUserRecipes` (selecting `turbo_expires_at`), and `fetchPublicShowcaseBacktest`. `assertQuotaAllowsJob(userId, mode)` accepts only `mode: 'backtest'` and enforces the concurrent-backtest, daily-backtest, and global-queue caps. `fetchRecipeQuotaStatus` selects `last_turbo_et_date` alongside the tier columns and returns `turboUsedToday: lastTurboEtDate === getEtDateString(new Date())`. It also selects `started_at` and counts a backtest against the 24h allowance only when `status === 'completed'` **or** `started_at` is set — a never-started row or a provider failure never burns the day, while a run the user cancelled after it spent LLM calls still counts.
- **`api/recipes-studio-api.ts`** — alerts (`fetchRecipeAlerts`, `markAlertRead`), waitlist pledges (`submitWaitlistPledge`), `fetchLivePortfolioAndRuns` (returning `liveMeta`), and `previewStrategyPrompt`.
- **`api/fork-recipe.ts`** — `forkRecipe` / `forkRecipeFn` (see the Fork section).
- **`api/public-board-api.ts`** — `fetchPublicDesk` / `fetchPublicDeskFn`, reading only `recipe_public_stats`, `recipe_desk_summary`, and `recipe_desk_feed`.
- `RecipeJobStatus` includes `'pending' | 'processing' | 'completed' | 'failed' | 'cancelled'`.

## Client Types (`apps/web/src/features/recipes/types.ts`)

- `StrategyStage` — `{ id, blocks, selected_tools }`. The per-stage `title` field is gone; stages render as a fixed `LLM Call` label.
- `LLMExecutionTrace` — `{ forced_final_synthesis, rounds: [{ round, reasoning, assistant_text, tool_calls: [{ name, args, result }] }] }`.
- `LiveStageOutput` — `{ stage_id, prompt, output, tool_calls, ... }` (no `title`).
- `OpenPositionRecord` — `{ ticker, side?, shares, entry_price, entry_time, cost_basis?, current_price?, market_value?, unrealized_pnl_net?, unrealized_return_pct?, alpaca_status?, alpaca_order_id?, alpaca_submitted_at? }`, the enriched open-position shape shared by backtest snapshots, live paper portfolios, and `RecipePortfolioBlock`.
- `BacktestDayStep` — `{ day, day_index, status, signals, tool_calls, output_excerpt, full_output?, prompt?, trace?, day_pnl_net, trades_executed, trades_skipped }`.
- `BacktestResultData` — the accumulator snapshot shape, extended with `mode`, `days_completed`, `total_days`, `current_day`, `cash?`, `total_equity?`, `open_positions?`, and `day_steps` so a partial in-flight payload is a valid `BacktestResultData`. Note: `window_dates`, `days_completed`, and `total_days` intentionally retain their existing JSON keys while holding ET slot labels and slot counts (`30` slots for 10 trading days) for backwards schema compatibility.
- `LiveRunResult` — `{ mode: 'live_turn', as_of_utc, slot_label?, stages, final_output, signals, executed_signals?, alpaca_fills?, signal_prices?, updated_portfolio? }`.
- `LivePortfolioSnapshot` / `LivePortfolioAndRuns` — the live paper portfolio view model, with `LivePortfolioAndRuns.liveMeta?: LiveStatusMeta`.
- `LiveStatusMeta` — `{ recipeName, isLive, isOwner, turboExpiresAt, turboUsedToday }`, computed server-side by `fetchLivePortfolioAndRuns`.
- `RecipeJobStatus` / `RecipeJobRecord` / `RecipeRunDetail` — the queue row projections.
- `RecipeUserQuotaStatus` & `RecipeSummaryItem` — per-user limits (`maxConcurrentBacktests`, `dailyBacktestLimit`, `dailyLiveTurnLimit`, `maxLiveRecipes`, `globalPendingBacktests`, `globalQueueCap`, `turboUsedToday`, `lastTurboEtDate`) and owned recipe list projections (`turbo_expires_at`).
- `RecipeSaveState` — `'idle' | 'saving' | 'saved' | 'error'`.
- `BacktestError` — `{ kind: 'quota' | 'navigation' | 'execution', message: string, backtestJobId?: string }`. See [[concepts/state-machines]].

## Public Recipe Surface & Homepage

`/` is the recipe desk, not the benchmark dashboard. The landing page (`apps/web/src/routes/index.tsx` -> `apps/web/src/features/playground/pages/HomePlaygroundPage.tsx`) renders a one-line idea form that routes to `/build`, a live board sorted by most recent activity, a same-day execution feed, and a Fork button per card. The board publishes losers as well as winners, with the recipe return and the SPY return over the same equity window, plus a `N live · X beating SPY · median` header. Its empty state reads "The board fills as recipes run every 30 minutes during market hours (09:30–16:00 ET)."

- **Materialised stats, zero frontend compute**: `apps/engine/recipes/public_stats.py` rebuilds `recipe_public_stats` each runner cycle (`return_pct`, `spy_return_pct`, `trade_count`, `open_positions`, `runs_today`, `last_action`, `resolved_model`), `recipe_desk_summary` (single-row live count, beat-SPY count, median return) and `recipe_desk_feed` (same-day executed signals, 24 rows). `apps/web/src/features/recipes/api/public-board-api.ts` reads those three tables only — never `recipe_execution_queue` and never `paper_equity_curve` in the browser. The header numbers come from the materialised summary, so a truncated card list can never masquerade as the live count. See [[concepts/recipe-public-stats]] and [[concepts/zero-frontend-compute]].
- **Resilient loader** — `getDesk()` in `routes/index.tsx` wraps `fetchPublicDesk()` in `try/catch` and returns an `EMPTY_DESK` on failure, so the front door renders the empty state (including before the public-stats migration is applied) instead of an error page.
- **Signed-percentage display** — `formatPct(value)` in `apps/web/src/features/home/pages/format-pct.ts` renders a `+`/`-` two-decimal percentage, folds `|value| < 0.005` to `0`, and renders `—` for `null`/`undefined`/non-finite input so an unknown value never reads as `0.00%`.
- **Public `/recipes`**: `apps/web/src/routes/recipes/index.tsx` is no longer under `_authed`. Anonymous visitors get `RecipeGalleryPage` (template catalogue, block badges, prompt excerpt, `Describe your own` → `/build`, `See a finished backtest` → `/recipes-demo`, `Sign in to fork` → `/login?redirect=/recipes`); signed-in visitors get the studio.
- **Fork = cheapest "this is mine"** — `apps/web/src/features/recipes/api/fork-recipe.ts` copies a public/template/own graph into a new row owned by the caller (see the Fork section).
- **Builder chat (`/build`)** — `apps/web/src/routes/build.tsx` + `apps/web/src/features/recipes/builder/` compile a plain-English idea into a validated Push v2 graph. See concepts/recipe-builder-compiler.
- **Instrumentation** — `apps/web/src/lib/analytics.ts` wraps `track(client, event, props)` for named outcome events (`recipe_forked`, `builder_opened`, `builder_compiled`, `builder_question_answered`, `builder_declined`, `gallery_signin_clicked`). Autocapture alone cannot tell you a backtest finished, because element text is not a funnel.

## Backtest Concurrency, Quotas, Turbo and Ops Telemetry

- **Three concurrent backtests**: `supabase/migrations/20261119000000_recipe_public_stats_and_concurrency.sql` drops `idx_recipe_single_processing_backtest` and replaces the boolean guard in `pop_next_recipe_job` with a counted guard (`c_max_processing_backtests = 3`) evaluated under the existing advisory lock. `apps/engine/recipes/runner.py` passes `RECIPE_BACKTEST_CONCURRENCY` (default 3) for the backtest lane. Priority only reorders pending jobs, so a newcomer jump never preempts a running backtest. See [[concepts/recipe-backtest-concurrency]].
- **One open live turn per recipe**: `idx_recipe_one_open_live_turn_per_recipe` (unique partial index on `(recipe_id)` for `pending`/`processing` `live_turn` rows) plus `_insert_live_jobs_idempotent` makes 5-minute Turbo ticks and 30-minute slots mutually exclusive for a single bot. See [[concepts/recipe-turbo-mode]].
- **Backtests and live turns run on the free-llm proxy**: `recipes/worker.py` resolves `auto-go` for both lanes, and the resolved provider model is persisted per run so a board card can state which model produced it.
- **Quotas**: two backtests a day, counting only runs that actually started (`completed`, or any row carrying `started_at`), so a never-started row or a provider failure cannot lock a user out for the day while a cancelled-but-spent run still counts. Three live bots per user (`maxLiveRecipes: 3`). The per-user live-turn cap is no longer displayed or enforced (`dailyLiveTurnLimit` is `Number.POSITIVE_INFINITY`) because the live-bot cap already bounds the work at three bots across the 30-minute slots, and Turbo is capped separately at one activation per ET trading day.
- **First-run priority**: a caller's first-ever completed-backtest count of zero stamps `priority: 0`, so a brand-new user's first backtest jumps the pending queue.
- **Scheduler telemetry**: `enqueue_live_recipes_with_stats` pages every live recipe and open job, then reconciles `seen == enqueued + skipped_open + skipped_recent_turbo + skipped_invalid_graph`. A mismatch is written to `recipe_ops_events` as an error; more than 10% skipped as already-open is a warning. The 500-row `.limit()` that silently stopped scheduling recipes is gone. See [[concepts/recipe-ops-telemetry]].
- **Paid fallback visibility**: the proxy records `billing` on every `call_logs` row (`apps/free_llm_proxy/db.py`) and reports `paid_calls_total`, `paid_calls_24h` and `paid_tokens_24h`.

### Desk materialisation and builder metering

The homepage header and tape are written, not computed: `refresh_public_stats` also upserts `recipe_desk_summary` and rewrites `recipe_desk_feed` from the results the runner already holds, so `public-board-api.ts` only reads three tables. `supabase/migrations/20261119020000_recipe_desk_summary_feed_and_builder_usage.sql` adds both, plus `recipe_builder_usage` and `consume_builder_compile()`, which atomically spends one of 25 daily `/build` compiles per user before the proxy call (see [[concepts/recipe-builder-usage]]).

## Related Pages

- [[entities/database]] — `recipe_*` / `strategy_recipes` tables, `price_history`, the `activate_recipe_turbo` RPC, and `pop_next_recipe_job()`
- [[entities/recipe-live-status]] — the dedicated `/recipes/live/$recipeId` page and its Turbo control
- [[entities/secondary-minipc-edge]] — hosts the `recipe-worker` container
- [[concepts/recipe-turbo-mode]] — the 5-minute Turbo window, its atomic RPC, and market-hours helpers
- [[concepts/recipe-portfolio-engine]] — whole-share sizing, `ALLOCATION_BELOW_ONE_SHARE`, and the Alpaca paper mirror
- [[concepts/recipe-backtest-concurrency]] — the counted three-concurrent-backtest guard
- [[concepts/recipe-public-stats]] — the materialised public board and desk tables
- [[concepts/recipe-ops-telemetry]] — durable scheduler telemetry
- [[concepts/recipe-builder-usage]] — per-user daily compile metering
- concepts/recipe-builder-compiler — the plain-English → Push v2 compiler behind `/build`
- [[entities/free-llm-proxy]]
- [[entities/design-system]]
- [[concepts/zero-frontend-compute]]
- [[concepts/zero-lookahead-materialization]]
- [[concepts/state-machines]] — `RecipeJobStatus`, `RecipeSaveState`, and `BacktestError` lifecycle registry
- `packages/config/recipe-naming.json` — shared naming contract (`defaultName`, `nameMaxLength`) between engine and web
