---
tags: [entity, tools, dispatch, llm]
category: entity
---

# Tool Registry

`TOOL_DISPATCH_TABLE` in `apps/engine/core/llm/handlers/base.py` maps tool names to their executor lambdas. `execute_tool(name, args, model_name)` looks up the name, invokes the executor, and wraps the call in audit logging via `async_record_tool_audit` (see [[entities/tool-audit]]).

## Dispatch Entries

The table covers market data, options, macro, valuation, screening, research, and prediction-market tools. Notable entries include:

- `get_options_sentiment` — single-ticker options sentiment
- `get_macro_options_sentiment` — cross-asset macro options skew; defaults `primary_ticker` to the calling ticker or `SPY`
- `get_option_chain` — full option chain for a ticker/expiration
- `get_volatility_metrics`, `get_volatility_index_details`
- `audit_financial_valuation`, `get_sector_alternatives`, `find_uncorrelated_assets`, `run_stock_screener`
- `web_search`, `get_ticker_news`, `get_market_moving_news`, `search_prediction_markets`, `get_prediction_market_odds`
- `get_calendar_scenario_analysis`, `get_today_economic_releases`, `get_global_macro_context`, `get_market_health_barometer`, `get_market_feeling`
- `get_position_pnl` — detailed profit & loss statistics for open model positions
- `get_system_portfolios` — inspects mechanical baseline system portfolios (mean-reversion, momentum, sector long/short, intraday SPY) returning holdings, mark-to-market unrealized PnL, trailing returns, and quantitative signals without prompt bloat (see [[concepts/system-portfolios]])
- `search_related_tickers` — thematic keyword stock searches
- `get_verifier_rejections` — past trade compliance rejection logs and verifier feedback
- `get_thematic_flows`, `add_thematic_flow` — retrieve active thematic flows and register new narrative signals
- `get_catalyst_radar` — high-velocity market concepts paired with upcoming and digesting calendar triggers
- `analyze_thematic_beneficiaries` — screens second-order winners and thematic beneficiaries via correlation and co-ownership
- `call_warren_buffett` — value investing analysis, margin of safety, moat quality, debt sanity, and the Munger Inversion test
- `get_treasury_yield_curve` — US Treasury yields across key tenors (3M, 2Y, 5Y, 10Y, 30Y) and 1-day basis point changes from FRED

## Related

- [[entities/tool-audit]]
- [[concepts/tool-enforcement]]
- [[entities/daily-market-predictor]]
- [[concepts/system-portfolios]]
