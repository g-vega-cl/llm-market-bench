---
tags: [database, supabase, postgresql, pgvector, rls]
category: entity
---

# Supabase PostgreSQL Database

The platform uses **Supabase PostgreSQL** as its single database with row-level security, pgvector for semantic search, and explicit grant conventions for the PostgREST Data API.

## Schema Overview

The database is organized into several functional areas:

### Core Tables
- `agents` — Registered LLM agents and their model configurations
- `agents_tool_use` — Tool execution logs per agent
- `analysis_sessions` — Top-level grouping for each analysis cycle
- `catalyst_radar` — Pre-computed collisions between narrative concepts and calendar events for the Keep an Eye radar (see [[concepts/catalyst-radar]])
- `chat_memories` — User-curated private research theses with full RLS isolation (see [[concepts/private-memory-vault]])
- `decisions` — Agent buy/sell decisions (1 row per agent per ticker per session)
- `economic_calendar_events` — Parsed economic indicator data
- `frontier_themes` — Qualified frontier technology supercycle themes and constituent pure-play tickers (see [[entities/frontier-tech-portfolio]])
- `generated_newsletters` — Daily AI market briefings
- `government_incentives` — High-impact policy tracking
- `market_feeling` — Daily and weekly market sentiment assessments
- `memory_hooks` — Contrarian analysis and causal chain entries
- `memory_tags` — Tagged memory cards
- `meta_prompt_experiments` — Auto-research prompt experiment logs
- `newsletter_scrape_data` — Raw newsletter source scrapes
- `options_data_cache` — Temporary cache for Massive/Polygon options snapshots and implied volatility metrics
- `portfolio_snapshots` — Point-in-time portfolio state
- `position_actions` — Delta-based position change queue (buy/sell/hold)
- `sector_predictions` — Weekly sector ranking predictions
- `trades` — Executed trade records with attribution

### Market Data Cache Tables

These two tables form the market data persistence layer used by `MarketDataManager` (`execution/market_data.py`):

- **`price_history`** — EOD (end-of-day) price bars per ticker, persisted after every provider fetch and used as the warm-cache source for history requests. Schema:
  - `ticker TEXT NOT NULL`
  - `price NUMERIC NOT NULL` — closing price (mirrors `close`)
  - `market_cap NUMERIC NOT NULL`
  - `open NUMERIC`, `high NUMERIC`, `low NUMERIC`, `close NUMERIC` — OHLC (added Aug 2026)
  - `volume BIGINT` — daily share volume (added Sep 2026, migration `20260924000000`)
  - `fetched_at TIMESTAMPTZ` — unique constraint with `ticker` (dedup key)
  - RLS enabled; service-role write, public read. Unique constraint: `(ticker, fetched_at)`.

- **`market_data_cache`** — Live intraday quote snapshot (TTL-based). Stores `ticker`, `price`, `market_cap`, `today_pct_change`, `fetched_at`. Evicted after `MARKET_DATA_CACHE_TTL_SECONDS` (default 300 s). Does **not** store volume; volume context is computed from `price_history`.

> [!IMPORTANT]
> `price_history.volume` must be populated on every provider fetch. If it is absent, `compute_volume_context` in `core/llm/tools.py` silently returns `"insufficient volume data"` for all warm-cache reads, breaking RVOL and percentile-rank signals for volatility metrics and the stock screener tool.

### Additional Tables
- `sector_predictions_calibration` — Calibration data for sector prediction scores
- `snp500_stocks` — S&P 500 constituent list and metadata
- Other tables for experiments, prompts, and logging

### Views
- `vw_daily_score` — Daily ratchet score audit view
- `vw_latest_trades` — Latest trades with agent and ticker details

### pgvector Extensions
- `memories` — Vector-indexed benchmark memory store (semantic search)
- `research_papers` — Academic paper embeddings for RAG grounding

## Row-Level Security (RLS)

Applied to 100% of tables in the `public` schema without exception. All tables enforce RLS (`ALTER TABLE public.<table> ENABLE ROW LEVEL SECURITY;`) with explicit access policies, verified continuously in CI via `apps/engine/tests/test_migration_grants.py`. User-facing tables like `chat_memories` use user-isolated policies (`auth.uid() = user_id`), while benchmark cache tables provide public read and service-role write policies.

## Grant Convention

Following [[concepts/supabase-grant-convention]], all tables exposed via the PostgREST Data API must have explicit `GRANT SELECT, INSERT, UPDATE, DELETE ON public.<table> TO authenticated;` statements. The `chat_memories` migration includes both authenticated and service_role grants.


## Migrations

Migrations live in `supabase/migrations/` and follow the Supabase naming convention: `YYYYMMDDHHMMSS_description.sql`. Each migration is idempotent and tracked in version control.

## Related

- [[concepts/rag-strategy]]
- [[concepts/private-memory-vault]]
- [[concepts/supabase-grant-convention]]
- [[entities/engine]]
