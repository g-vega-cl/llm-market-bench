-- ============================================================================
-- Migration: 20261112103000_create_recipe_studio_v2.sql
-- Description: Core tables and RPCs for Voxel DAG Strategy Recipe Studio,
--              unified news corpus, execution queue, alerts inbox, and waitlist.
-- Strict rules:
--   - Decoupled from auth.users (cloud user UUIDs stored directly).
--   - RLS enabled on 100% of tables with explicit policies.
--   - Explicit GRANT statements for anon, authenticated, and service_role.
-- ============================================================================

-- 1. Recipe News Corpus
CREATE TABLE IF NOT EXISTS public.recipe_news_corpus (
    article_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    date_published TIMESTAMPTZ NOT NULL,
    date_precision TEXT NOT NULL DEFAULT 'article_meta',
    source TEXT NOT NULL,
    source_family TEXT NOT NULL,
    full_text TEXT NOT NULL,
    word_count INTEGER NOT NULL DEFAULT 0,
    company TEXT NOT NULL,
    companies TEXT[] NOT NULL DEFAULT '{}',
    tickers TEXT[] NOT NULL DEFAULT '{}',
    company_in_headline BOOLEAN NOT NULL DEFAULT FALSE,
    buckets TEXT[] NOT NULL DEFAULT '{}',
    search_tsv TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('english', title || ' ' || coalesce(full_text, ''))
    ) STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recipe_news_date_published 
    ON public.recipe_news_corpus (date_published DESC);
CREATE INDEX IF NOT EXISTS idx_recipe_news_tickers 
    ON public.recipe_news_corpus USING GIN (tickers);
CREATE INDEX IF NOT EXISTS idx_recipe_news_buckets 
    ON public.recipe_news_corpus USING GIN (buckets);
CREATE INDEX IF NOT EXISTS idx_recipe_news_search_tsv 
    ON public.recipe_news_corpus USING GIN (search_tsv);

-- 2. Strategy Recipes (Voxel DAG configurations & paper ledger)
CREATE TABLE IF NOT EXISTS public.strategy_recipes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    is_template BOOLEAN NOT NULL DEFAULT FALSE,
    is_live BOOLEAN NOT NULL DEFAULT FALSE,
    cadence TEXT NOT NULL DEFAULT '5m' CHECK (cadence IN ('5m', '1d')),
    graph_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    concurrency_config JSONB NOT NULL DEFAULT '{"max_open_trades": 3, "max_equity_pct_per_trade": 33.3}'::jsonb,
    paper_cash NUMERIC(14, 2) NOT NULL DEFAULT 10000.00,
    paper_positions JSONB NOT NULL DEFAULT '[]'::jsonb,
    paper_trades JSONB NOT NULL DEFAULT '[]'::jsonb,
    paper_equity_curve JSONB NOT NULL DEFAULT '[]'::jsonb,
    trial_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_strategy_recipes_user 
    ON public.strategy_recipes (user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_strategy_recipes_public 
    ON public.strategy_recipes (is_public, is_template);
CREATE INDEX IF NOT EXISTS idx_strategy_recipes_live 
    ON public.strategy_recipes (is_live, cadence) WHERE is_live = TRUE;

-- 3. Recipe Execution Queue (Local GPU auto-strata / preview / backtest / live turns)
CREATE TABLE IF NOT EXISTS public.recipe_execution_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipe_id UUID NOT NULL REFERENCES public.strategy_recipes(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('preview', 'backtest', 'live_turn')),
    priority INTEGER NOT NULL DEFAULT 10, -- Priority 1 for live turns, 10 for background backtests
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    provider TEXT NOT NULL DEFAULT 'auto-strata',
    model TEXT NOT NULL DEFAULT 'strata',
    weeks_requested JSONB NOT NULL DEFAULT '[]'::jsonb,
    progress_pct INTEGER NOT NULL DEFAULT 0,
    result_json JSONB,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recipe_queue_priority_created 
    ON public.recipe_execution_queue (priority ASC, created_at ASC) 
    WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_recipe_queue_user 
    ON public.recipe_execution_queue (user_id, created_at DESC);

-- 4. Recipe Alerts Inbox (Self-contained in-app signals)
CREATE TABLE IF NOT EXISTS public.recipe_alerts_inbox (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    recipe_id UUID REFERENCES public.strategy_recipes(id) ON DELETE SET NULL,
    recipe_name TEXT NOT NULL,
    ticker TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('BUY', 'SELL', 'HOLD', 'EXIT')),
    entry_price NUMERIC(12, 4) NOT NULL,
    target_price NUMERIC(12, 4),
    stop_loss NUMERIC(12, 4),
    timeframe TEXT NOT NULL,
    reason TEXT NOT NULL,
    context JSONB DEFAULT '{}'::jsonb,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recipe_alerts_user_created 
    ON public.recipe_alerts_inbox (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_recipe_alerts_unread 
    ON public.recipe_alerts_inbox (user_id) WHERE is_read = FALSE;

-- 5. Recipe Intraday Bars Cache (Point-in-time 5-minute bar cache)
CREATE TABLE IF NOT EXISTS public.recipe_intraday_bars (
    ticker TEXT NOT NULL,
    bar_time_utc TIMESTAMPTZ NOT NULL,
    open NUMERIC(12, 4) NOT NULL,
    high NUMERIC(12, 4) NOT NULL,
    low NUMERIC(12, 4) NOT NULL,
    close NUMERIC(12, 4) NOT NULL,
    volume BIGINT NOT NULL DEFAULT 0,
    vwap NUMERIC(12, 4),
    PRIMARY KEY (ticker, bar_time_utc)
);

CREATE INDEX IF NOT EXISTS idx_recipe_intraday_bars_ticker_time 
    ON public.recipe_intraday_bars (ticker, bar_time_utc DESC);

-- 6. Early-Supporter Waitlist Pledges
CREATE TABLE IF NOT EXISTS public.recipe_waitlist_pledges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    email TEXT NOT NULL,
    intended_tier TEXT NOT NULL DEFAULT 'supporter',
    feedback TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recipe_waitlist_user 
    ON public.recipe_waitlist_pledges (user_id);

-- ============================================================================
-- Atomic Dequeue RPC (Priority Queue with SKIP LOCKED)
-- ============================================================================
CREATE OR REPLACE FUNCTION public.pop_next_recipe_job()
RETURNS TABLE (
    job_id UUID,
    job_recipe_id UUID,
    job_user_id UUID,
    job_mode TEXT,
    job_priority INTEGER,
    job_provider TEXT,
    job_model TEXT,
    job_weeks_requested JSONB
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    target_id UUID;
BEGIN
    -- Re-queue stalled jobs older than 5 minutes
    UPDATE public.recipe_execution_queue
    SET status = 'pending', started_at = NULL
    WHERE status = 'processing'
      AND started_at < NOW() - INTERVAL '5 minutes';

    -- Atomically select the highest-priority pending job (lowest priority integer)
    SELECT id INTO target_id
    FROM public.recipe_execution_queue
    WHERE status = 'pending'
    ORDER BY priority ASC, created_at ASC
    FOR UPDATE SKIP LOCKED
    LIMIT 1;

    IF target_id IS NOT NULL THEN
        UPDATE public.recipe_execution_queue
        SET status = 'processing',
            started_at = NOW(),
            progress_pct = 5
        WHERE id = target_id;

        RETURN QUERY
        SELECT 
            q.id AS job_id,
            q.recipe_id AS job_recipe_id,
            q.user_id AS job_user_id,
            q.mode AS job_mode,
            q.priority AS job_priority,
            q.provider AS job_provider,
            q.model AS job_model,
            q.weeks_requested AS job_weeks_requested
        FROM public.recipe_execution_queue q
        WHERE q.id = target_id;
    END IF;
END;
$$;

-- ============================================================================
-- Row-Level Security (RLS) Configuration
-- ============================================================================
ALTER TABLE public.recipe_news_corpus ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.strategy_recipes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.recipe_execution_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.recipe_alerts_inbox ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.recipe_intraday_bars ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.recipe_waitlist_pledges ENABLE ROW LEVEL SECURITY;

-- Policies: recipe_news_corpus (Public Read, Service Role Write)
CREATE POLICY "Allow public read access on recipe_news_corpus"
    ON public.recipe_news_corpus FOR SELECT
    USING (true);

CREATE POLICY "Allow service_role full access on recipe_news_corpus"
    ON public.recipe_news_corpus FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Policies: strategy_recipes (Public Read for templates/public, Service Role Full Access)
CREATE POLICY "Allow public read on templates and public recipes"
    ON public.strategy_recipes FOR SELECT
    USING (is_public = TRUE OR is_template = TRUE);

CREATE POLICY "Allow service_role full access on strategy_recipes"
    ON public.strategy_recipes FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Policies: recipe_execution_queue (Service Role Full Access)
CREATE POLICY "Allow service_role full access on recipe_execution_queue"
    ON public.recipe_execution_queue FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Policies: recipe_alerts_inbox (Service Role Full Access)
CREATE POLICY "Allow service_role full access on recipe_alerts_inbox"
    ON public.recipe_alerts_inbox FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Policies: recipe_intraday_bars (Public Read, Service Role Write)
CREATE POLICY "Allow public read on recipe_intraday_bars"
    ON public.recipe_intraday_bars FOR SELECT
    USING (true);

CREATE POLICY "Allow service_role full access on recipe_intraday_bars"
    ON public.recipe_intraday_bars FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Policies: recipe_waitlist_pledges (Service Role Full Access)
CREATE POLICY "Allow service_role full access on recipe_waitlist_pledges"
    ON public.recipe_waitlist_pledges FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- ============================================================================
-- Explicit Grants
-- ============================================================================
GRANT SELECT ON public.recipe_news_corpus TO anon, authenticated;
GRANT ALL ON public.recipe_news_corpus TO service_role;

GRANT SELECT ON public.strategy_recipes TO anon, authenticated;
GRANT ALL ON public.strategy_recipes TO service_role;

GRANT ALL ON public.recipe_execution_queue TO service_role;

GRANT ALL ON public.recipe_alerts_inbox TO service_role;

GRANT SELECT ON public.recipe_intraday_bars TO anon, authenticated;
GRANT ALL ON public.recipe_intraday_bars TO service_role;

GRANT ALL ON public.recipe_waitlist_pledges TO service_role;

REVOKE EXECUTE ON FUNCTION public.pop_next_recipe_job() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.pop_next_recipe_job() TO service_role;
