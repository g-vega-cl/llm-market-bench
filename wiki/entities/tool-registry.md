---
tags: [tools, configuration, source-of-truth, entity]
category: entity
---

# Tool Registry

The centralized canonical tool registry at `packages/config/tools.json` is the single source of truth for all trading agent tools. It lists every tool name and description that the analysis agents, the frontend autoresearch arena, and the auto-researcher prompt documentation must be consistent with.

## Purpose

- Eliminate drift between the engine's tool definitions (`core/llm/tools.py`), the frontend's tool display (`ExperimentDetails.tsx`), the research prompt (`autoresearch/program.md`), and the JSON tool list used for LLM function calling.
- Provide a single importable source for the TanStack Start dashboard and any future consumers.

## Architecture & Domain Decomposition

To prevent monolithic bloat and uphold [[concepts/vertical-slice-islands]], tool implementations are decomposed across dedicated domain modules in `apps/engine/tools/`:
- `tools/market_data.py`: Quote, price history, intraday movement profiles, ticker news, volume context.
- `tools/prediction_markets.py`: Polymarket and Kalshi search and odds.
- `tools/portfolio.py`: Position PnL, buy/sell sizing, ledger queries, system portfolios.
- `tools/technicals_options.py`: Volatility metrics, screeners, options chains, vol surfaces, touch probabilities.
- `tools/macro.py`: Macro context, volatility index details, FRED series, yield curve, economic releases.
- `tools/earnings.py`: Sector alternatives, related tickers, earnings history, PEAD candidates, revisions, bellwethers.
- `tools/valuation.py`: Key metrics, market health barometer, sector fundamentals, 5-year DCF audit.
- `tools/news_memories.py`: Newsletters, pgvector memory search, thematic flow persistence, market feeling, web search.
- `tools/analyst_personas.py`: Warren Buffett/Munger audit, historical market analogs, future forces, thematic beneficiaries.
- `tools/compliance.py`: Verifier rejections, SOP inspection, thesis pillar tracking, catalyst radar, calendar scenarios, STOCK Act congress trades.

The canonical barrel in `core/llm/tools.py` maintains backward-compatible re-exports, provider adapters (`to_anthropic`, `to_gemini`), and declarative schemas, while `core/llm/handlers/base.py` executes calls via an $O(1)$ `TOOL_DISPATCH_TABLE` lookup table.

## Drift Prevention

`test_tools_consistency.py` and `test_tools_domain_decomposition.py` automatically verify that every tool in `tools.json` has a matching canonical definition in `core/llm/tools.py`, domain handler implementation in `apps/engine/tools/`, is documented in `PromptResearchResult.selected_tools`, and appears in `autoresearch/program.md`.

## Tool Coverage

The registry includes, among others:
- Portfolio & PnL tools (`get_portfolio_ledger`, `get_position_pnl`, `get_price_history`)
- News & feeling tools (`get_todays_news_menu`, `fetch_newsletter_content`, `get_market_feeling`)
- Screening & analysis tools (`run_stock_screener`, `find_uncorrelated_assets`, `get_key_metrics`, `search_related_tickers`, `analyze_thematic_beneficiaries`)
- Earnings Alpha & PEAD tools (`get_pead_candidates`, `get_earnings_revisions`, `get_sector_bellwethers`, `get_earnings_history`)
- Prediction market tools (`search_prediction_markets`, `get_prediction_market_odds`)
- Macro & volatility tools (`get_global_macro_context`, `get_volatility_index_details`, `get_macro_economic_series`, `get_thematic_flows`, `add_thematic_flow`, `get_options_sentiment`, `get_option_chain`, `research_historical_market_analog`)
- Quantitative FSI tools (`get_yield_curve_regime`, `get_options_vol_surface`, `track_thesis_pillars`, `get_catalyst_radar`, `get_intraday_movement_profile`)
- Audit & compliance tools (`audit_financial_valuation`, `get_verifier_rejections`, `call_warren_buffett`)

## Related

- [[entities/engine]]
- [[entities/autoresearch-arena]]
- [[concepts/tool-enforcement]]
- [[concepts/anthropic-fs-insights]]

