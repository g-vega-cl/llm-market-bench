---
tags: [database, supabase, postgresql, pgvector]
category: entity
---

# Database

Supabase PostgreSQL with pgvector extension. Manages four domains: ingestion
(newsletter snapshots), memory & retrieval (vector embeddings), market data
(price cache), and trading (portfolios, positions, trades).

## Key Tables

- **`portfolios`** — Financial state per LLM agent (cash, equity, buying power, SMA)
- **`portfolio_positions`** — Active holdings (ticker, quantity, cost basis)
- **`trades`** — Immutable trade ledger with decision_id FK for audit trail
- **`memories`** — Semantic events with vector embeddings for RAG (MARKET_EVENT, LESSON_LEARNED, etc.)
- **`decisions`** — LLM reasoning with status tracking (VALIDATED, EXECUTED, REJECTED_*)
- **`newsletter_snapshots`** — Cleaned newsletter content with chunk hashing for dedup
- **`concept_metrics`** — Momentum tracking with PCA coordinates
- **`market_feeling`** — LLM-driven sentiment (refreshed multiple times daily)
- **`system_audits`** — Weekly anomaly detection findings

## Vector Search

Two RPC functions power RAG: `match_memories` (cross-agent global memories) and
`match_decisions` (per-agent trade reasoning scoped by `model_name`).

## Related

- [[entities/engine]]
- [[entities/web-app]]
- [[concepts/memory-feedback]]
- [[concepts/rag-strategy]]
- [[concepts/supabase-grant-convention]]
