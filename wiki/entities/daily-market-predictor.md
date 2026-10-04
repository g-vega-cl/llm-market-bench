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

## Idempotency

`run_daily_prediction` refuses to overwrite existing morning predictions for the same ticker and date unless `force=True` is passed.

## Related

- [[entities/tool-audit]]
- [[entities/tool-registry]]
- [[concepts/hybrid-database-archival]]
- [[entities/macro-options]]
