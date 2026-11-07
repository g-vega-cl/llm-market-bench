---
tags: [database, supabase, postgresql, pgvector, rls]
category: entity
---

# PostgreSQL & PostgREST Database

The platform operates on a **self-hosted PostgreSQL with pgvector** backend managed via Docker (`docker/archive/docker-compose.yml`), fronted by PostgREST and an Nginx reverse proxy exposed at `https://benchify-archive-db.clvg.uk` via Cloudflare Tunnel. This unified stack replaces the previous cloud-hosted Supabase instance to eliminate cloud egress limitations, while maintaining 100% compatibility with `@supabase/supabase-js` and `supabase-py` SDKs, pgvector semantic search, and Row-Level Security (RLS).

> [!IMPORTANT]
> This archive DB serves the **Data API only** — it does not run an Auth (GoTrue) service. Authentication remains on Supabase Cloud. The web app uses separate Auth and DB clients (see [[concepts/auth-db-client-separation]]).

## Schema Overview

The database is organized into several functional areas:

### Core Tables
- `agents` — Registered LLM agents and their model configurations
- `agents_tool_use` — Tool execution logs per agent
- `agent_chat_queue` — Audience-submitted questions for the live intraday agent's next thinking turn (`status` ∈ `pending`/`injected`/`answered`/`archived`/`rejected`, plus `injected_turn_at` and `agent_response`); see [[entities/live-agent-trader]]. Foreign key to the local `auth.users` stub was dropped in migration `20261030190000_decouple_agent_chat_queue_auth_fk.sql` to store Supabase Cloud user UUIDs directly.
- `analysis_sessions` — Top-level grouping for each analysis cycle
- `catalyst_radar` — Pre-computed collisions between narrative concepts and calendar events for the Keep an Eye radar (see [[concepts/catalyst-radar]])
- `chat_memories` — User-curated private research theses with full RLS isolation (see [[concepts/private-memory-vault]]). `user_id UUID NOT NULL` stores the Supabase Cloud user UUID directly; the foreign key to the local `auth.users` stub was dropped in migration `20261030150000_decouple_chat_memories_auth_fk.sql` because Auth lives in Supabase Cloud while data lives in this archive DB.
- `decisions` — Agent buy/sell decisions (1 row per agent per ticker per session)
- `economic_calendar_events` — Parsed economic indicator data
- `frontier_themes` — Qualified frontier technology supercycle themes and constituent pure-play tickers (see [[entities/frontier-tech-portfolio]])
- `generated_newsletters` — Daily AI market briefings
- `government_incentives` — High-impact policy tracking
- `market_feeling` — Daily and weekly market sentiment assessments (also receives each live intraday agent turn)
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

### Government & Institutional Ownership Tables

These three tables back the [[entities/government-ingestion]] pipeline (`apps/engine/ingest/government_fetchers.py` and `apps/engine/ingest/whale_fetchers.py`):

- **`gov_macro_liquidity`** — Daily US Treasury General Account cash, national debt, and monthly deficit. Columns: `record_date DATE NOT NULL UNIQUE`, `tga_balance`, `tot_pub_debt`, `debt_held_public`, `intragov_holdings`, `monthly_deficit_surplus` (all `NUMERIC(18, 2)`), `raw_metadata JSONB DEFAULT '{}'`, `created_at TIMESTAMPTZ`. Indexed on `record_date DESC`. Upserted on conflict `record_date` by `upsert_gov_macro_liquidity`.
- **`gov_contracts`** — US (USAspending) and Canadian (CanadaBuys) federal contract awards. Columns: `country TEXT NOT NULL CHECK (country IN ('US', 'CA', 'OTHER'))`, `award_id TEXT NOT NULL`, `recipient_name TEXT NOT NULL`, `award_amount NUMERIC(16, 2) NOT NULL DEFAULT 0.00`, `currency TEXT NOT NULL DEFAULT 'USD'`, `description`, `agency_name`, `award_date DATE NOT NULL`, `contract_number`, `source_url`, `raw_metadata JSONB`, `created_at`. Unique constraint `uq_gov_contracts (country, award_id, recipient_name, award_date)`; indexes on `(country, award_date DESC)`, `recipient_name`, and `award_amount DESC`. Upserted by `upsert_gov_contracts`.
- **`institutional_whale_stakes`** — SEC Schedule 13D/13G beneficial ownership disclosures. Columns: `symbol TEXT NOT NULL`, `filer_name TEXT NOT NULL`, `filer_cik`, `filing_date DATE NOT NULL`, `accepted_date DATE`, `percent_of_class NUMERIC(6, 2) NOT NULL DEFAULT 0.00`, `shares_beneficially_owned NUMERIC(16, 2) NOT NULL DEFAULT 0.00`, `reporting_type`, `filing_type TEXT NOT NULL DEFAULT '13G' CHECK (filing_type IN ('13D', '13G', '13F', 'OTHER'))`, `is_exit BOOLEAN NOT NULL DEFAULT false`, `source_url`, `raw_metadata JSONB`, `created_at`. Unique constraint `uq_institutional_whale_stake (symbol, filer_name, filing_date, percent_of_class)`; indexes on `(symbol, filing_date DESC)`, `filer_name`, and `filing_date DESC`. Upserted by `upsert_institutional_whale_stakes`.

All three enable RLS with public `SELECT` and `service_role` full access, and are created by migrations `20261106180000_create_gov_macro_and_contracts.sql` and `20261106190000_create_institutional_whale_stakes.sql` (mirrored in `docker/archive/init.sql`).

### Additional Tables
- `sector_predictions_calibration` — Calibration data for sector prediction scores
- `snp500_stocks` — S&P 500 constituent list and metadata
- Other tables for experiments, prompts, and logging

### Prediction Scoring Columns

Migration `supabase/migrations/20261105000000_add_conviction_scoring.sql` adds:

- `conviction_score FLOAT` on `daily_predictions`, `earnings_predictions`, and `sector_predictions` — the raw logarithmic score persisted at evaluation time (see [[concepts/conviction-points]]).
- `worst_confidence FLOAT` on `sector_predictions` — the separately stated probability for the worst-sector call, used so the worst leg is never priced with the best-pick confidence.

The same migration rewrites `public.get_llm_leaderboard_metrics(INT)` to return a `conviction_score` column and to stop paying `0.3 × average_confidence` inside the reasoning-quality score. `average_confidence` remains an informational column. Backfilled history is produced by `apps/engine/scripts/backfill_conviction_scores.py`.

### Views
- `vw_daily_score` — Daily ratchet score audit view
- `vw_latest_trades` — Latest trades with agent and ticker details

### pgvector Extensions
- `memories` — Vector-indexed benchmark memory store (semantic search)
- `research_papers` — Academic paper embeddings for RAG grounding

## Row-Level Security (RLS)

Applied to 100% of tables in the `public` schema without exception. All tables enforce RLS (`ALTER TABLE public.<table> ENABLE ROW LEVEL SECURITY;`) with explicit access policies, verified continuously in CI via `apps/engine/tests/test_migration_grants.py`. User-facing tables like `chat_memories` use user-isolated policies (`auth.uid() = user_id`), while benchmark cache tables provide public read and service-role write policies. `agent_chat_queue` grants public `SELECT` for queue visibility, while `INSERT` is strictly restricted to `service_role` through server-side authenticated functions to prevent unauthenticated direct PostgREST injections (migration `20261030190000_decouple_agent_chat_queue_auth_fk.sql`).

## Grant Convention

Following [[concepts/supabase-grant-convention]], all tables exposed via the PostgREST Data API must have explicit `GRANT SELECT, INSERT, UPDATE, DELETE ON public.<table> TO authenticated;` statements. The `chat_memories` migration includes both authenticated and service_role grants.

## RPC Functions

- `pop_next_queue_item()` — Atomic FIFO dequeue for the live intraday agent's audience queue (migration `20261029220000_add_pop_next_queue_item_rpc.sql`). Uses `SELECT ... FOR UPDATE SKIP LOCKED` to atomically transition the oldest `pending` row to `injected` (stamping `injected_turn_at = NOW()`) and returns it, avoiding race conditions between concurrent runner turns. Declared `SECURITY DEFINER` and granted `EXECUTE` to `anon`, `authenticated`, and `service_role`.
- `match_memories(query_embedding extensions.vector(768), match_threshold float, match_count int, filter_memory_types text[] DEFAULT NULL)` — pgvector cosine-similarity search over the `memories` store used by the tiered RAG path (see [[concepts/rag-strategy]]). The embedding argument is qualified as `extensions.vector(768)` and pinned with `SET search_path = public, extensions` because pgvector lives in the `extensions` schema (migrations `20260129000000_add_memory_type_to_memories.sql` and `20260305000000_add_importance_score_to_memories.sql`). The 4-argument signature is canonical; a stale 3-argument definition surfaces as `PGRST202` and silently empties Tier 2 RAG.
- `match_decisions(query_embedding extensions.vector, match_threshold double precision, match_count integer, filter_model_name text DEFAULT NULL)` — pgvector similarity search over `decisions.embedding`, the per-agent decision half of `retrieve_for_decision()`. Restored by `20261106000000_fix_match_decisions_search_path.sql` after the overload migration dropped the search path (runtime error `42883`: `operator does not exist: extensions.vector <=> extensions.vector`).

After applying any `match_*` DDL, run `NOTIFY pgrst, 'reload schema';` on the primary. `NOTIFY` does not cross a physical standby, so the MiniPC PostgREST replica needs `docker kill -s SIGUSR1 market-bench-archive-postgrest-replica`. Failure-mode notes live in [[concepts/hybrid-database-archival]].

## Migrations

Migrations live in `supabase/migrations/` and follow the Supabase naming convention: `YYYYMMDDHHMMSS_description.sql`. Each migration is idempotent and tracked in version control.

## Related

- [[entities/government-ingestion]]
- [[entities/secondary-minipc-edge]]
- [[concepts/hybrid-database-archival]]
- [[concepts/auth-db-client-separation]]
- [[concepts/rag-strategy]]
- [[concepts/private-memory-vault]]
- [[concepts/supabase-grant-convention]]
- [[entities/live-agent-trader]]
- [[entities/engine]]
