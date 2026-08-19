---
tags: [database, supabase, postgresql, schema]
category: entity
---

# Database

Supabase PostgreSQL instance serving as the persistent data layer for the LLM Market Bench platform. Uses pgvector for semantic search, Row Level Security (RLS) for access control, and custom PostgREST endpoints for API access.

## Schema

### Trading & Portfolio

- `portfolios` — managed portfolio definitions (type, model, status, cash/equity split)
- `portfolio_ledger` — trade journal with thesis, execution, timestamps
- `portfolio_performance` — daily snapshots of equity, cash, returns
- `portfolio_holdings` — current holdings per portfolio
- `orders` — raw alpaca order records
- `pnl_cache` — P&L aggregation cache

### Analysis & Consensus

- `analysis_state` — per-agent analysis results (signal, catalyst, impact, context)
- `consensus_state` — aggregated agent consensus (event records, debate trails)
- `trading_consensus` — merged trading consensus with voting
- `event_ledger` — promoted events and trend tracking

### Macro & Market Data

- `macro_tracker` — 23-ticker global regime monitoring cache
- `price_history` — historical price data for backtesting and display
- `correlation_cache` — inter-asset correlation matrix
- `fred_series_cache` — cached FRED macroeconomic time series observations (configurable TTL, used by `get_macro_economic_series` tool and newsletter macro context)

### Memory & Feedback

- `memory_entries` — long-term memory store for agent recall
- `agent_memory_context` — per-agent memory summaries
- `post_mortem` — post-trade analysis records

### Autoresearch

- `prompt_experiments` — experiment tracking for prompt mutation
- `backtest_results` — backtest outcome records

### Newsletters & Content

- `newsletter_snapshots` — ingested raw newsletter content
- `generated_newsletters` — synthesized daily market briefings

### System

- `migrations` — schema version tracking

## Key Features

- **pgvector**: Semantic search across memory and analysis contexts
- **RLS**: Row-level security with anon, authenticated, and service_role policies
- **PostgREST**: Auto-generated REST API from schema
- **Migration-based**: All schema changes via Supabase migrations

## Related

- [[concepts/macroeconomic-data-fred]] — FRED economic data caching and tool integration
- [[entities/engine]]
- [[entities/autoresearch]]
- [[concepts/supabase-grant-convention]]
- [[concepts/supabase-redirect-whitelisting]]
