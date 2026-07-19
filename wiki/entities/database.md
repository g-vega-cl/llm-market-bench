---
tags: [database, supabase, schema, postgres, pgvector]
category: entity
---

# Database

Supabase PostgreSQL instance that powers the entire LLM Market Bench platform. It stores everything from real-time portfolio snapshots and trade audit logs to LLM predictions, raw analysis outputs, and vector embeddings for RAG.

## Core Tables

### Portfolios & Trading
- `portfolios` – current holdings, cash, and equity for each agent
- `trades` – normalized trade history with linking to analysis sessions
- `portfolio_snapshots` – daily portfolio state (PnL, positions, benchmark)
- `orders` – order lifecycle (from planned to Alpaca-submitted to filled)

### Analysis Pipeline
- `analysis_sessions` – low-level LLM outputs, tool calls, and execution traces
- `newsletter_ingestions` – raw scraped/processed newsletter content
- `market_data_cache` – cached price histories and reference data
- `economic_events` – economic calendar events and government data
- `feedback_analyses` – post-mortem contrarian analysis and cause–effect records

### LLM Predictions & Arena
- `sector_predictions` – LLM-generated sector and pair predictions with evaluation results
  - Core fields: `prediction_date`, `target_date`, `timeframe`, `model_name`, `prompt_tag`, `predicted_sector`, `predicted_pair`, `reasoning`, `sector_percentile_score`, `pair_percentile_score`, `status` (`pending`/`evaluated`)
  - New return columns (2026-07-19 migration): `predicted_sector_return` (float), `predicted_pair_return` (float), `benchmark_spy_return` (float) – actual window returns of the predicted sector, pair basket, and S&P 500 benchmark
  - Audit data: `evaluation_audit_data` (JSONB) – stores starting prices, ending prices, and percentage returns per ticker for SPY, the sector ETF, and each pair ETF, along with start/end dates
- `prompt_experiments` – prompt variant registry for the sector predictor arena and main trading prompts

### Vector Search & Knowledge
- `knowledge_base` – chunked and embedded documents (academic papers, manuals, market heuristics)
- `market_anomalies` – catalog of documented market patterns

### Meta & Configuration
- `pipeline_runs` – daily pipeline run logs and phase status
- `agent_configs` – per-agent settings and model assignments
- `research_loops` – autonomous prompt improvement cycles

## Migrations
All schema changes are tracked via timestamped migration files in `supabase/migrations/`. Recent additions include:

- `20260719000000_add_returns_to_sector_predictions.sql` – adds actual return columns to `sector_predictions`
- `20260719010000_add_evaluation_audit_data_to_sector_predictions.sql` – adds `evaluation_audit_data` JSONB column

## Related

- [[entities/pipeline]]
- [[entities/engine]]
- [[entities/sector-predictor-arena]]
- [[concepts/auditability]]
- [[concepts/supabase-grant-convention]]
- [[sources/database-schema-source]]
