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

## Zero Abstention & Binary Direction Enforcement

Per the Zero Abstention invariant (see [[concepts/confidence-gating]]), all models in the arena are strictly required to predict either `UP` or `DOWN`. Confidence gating to `NO_TRADE` is deprecated and prohibited across the live pipeline. Low-conviction regimes are reflected through lower confidence percentages (e.g. $51\%–54\%$), while database integrity is preserved against the canonical schema constraint `CHECK (predicted_direction IN ('UP', 'DOWN'))`.


## Daily Bond Predictor (`TLT`)

The daily bond predictor (`apps/engine/tasks/bond_predictor.py`) implements a pure tool-first, pull-based architecture for fixed income (enforcing Principle 8: "Provide Tools, Don't Push Data"):
- **Target Asset**: `TLT` (iShares 20+ Year Treasury Bond ETF, ~17y duration).
- **Prompt Structure**: Initial prompt injects only lean temporal context (date, session, pre-market quote/overnight gap), omitting bulky context tables.
- **Autonomous Tool Loop**: Reasoning models (`gpt-5.6-luna`, `deepseek-v4-flash`) pull data dynamically from a curated fixed-income toolbox (`get_treasury_yield_curve`, `get_today_economic_releases`, `get_yield_curve_regime`, `get_macro_options_sentiment`, `get_calendar_scenario_analysis`).
- **Jev Integration**: Single-turn Decisions API receives an automated lean tool bundle pre-compiled from the yield curve and economic calendar.
- **Portfolios**: Feeds into systematic close-exit portfolios (`sys-daily-tlt-close-{model}`) executed via `apps/engine/execution/daily_bond_trading.py`.

## Related

- [[concepts/system-portfolios]]
- [[entities/tool-audit]]
- [[entities/tool-registry]]
- [[concepts/hybrid-database-archival]]
- [[entities/macro-options]]
