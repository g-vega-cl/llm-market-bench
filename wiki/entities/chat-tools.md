---
tags: [entity, chat, tools, database]
category: entity
---

# Chat Tools

Server-side backend functions that execute LLM tool calls against Supabase tables for the Investment Chat Gateway. Each tool returns a `ToolTrace` with name and summary for collapsible UI display.

## Tool Definitions

Defined in `chat-tools.ts`:

1. **SEARCH_MEMORIES_AND_THESES_TOOL** — Searches `memories` and `cause_and_effect` tables by ticker (contains) or keyword (ilike on title). Returns memory cards with importance scores, possible scenarios, and causal chains. Parameters: ticker (optional), query (optional), limit (default 5, max 20).

2. **GET_STOCK_CONTEXT_AND_TRADES_TOOL** — Retrieves recent trades (`trades` table) and decisions (`decisions` table) for a ticker. Parameters: ticker (required), limit (default 10, max 30).

3. **GET_MARKET_SENTIMENT_AND_NEWSLETTER_TOOL** — Fetches latest `market_feeling` and `generated_newsletters` entries. Parameters: limit (default 1, max 5).

4. **QUERY_DATABASE_TABLE_TOOL** — Generic safe read-only query against any table. Supports select_columns, where_column, where_value, order_by, limit, and offset. Parameters: table_name (required), select_columns, where_column, where_value, order_by, limit, offset.

## Handler Functions

- **executeDatabaseQueryTool**: Queries any table via `performSupabaseSelect`. Falls back to simulated response if no real client. Returns structured JSON with table name, count, and rows.
- **executeSearchMemoriesTool**: Queries `memories` (select: id, title, content, tickers, tags, importance_score, possible_scenarios, created_at) and `cause_and_effect` (select: *). Supports ticker.contains and query.ilike filters.
- **executeStockContextTool**: Queries `trades` (select: id, ticker, action, quantity, price, model_name, thesis, reasoning, pnl, created_at) and `decisions` (select: id, model_name, ticker, action, thesis, created_at).
- **executeMarketSentimentTool**: Queries `market_feeling` (select: id, sentiment, confidence, why_explanation, created_at) and `generated_newsletters` (select: id, title, content, created_at).

## Schema Summary Construction

`getDatabaseSchemaSummary` caches table column information for the system prompt. Provides dynamic or fallback schema listing:
- portfolios: id, agent_name, cash, total_equity, updated_at
- trades: id, ticker, action, quantity, price, model_name, thesis, reasoning, created_at
- memories: id, title, content, tickers, tags, importance_score, possible_scenarios, created_at
- cause_and_effect: id, cause, effect, tickers, confidence, horizon, created_at
- market_feeling: id, sentiment, confidence, why_explanation, attempts_summary, created_at
- portfolio_snapshots: id, agent_name, snapshot_date, total_equity, daily_pnl
- sector_predictions: id, prediction_date, target_date, model_name, predicted_sector, status, sector_percentile_score
- prompt_experiments: id, prompt_tag, confidence, track_id, research_reasoning, created_at
- generated_newsletters: id, title, summary, content, read_time_minutes, created_at
- decisions: id, model_name, ticker, action, thesis, created_at
- leaderboard: id, agent_name, total_return, win_rate, sharpe_ratio

## Related

- [[entities/investment-chat-gateway]] — Parent chat gateway
- [[entities/database]] — Supabase schema
- [[concepts/rag-strategy]] — Tiered context injection
