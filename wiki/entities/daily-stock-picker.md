---
tags: [entity, stock-picker, daily-predictions, long-short, autoresearch]
category: entity
---

# Daily Stock Picker Arena (3 Up, 3 Down)

The **Daily Stock Picker Arena** (`apps/engine/tasks/stock_picker.py`) is an autonomous multi-model equity selection engine that runs every morning before the US market opens. It screens morning intelligence briefings, tasks an arena of foundation models with selecting exactly 3 stocks to go UP (Long) and 3 stocks to go DOWN (Short) during Regular Trading Hours (09:30 AM to 04:00 PM ET), evaluates directional hit rates and Long/Short spread alpha at market close, and continuously evolves its prompt strategies via an isolated weekly autoresearcher.

## 1. Candidate Universe & Extraction

Unlike static watchlists or unconstrained universe scans, candidate tickers are dynamically extracted from that morning's synthesized intelligence briefing (`apps/engine/tasks/newsletter_generator.py` open session) and pre-market gap scans:
* **Pool Size**: 15 to 30 active equities per session.
* **Extraction**: `extract_candidate_tickers(briefing_text)` extracts capitalized stock mentions (with regex filtering out macro acronyms like `CPI`, `FOMC`, and index ETFs `SPY`, `QQQ`).
* **Anchor Fallback**: Supplemented with high-liquidity large-cap anchors (`NVDA`, `TSM`, `AAPL`, `MSFT`, `AMZN`, `GOOGL`, `META`, `TSLA`, `AVGO`, `CRWV`, `ETR`, `CB`, `XLF`, `ABNB`) to ensure depth.

## 2. Multi-Model Arena & Deterministic Consensus

Three distinct frontier models compete in parallel under independent prompt lineages:
1. **DeepSeek Flash** (`deepseek-flash`) — Instruct-based structured JSON extraction.
2. **MiniMax** (`MiniMax-M3.1-Flash`) — High-context reasoning LLM with JSON format output.
3. **GPT Luna** (`gpt-6-luna`) — OpenAI high-conviction decision model.

### Reciprocal Rank Fusion (RRF) with Leg Exclusivity

To generate the platform's official **Consensus Basket** without model hallucination or empty sets:
* **Score Accumulation**: For each direction (UP, DOWN), each model vote contributes:
  $$
  \text{Score}(t) = \sum_{m \in \text{models}} \left( \frac{1}{60 + \text{Rank}_m(t)} \times \frac{\text{Confidence}_m(t)}{100.0} \right)
  $$
* **Leg Exclusivity**: If a ticker receives votes in both UP and DOWN across models, it is assigned strictly to the direction with the higher aggregate score and disqualified from the opposing leg.
* **Tie-Breaking**: Sorted descending by `Score` $\to$ `Mean Confidence` $\to$ `Alphabetical Ticker`.
* **Sanitization Invariant**: The top 3 ranked tickers for UP and top 3 for DOWN are selected, guaranteeing exactly 6 unique stocks per consensus basket (`apps/engine/tasks/stock_picker.py`).

## 3. Two-Tier Relational Schema

To enforce [[concepts/zero-frontend-compute]] and CP-safe atomic transactions, data is persisted across two relational tables (`supabase/migrations/20261112000000_create_daily_stock_picks.sql`):

* **Parent Basket** (`daily_stock_baskets`):
  * `id` (UUID PK), `target_date`, `model_name` (`consensus`, `deepseek-flash`, `MiniMax-M3.1-Flash`, `gpt-6-luna`).
  * Pre-materialized performance metrics: `directional_hit_rate`, `mean_long_return_pct`, `mean_short_return_pct`, `ls_spread_alpha_pct`, `excess_alpha_vs_spy_pct`, `benchmark_spy_return_pct`.
  * `status`: `pending` $\to$ `evaluated` or `cancelled`.
  * Unique constraint: `(target_date, model_name)`.
* **Granular Pick Items** (`daily_stock_picks`):
  * `basket_id` (FK referencing `daily_stock_baskets`), `ticker`, `direction` (`UP` / `DOWN`), `rank` (1..3), `confidence` (50..100%).
  * Execution columns: `open_price`, `close_price`, `stock_return_pct`, `position_return_pct` (`stock_return` for Long, `-stock_return` for Short), `is_hit`, `conviction_points`.
  * Unique constraints: `(target_date, model_name, ticker)` preventing duplicate picks within a basket, and `(target_date, model_name, direction, rank)`.
  * Invariant check constraint `chk_pick_evaluation_invariants` making illegal states unrepresentable (see [[concepts/state-machines]]).

## 4. Post-Market Close Evaluation

Scheduled at 17:00 ET (`apps/engine/tasks/evaluate_stock_picks.py`), the evaluator fetches Regular Trading Hours (09:30 to 16:00 ET) Open and Close prices. The module is decomposed into three pure, independently testable helpers around a thin orchestration shell:

| Helper | Responsibility |
| :--- | :--- |
| `_fetch_session_prices(tickers, session_date, force_recalc)` | Concurrently fetches RTH OHLC tuples for the unique ticker set (plus `SPY`) behind an `asyncio.Semaphore(5)` bulkhead. Any per-ticker exception is logged with `logger.exception` and mapped to `(None, None, None, None)` so one bad provider call cannot abort the whole session. |
| `_grade_pick(pick, prices, session_date, evaluated_at_iso)` | Grades a single pick — halt guard, return math, hit determination, conviction points — and returns the full merged row. |
| `_aggregate_basket(basket, basket_picks, spy_return_pct, evaluated_at_iso)` | Rolls graded picks up into basket-level mean long / mean short / L/S alpha / excess alpha / directional hit rate, or cancels a basket with zero valid picks. |

### Halt & Sub-Cent Defensive Guard

If `open_price` is `None`, `close_price` is `None`, `open_price <= 0`, **or `round(open_price, 2) <= 0`** (an LULD volatility halt, missing print, or a sub-cent penny quote that would round to `0.00` and violate the `open_price > 0` check constraint), the pick is marked `status = 'cancelled'` with `open_price`, `close_price`, `stock_return_pct`, `position_return_pct`, `is_hit`, `conviction_points`, and `evaluated_at` all explicitly set to `null`. The rounding guard is checked against the *persisted* (2-decimal) value, not the raw float, so a constraint violation can never reach PostgreSQL.

### Return Metrics

* $\text{Stock Return} = \frac{\text{Close} - \text{Open}}{\text{Open}} \times 100\%$ (rounded to 4 decimals)
* $\text{Position Return} = \text{Stock Return}$ for UP, $-\text{Stock Return}$ for DOWN
* $\text{L/S Spread Alpha} = \text{Mean}(\text{Long Position Returns}) - \text{Mean}(\text{Short Stock Returns})$
* $\text{Excess Alpha vs SPY} = \text{L/S Spread Alpha} - \text{SPY Return}$ (left `null` when the SPY benchmark return itself is unavailable — never silently coerced to zero)
* $\text{Directional Hit Rate} = \frac{\text{Count}(\text{is\_hit})}{\text{Total Valid Evaluated Picks}} \times 100\%$ (2 decimals)

A basket whose picks are *all* cancelled is itself marked `status = 'cancelled'`, with `directional_hit_rate`, `mean_long_return_pct`, `mean_short_return_pct`, `ls_spread_alpha_pct`, and `excess_alpha_vs_spy_pct` explicitly cleared to `null` (so stale graded metrics from a prior run never survive), while `benchmark_spy_return_pct` and `evaluated_at` are still stamped.

## 5. Weekly Autoresearch & Normalized Ratchet Hurdle

Every Sunday at 18:00 ET (`apps/engine/tasks/stock_picker_autoresearch.py`), each model track evaluates its rolling 5-session window against its historical baseline.

### Normalized Ratchet Hurdle Score
To eliminate dimension mismatch between percentage-point returns and hit rates, raw L/S Alpha is mapped into $[0, 100]$ centered at 50 ($10\text{ pts}$ per $1\%$ alpha):
$$
\text{Alpha}_{\text{norm}} = \text{clamp}(50.0 + (\text{LS\_Alpha\_pct} \times 10.0), 0.0, 100.0)
$$
$$
\text{Score} = 0.50 \times \text{Hit Rate} + 0.40 \times \text{Alpha}_{\text{norm}} + 0.10 \times \text{Conviction}_{\text{norm}}
$$

### Baseline Selection & Ratchet Reversion

Before selection, every stored variant is normalized so legacy rows participate in the shared guard: `metrics.score` is backfilled from `metrics.hurdle_score`, and `metrics.predictions_evaluated` from `metrics.sample_baskets`.

`select_baseline_candidate(normalized_variants, parent_tag, min_sample=1, min_traded=0)` returns a `(ceiling, variant)` tuple. The stock picker deliberately uses a **1-basket minimum** (a single graded session is enough to set the ceiling) rather than the 5-prediction guard used by the daily SPY and sector loops, because a track only produces one basket per session.

* **Beat the ceiling** — the active variant is promoted to `status = 'baseline'` and every other `active`/`baseline` variant on that track is demoted to `saved`.
* **Miss the ceiling** — the active variant is marked `status = 'discarded'`, and both `parent_tag` and `current_prompt` are reverted to the winning baseline variant, so the next mutation chains off the proven baseline instead of compounding on a losing variant. The reversion happens *before* the mutation call, so the meta-researcher is prompted with the baseline strategy rather than the discarded one.

The weekly metrics bundle written to `prompt_experiments.metrics` carries both `score` and `hurdle_score` (identical values), plus `hit_rate_pct`, `ls_spread_alpha_pct`, `conviction_norm`, `sample_baskets`, and `predictions_evaluated`.

### Mutation Sanitization

`sanitize_mutated_stock_strategy(raw_strategy)` guards the mutable section before it is wrapped in the frozen header/footer:

1. Strips a leading/trailing markdown code fence (```` ``` ````) if the model wrapped its answer.
2. If the `=== LONG/SHORT RELATIVE SELECTION STRATEGY ===` header is present, the mutable section is re-extracted through `split_stock_picker_prompt`.
3. Otherwise the header is prepended, so the stored prompt always splits cleanly in the UI.

### Experiment Record

New variants are inserted with `week_start` / `week_end` (a 7-day window), `experiment_type` (`radical` on a stochastic cold start, otherwise `incremental`), `parent_tag`, `change_description`, and a `research_output` payload carrying `research_insight`, `hypothesis`, `research_reasoning`, `confidence` (`0.85` when the baseline was beaten, else `0.50`), `is_cold_start`, `weekly_score`, and `is_baseline_beat`. The meta-prompt response schema (`StockPickerMetaPromptResponse`) now requests `hypothesis` and `research_reasoning` alongside `new_strategy` and `research_insight`.

Baseline seeding is an idempotent `upsert` on `variant_tag` (writing `week_start`, `week_end`, `experiment_type = 'baseline'`, and `change_description`), so a re-run can never duplicate the seed row.

* **1-in-6 Stochastic Cold Start**: Independently rolled per model track (`random.randint(1, 6) == 1`). If triggered, prompt mutations reset "from 0" using default strategy rules (see [[concepts/stochastic-cold-start]]).
* **Prompt Section Splitting**: Frozen headers and JSON schema footers are strictly preserved via `split_stock_picker_prompt`, mutating only the analytical strategy body.
* **Promotion & Memory**: Variants that beat the baseline are promoted to `status = 'baseline'`, demoting prior active variants to `saved`. High-conviction takeaways are stored in `memories` with `memory_type = 'AUTORESEARCH_INSIGHT'`.

### Failure Semantics

`run_stock_picker_autoresearch` counts per-track failures and raises `RuntimeError` when **every** track in `TARGET_TRACK_MODELS` fails, so a total provider outage exits non-zero instead of logging-and-continuing. A partial failure (some tracks succeed) still logs and continues. The mutation client is closed with its provider name (`close_client(ds_client, "deepseek")`); a missing provider argument raises `TypeError` inside the `finally` block after the mutation was generated and before the insert, which would silently discard the variant every run.

## 6. Pipeline Scheduling & Workflow Piggybacking

Enforcing Principle 14 (Workflow Consolidation):
* **Morning Run**: Piggybacked into `.github/workflows/daily-predictor.yml` under step `Run Daily Stock Picker Arena (3 Up, 3 Down)` at 9:17 AM ET.
* **Evening Evaluation**: Chained in `daily-predictor.yml` under step `Evaluate Daily Stock Picks` at 5:00 PM ET.
* **Sunday Autoresearch**: Triggered via scheduled cron `0 22 * * SUN` in `daily-predictor.yml` under step `Run Weekly Stock Picker Autoresearch`.

## 7. Web Dashboard Presentation

Surfaced as a first-class segmented tab in the Daily Predictions Arena (`apps/web/src/features/daily-predictions/components/DailyStockPicksTab.tsx`):
* **Model Filter Buttons**: Instant toggle between `⭐ Consensus`, `DeepSeek Flash`, `MiniMax-M3.1-Flash`, and `GPT-6 Luna`, driven by `STOCK_PICKER_TRACK_MODELS` in `daily-predictions-helpers.ts` (each entry carries an `id`, a `label`, and a `matches(trackId)` predicate).
* **View Mode Toggle (`Picks Log` | `Autoresearch & Prompt History`)**: A `voxel-trough` segmented control switches between the daily picks showcase and the stock picker prompt evolution arena. The autoresearch button carries the live experiment count (`Autoresearch & Prompt History (N)`).
* **Two-Column Pick Showcase**: 3 UP (Long) cards with rank badges and green borders; 3 DOWN (Short) cards with red borders, laid out in an `items-stretch` fluid grid (`repeat(auto-fit, minmax(min(100%, 20rem), 1fr))`).
* **Performance Tiles**: Directional Hit Rate, Net L/S Spread Alpha, SPY Benchmark move, and Excess Alpha, in a `repeat(auto-fit, minmax(min(100%, 13rem), 1fr))` `items-stretch` grid.
* **Historical Baskets Table**: Complete audited ledger of past sessions with right-aligned tabular numbers and zero floating tooltips (Principle 11).
* **Autoresearch & Hurdle Score Audit** (`StockPickerAutoresearchPanel.tsx`):
  - **Consensus banner** — when the `⭐ Consensus` filter is active, an in-flow `voxel-trough` banner explains that the consensus basket is an RRF aggregate of three independent autoresearch tracks and that an underlying track must be selected to inspect its mutations.
  - **Track cards** — one card per `STOCK_PICKER_TRACK_MODELS` entry showing the variant count, the active `variant_tag` (or `Unseeded baseline`), and the display score in points (or `Pending`). Clicking a card switches the selected model track.
  - **Milestones** — `AutoresearchMilestoneCards` for the selected track.
  - **Lineage sidebar** — `VariantSidebar` listing every variant of the track, with the active runtime tag pinned in the header.
  - **Selected variant detail** — `SelectedVariantHeader`, `StockPickerScoreBreakdown`, `ResearchRationaleCard`, `PromptChanges` (diffed against the parent variant), and the triple-band `SegmentedPromptInspector` (`=== LONG/SHORT RELATIVE SELECTION STRATEGY ===` split via `apps/web/src/features/autoresearch/utils/promptSections.ts`).
  - **Empty state** — a track with no recorded experiments renders an in-flow notice naming the Sunday 6:00 PM ET (10:00 PM UTC) cadence.

### Track, Parent & Score Resolution

Three resolution rules keep the panel coherent when data is sparse or legacy:

- **Active track** — `StockPickerAutoresearchPanel` resolves the active track config from `selectedModel` by id; when that id is not one of `STOCK_PICKER_TRACK_MODELS` it falls back to the first track whose `matches()` accepts any experiment's `track_id`, then to the first track. Experiments with no `track_id` are included in every track's filtered list (`e.track_id ? activeTrackCfg.matches(e.track_id) : true`), so legacy untagged rows never vanish from the lineage.
- **Parent for the diff** — `PromptChanges` diffs against `selectedExperiment.parent_tag` when that variant exists in the track; otherwise it falls back to the next-older experiment in the newest-first list (`trackExperiments[selectedIdx + 1]`), so a variant whose parent was pruned still renders a meaningful diff.
- **Score** — `StockPickerScoreBreakdown` reads `metrics.hurdle_score` first and falls back to `metrics.score`; when neither is a number it renders the `Pending Evaluation` notice describing the rolling 5-session window and the Sunday 6:00 PM ET cadence.

* **Normalized Ratchet Hurdle Score Audit** (`StockPickerScoreBreakdown.tsx`): renders the formula substitution bar (`Score = 0.50 * Hit_Rate + 0.40 * clamp(50 + LS_Alpha * 10, 0, 100) + 0.10 * Conviction_Norm`), a `Sessions Evaluated` badge, a solid `Hurdle Score: N` badge (success at ≥ 50, danger below), and three weighted pillar tiles (Directional Hit Rate 50%, L/S Spread Alpha 40% with its normalized value, Conviction Calibration 10%). When no score is stored it renders a `Pending Evaluation` notice describing the rolling 5-session window. `clampNormalizedAlpha(lsAlphaPct)` is exported for direct testing.

### Where To Read The Picks

`https://www.benchify.dev/daily-predictions?ticker=PICKS` opens the 3 UP / 3 DOWN tab directly (the `PICKS` value is accepted by the route's `validateSearch` in `apps/web/src/routes/daily-predictions/index.tsx`; `SPY` and `TLT` are accepted too, and any other value normalizes to `SPY`). Without the query param the page lands on SPY and the tab must be clicked — see [[concepts/unified-daily-predictor]] for why the validator must round-trip every value it accepts.

The route loader delegates to `loadDailyPredictionsPageData()` (`apps/web/src/features/daily-predictions/api/load-daily-predictions-page-data.ts`), which fetches predictions, daily predictor experiments, `fetchDailyStockBaskets()`, and `fetchStockPickerExperiments()` (`STOCK_PICKER_PROMPT` rows from `prompt_experiments` with `is_backtest = false`, via `apps/web/src/features/daily-predictions/api/fetch-daily-predictions.ts`) in one `Promise.allSettled`. The baskets payload is what the picks view renders — a loader that omits it leaves the tab permanently on its empty state ("No active stock picks found for selected model track"), which is exactly how the surface silently broke before the aggregator existed. The `stockExperiments` payload feeds the autoresearch view and degrades to an empty list (logged, never thrown) if the query fails.

### Bounded Pick Scan (Newest Basket Per Track)

`fetchDailyStockBaskets()` (`apps/web/src/features/daily-predictions/api/fetch-stock-picks.ts`) narrows the child-pick query with `latestBasketIdsByModel(baskets)`: it walks the newest-first basket list, keeps the first basket id seen for each `model_name`, and issues one `daily_stock_picks` query scoped with `.in('basket_id', latestBasketIds)` ordered by `rank`.

Only the newest basket of each track is rendered as a 3 UP / 3 DOWN card set, and the historical ledger table reads basket-level pre-materialized metrics only. Fetching picks for every historical basket would grow the payload unbounded with nothing to render, so the pick scan stays bounded by model count rather than by session count (see [[concepts/zero-frontend-compute]]).

## 8. Provider Client Contract

`execute_model_picker` (`apps/engine/tasks/stock_picker.py`) resolves one instructor client per provider through the declarative `PROVIDER_CLIENTS` map (an unknown provider raises `ValueError` instead of silently falling through to another vendor), then builds the call with the shared `build_provider_extraction_args()` helper (`apps/engine/core/llm/analysis_pipeline/prompt_assembly.py`) used by the rest of the analysis/extraction stack:

| Provider | Client | Args from the shared builder |
| :--- | :--- | :--- |
| `deepseek` | `get_deepseek_client()` | `max_retries=2`, schema-recovery handling; no `temperature` |
| `minimax` | `get_minimax_client()` (Anthropic-format) | `max_tokens=32000`, system message hoisted to the `system` kwarg; no `temperature` |
| `openai` | `get_openai_json_client()` (`Mode.JSON`, no tool injection) | `reasoning_effort="none"` — `gpt-6-luna` is a reasoning model that rejects function tools and any non-default temperature on `/v1/chat/completions` |

Re-implementing per-provider kwargs inline would fork the token ceiling and reasoning contract from every other extraction call site, so the arena deliberately owns only client selection. `close_client(client, provider)` requires the provider argument; every track closes in a `finally` block so a failed model does not leak its HTTP client.

## 9. Rerun Safety & Append-Only Sessions

`persist_stock_basket` writes the basket row with `status='pending'` and explicitly nulls `directional_hit_rate`, `mean_long_return_pct`, `mean_short_return_pct`, `ls_spread_alpha_pct`, `excess_alpha_vs_spy_pct`, `benchmark_spy_return_pct` and `evaluated_at`, so a rerun cannot leave a pending basket carrying stale graded metrics.

Picks are replaced by the `replace_daily_stock_picks(p_basket_id, p_picks)` RPC (`supabase/migrations/20261113130000_create_replace_daily_stock_picks_rpc.sql`), which runs the delete and the insert of the 6 picks inside one transaction. Two independent PostgREST round-trips could leave a basket with zero picks on a crash between them, and the rerun guard only skips dates that already have a consensus basket — an emptied basket would never be repaired.

`session_skip_reason(existing_rows, force)` gates the session:

* Any basket already `evaluated` → skip even with `--force` (`already-evaluated`). Graded sessions carry open/close/return/hit data, feed the `status='evaluated'` filter of `apps/engine/tasks/stock_picker_autoresearch.py`, and must stay immutable.
* A consensus basket exists and `--force` was not passed → skip (`already-exists`).

### Full-Row Batch Upserts (`on_conflict="id"`)

Both the pick and basket write paths merge the graded fields onto the *original* row (`{**orig, ...updates}`) and upsert with `on_conflict="id"`. PostgreSQL evaluates `NOT NULL` constraints on the candidate tuple during `INSERT ... ON CONFLICT DO UPDATE`, so a partial payload (e.g. only `id` + `status`) would be rejected before the `DO UPDATE` branch ever ran. Carrying the source columns through:

* keeps `daily_stock_picks` NOT NULL columns (`basket_id`, `target_date`, `model_name`, `ticker`, `direction`, `rank`, `confidence`) intact,
* keeps `daily_stock_baskets` NOT NULL columns (`target_date`, `model_name`) intact,
* guarantees every row in a batch shares an identical key set, which PostgREST requires for a multi-row upsert,
* and makes `status`, `is_hit`, and the aggregate metrics idempotent on rerun because the same `id` is updated in place rather than re-inserted.

Regression coverage lives in `apps/engine/tests/test_stock_picker_arena.py` and `apps/engine/tests/test_evaluate_stock_picks.py` (hermetic: mocked clients, no network, no sleeps). The evaluation suite's `test_evaluate_stock_picks_full_row_batch_upsert_and_cancelled_basket` asserts uniform keys, `on_conflict="id"`, NOT NULL preservation, sub-cent-open cancellation, and that a cancelled basket clears all six performance metrics.

## 10. System Portfolio Execution (`sys-picks-*`)

Each basket is also paper-executed as a mechanical long/short portfolio by `apps/engine/execution/stock_picks_trading.py`, so the arena's picks produce an equity curve rather than only a grading ledger:

* **Portfolios**: `sys-picks-deepseek-flash`, `sys-picks-MiniMax-M3.1-Flash`, `sys-picks-gpt-6-luna`, and `sys-picks-consensus` (id = `sys-picks-` + the basket's `model_name`, case preserved). Inception `SYS_PICKS_START_DATE = 2026-11-19`; earlier sessions are never backfilled.
* **Sizing**: 50% long / 50% short of equity, equal weight per leg (16.67% notional), 5 bps slippage per side, gross 100% / net 0.
* **Prices**: entry at the official RTH open print (09:31–10:00 ET window, hard cutoff) and exit at the official closing print (16:00–16:05 ET) — the same basis `evaluate_stock_picks.py` grades on, so portfolio PnL and `ls_spread_alpha_pct` reconcile.
* **Ledger**: longs write `BUY` + `portfolio_positions`; shorts write `SHORT`/`COVER` only. `trades.decision_id` = originating basket id. Exits write `portfolio_performance` `(portfolio_id, date)`.
* **Equity is derived, never assigned**: `Portfolio.total_equity` resolves to `metrics.total_equity` and falls back to `cash_balance`, so the exit path never sets it on the object — the persisted `portfolios` column is the truth and is written alongside the `portfolio_performance` snapshot.
* **All-or-nothing close**: if any open leg lacks a close price, the whole session is skipped and stays flagged rather than persisted with an equity that omits the unpriced leg. Re-runs resume: legs that already carry an exit row at that session's `exit_ts` are skipped by ticker, so a crash mid-loop is finished by the next run instead of being blocked forever as `already exited`.
* **Trigger**: MiniPC daemon `run_systematic_strategy_hooks` → `_run_picks_portfolio_hook` (hooks window widened to 16:05 ET), and manually `main.py picks-trade --action entry|exit|status`.
* **Audit**: `portfolio_auditor.py` flags `unliquidated_picks_legs` and liquidates stale legs in `--fix`. See [[concepts/system-portfolios]] §13.

## Related

- [[concepts/system-portfolios]] — mechanical strategies, including the `sys-picks-*` portfolios
- [[entities/daily-market-predictor]] — the SPY and TLT directional arenas
- [[entities/autoresearch]] — the platform auto-research framework
- [[concepts/multi-track-autoresearch]] — parallel isolated model lineages
- [[concepts/zero-frontend-compute]] — pre-materialization architecture
- [[concepts/stochastic-cold-start]] — 1-in-6 dice resets
- [[entities/cli]] — CLI commands `stock-picker`, `evaluate-stock-picks`, `stock-picker-autoresearch`
- [[entities/database]] — `daily_stock_baskets` and `daily_stock_picks` tables
- [[concepts/prompt-section-splitting]] — frozen header/mutable strategy/frozen footer prompt structure
- [[concepts/experiment-display-score]] — `hurdle_score` fallback used by the track cards
- [[concepts/state-machines]] — `pending` → `evaluated` | `cancelled` lifecycle registry
