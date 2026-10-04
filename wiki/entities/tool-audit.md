---
tags: [entity, tool-audit, observability, logging]
category: entity
---

# Tool Audit

Non-blocking background audit logging for LLM tool execution. Records every tool call's name, arguments, result, model, duration, and status to the archive database's `public.tool_execution_logs` table without consuming Supabase storage quota.

## Mechanism

Used in `core/llm/handlers/base.py` wrapping `execute_tool` for all tools. Every tool execution measures wall-clock duration in milliseconds, emits a warning log when `duration_ms >= 5000` (`[tool_audit] Slow tool: ...`), logs standard completions, and non-blockingly dispatches records to `public.tool_execution_logs` via `async_record_tool_audit`.

### Coverage & Phased Rollout
- **Phase 1 (Volatility)**: `get_volatility_metrics` (1 MB truncation ceiling, background non-blocking execution).
- **Phase 2 (Valuation & Screening)**: `audit_financial_valuation`, `get_sector_alternatives`, `find_uncorrelated_assets`, `run_stock_screener`.
- **Phase 3 (Research & Grounding)**: `web_search`, `get_ticker_news`, `search_prediction_markets`, `get_prediction_market_odds`.
- **Phase 4 (Daily Predictor Macro Suite)**: `tasks/daily_predictor.py:get_daily_market_context` dispatches its pre-market intelligence tools (`get_today_economic_releases`, `get_calendar_scenario_analysis`, `get_macro_options_sentiment`, `get_global_macro_context`, `get_volatility_index_details`, `get_market_health_barometer`, `get_market_feeling`) through `execute_tool(..., model_name="daily_predictor")`, ensuring pre-market background compilations are audited with zero Supabase quota impact while preserving the synthesized `daily_predictions.market_context` for presentation in the web viewer.

## Related

- [[concepts/hybrid-database-archival]] — The archive database infrastructure
- [[entities/tool-registry]] — The dispatch table that routes tool calls
- [[entities/daily-market-predictor]] — Phase 4 consumer
