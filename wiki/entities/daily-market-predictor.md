---
tags: [entity, daily-predictor, prediction, macro, audit]
category: entity
---

# Daily Market Predictor

The daily market predictor (`apps/engine/tasks/daily_predictor.py`) generates a morning directional prediction for a ticker (default `SPY`) before the US market opens. It compiles a rich pre-market context, asks an LLM for a prediction across a four-model arena, and persists the result to `daily_predictions`.

## Model Arena (S&P 500)

The daily predictor arena compares four distinct model architectures:
1. **DeepSeek Flash** (`deepseek-v4-flash`) — Direct thinking/reasoning prompt with structured output via Instructor.
2. **MiniMax** (`MiniMax-M3`) — High-context reasoning LLM with JSON format output.
3. **Jev Baseline** (`~typesafe/jev-latest`) — Direct System One typed classification via OpenRouter Decisions API.
4. **Jev Four-Regime Champion** (`jev-four-regime-champion`) — Evolved via Strata single-prompt ratchet tournament (Iteration 43 Champion, Score 54.34, Win Rate 72.73%, $p = 0.0262$). Promoted to replace deprecated `jev-local-autoresearched`. Uses a tailored **Curated Manifest** ("Box of Data") compiled by `pack_daily_context()`, symmetrical four-regime classification criteria (*Risk-On Expansion*, *Risk-Off Expansion*, *Balanced Pinning*, *Catalyst Shock*), and **Zero Abstention** (forces a binary directional prediction `UP` or `DOWN` on every session).

## Market Context Compilation & Curated Manifests

`get_structured_daily_market_context(ticker, include_full_prior_close)` assembles both the full raw pre-market intelligence string AND a structured data record (`data_record`). Every data source is fetched through the canonical tool dispatcher `core.llm.handlers.base.execute_tool` with `model_name="daily_predictor"`, so each call is measured, logged, and non-blockingly audited to `tool_execution_logs` (see [[entities/tool-audit]]).

Multi-day momentum and trend indicators are calculated by `analytics/trend_profile.py` (`compute_trend_profile`) strictly with zero lookahead (excluding bars on or after the target date) and zero hallucination (SMA20 is strictly `None` when fewer than 20 completed sessions exist). Metrics include:
- Prior session verified close price.
- Rolling 5-day return % (weekly cycle).
- 20-day Simple Moving Average (SMA20) and distance % (monthly cycle, verified history only).
- 3-day direction sequence (e.g. `UP (+0.3%) -> DOWN (-0.2%) -> UP (+0.6%)`).

For standard models, the full narrative context is passed. For `jev-four-regime-champion`, the raw data record is compiled dynamically through `pack_daily_context(data_record, manifest)` into a lean, noise-pruned "Box of Data" adhering to the winning variant's active manifest:
- **Included**: Multi-day momentum & trend vector (`include_trend_vector=True`), prior session intraday technical profile (VWAP, Close Location Value), high-signal proxies (`QQQ`, `IWM`), options positioning, economic releases, and curated newsletters (`Sherwood News`, `Chartr`).
- **Pruned / Excluded**: FX noise (`UUP`), market health barometer, qualitative market feeling.

## Confidence Gating, HOLD Execution, & Zero Abstention

Daily predictions are gated mechanically through `apply_confidence_hold_gate`:
- Standard models predict direction (`UP` or `DOWN`) with confidence $50.0\%–100.0\%$.
- Calls with confidence strictly below `HOLD_CONFIDENCE_THRESHOLD = 56.0%` are automatically gated to `HOLD`.
- Gated `HOLD` predictions enter zero market exposure (100% cash) with `expected_return_pct = 0.0`.
- To prevent cowardice and selective abstention, weekly autoresearch enforces a 75% trade participation hurdle ($\text{participation\_factor} = \min(1.0, \text{trade\_rate} / 0.75)$) and awards move-aware credits ($+52.0$ pts on flat chop, $+45.0$ pts on normal moves, $+35.0$ pts on missed trends).
- Dedicated high-frequency decision classifiers (e.g. `jev-four-regime-champion`) can configure explicit zero abstention (`min_confidence = 0.0%`).
- Database integrity is maintained via `CHECK (predicted_direction IN ('UP', 'DOWN', 'HOLD'))`. See [[concepts/confidence-gating]].


## Daily Bond Predictor (`TLT`)

The daily bond predictor (`apps/engine/tasks/bond_predictor.py`) implements a pure tool-first, pull-based architecture for fixed income (enforcing Principle 8: "Provide Tools, Don't Push Data"):
- **Target Asset**: `TLT` (iShares 20+ Year Treasury Bond ETF, ~17y duration).
- **Prompt Structure**: Initial prompt injects only lean temporal context (date, session, pre-market quote/overnight gap), omitting bulky context tables.
- **Autonomous Tool Loop**: Reasoning models (`gpt-5.6-luna`, `deepseek-v4-flash`) pull data dynamically from a curated fixed-income toolbox (`get_treasury_yield_curve`, `get_today_economic_releases`, `get_yield_curve_regime`, `get_macro_options_sentiment`, `get_calendar_scenario_analysis`).
- **Jev Integration**: Single-turn Decisions API receives an automated lean tool bundle pre-compiled from the yield curve and economic calendar.
- **Portfolios**: Feeds into systematic close-exit portfolios (`sys-daily-tlt-close-{model}`) executed via `apps/engine/execution/daily_bond_trading.py`.

## Scoring & Metrics Surface

- **`DailyMetricsOverview`** shows directional accuracy, intraday hit rate, a **Conviction Score** card (normalised logarithmic confidence term, 50 = coin flip), total predictions, and the active prompt tag. Brier is no longer displayed here.
- **`PredictionsTable`** replaces the old Brier column with a per-row **Conviction** value: the raw `conviction_score` the engine persisted at evaluation time, signed and coloured (green non-negative, red negative, `-` when unscored).
- **`DailyScoreBreakdown`** explains the ratchet arithmetic: `0.90 × (0.55·accuracy + 0.35·intraday hit + 0.10·magnitude capture) + 0.10 × conviction_norm`, with Brier shown as a diagnostic only. See [[entities/daily-score-breakdown]].
- **`DailyPredictionsBacktestPage`** mirrors the live arena with a Conviction Score stat card and a Conviction column in the prediction log.

Scoring itself lives in `apps/engine/core/conviction_scoring.py`; see [[concepts/conviction-points]] for the formula, the properness property, and the ratchet baseline guard.

## Related

- [[concepts/conviction-points]]

- [[concepts/system-portfolios]]
- [[entities/tool-audit]]
- [[entities/tool-registry]]
- [[concepts/hybrid-database-archival]]
- [[entities/macro-options]]
