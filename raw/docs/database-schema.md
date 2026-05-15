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
- `owner_id` (TEXT): Unique model identifier (e.g., model name from `models.json`).
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
An immutable ledger of all executed trades. **Supabase is the source of truth.**
- `id` (UUID): Primary key.
- `portfolio_id` (UUID): FK to `portfolios`.
- `ticker` (TEXT): Stock symbol.
- `signal` (TEXT): `BUY` or `SELL`.
- `quantity` (INT): Shares traded.
- `price` (NUMERIC): Execution price.
- `total_cost` (NUMERIC): Total transaction value.
- `executed_at` (TIMESTAMPTZ): Timestamp of execution.
- `decision_id` (UUID): Link to the triggering decision.
- `realized_pnl` (NUMERIC): The profit or loss realized by this trade (for SELL signals).
- `realized_pnl_pct` (NUMERIC): The profit or loss percentage realized by this trade.
- `alpaca_order_id` (TEXT): Broker paper-trading order UUID for third-party audit.
- `alpaca_status` (TEXT): Broker order lifecycle: `SUBMITTED` (order placed), `FILLED`, `REJECTED`, `CANCELED`, `EXPIRED` (terminal states synced by daily GitHub Actions job), `ERROR` (submission failure), `SKIPPED_NO_POSITION` (SELL blocked — no shares held). Before 2026-05-14, initial status was `PENDING` instead of `SUBMITTED`; the sync script handles both.
- `alpaca_submitted_at` (TIMESTAMPTZ): When the order was submitted to Alpaca.
- `alpaca_filled_at` (TIMESTAMPTZ): When Alpaca reported the order as filled (set by sync script). Added 2026-05-14.

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
- `embedding` (VECTOR): The embedding provider's vector (dimensionality depends on model — see `memory/embeddings.py`).
- `metadata` (JSONB): Source and context metadata. 
  - **Required for Future Catalysts:** `scenario_analysis` must contain at least two outcomes and associated Trading Plans.
- `memory_type` (TEXT): `MARKET_EVENT`, `GOVERNMENT_INCENTIVE`, `LESSON_LEARNED`, `UNCROWDED_TRADE`, `CALENDAR_EVENT`.
- `status` (TEXT): `ACTIVE`, `RESOLVED`, `SUPERSEDED`.
- `target_date` (TEXT): For proactive catalyst tracking (ISO 8601). Vague timeframes are excluded from Horizon Watch (see `Overview.md`).
- `importance_score` (INT): Unified score (1-10); Horizon Watch visibility requires score >= 8.
- `parent_id` (UUID): Link to ancestor event (Memory Chains).
- `relationship_type` (TEXT): `REVERSAL`, `UPDATE`, `RESOLUTION`, `GENERAL`.
- `relevance_score` (FLOAT): Decay-adjusted score.
- `created_at` (TIMESTAMPTZ): Entry timestamp.

### `decisions`
Stores reasoning and attribution for every LLM signal.
- `id` (UUID): Primary key.
- `source_id` (TEXT): Link to originating newsletter.
- `ticker`, `signal`, `confidence` (TEXT/INT): Trade intent.
- `price` (NUMERIC): Deprecated (always null post-Approach 3). Use `metadata->>'injected_market_price'` for the system-injected price at analysis time.
- `reasoning` (TEXT): Full LLM justification.
- `metadata` (JSONB): Detailed status and execution info (includes `strategy_reasoning`, `advance_planning_notes`, `injected_market_price`).
- `status` (TEXT): `CREATED`, `EXECUTED`, `VALIDATED`, `REJECTED_MARGIN`, `REJECTED_OWNERSHIP`, `REJECTED_REDUNDANCY`, `REJECTED_TOOL_USAGE`, `REJECTED_VERIFICATION`, `REJECTED_HALLUCINATION`, `REJECTED_LIQUIDITY`, `REJECTED_MARKET_CLOSED`, `REJECTED_STALE_QUOTE`, `ERROR_PROVIDER`. Deprecated (historical only): `REJECTED_PRICE_DEVIATION`, `REJECTED_LIMIT_PRICE`.
- `trade_id` (UUID): Link to `trades` table.
- `embedding` (VECTOR): Embedding of reasoning (dimensionality: see `memory/embeddings.py`).
- `model_provider`, `model_name` (TEXT): LLM attribution.
- `created_at` (TIMESTAMPTZ): Entry timestamp.

### `cause_and_effect`
Stores bi-weekly retrospective audits of market events.
- `id` (UUID): Primary key.
- `event_id` (UUID): FK to `memories`.
- `analysis` (TEXT): Detailed causal breakdown and ripple effects.
- `market_outcome` (TEXT): Concise summary of actual market movement.
- `confidence` (INT): Causal link confidence (0-100).
- `tags` (TEXT[]): Classification labels.
- `created_at` (TIMESTAMPTZ): Audit timestamp.

### `llm_reasoning_logs`
Stores the full conversation history and tool traces for research and auditing.
- `id` (UUID): Primary key.
- `task_type` (TEXT): The engine phase (`INGESTION`, `VERIFICATION`, `CONSENSUS`).
- `model_provider`, `model_name` (TEXT): Attribution.
- `prompt` (JSONB): The full message list (System, User, Assistant, Tool).
- `response` (JSONB): The structured result or text output.
- `metadata` (JSONB): Ticker, source_id, and other context.
- `created_at` (TIMESTAMPTZ): Entry timestamp.

#### Security (RLS)
The `decisions` and `llm_reasoning_logs` tables have **Row Level Security** enabled.
- **Service Role**: Full access for backend engines to save decisions.
- **Anon/Authenticated**: Read access (`SELECT`) is allowed for all users to enable the frontend "Thinking Process" feature.

### `concept_metrics`
Tracks momentum and frequency of semantic concepts.
- `id` (UUID): Primary key.
- `concept_name` (TEXT): e.g., "AI Infrastructure".
- `concept_vector` (VECTOR): Semantic centroid (dimensionality: see `memory/embeddings.py`).
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
- `fetched_at` (TIMESTAMPTZ): TTL enforced in application logic (see `core/config.py`).

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
Retrieves past agent reasoning for consistent RAG retrieval. The latest version accepts a `filter_model_name` parameter to scope results to a single agent, preventing cross-contamination during verification.

```sql
SELECT * FROM match_decisions(
  query_embedding := [0.12, ...],
  match_threshold := 0.5,
  match_count := 5,
  filter_model_name := 'claude-haiku-4-5'
);
```

### `exec_sql`
Executes arbitrary read queries for audit checks. Used internally by the audit system.
```sql
SELECT * FROM exec_sql(
  query := 'SELECT row_to_json(t)::jsonb FROM (SELECT id, status FROM decisions LIMIT 5) t'
);
```

---

## 6. System Auditing

### `system_audits`
Tracks database anomalies, data quality issues, and code errors discovered during weekly audits.
- `id` (UUID): Primary key.
- `audit_type` (TEXT): `DB_ANOMALY`, `DATA_QUALITY`, `CODE_ERROR`, `SYSTEM_LOG`, `IMPROVEMENT`.
- `severity` (TEXT): `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.
- `title` (TEXT): Short summary.
- `description` (TEXT): Detailed findings.
- `suggestion` (TEXT): LLM-generated resolution suggestion.
- `status` (TEXT): `OPEN`, `IN_PROGRESS`, `RESOLVED`, `IGNORED`.
- `source_table` (TEXT): Table where anomaly was found.
- `source_id` (UUID): ID of the problematic record.
- `metadata` (JSONB): Additional context.
- `audit_run_id` (TEXT): Links to the weekly audit run.
- `analysis_method` (TEXT): `SQL_CHECK` or `LLM_ANALYSIS`.
- `created_by` (TEXT): `SYSTEM` or `MANUAL`.
- `resolved_at`, `resolved_by`: Resolution tracking.
- `created_at` (TIMESTAMPTZ): Entry timestamp.

### `ingestion_logs`
Stores pipeline stdout/stderr blobs for log analysis and debugging.
- `id` (UUID): Primary key.
- `run_id` (TEXT): Unique run identifier (e.g., `2026-04-09_15-30-45`).
- `run_date` (DATE): Date of ingestion.
- `run_number` (INT): 1 (first run), 2 (second run), or 3 (third run) during the trading day.
- `log_blob` (TEXT): Full stdout/stderr capture.
- `created_at` (TIMESTAMPTZ): Entry timestamp.

**Retention:** Logs are automatically deleted after 48 hours via the **System Audit** workflow (`.github/workflows/audit.yml`).

---

## 7. Views

### `position_pnl`
Calculates real-time P&L for all active positions by joining `portfolio_positions` with `market_data_cache`.
- `unrealized_pnl_usd`
- `unrealized_pnl_pct`

---

## 8. Market Feeling (LLM-Driven Sentiment)

### `market_feeling`
Stores the LLM-generated "How I'm feeling and why" market sentiment analysis.
Refreshed multiple times daily during market hours.

**Purpose**: Provides a nuanced, LLM-driven market sentiment that considers trades, lessons learned, and market events - displayed prominently on the Today page.

**Fields**:
- `id` (UUID): Primary key.
- `sentiment_label` (TEXT): LLM-generated sentiment (e.g., "Cautiously Optimistic", "Risk-Off", "Wait-and-See").
- `sentiment_emoji` (TEXT): Single emoji representing the sentiment.
- `confidence_score` (INT): 0-100 confidence in the assessment.
- `why_explanation` (TEXT): 2-3 sentence explanation of the sentiment.
- `market_direction` (TEXT): `BULLISH`, `BEARISH`, or `NEUTRAL`.
- `primary_concern` (TEXT): Main risk or opportunity.
- `secondary_concern` (TEXT): Secondary consideration.
- `trades_summary` (JSONB): `{buys: N, sells: N, total_value: number}`.
- `lessons_incorporated` (INT): Count of LESSON_LEARNED memories factored in.
- `memories_incorporated` (INT): Count of MARKET_EVENT memories factored in.
- `model_used` (TEXT): The LLM model used (see `analysis/market_feeling.py` for the current default).
- `processing_time_ms` (INT): API processing time.
- `input_tokens`, `output_tokens` (INT): Token usage for cost tracking.
- `created_at`, `updated_at` (TIMESTAMPTZ): Timestamps.

**Retention**: Records older than 30 days are automatically cleaned up via the **System Audit** workflow (`.github/workflows/audit.yml`).

**Security (RLS)**:
- **Public**: Read access (`SELECT`) for frontend display.
- **Service Role**: Write access (`INSERT`, `UPDATE`) for pipeline updates.

**Integration**:
- Frontend: Displayed in the "How I'm Feeling" card on the Today page (`MarketStatusHero` component).
- Backend: Generated by `analysis.market_feeling.analyze_market_feeling()` during pipeline runs.

**Related Files**:
- Migration: `supabase/migrations/20260416000001_create_market_feeling.sql`
- Analyzer: `apps/engine/analysis/market_feeling.py`
- Client: `apps/engine/core/llm/minimax.py`
- Frontend Component: `apps/web/src/components/today/MarketStatusHero.tsx`
