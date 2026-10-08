---
tags: [entity, daily-predictor, prediction, macro, audit]
category: entity
---

# Daily Market Predictor

The daily market predictor (`apps/engine/tasks/daily_predictor.py`) generates a morning directional prediction for a ticker (default `SPY`) before the US market opens. It compiles a rich pre-market context, asks an LLM for a prediction, and persists the result to `daily_predictions`.

## Market Context Compilation

`get_daily_market_context(ticker, include_full_prior_close)` assembles the pre-market intelligence block injected into the prediction prompt. Every data source is fetched through the canonical tool dispatcher `core.llm.handlers.base.execute_tool` with `model_name="daily_predictor"`, so each call is measured, logged, and non-blockingly audited to `tool_execution_logs` (see [[entities/tool-audit]]).

The context includes:

- **Today's economic releases** — `get_today_economic_releases`
- **Forward high-impact calendar scenarios** — `get_calendar_scenario_analysis`
- **Options derivatives positioning & cross-asset skew** — `get_macro_options_sentiment`
- **Prior session macro baseline** — `get_global_macro_context`
- **Volatility index details** — `get_volatility_index_details`
- **Market health barometer** — `get_market_health_barometer`
- **Recent market feeling** — `get_market_feeling`
- **Daily newsletter** — `execute_fetch_daily_newsletter_tool`

Routing through `execute_tool` keeps the predictor's background compilations audited with zero Supabase storage quota impact, while the synthesized `daily_predictions.market_context` is preserved for presentation in the web viewer.

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
