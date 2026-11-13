---
tags: [recipes, dag, trading, backtest, news-corpus, voxel, studio]
category: entity
---

# Recipe Studio

The **Recipe Studio** (`/recipes`) is a visual, agency-driven trading strategy pipeline builder. Inspired by Unsloth Studio Data Recipes and systematic market inefficiency research, it enables quants and researchers to compose multi-stage Directed Acyclic Graphs (DAGs) connecting point-in-time financial news catalysts, technical indicator gates, and LLM classifiers without writing custom Python code.

## Architecture

The system is decoupled across three vertical slice layers:

1. **Storage & Corpus (`supabase/migrations/20261112103000_create_recipe_studio_v2.sql`)**:
   - `public.recipe_news_corpus`: Point-in-time news articles imported from `stock-news-scraper` shards, tagged across 10 canonical market buckets (`semiconductors`, `ai_cloud`, `fed_rates`, `earnings`, `macro_inflation`, `energy`, `financials`, `healthcare`, `tariffs_trade`, `m_and_a`). Carries a generated `search_tsv` column plus GIN indexes on `tickers`, `buckets`, and `search_tsv`.
   - `public.strategy_recipes`: Recipe DAG configurations (`graph_json`), cadence (`5m` or `1d`), concurrency limits, and isolated paper ledgers (`paper_cash`, `paper_positions`, `paper_trades`, `paper_equity_curve`).
   - `public.recipe_execution_queue`: Priority queue for backtests (priority 10) and live turns (priority 1) with atomic dequeue RPC `pop_next_recipe_job()`.
   - `public.recipe_alerts_inbox`: In-app trade alert delivery table.
   - `public.recipe_intraday_bars`: Point-in-time 5-minute candle cache.
   - `public.recipe_waitlist_pledges`: Early supporter pledges for future dedicated GPU compute tiers.

2. **Engine Processing (`apps/engine/recipes/`)**:
   - `schema.py`: Pydantic models for the whole graph — `RecipeGraph`, `DAGNode`, `DAGEdge`, `ConditionRule`, and the per-node config models (`NewsSourceConfig`, `TechnicalGateConfig`, `ClassificationConfig`, `GenerativeAnalystConfig`, `RiskOutputConfig`).
   - `validator.py`: `validate_recipe_graph()` — schema conformance, unique node IDs, edge integrity, source/sink presence, and three-color DFS cycle detection. See [[concepts/recipe-dag-backtesting]].
   - `indicators.py`: Technical indicators computed on candle streams (`rsi_14`, `vwap`, `sma_20`, `sma_50`, `rvol`, `price`) and rule evaluation.
   - `backtester.py`: Stepped timeline simulator across non-contiguous ISO weeks with technical gate short-circuiting, point-in-time LLM catalyst caching, dual-P&L tracking (Midpoint vs 5 bps Slippage-Adjusted), and counterfactual skipped trade attribution.
   - `backtest_models.py`: `Position`, `CompletedTrade`, `SkippedTrade`, `close_position()`, and `build_backtest_summary()`.
   - `worker.py`: `process_next_recipe_job()` — pops one job from the priority queue, validates the recipe, dispatches to the backtest or live-turn path, and records the result.
   - `news_corpus.py`: News ingestion parser, bucket categorizer, and temporal query engine.
   - `import_news_cli.py`: CLI importer for `stock-news-scraper/output/` JSONL files.

3. **Presentation & Studio UI (`apps/web/src/features/recipes/`)**:
   - Built strictly with Cheddar Boxel (Voxel) tokens (`bg-boxel-canvas`, `bg-boxel-surface`, 0px corners, 2px directional bevels, recessed `.voxel-trough` slots).
   - `RecipeFlowCanvas.tsx`: Stepped visual DAG pipeline canvas.
   - `BlockConfigureModal.tsx`: Dropdown configuration builder for indicators and conditions.
   - `RecipeBacktestResults.tsx`: Dual-P&L performance curves and counterfactual skipped trade forensics.
   - `RecipeAlertsInbox.tsx`: In-app trade signals notifications.
   - `WaitlistPledgeModal.tsx`: Free beta supporter pledge modal.
   - `starter-templates.ts`: Four ready-made recipes (`NVDA Semiconductor VWAP Momentum`, `SPY Macro Fed Rates Gate`, `Tech SMA Trend Following`, `Earnings Guidance Drift`).
   - `api/recipes-api.ts`: Server functions for save, enqueue, status polling, alerts, and waitlist pledges.

## DAG Node Types

| Node Type | Purpose | Key Parameters |
| :--- | :--- | :--- |
| `news_source` | Pulls point-in-time headlines within lookback window | `bucket`, `tickers`, `lookback_hours` |
| `price_tape` | Streams market price bars | `ticker`, `cadence` (`5m`, `1d`) |
| `technical_gate` | Filters execution based on technical rules (AND) | `metric`, `operator`, `target` |
| `classification` | LLM catalyst sentiment classifier | `model` (`~typesafe/jev-latest`), `target_choice`, `min_confidence` |
| `generative_analyst` | Open-ended reasoning analyst | `model` (`auto-strata`), `system_prompt`, `user_template` |
| `risk_output` | Sizing, stops, profit targets, and exit rules | `action` (`BUY`/`SELL`), `stop_loss_pct`, `target_profit_pct`, `max_hold_bars` |

## Queue Worker (`apps/engine/recipes/worker.py`)

`process_next_recipe_job(client=None)` processes exactly one job per call and returns `True` when a job was handled, `False` when the queue was empty or the job failed.

1. **Atomic dequeue** — calls the `pop_next_recipe_job()` RPC, which re-queues `processing` rows stalled longer than 5 minutes, then selects the lowest `priority` / oldest `created_at` pending row with `FOR UPDATE SKIP LOCKED` and flips it to `processing` with `progress_pct = 5`.
2. **Mark processing** — stamps `status = 'processing'` and `started_at`.
3. **Parse & validate** — loads `strategy_recipes.graph_json` (accepting a JSON string or object) and runs `validate_recipe_graph`. A validation failure raises `ValueError`, which marks the queue row `failed` with the joined error list in `error_message`.
4. **Dispatch by mode** — `live_turn` routes to `_execute_live_turn`, everything else to `_execute_backtest_job`.
5. **Complete** — writes `status = 'completed'`, `progress_pct = 100`, `result_json`, and `completed_at`, then increments `strategy_recipes.trial_count` and refreshes `updated_at`.

### Backtest Path

`_execute_backtest_job` resolves the ticker in priority order: the `price_tape` node's `ticker`, then the first entry of a `news_source` node's `tickers`, then the first word of the recipe name when it is alphabetic and ≤ 5 characters, defaulting to `SPY`. It loads that ticker's rows from `recipe_intraday_bars`, and when the cache is empty it substitutes a single synthetic anchor bar (`open 500.0`, `high 501.0`, `low 499.0`, `close 500.5`, `volume 10000`) so the simulation still produces a result. The 100 most recent `recipe_news_corpus` rows are passed as the news feed, and `run_recipe_backtest` is invoked **without** an injected `llm_evaluator` — `classification` nodes therefore resolve to their configured `target_choice` at 90% confidence rather than issuing a live LLM call.

### Live Turn Path

`_execute_live_turn` reads the latest `recipe_intraday_bars` row for the ticker (coercing missing or malformed OHLCV values to safe defaults), evaluates **only** the `technical_gate` conditions, and on a pass inserts a `recipe_alerts_inbox` row carrying the `risk_output` action, entry price, target price, stop loss, cadence, and the joined condition explanations. No news or LLM gate runs in the live path.

## Web API Server Functions (`apps/web/src/features/recipes/api/recipes-api.ts`)

| Function | Method | Purpose |
| :--- | :--- | :--- |
| `fetchPublicRecipes()` | direct DB read | Lists up to 20 recipes where `is_public` or `is_template` is true |
| `fetchRecipeAlertsFn` | `GET` | Returns the caller's 50 most recent `recipe_alerts_inbox` rows |
| `markAlertReadFn` | `POST` | Sets `is_read = true` on one alert scoped to the caller |
| `saveRecipeFn` | `POST` | Inserts or updates a recipe; rejects edits to another user's recipe |
| `enqueueRecipeJobFn` | `POST` | Enqueues a `preview` / `backtest` / `live_turn` job (priority 1 for live turns, 10 otherwise) and selects the provider from the supplied BYO keys |
| `getRecipeJobStatusFn` | `GET` | Returns `status`, `progress_pct`, `result_json`, and `error_message` for a job |
| `submitWaitlistPledgeFn` | `POST` | Records an early-supporter pledge |

Unauthenticated callers are attributed to the sentinel `ANONYMOUS_USER_ID` (`00000000-0000-0000-0000-000000000000`). Privileged writes go through `getDbAdminClient()`; reads use `getDbServerClient()` (see [[concepts/auth-db-client-separation]]).

## Model Routing & Free Tier Policy

- **Free Tier Default**: All simulations and paper turns run at zero user cost via our dedicated local GPU queue (`auto-strata`).
- **BYO OpenRouter Key**: Users providing an OpenRouter key unlock Jev (`~typesafe/jev-latest`) for low-cost catalyst classification. Jev is *only* invoked if an OpenRouter key is supplied.
- **Queue Starvation Guard**: A hard limit of 40 local LLM calls per backtest prevents long multi-week simulations from exhausting GPU queues. Technical gates evaluate first to short-circuit non-viable entries before invoking LLMs.

## News Corpus Import CLI

`apps/engine/recipes/import_news_cli.py` imports `stock-news-scraper` JSONL shards into `recipe_news_corpus`:

```sh
PYTHONPATH=apps/engine ./apps/engine/.venv/bin/python3 -m recipes.import_news_cli \
  --scraper-dir /path/to/stock-news-scraper [--batch-size 50] [--dry-run]
```

It scans `<scraper-dir>/output/corpus/*.jsonl` and `<scraper-dir>/output/news_*.jsonl`, upserts idempotently on `article_id`, and reports inserted/skipped counts. `--dry-run` parses and validates records without touching the database.

## Route Registration

The page is served by `apps/web/src/routes/recipes/index.tsx` (`createFileRoute('/recipes/')`) and is linked from the `/lab` directory under **Research & Prediction Engines**. The client polls `getRecipeJobStatusFn` up to six times at one-second intervals after enqueuing a backtest, rendering `RecipeBacktestResults` as soon as `status === 'completed'`.

## 5-Block Push-Based MVP (`version: "2.0-push"`)

In addition to legacy `RecipeGraph` DAGs, `/recipes` now defaults to a simpler linear **5-Block Push-Based Strategy Builder** (`apps/engine/recipes/push_schema.py`, `apps/engine/recipes/push_hydrator.py`, `apps/engine/recipes/push_runner.py`):

- **Multi-Stage Sequential Chaining**: A strategy contains 1 or more ordered `StrategyStage` items (`Stage 1..N`), where Stage $N$'s output is passed into Stage $N+1$ via `{{prev_output}}`.
- **5 Push Blocks**:
  - `output_format`: Immutable output-format contract locked to the trade-signal schema
    `[{"action": "BUY"|"SELL", "ticker": "..."}]`. Frozen content — add or remove the
    block, but do not edit its rendered text. The block is rendered **last** in the
    assembled stage prompt regardless of its position in the stage's block list, so the
    schema lock is always the final instruction the model sees. `OutputFormatBlock` is a
    frozen Pydantic model (`ConfigDict(frozen=True)`) and the UI hides its move/delete
    controls, showing an `IMMUTABLE` badge instead.
  - `prompt`: Free-text prompt instructions.
  - `news`: Keyword `contains` + `recency_hours` filter over `recipe_news_corpus`.
    Each hit renders its headline plus a ~300-char body excerpt centered on the first keyword hit (lead fallback), built by `build_news_excerpt` in `apps/engine/recipes/push_hydrator.py` and mirrored in `apps/web/src/features/recipes/news-excerpt.ts`. Both implementations are asserted against the shared cases in `packages/config/news-excerpt-cases.json`; regenerate expectations only from the engine and keep both suites green.
  - `memories`: Keyword `contains` + `recency_hours` + `category` (`memory_type`) + `min_importance` filter over `memories` (explicitly projecting columns without `embedding` vectors).
  - `technicals`: Company rules (`P/E`, `FCF`, `VWAP`, `RSI`, `MACD`, `price_52w_pct`, etc.) serialized as prompt criteria.
- **UI & Prompt Visualizer**: `StageBuilder.tsx`, `ToolPicker.tsx` (curated 12-tool checklist including `get_technical_indicators`), and `PromptVisualizer.tsx` (instant template preview + `previewStrategyPromptFn` live DB hydration) in `apps/web/src/features/recipes/`.
- **Random 2-Week Point-in-Time Backtest**: `run_push_backtest` selects a random contiguous 10-trading-day window (preventing overfitting), steps day-by-day injecting point-in-time news/memories (`<= sim_date`) and passing `cutoff_date` into tools, and scores `BUY`/`SELL` picks.

## Related Pages

- [[concepts/recipe-dag-backtesting]] — DAG validation invariants, point-in-time news queries, and dual P&L accounting
- [[entities/database]] — the six `recipe_*` / `strategy_recipes` tables and the `pop_next_recipe_job()` RPC
- [[entities/free-llm-proxy]]
- [[entities/design-system]]
- [[entities/autoresearch]]
- [[concepts/zero-frontend-compute]]
- [[concepts/jev-decisions-model]]
