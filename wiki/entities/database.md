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
- **`prediction_market_snapshots`** — Filtered Polymarket and Kalshi active market odds for sentiment checking
- **`system_audits`** — Weekly anomaly detection findings

## Database RPC Functions

- **`match_memories`** — Cross-agent semantic global memory vector searches.
- **`match_decisions`** — Per-agent trade reasoning searches scoped by `model_name`.
- **`get_llm_leaderboard_metrics`** — Aggregates and calculates dynamic metrics (Return %, Win Rate, Verifier Approval Rate, Consistency Score, and composite Leaderboard Score) for all models over a selectable timeframe (`time_window_days`).


## JSONB Querying Conventions

When querying nested fields inside `JSONB` columns (such as `metadata` in `memories` or `decisions`) via the Supabase client or PostgREST:

- **Always use `->>` (Text Extraction)** instead of `->` (Object Extraction) for comparing primitive string or number values.
  - *Correct:* `query.eq('metadata->>source_type', 'academic_paper')` (queries standard string against text).
  - *Incorrect:* `query.eq('metadata->source_type', 'academic_paper')` (PostgreSQL attempts to cast `'academic_paper'` to a JSON object/string literal, causing casting error `22P02`).
- **NULL checking**: Both `->>` and `->` can check for SQL NULL values (using `.is('metadata->>key', null)`), but `->>` is preferred for consistency across key extraction.
- **Exceptions**: The `->` operator should be used when querying JSON boolean literals (e.g. `true`/`false`), checking JSON containment (`@>`), or extracting nested objects as valid sub-JSON objects.

## Related

- [[entities/engine]]
- [[entities/web-app]]
- [[concepts/memory-feedback]]
- [[concepts/rag-strategy]]
- [[concepts/supabase-grant-convention]]
