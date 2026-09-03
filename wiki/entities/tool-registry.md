---
tags: [tools, configuration, source-of-truth, entity]
category: entity
---

# Tool Registry

The centralized canonical tool registry at `packages/config/tools.json` is the single source of truth for all trading agent tools. It lists every tool name and description that the analysis agents, the frontend autoresearch arena, and the auto-researcher prompt documentation must be consistent with.

## Purpose

- Eliminate drift between the engine's tool definitions (`core/llm/tools.py`), the frontend's tool display (`ExperimentDetails.tsx`), the research prompt (`autoresearch/program.md`), and the JSON tool list used for LLM function calling.
- Provide a single importable source for the TanStack Start dashboard and any future consumers.

## Structure

The file is a JSON array of objects, each with:

- `name` — the exact function name used in LLM tool definitions and prompt documentation
- `desc` — a short human-readable description

Current tools: 35 entries covering portfolio ledger, news, market data, prediction markets, macro indicators, thematic flows, earnings alpha, and quantitative options/macro regimes.

## Drift Prevention

`test_tools_consistency.py` automatically verifies that every tool in `tools.json` has a matching canonical definition in `core/llm/tools.py`, is documented in `PromptResearchResult.selected_tools` description, and appears in `autoresearch/program.md`. This test runs as part of the engine test suite.

## Tool Coverage

The registry includes, among others:
- Portfolio & PnL tools (`get_portfolio_ledger`, `get_position_pnl`, `get_price_history`)
- News & feeling tools (`get_todays_news_menu`, `fetch_newsletter_content`, `get_market_feeling`)
- Screening & analysis tools (`run_stock_screener`, `find_uncorrelated_assets`, `get_key_metrics`, `search_related_tickers`)
- Earnings Alpha & PEAD tools (`get_pead_candidates`, `get_earnings_revisions`, `get_sector_bellwethers`, `get_earnings_history`)
- Prediction market tools (`search_prediction_markets`, `get_prediction_market_odds`)
- Macro & volatility tools (`get_global_macro_context`, `get_volatility_index_details`, `get_macro_economic_series`, `get_thematic_flows`, `add_thematic_flow`, `get_options_sentiment`, `get_option_chain`)
- Quantitative FSI tools (`get_yield_curve_regime`, `get_options_vol_surface`, `track_thesis_pillars`)
- Audit & compliance tools (`audit_financial_valuation`, `get_verifier_rejections`)

## Related

- [[entities/engine]]
- [[entities/autoresearch-arena]]
- [[concepts/tool-enforcement]]
- [[concepts/anthropic-fs-insights]]

