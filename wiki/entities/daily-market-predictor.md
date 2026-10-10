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
4. **Jev Local Champion** (`jev-local-autoresearched`) — Evolved via local Strata/Qwen autoresearch (`qwen-jev-243de1`). Uses a tailored **Curated Manifest** ("Box of Data") compiled by `pack_daily_context()`, observable multi-signal criteria, and **Confidence Gating** below 61.0% routing to `⚡ NO TRADE` (`predicted_direction = 'NO_TRADE'`).

## Market Context Compilation & Curated Manifests

`get_structured_daily_market_context(ticker, include_full_prior_close)` assembles both the full raw pre-market intelligence string AND a structured data record (`data_record`). Every data source is fetched through the canonical tool dispatcher `core.llm.handlers.base.execute_tool` with `model_name="daily_predictor"`, so each call is measured, logged, and non-blockingly audited to `tool_execution_logs` (see [[entities/tool-audit]]).

For standard models, the full narrative context is passed. For `jev-local-autoresearched`, the raw data record is compiled dynamically through `pack_daily_context(data_record, manifest)` into a lean, noise-pruned "Box of Data" adhering to the winning variant's active manifest:
- **Included**: Prior session intraday technical profile (VWAP, Close Location Value), high-signal proxies (`QQQ`, `IWM`), options positioning, economic releases, and curated newsletters (`Sherwood News`, `Chartr`).
- **Pruned / Excluded**: FX noise (`UUP`), market health barometer, qualitative market feeling.

## Confidence Gating & Evaluation

Predictions with confidence below the model's threshold (e.g. $61.0\%$ for the local champion) are classified as `NO_TRADE`. In `apps/engine/tasks/evaluate_daily_predictions.py`, `NO_TRADE` outcomes are recorded with `is_correct = None` and `brier_score = None`, protecting portfolio capital and win rate during low-conviction market regimes.


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
