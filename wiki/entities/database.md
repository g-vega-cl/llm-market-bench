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
- `congress_trades` — US Senate and House STOCK Act personal transaction disclosures (see [[entities/congress-trades]])
- `decisions` — Agent buy/sell decisions (1 row per agent per ticker per session)
- `economic_calendar_events` — Parsed economic indicator data
- `frontier_themes` — Qualified frontier technology supercycle themes and constituent pure-play tickers (see [[entities/frontier-tech-portfolio]])
- `generated_newsletters` — Daily AI market briefings
- `government_incentives` — High-impact policy tracking
- `insider_trades` — SEC Form 4 corporate insider transactions and Canadian cross-listed insider activity (see [[entities/insider-trades]])
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

### Daily Stock Picker Tables

These two tables back the [[entities/daily-stock-picker]] arena (migration `20261112000000_create_daily_stock_picks.sql`) and pre-materialize Long/Short spread alpha and hit rates per model track (see [[concepts/zero-frontend-compute]]):

- **`daily_stock_baskets`** — Parent basket per model track (`consensus`, `deepseek-v4-flash`, `MiniMax-M3`, `gpt-5.6-luna`) for each session. Columns: `id UUID PK`, `target_date DATE NOT NULL`, `model_name TEXT NOT NULL`, `status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','evaluated','cancelled'))`, `directional_hit_rate NUMERIC`, `mean_long_return_pct NUMERIC`, `mean_short_return_pct NUMERIC`, `ls_spread_alpha_pct NUMERIC`, `excess_alpha_vs_spy_pct NUMERIC`, `benchmark_spy_return_pct NUMERIC`, `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`, `evaluated_at TIMESTAMPTZ`. Unique constraint `uq_daily_stock_basket (target_date, model_name)`; indexes on `target_date` and `model_name`.
- **`daily_stock_picks`** — Granular child picks (3 UP + 3 DOWN) for each basket. Columns: `id UUID PK`, `basket_id UUID REFERENCES daily_stock_baskets(id) ON DELETE CASCADE`, `target_date DATE NOT NULL`, `model_name TEXT NOT NULL`, `ticker TEXT NOT NULL`, `direction TEXT NOT NULL CHECK (direction IN ('UP','DOWN'))`, `rank INT NOT NULL CHECK (rank BETWEEN 1 AND 3)`, `confidence NUMERIC NOT NULL CHECK (confidence BETWEEN 50.0 AND 100.0)`, `expected_return_pct NUMERIC`, `reasoning TEXT`, `status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','evaluated','cancelled'))`, `open_price NUMERIC`, `close_price NUMERIC`, `stock_return_pct NUMERIC`, `position_return_pct NUMERIC`, `is_hit BOOLEAN`, `conviction_points NUMERIC`, `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`, `evaluated_at TIMESTAMPTZ`. Unique constraints `uq_stock_picks_slot (target_date, model_name, direction, rank)` and `uq_stock_picks_ticker (target_date, model_name, ticker)`, plus `chk_pick_evaluation_invariants` making illegal lifecycles unrepresentable (see [[concepts/state-machines]]). Indexes on `status`, `basket_id`, and `(model_name, target_date)`.

Both tables enable RLS with public `SELECT`, `service_role` full access, and explicit `GRANT SELECT` to `anon`/`authenticated` per [[concepts/supabase-grant-convention]].

Pick writes go through the `replace_daily_stock_picks` RPC rather than independent delete/insert round-trips, so a basket can never be left with zero picks (see RPC Functions below).

### Company Research Tables

These two tables back the [[entities/company-research-reports]] pipeline (migration `20261110120000_create_company_research_reports.sql`):

- **`company_research_reports`** — Historical ledger of institutional research dossiers on stocks and sector ETFs spotlighted in daily briefings. Columns: `ticker TEXT NOT NULL`, `company_name TEXT NOT NULL`, `sector TEXT`, `is_sector_etf BOOLEAN DEFAULT FALSE`, `entity_type TEXT DEFAULT 'stock' CHECK (entity_type IN ('stock','etf'))`, `session TEXT NOT NULL CHECK (session IN ('open','close','on_demand'))`, `date DATE NOT NULL`, `verdict TEXT NOT NULL CHECK (verdict IN ('bullish','bearish','neutral'))`, `conviction_score INTEGER NOT NULL CHECK (conviction_score BETWEEN 1 AND 100)`, `risk_reward_score NUMERIC(3,1)`, `target_horizon TEXT NOT NULL`, `spot_price_at_report NUMERIC(12,4)`, `forward_5d_return NUMERIC(6,4)`, `forward_20d_return NUMERIC(6,4)`, `valuation_summary TEXT`, `buffett_moat_analysis JSONB DEFAULT '{}'::jsonb`, `options_sentiment_summary TEXT`, `catalyst_context TEXT`, `falsification_triggers JSONB DEFAULT '[]'::jsonb`, `full_report_markdown TEXT NOT NULL`, `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`. Unique constraint `uq_company_report_session (ticker, date, session)` for idempotent upserts; indexes on `ticker`, `date DESC`, and `verdict`.
- **`newsletter_company_mentions`** — Junction table linking `generated_newsletters` to research reports. Columns: `newsletter_id UUID NOT NULL REFERENCES generated_newsletters(id) ON DELETE CASCADE`, `ticker TEXT NOT NULL`, `research_report_id UUID REFERENCES company_research_reports(id) ON DELETE SET NULL`, `created_at TIMESTAMPTZ`. Unique constraint `uq_newsletter_ticker (newsletter_id, ticker)`; indexes on `newsletter_id` and `ticker`.

Both tables enable RLS with public `SELECT`, `service_role` full access, and explicit `GRANT SELECT` to `anon`/`authenticated` per [[concepts/supabase-grant-convention]].

### Recipe Studio Tables

These five active tables back the [[entities/recipe-studio]] subsystem (migration `20261112103000_create_recipe_studio_v2.sql`; `recipe_intraday_bars` was removed in `20261113112000_drop_recipe_intraday_bars.sql` in favor of `price_history`):

- **`recipe_news_corpus`** — Point-in-time news articles imported from `stock-news-scraper` JSONL shards and synced hourly from live market wires + `newsletter_snapshots`. Columns: `article_id TEXT PRIMARY KEY`, `title TEXT NOT NULL`, `url TEXT NOT NULL`, `date_published TIMESTAMPTZ NOT NULL`, `date_precision TEXT NOT NULL DEFAULT 'article_meta'`, `source TEXT NOT NULL`, `source_family TEXT NOT NULL`, `full_text TEXT NOT NULL`, `word_count INTEGER NOT NULL DEFAULT 0`, `company TEXT NOT NULL`, `companies TEXT[] NOT NULL DEFAULT '{}'`, `tickers TEXT[] NOT NULL DEFAULT '{}'`, `company_in_headline BOOLEAN NOT NULL DEFAULT FALSE`, `buckets TEXT[] NOT NULL DEFAULT '{}'`, `search_tsv TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', title || ' ' || coalesce(full_text, ''))) STORED`, `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`. Indexes: `date_published DESC`, GIN on `tickers`, GIN on `buckets`, GIN on `search_tsv`.
- **`strategy_recipes`** — Push v2 strategy configurations (`graph_json`, one LLM stage per strategy for the MVP) plus isolated paper ledgers. Columns: `id UUID PK`, `user_id UUID NOT NULL` (Supabase Cloud UUID stored directly, no FK to the local `auth.users` stub), `name TEXT NOT NULL`, `description TEXT NOT NULL DEFAULT ''`, `is_public BOOLEAN NOT NULL DEFAULT FALSE`, `is_template BOOLEAN NOT NULL DEFAULT FALSE`, `is_live BOOLEAN NOT NULL DEFAULT FALSE`, `cadence TEXT NOT NULL DEFAULT '5m' CHECK (cadence IN ('5m','1d'))`, `graph_json JSONB NOT NULL DEFAULT '{}'::jsonb`, `concurrency_config JSONB NOT NULL DEFAULT '{"max_open_trades": 3, "max_equity_pct_per_trade": 33.3}'::jsonb`, `paper_cash NUMERIC(14,2) NOT NULL DEFAULT 10000.00`, `paper_positions JSONB NOT NULL DEFAULT '[]'::jsonb`, `paper_trades JSONB NOT NULL DEFAULT '[]'::jsonb`, `paper_equity_curve JSONB NOT NULL DEFAULT '[]'::jsonb`, `trial_count INTEGER NOT NULL DEFAULT 0`, `created_at`, `updated_at`. Indexes: `(user_id, updated_at DESC)`, `(is_public, is_template)`, and a partial `(is_live, cadence) WHERE is_live = TRUE`.
- **`recipe_execution_queue`** — Priority queue for previews, backtests, and live turns. Columns: `id UUID PK`, `recipe_id UUID NOT NULL REFERENCES strategy_recipes(id) ON DELETE CASCADE`, `user_id UUID NOT NULL`, `mode TEXT NOT NULL CHECK (mode IN ('preview','backtest','live_turn'))`, `priority INTEGER NOT NULL DEFAULT 10` (1 = live turn, 10 = background backtest), `status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','processing','completed','failed'))`, `provider TEXT NOT NULL DEFAULT 'auto-strata'`, `model TEXT NOT NULL DEFAULT 'strata'`, `weeks_requested JSONB NOT NULL DEFAULT '[]'::jsonb`, `progress_pct INTEGER NOT NULL DEFAULT 0`, `result_json JSONB`, `error_message TEXT`, `started_at`, `completed_at`, `created_at`. Partial index `(priority ASC, created_at ASC) WHERE status = 'pending'` plus `(user_id, created_at DESC)`.
- **`recipe_alerts_inbox`** — In-app trade signal delivery. Columns: `id UUID PK`, `user_id UUID NOT NULL`, `recipe_id UUID REFERENCES strategy_recipes(id) ON DELETE SET NULL`, `recipe_name TEXT NOT NULL`, `ticker TEXT NOT NULL`, `action TEXT NOT NULL CHECK (action IN ('BUY','SELL','HOLD','EXIT'))`, `entry_price NUMERIC(12,4) NOT NULL`, `target_price NUMERIC(12,4)`, `stop_loss NUMERIC(12,4)`, `timeframe TEXT NOT NULL`, `reason TEXT NOT NULL`, `context JSONB DEFAULT '{}'::jsonb`, `is_read BOOLEAN NOT NULL DEFAULT FALSE`, `created_at`. Indexes: `(user_id, created_at DESC)` and a partial `(user_id) WHERE is_read = FALSE`.
- **`recipe_waitlist_pledges`** — Early-supporter pledges for future dedicated GPU compute tiers. Columns: `id UUID PK`, `user_id UUID NOT NULL`, `email TEXT NOT NULL`, `intended_tier TEXT NOT NULL DEFAULT 'supporter'`, `feedback TEXT NOT NULL DEFAULT ''`, `created_at`. Index on `user_id`.

RLS is enabled on all five tables. `recipe_news_corpus` grants public `SELECT`; `strategy_recipes` grants public `SELECT` only for rows where `is_public = TRUE OR is_template = TRUE`; `recipe_execution_queue`, `recipe_alerts_inbox`, and `recipe_waitlist_pledges` are `service_role`-only. Explicit grants follow [[concepts/supabase-grant-convention]]: `SELECT` to `anon, authenticated` on `recipe_news_corpus` and `strategy_recipes`, and `ALL` to `service_role` on all five.

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

These five tables back the [[entities/government-ingestion]] pipeline (`apps/engine/ingest/government_fetchers.py`, `apps/engine/ingest/whale_fetchers.py`, `apps/engine/ingest/congress_fetchers.py`, and `apps/engine/ingest/insider_fetchers.py`):

- **`gov_macro_liquidity`** — Daily US Treasury General Account cash, national debt, and monthly deficit. Columns: `record_date DATE NOT NULL UNIQUE`, `tga_balance`, `tot_pub_debt`, `debt_held_public`, `intragov_holdings`, `monthly_deficit_surplus` (all `NUMERIC(18, 2)`), `raw_metadata JSONB DEFAULT '{}'`, `created_at TIMESTAMPTZ`. Indexed on `record_date DESC`. Upserted on conflict `record_date` by `upsert_gov_macro_liquidity`.
- **`gov_contracts`** — US (USAspending) and Canadian (CanadaBuys) federal contract awards. Columns: `country TEXT NOT NULL CHECK (country IN ('US', 'CA', 'OTHER'))`, `award_id TEXT NOT NULL`, `recipient_name TEXT NOT NULL`, `award_amount NUMERIC(16, 2) NOT NULL DEFAULT 0.00`, `currency TEXT NOT NULL DEFAULT 'USD'`, `description`, `agency_name`, `award_date DATE NOT NULL`, `contract_number`, `source_url`, `raw_metadata JSONB`, `created_at`. Unique constraint `uq_gov_contracts (country, award_id, recipient_name, award_date)`; indexes on `(country, award_date DESC)`, `recipient_name`, and `award_amount DESC`. Upserted by `upsert_gov_contracts`.
- **`institutional_whale_stakes`** — SEC Schedule 13D/13G beneficial ownership disclosures. Columns: `symbol TEXT NOT NULL`, `filer_name TEXT NOT NULL`, `filer_cik`, `filing_date DATE NOT NULL`, `accepted_date DATE`, `percent_of_class NUMERIC(6, 2) NOT NULL DEFAULT 0.00`, `shares_beneficially_owned NUMERIC(16, 2) NOT NULL DEFAULT 0.00`, `reporting_type`, `filing_type TEXT NOT NULL DEFAULT '13G' CHECK (filing_type IN ('13D', '13G', '13F', 'OTHER'))`, `is_exit BOOLEAN NOT NULL DEFAULT false`, `source_url`, `raw_metadata JSONB`, `created_at`. Unique constraint `uq_institutional_whale_stake (symbol, filer_name, filing_date, percent_of_class)`; indexes on `(symbol, filing_date DESC)`, `filer_name`, and `filing_date DESC`. Upserted by `upsert_institutional_whale_stakes`.
- **`congress_trades`** — US Senate and House STOCK Act personal transaction disclosures ingested from FMP (`/stable/senate-latest`, `/stable/house-latest`). Columns: `chamber` (`senate`/`house`), `representative_name`, `symbol`, `transaction_date`, `disclosure_date`, `district`, `owner`, `transaction_type` (`purchase`/`sale`/`exchange`), `amount_range`, `amount_est_midpoint` (numeric midpoint of the disclosed dollar band), `asset_description`, `source_url`. Dedup/upsert key: `(chamber, representative_name, symbol, transaction_date, transaction_type, amount_range)`. Upserted by `upsert_congress_trades`.
- **`insider_trades`** — SEC Form 4 corporate insider transactions plus Canadian cross-listed insider activity ingested from FMP (`/stable/insider-trading/latest`, `/stable/insider-trading/search`). Columns: `symbol`, `reporting_name`, `type_of_owner`, `transaction_date`, `filing_date`, `transaction_type` (`purchase`/`sale`), `securities_transacted`, `price`, `total_value`, `securities_owned`, `source_url`. Dedup/upsert key: `(symbol, reporting_name, transaction_date, filing_date, transaction_type, securities_transacted, price)`. Upserted by `upsert_insider_trades`.

All five enable RLS with public `SELECT` and `service_role` full access. The fiscal/contract/whale trio is created by migrations `20261106180000_create_gov_macro_and_contracts.sql` and `20261106190000_create_institutional_whale_stakes.sql` (mirrored in `docker/archive/init.sql`); `congress_trades` and `insider_trades` are populated by the Congress and insider ingestion stages of the same pipeline.

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
- `pop_next_recipe_job()` — Atomic priority dequeue for the [[entities/recipe-studio]] worker (migration `20261112103000_create_recipe_studio_v2.sql`). Re-queues `processing` rows stalled longer than 5 minutes, then selects the lowest `priority` / oldest `created_at` pending row with `FOR UPDATE SKIP LOCKED`, flips it to `processing` with `progress_pct = 5`, and returns the job tuple (`job_id`, `job_recipe_id`, `job_user_id`, `job_mode`, `job_priority`, `job_provider`, `job_model`, `job_weeks_requested`). Declared `SECURITY DEFINER` with `SET search_path = public`; `EXECUTE` is revoked from `PUBLIC`, `anon`, and `authenticated` and granted only to `service_role`.
- `replace_daily_stock_picks(p_basket_id UUID, p_picks JSONB)` — Atomic replacement of a [[entities/daily-stock-picker]] basket's picks (migration `20261113130000_create_replace_daily_stock_picks_rpc.sql`). Deletes every `daily_stock_picks` row for `p_basket_id` and re-inserts the 6 picks from the JSONB array (`target_date`, `model_name`, `ticker`, `direction`, `rank`, `confidence`, `expected_return_pct`, `reasoning`, `status = 'pending'`) inside a single transaction, so a crash or conflict between two independent PostgREST round-trips can never leave a basket with zero picks. Declared `SECURITY DEFINER` with `SET search_path = public`; `EXECUTE` is revoked from `PUBLIC` and granted only to `service_role`.
- `match_memories(query_embedding extensions.vector(768), match_threshold float, match_count int, filter_memory_types text[] DEFAULT NULL)` — pgvector cosine-similarity search over the `memories` store used by the tiered RAG path (see [[concepts/rag-strategy]]). The embedding argument is qualified as `extensions.vector(768)` and pinned with `SET search_path = public, extensions` because pgvector lives in the `extensions` schema (migrations `20260129000000_add_memory_type_to_memories.sql` and `20260305000000_add_importance_score_to_memories.sql`). The 4-argument signature is canonical; a stale 3-argument definition surfaces as `PGRST202` and silently empties Tier 2 RAG.
- `match_decisions(query_embedding extensions.vector, match_threshold double precision, match_count integer, filter_model_name text DEFAULT NULL)` — pgvector similarity search over `decisions.embedding`, the per-agent decision half of `retrieve_for_decision()`. Restored by `20261106000000_fix_match_decisions_search_path.sql` after the overload migration dropped the search path (runtime error `42883`: `operator does not exist: extensions.vector <=> extensions.vector`).

After applying any `match_*` DDL or table migrations, run `NOTIFY pgrst, 'reload schema';` on the primary. Because PostgreSQL physical streaming replication does not propagate `NOTIFY` events across standby instances, the MiniPC PostgREST replica must be restarted to reload its schema cache. Deploy and restart via `./docker/archive/deploy_secondary.sh cv-minipc@minipc` (which executes `docker compose restart archive-postgrest` and verifies local read health). Failure-mode notes live in [[concepts/hybrid-database-archival]].

## Migrations

Migrations live in `supabase/migrations/` and follow the Supabase naming convention: `YYYYMMDDHHMMSS_description.sql`. Each migration is idempotent and tracked in version control.

## Related

- [[entities/recipe-studio]]
- [[entities/daily-stock-picker]]
- [[entities/company-research-reports]]
- [[entities/government-ingestion]]
- [[entities/congress-trades]]
- [[entities/insider-trades]]
- [[entities/secondary-minipc-edge]]
- [[concepts/hybrid-database-archival]]
- [[concepts/auth-db-client-separation]]
- [[concepts/rag-strategy]]
- [[concepts/private-memory-vault]]
- [[concepts/supabase-grant-convention]]
- [[entities/live-agent-trader]]
- [[entities/engine]]
