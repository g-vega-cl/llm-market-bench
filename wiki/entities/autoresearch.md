---
tags: [entity, auto-research, prompt-improvement]
category: entity
---

# Auto-Research Module

The `apps/engine/autoresearch/` module implements the Karpathy-style autonomous prompt improvement loop. A meta-researcher LLM evaluates weekly live trading performance and iteratively improves the trading prompt.

## Configuration

The auto-research system is configured via:
- `packages/config/models.json`: Defines `AUTORESEARCH_EXPERIMENT_OWNER_IDS` and `AUTORESEARCH_TRACKS` (mapping track IDs to portfolio/model owner groups) and `SKIP_VERIFIER_OWNER_IDS` (models bypassing skeptical verification).
- `apps/engine/core/config.py`: Loads model names, tracks, and verifier bypass settings from `models.json`.
- `AUTORESEARCH_MODEL`: Environment variable (defaults to DeepSeek) used for the meta-researcher.

## Architecture

The auto-research loop runs weekly:
1. **Safety check** — did the prompt crash trading (< 2 trades)? If so, revert to baseline via `revert_to_previous()` and immediately proceed to Step 4 to generate a fresh candidate prompt off the baseline for the upcoming week.
2. **Evaluate** — compute a single score: `(portfolio_return% - SPY_return%) - Opportunity Cost% - (max_drawdown% × 0.3)`. Update the completed week's metrics directly on the active prompt row (`P_active`) that actually ran during the week. Find the baseline (best score so far) and show Δ.
3. **Revert on failure** — if score < baseline, revert the active prompt to the baseline via `revert_to_baseline()`. This revert happens **before** generating the new prompt in Step 4. This enforces the Karpathy ratchet: the meta-researcher always builds from the known-good foundation, never from a failed experiment.
4. **Research** — LLM proposes a new prompt variant (incremental or radical) building on top of the **post-revert baseline**.
5. **Deploy** — always activate the new variant generated in step 4. Save it as a new database row with empty metrics (`{}`), status `active`, and scheduled for the upcoming week (advanced by 7 days from the prior week).
6. **Track** — if this week's score > baseline, it becomes the new baseline (best prompt+score pair). The baseline only moves up.

## Pull-Based Tool-Selection & System-Heavy Prompt Architecture

To keep prompts compact and empower the trading agent to autonomously seek information when needed, the system uses a **Pull-Based Tool-Selection** architecture combined with a **System-Heavy** split:

- **System Prompt (The Rulebook)**: Contains 100% of the trading logic, risk management (SMA rules), SOPs (5-Whys), and tool-usage requirements. This part is stored in the database and is mutated by the meta-researcher.
- **Dynamic Tool Selection (Weekly Toolbox Selection)**: The meta-researcher decides which tools from the toolbox are enabled for the trading agent during the upcoming week (e.g., pulling newsletters, retrieving the XML portfolio ledger, fetching market sentiment).
- **User Prompt (Static Trigger & Schema)**: Stripped of all automatic data injection (no pre-loaded newsletters or portfolio ledger XML). It is reduced to a minimal static trigger containing today's date context and the hardcoded output JSON schema constraints (frozen, cannot be altered by the meta-researcher).

This decouples the "Brain" (System and tool choices) from the "Environment" (User prompt), allowing the Auto-Research engine to optimize not just the guidelines of the agent but its cognitive tools and info-gathering strategy itself.

## Prompt Status Lifecycle

Every variant saved in the `prompt_experiments` table transitions through a structured status lifecycle:
- **`active`**: The prompt variant that is currently trading/predicting in the live market for the active trading week.
- **`baseline`**: The single best-performing evaluated prompt variant (all-time highest score) that serves as the foundation for future mutations.
- **`saved`**: A historical prompt variant that once served as a baseline but has since been surpassed by a higher-scoring prompt.
- **`discarded`**: An experiment variant that underperformed the baseline and was discarded. The system automatically reverts the active pointer back to the baseline prompt.
- **`crashed`**: A variant that caused a trading crash (fewer than 2 trades executed during its active week), triggering the safety checker's revert action.

## Files

- [program.md](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/autoresearch/program.md) — the meta-researcher's instructions (constraints and goals)
- `metrics.py` — Wall Street metrics computation + `compute_score()`
- `evaluator.py` — gathers weekly data, computes baseline, formats report
- `researcher.py` — calls DeepSeek v4 Pro with structured output
- `runner.py` — orchestrates the weekly evaluation and deployment cycle
- `prompt_store.py` — DB operations for prompt_experiments
- `bootstrap.py` — initializes the baseline variant (score = 0)
- `window.py` — shared week-window helper

## Key Design Decisions

- **Single score**: One number to optimize — risk-adjusted return vs SPY. No composite of 8 dimensions.
- **No validator**: Removed. The safety checker (< 2 trades → revert) is the only guardrail. Trust the process.
- **Always deploy**: Every week deploys a new prompt. No gate. The meta-researcher always explores.
- **Hard ratchet**: When an experiment fails to beat the baseline, `revert_to_baseline()` is called to set the active prompt back to the baseline before the next experiment. Code-level enforcement — not just instructions to the LLM.
- **Baseline tracking**: The highest score achieved so far (tied to its prompt). The meta-researcher's target. Only moves up. *Note: Variants without a `"score"` key in their metrics (such as the pre-May-12 composite metrics or explicitly demoted variants using `"old_score"`) are ignored by `get_all_time_baseline()`.*
- **System-Heavy Evolution**: Moving logic from User to System prompt to ensure 100% of the trading "SOP" can be improved by the LLM.
- **Control portfolios are reference only**: Shown in the report but not part of the score.
- **Volatility Tracking**: Calculates annualized standard deviation of daily returns into metrics tracking.

## Score Formula

```
hurdle_pct = bond_return_pct
penalty_opp = max(0.0, hurdle_pct - portfolio_return_pct)
excess_return = (portfolio_return_pct - spy_return_pct) + (portfolio_return_pct - do_nothing_return_pct)
score = excess_return - penalty_opp - (max_drawdown_pct × 0.3)

Baseline = max(all previous scores) — the bar to beat. Only moves up.
The meta-researcher's report shows: "Baseline: X (best so far)  (Δ: +/-Y vs baseline)"
```

- **Dual-Benchmark Excess Return**: Evaluates the agent against both the absolute S&P 500 (`spy_return_pct`) and the "Do-Nothing" portfolio (`do_nothing_return_pct`), directly measuring the active trading value-add over simply holding the inherited positions. To ensure pricing accuracy and prevent calculation drift from stale values:
  - **On-Demand Synchronization**: The evaluation engine dynamically pre-populates/updates `price_history` for all held assets at evaluation time via `MarketDataManager.get_history()`. This pulls fresh close prices from the financial provider (FMP), ensuring both active portfolio-specific tickers and legacy positions are correctly valued at the end of the week (`week_end`).
  - **Freshness Guardrail**: The pricing query retrieves the last known price up to `week_end` individually for each asset. It actively validates the age of the retrieved price and logs a `CRITICAL METRIC ERROR` if the price timestamp (`fetched_at`) is older than 4 days before `week_end`, preventing any silent database omissions or stale valuation errors.
  - **Factual Audit Ledger**: The evaluation engine compiles a granular positions ledger (`portfolio_details`) including position quantity (`qty`), starting price (`start_price`), starting value (`start_value`), ending price (`end_price`), and ending value (`end_value`). Additionally, it maps the exact fetched date and hour (`YYYY-MM-DD HH:MM`) of when each start and end price was recorded in the database, allowing users to verify price factualness and account for weekends or market holidays.
  - **Mathematical Transparency & Portfolio Breakdown**: The frontend day-by-day score inspection ledger exposes the exact base equations and formula derivations. Furthermore, it displays a breakdown of individual constituent model portfolios (e.g., Gemini 3.1 Flash Lite, DeepSeek V4 Pro) with their specific base and scaled actual/do-nothing returns, letting users trace daily scores back to individual portfolio metrics.
- **Dynamic Treasury Bond Hurdle**: Annually-reported 10-year Treasury yield (`year10`) fetched from FMP and compounded to the exact duration of the evaluation window. This serves as the active risk-free rate hurdle.
- **Dynamic USD Index Return (Context Only)**: Actual weekly return percentage of `UUP` (US Dollar Index ETF proxy for DXY) fetched from FMP, displayed in the report for macroeconomic context only (no active penalty).
- **Asymmetric Penalty**: Applied only if the portfolio returns fail to clear the active Treasury Bond hurdle.

## Recent Changes

- **2026-07-31**: **Multi-Track Isolation, Stochastic Cold-Start Reset & Verifier Bypass** — Added `track_id` parameter to `prompt_store.py` and `prompt_experiments` DB table, enabling multiple isolated AutoResearcher tracks (e.g. `track_default`, `track_claude`, `track_openai`) to optimize distinct portfolio groups without prompt overwrite collisions. Implemented `SKIP_VERIFIER_OWNER_IDS` in `main.py` allowing fast models (e.g. DeepSeek Flash, MiniMax) to bypass skeptical verification. Added stochastic cold-start reset helper (`get_next_cold_start_interval`, random 2–5 weeks) and `run_research(cold_start=True)` to break out of local optima by constructing fresh prompt strategies from scratch.
- **2026-07-28**: **Backtest Trade Telemetry & Audit Ledger UI** — Updated `evaluate_backtest_week` in `backtest_autoresearch.py` to query local SQLite simulation trade ledgers and persist executed trades directly inside `metrics["trades"]` on `prompt_experiments`. Built `BacktestTradesAudit` React component in `apps/web/src/features/autoresearch/components/` and integrated it into `ExperimentDetails.tsx`, allowing full point-in-time auditing of ticker, signal, quantity, execution price, cost, PnL, and agent decision thesis for every backtest run.
- **2026-07-25**: **Active Week SPY Return Priority & Ungated Fetching in UI** — Fixed `DailyScoreDisplay` to query and prioritize actual `SPY` price history from `price_history` for active experiment tracking, overriding preset/default `spy_return_pct` values (e.g. `0.85%`). Removed the `portfolioIds.length === 0` early-return gate in `useEffect` so that `SPY` price history is fetched even when `metrics.portfolio_details` is `{}` for a newly active experiment.
- **2026-07-24**: **Backtest Sandbox Isolation & Evaluator Math Fix** — Added `portfolio_performance` table sandboxing to prevent simulated backtest snapshots from leaking into the production database (preventing frontend chart contamination). Updated the backtest weekly return calculation logic in `evaluate_backtest_week` to compute returns using `total_equity` (including held stock value) rather than `cash_balance` (which was negative due to margin loans), fixing the artificial `-143.12%` return report. Added direct "Backtests" navigation link to the layout header.
- **2026-07-23**: **Dynamic Database-Backed Active Returns in UI** — Updated the frontend day-by-day score inspection component to query and calculate actual S&P 500 (SPY) returns from `price_history` and agent portfolio returns from `portfolio_performance` dynamically for the active/running week. This replaces static placeholder fallbacks (`0.85%` for SPY and `1.45%` for portfolio returns) with real-time database-driven calculations.
- **2026-07-22**: **Global Macro & Volatility Toolbox Expansion** — Added `get_global_macro_context` and `get_volatility_index_details` to the allowed tool list in `program.md`, enabling pull-based experiment agents to actively query volatility percentiles, trends, term structure (VIXY/VIXM), and correlation coefficients with SPY.
- **2026-07-20**: **Pull Baseline Isolation & Query Filtering** — Enforced strict pull-based baseline isolation in `prompt_store.get_all_time_baseline()` by requiring variants to contain a non-empty `selected_tools` list in `research_output`. This prevents legacy pre-pull push variants (e.g. `v20260705-221937`) from contaminating the meta-researcher's prompt mutation foundation. Promoted `v20260712-223711` to `baseline` status in Supabase while preserving its evaluated score of `-4.5858`.
- **2026-07-17**: **Default Pull Baseline & Robust Fallback** — Established the pull-based tool-calling model as the default baseline for auto-research. Updated bootstrap scripts to pre-populate variant `research_output` metadata with default selected tools (`get_portfolio_ledger`, `get_todays_news_menu`, `web_search`), and implemented robust fallback logic in the trading execution loop to automatically default to these pull-based tools if variant metadata is missing.
- **2026-07-14**: **Detailed audit breakdown and portfolio constituents in DailyScoreDisplay** — Added mathematically transparent base equations, formula derivations, and constituent model portfolios list displaying individual base/scaled actual and do-nothing returns to allow easy auditing of daily calculations.
- **2026-07-09**: **Pull-Based Meta-Evolutionary Tool Selection Architecture** — Converted the trading agent from a push-based data-injection model to a pull-based tool-calling model. The meta-researcher (autoresearcher) now dynamically selects which tools are enabled for the agent each week by outputting a list of string names in `selected_tools`. The system automatically wraps these selections, force-injects execution safety tools (`calculate_buy_quantity`, `calculate_sell_quantity`), intercepts the generic `web_search` to map to native provider search capabilities, and strips portfolio ledger data/newsletter menus from the user prompt (reducing the user prompt to a minimal trigger with date context and hardcoded output JSON format).
- **2026-06-27**: **Continuous Crash Recovery Generation** — Updated `runner.py` so that when a prompt variant triggers the safety checker (< 2 trades), the runner demotes the crashed variant, restores the active baseline, and immediately proceeds with auto-research generation to deploy a new candidate prompt off the baseline for the upcoming trading week. Added `TestCrashRecoveryContinuesGeneration` test coverage.
- **2026-07-27**: **Benchmark-Triad Weighted Model (Approach 3 Migration)** — Refactored the score evaluation formula from an unweighted multi-benchmark sum with an asymmetric double-penalty to a normalized **Benchmark-Triad Composite Model** ($0.4 \times \text{vs. SPY} + 0.4 \times \text{vs. Do-Nothing} + 0.2 \times \text{vs. 10Y Treasury Bond} - 0.3 \times \text{Drawdown}$). This eliminated double-counting penalties for sub-hurdle returns, provided a clean 1:1 return optimization signal for the meta-researcher LLM, and updated UI cards to display positive/negative `Risk-Free Excess (vs 10Y Bond)` cleanly.
- **2026-06-01**: **Granular Valuation Ledger & Auditable Starting Prices/Hours** — Expanded the do-nothing return calculations and React dashboard to display exact initial vs. ending stock prices, starting/ending values, and the precise date and hour (`YYYY-MM-DD HH:MM`) when the database price records were fetched. Backfilled last week's active prompt experiment `v20260524-221848` in Supabase with complete granular hourly valuation ledger records.
- **2026-05-31**: **Do-Nothing Legacy Position Valuations & DB Corrected Backfill** — Resolved a critical evaluation bug where legacy held positions without active trading activity for >14 days were omitted from end-of-week price history snapshots and valued at $0.00, artificially tanking the "Do-Nothing" return to -38.33%. Modified `_do_nothing_return` in `metrics.py` to retrieve the latest known price up to `week_end` individually for each asset (removing the 14-day lookup limit). Backfilled the active prompt experiment (`37b238f1-96c6-4c98-9743-2c3f9ed980bd`) with the recalculated correct metrics (score: 8.4638, do_nothing_return_pct: -3.3962%).
- **2026-05-29**: **Do-Nothing Formula Presentation & Instruction Alignment** — Aligned the meta-researcher's system instructions (`program.md`), the scoring methodology UI (`ScoreCalculation.tsx`), and the visual score breakdown UI (`ScoreBreakdown.tsx`) to represent the correct dual-benchmark score formula including both `SPY` and `Do-Nothing` portfolio return comparisons.

- **2026-05-25**: **Metrics & Baseline Ratchet Alignment** — Refactored the runner to update performance metrics directly on the active prompt row that actually ran, while initializing the newly generated active prompt with empty/N/A metrics and advancing its week dates by 7 days for the upcoming trading week.
- **2026-05-24**: **Volatility & Score Breakdown UI** — Added `volatility` (annualized standard deviation) metric computation in the engine. Built a new Score Breakdown UI component to visually explain the arithmetic of the risk-adjusted scoring formula on the web app's experiment details screen.
- **2026-05-24**: **Resilience & Execution Alignment** — Documented multi-agent system overview and verified overall pipeline integrity, ensuring zero-warning enforcement and clean wiki links.
- **2026-05-20**: **USD Strength Decoupling** — Decoupled the USD Index return from the opportunity cost penalty calculation (retaining it in the weekly report and database payload for macroeconomic context only) and set the Treasury Bond yield as the sole active hurdle.
- **2026-05-20**: **Dynamic Hurdles Integration** — Integrated actual Treasury Bond yields and actual USD strength returns (via `UUP` ETF proxy) fetched dynamically from the FMP API into the scoring formula as an asymmetric opportunity cost penalty.
- **2026-05-19**: **System-Heavy Refactor** — Moved all 16 logic points, SMA rules, and output definitions from the static User prompt to the evolvable System prompt. Reduced User prompt to a data-only skeleton.
- **2026-05-13**: Hard ratchet — `revert_to_baseline()` enforces Karpathy pattern.
- **2026-05-12**: Always deploy — removed activation gate. Every week gets a new prompt regardless of score.
- **2026-05-12**: Baseline tracking — baseline is max historical score, not last week's score. With tests.
- **2026-05-12**: Major simplification — removed validator.py, decision_quality.py. Replaced 8-dimension composite score with single formula. Dropped VIXY regime queries, concordance, conviction calibration, mistake patterns, sample trades, and stagnation checks.

## Related

- [[concepts/auto-research-prompt-improver]] — the concept behind this module
- [[entities/engine]] — the parent engine
