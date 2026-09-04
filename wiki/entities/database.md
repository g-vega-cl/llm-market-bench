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
- `chat_memories` — User-curated private research theses with full RLS isolation (see [[concepts/private-memory-vault]])
- `decisions` — Agent buy/sell decisions (1 row per agent per ticker per session)
- `economic_calendar_events` — Parsed economic indicator data
- `generated_newsletters` — Daily AI market briefings
- `government_incentives` — High-impact policy tracking
- `market_feeling` — Daily and weekly market sentiment assessments
- `memory_hooks` — Contrarian analysis and causal chain entries
- `memory_tags` — Tagged memory cards
- `meta_prompt_experiments` — Auto-research prompt experiment logs
- `newsletter_scrape_data` — Raw newsletter source scrapes
- `portfolio_snapshots` — Point-in-time portfolio state
- `position_actions` — Delta-based position change queue (buy/sell/hold)
- `sector_predictions` — Weekly sector ranking predictions
- `trades` — Executed trade records with attribution

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

Applied to all user-facing tables. The `chat_memories` table uses four permissive policies (`SELECT`, `INSERT`, `UPDATE`, `DELETE`) all scoped to `auth.uid() = user_id`.

## Grant Convention

Following [[concepts/supabase-grant-convention]], all tables exposed via the PostgREST Data API must have explicit `GRANT SELECT, INSERT, UPDATE, DELETE ON public.<table> TO authenticated;` statements. The `chat_memories` migration includes both authenticated and service_role grants.

## Migrations

Migrations live in `supabase/migrations/` and follow the Supabase naming convention: `YYYYMMDDHHMMSS_description.sql`. Each migration is idempotent and tracked in version control.

## Related

- [[concepts/rag-strategy]]
- [[concepts/private-memory-vault]]
- [[concepts/supabase-grant-convention]]
- [[entities/engine]]
