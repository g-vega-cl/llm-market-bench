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
- `get_technical_indicators` — computes RSI-14, MACD, Signal, Histogram, 20D VWAP, SMA-20, SMA-50, RVOL, and 52-week range % for a ticker, with an optional point-in-time `cutoff_date` for backtesting. Implemented in `apps/engine/tools/technicals.py` (`execute_technical_indicators_tool`, `compute_technical_snapshot`). Registered in `CANONICAL_TOOLS_REGISTRY` and `packages/config/tools.json`, marked ticker-required in `TICKER_REQUIRED_TOOLS`, and selectable by the Auto-Researcher (`PromptResearchResult.selected_tools`).
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
- `get_government_fiscal_and_spending` — sovereign money creation, US Treasury General Account (TGA) cash & liquidity impulse, national debt issuance, monthly & FYTD fiscal deficits, US federal budget outlays by category & agency, Canadian federal ministry budgets & YoY growth, G7/G20 global defense & infrastructure spending surges (World Bank & Eurostat), and recent federal contract deals (USAspending & CanadaBuys). Parameters: `country` (`ALL`/`US`/`CA`/`EU`/`INTL`), `ticker`, `recipient`, `limit`. Implemented in `apps/engine/tools/government_tools.py` and re-exported through `tools/macro.py` (see [[entities/government-ingestion]]).
- `get_corporate_spending` — corporate CapEx ($ and YoY %), CapEx/Revenue %, CapEx/OCF %, R&D ($ and % of Revenue), SG&A, share buybacks, dividends, M&A cash spend & filings, Free Cash Flow, ROIC, and matched federal government contract awards for a single ticker or the hyperscaler basket (`MSFT`, `AMZN`, `GOOGL`, `META`, `NVDA`). Parameters: `ticker`, `tickers`, `period` (`quarter`/`annual`), `limit`. Implemented in `apps/engine/tools/corporate_spending_tools.py` and re-exported through `tools/valuation.py`.
- `audit_price_overreaction` — audits sharp stock price drops or surges against normalized return distributions ($Z$-score), capitulation volume (RVOL), options-implied daily move cones, and analyst consensus revisions to classify moves into `STATISTICAL_OVERREACTION` (mean-reversion opportunity), `JUSTIFIED_REPRICING` (structural target cut warning), or `NORMAL_VOLATILITY`. Parameters: `ticker`, `lookback_days`. Implemented in `apps/engine/tools/overreaction.py`.
- `get_high_iv_ratio_watchlist` — screens stocks with the highest ratio of 30-day ATM Implied Volatility to 20-day Historical Realized Volatility (IV/HistIV), identifying `COILED_SPRING_EXTREME` setups ($\ge 1.8\times$) bracing for impending binary catalysts or extreme pricing dislocations across mega/mid caps, portfolio holdings, or custom universe. Parameters: `universe`, `custom_tickers`, `min_ratio`, `limit`. Implemented in `apps/engine/tools/technicals_options.py`.

## Related

- [[entities/tool-audit]]
- [[concepts/tool-enforcement]]
- [[entities/daily-market-predictor]]
- [[concepts/system-portfolios]]
- [[entities/government-ingestion]]
