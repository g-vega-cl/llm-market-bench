---
tags: [source, database, schema, supabase]
category: source
source: docs/database-schema.md
---

# Source: Database Schema

Supabase PostgreSQL schema for the entire platform. Covered in [[entities/database]].

Key details:

- 4 domains: Ingestion, Memory & Retrieval (pgvector), Market Data, Trading & Portfolios
- `match_memories`: vector search with filtering by status and memory_type
- `match_decisions`: vector search scoped by `filter_model_name` for per-agent retrieval
- `exec_sql`: RPC for read-only audit queries
- `system_audits`: weekly anomaly tracking with severity classification
- `ingestion_logs`: 48-hour retention pipeline stdout/stderr
- `position_pnl`: SQL view joining positions with market_data_cache
- RLS on `decisions` and `llm_reasoning_logs`: service_role write, anon SELECT
- `market_feeling`: LLM-driven sentiment with confidence, tokens, processing time
