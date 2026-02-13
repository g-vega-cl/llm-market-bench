# Database Schema: AI Wall Street

This document outlines the Supabase PostgreSQL schema for the AI Wall Street project, including key tables, relationships, and specialized RPC functions for vector search.

## Overview

The database manages four primary domains:
1.  **Ingestion:** Raw newsletter data and snapshots.
2.  **Memory & Retrieval:** Long-term memories and trade attribution with vector embeddings.
3.  **Market Data:** Historical prices and real-time cache.
4.  **Trading & Portfolios:** Agent balances, positions, and execution ledger.

---

## 1. Trading & Portfolios

### `portfolios`
Stores the current financial state for each AI model.
- `id` (UUID): Primary key.
- `owner_id` (TEXT): Unique model identifier (e.g., `gpt-5-mini`, `claude-haiku-4-5`).
- `cash_balance` (NUMERIC): Available cash for trading.
- `total_equity` (NUMERIC): Net Liquidation Value (Cash + Market Value).
- `buying_power` (NUMERIC): Intraday leverage limit (Reg T).
- `excess_liquidity` (NUMERIC): How much "buffer" before a margin call.
- `maintenance_margin` (NUMERIC): Minimum equity required to hold positions (33%).
- `realized` (NUMERIC): Total realized profit/loss.
- `sma` (NUMERIC): Special Memorandum Account.
- `last_updated_at` (TIMESTAMPTZ): Last metric refresh.

### `portfolio_positions`
Tracks active holdings for each portfolio.
- `id` (UUID): Primary key.
- `portfolio_id` (UUID): FK to `portfolios`.
- `ticker` (TEXT): Stock symbol (normalized to UPPERCASE).
- `quantity` (INT): Number of shares held.
- `average_cost_basis` (NUMERIC): Weighted average price paid.
- `last_updated_at` (TIMESTAMPTZ): Last position update.

### `trades`
An immutable ledger of all executed trades.
- `id` (UUID): Primary key.
- `portfolio_id` (UUID): FK to `portfolios`.
- `ticker` (TEXT): Stock symbol.
- `signal` (TEXT): `BUY` or `SELL`.
- `quantity` (INT): Shares traded.
- `price` (NUMERIC): Execution price.
- `total_cost` (NUMERIC): Total transaction value.
- `executed_at` (TIMESTAMPTZ): Timestamp of execution.
- `decision_id` (UUID): Link to the triggering decision.

### `portfolio_performance`
Daily snapshots of portfolio metrics for equity curve visualization.
- `id` (UUID): Primary key.
- `portfolio_id` (UUID): FK to `portfolios`.
- `date` (DATE): Snapshot date (Unique per portfolio/day).
- `total_equity`, `cash_balance`, `buying_power`, `sma` (NUMERIC): Core snapshots.
- `initial_margin_req`, `maintenance_margin_req` (NUMERIC): Margin snapshots.
- `available_funds`, `excess_liquidity` (NUMERIC): Liquidity snapshots.
- `realized` (NUMERIC): Realized P&L snapshot.
- `created_at` (TIMESTAMPTZ): Entry timestamp.

---

## 2. Ingestion & Snapshotting

### `newsletter_snapshots`
Stores raw content from ingested newsletters.
- `id` (UUID): Primary key.
- `source_id` (TEXT): Unique deterministic ID (`date_sender_subject_hash`).
- `chunk_hash` (TEXT): SHA-256 hash for deduplication.
- `sender`, `subject`, `content` (TEXT): Email metadata and cleaned body.
- `date` (TIMESTAMPTZ): Newsletter publish date.
- `ingested_at` (TIMESTAMPTZ): Arrival timestamp.

---

## 3. Memory & Decisions (pgvector)

### `memories`
Stores global market events for RAG retrieval.
- `id` (UUID): Primary key.
- `content` (TEXT): Synthesized event description.
- `embedding` (VECTOR(768)): Google Gemini embedding.
- `metadata` (JSONB): Source and context metadata.
- `memory_type` (TEXT): `MARKET_EVENT`, `GOVERNMENT_INCENTIVE`, `LESSON_LEARNED`.
- `status` (TEXT): `ACTIVE`, `RESOLVED`, `SUPERSEDED`.
- `target_date` (TEXT): For proactive catalyst tracking.
- `parent_id` (UUID): Link to ancestor event (Memory Chains).
- `relationship_type` (TEXT): `REVERSAL`, `UPDATE`, `RESOLUTION`, `GENERAL`.
- `relevance_score` (FLOAT): Decay-adjusted score.
- `created_at` (TIMESTAMPTZ): Entry timestamp.

### `decisions`
Stores reasoning and attribution for every LLM signal.
- `id` (UUID): Primary key.
- `source_id` (TEXT): Link to originating newsletter.
- `ticker`, `signal`, `confidence` (TEXT/INT): Trade intent.
- `price` (NUMERIC): LLM predicted/observed price.
- `reasoning` (TEXT): Full LLM justification.
- `metadata` (JSONB): Detailed status and execution info.
- `status` (TEXT): `CREATED`, `EXECUTED`, `REJECTED_MARGIN`, etc.
- `trade_id` (UUID): Link to `trades` table.
- `embedding` (VECTOR(768)): Embedding of reasoning.
- `model_provider`, `model_name` (TEXT): LLM attribution.
- `created_at` (TIMESTAMPTZ): Entry timestamp.

#### Security (RLS)
The `decisions` table has **Row Level Security** enabled.
- **Service Role**: Full access for backend engines to save decisions.
- **Anon/Authenticated**: Read access (`SELECT`) is allowed for all users to enable the frontend "Thinking Process" feature.

### `concept_metrics`
Tracks momentum and frequency of semantic concepts.
- `id` (UUID): Primary key.
- `concept_name` (TEXT): e.g., "AI Infrastructure".
- `concept_vector` (VECTOR(768)): Semantic centroid.
- `mention_count` (INT): 90-day frequency.
- `velocity_score` (FLOAT): Momentum metric.
- `pca_x`, `pca_y` (FLOAT): 2D coordinates for map.
- `first_mention_at`, `last_mention_at` (TIMESTAMPTZ).
- `created_at`, `updated_at` (TIMESTAMPTZ).

---

## 4. Market Data

### `market_data_cache`
Temporary storage to minimize external API calls.
- `ticker` (TEXT)
- `price`, `market_cap` (NUMERIC)
- `fetched_at` (TIMESTAMPTZ): 4-hour TTL enforced in logic.

### `price_history`
Permanent record of every price fetch for backtesting and analysis.

---

## 5. Specialized Functions (RPC)

### `match_memories`
Performs vector similarity search with filtering by `status` and `memory_type`.
```sql
SELECT * FROM match_memories(
  query_embedding := [0.12, ...],
  match_threshold := 0.5,
  match_count := 5,
  filter_memory_types := ARRAY['MARKET_EVENT']
);
```

### `match_decisions`
Retrieves past agent reasoning for consistent RAG retrieval.

---

## 6. Views

### `position_pnl`
Calculates real-time P&L for all active positions by joining `portfolio_positions` with `market_data_cache`.
- `unrealized_pnl_usd`
- `unrealized_pnl_pct`
