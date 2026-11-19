-- ============================================================================
-- Migration: 20261119000000_recipe_public_stats_and_concurrency.sql
-- Description:
--   1. public.recipe_public_stats — one materialised leaderboard row per recipe,
--      written by the recipe runner each cycle. The public homepage reads this
--      table directly (repo mandate: zero frontend compute), instead of parsing
--      strategy_recipes.paper_equity_curve in the browser.
--   2. public.recipe_ops_events — durable ops telemetry for scheduler health
--      (enqueue truncation, starved live recipes, paid-provider fallbacks).
--   3. Lift the single-processing-backtest guard to three concurrent backtests.
--      Dequeue stays serialised by the existing advisory lock, so the cap is a
--      counted guard rather than a boolean.
-- ============================================================================

-- 1. Materialised public leaderboard rows -------------------------------------
CREATE TABLE IF NOT EXISTS public.recipe_public_stats (
    recipe_id UUID PRIMARY KEY REFERENCES public.strategy_recipes(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    is_live BOOLEAN NOT NULL DEFAULT false,
    return_pct NUMERIC(10, 4),
    spy_return_pct NUMERIC(10, 4),
    trade_count INTEGER NOT NULL DEFAULT 0,
    open_positions INTEGER NOT NULL DEFAULT 0,
    runs_today INTEGER NOT NULL DEFAULT 0,
    first_equity_date DATE,
    last_equity_date DATE,
    last_run_at TIMESTAMPTZ,
    last_action JSONB NOT NULL DEFAULT '{}'::jsonb,
    resolved_model TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recipe_public_stats_active
    ON public.recipe_public_stats (last_run_at DESC)
    WHERE is_live = true;

ALTER TABLE public.recipe_public_stats ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow public read on recipe_public_stats" ON public.recipe_public_stats;
CREATE POLICY "Allow public read on recipe_public_stats"
    ON public.recipe_public_stats
    FOR SELECT
    USING (true);

DROP POLICY IF EXISTS "Allow service_role full access on recipe_public_stats" ON public.recipe_public_stats;
CREATE POLICY "Allow service_role full access on recipe_public_stats"
    ON public.recipe_public_stats
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

GRANT SELECT ON public.recipe_public_stats TO anon, authenticated;
GRANT ALL ON public.recipe_public_stats TO service_role;

-- 2. Durable ops telemetry ---------------------------------------------------
CREATE TABLE IF NOT EXISTS public.recipe_ops_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'warning',
    detail JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recipe_ops_events_created
    ON public.recipe_ops_events (created_at DESC);

ALTER TABLE public.recipe_ops_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow service_role full access on recipe_ops_events" ON public.recipe_ops_events;
CREATE POLICY "Allow service_role full access on recipe_ops_events"
    ON public.recipe_ops_events
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

GRANT ALL ON public.recipe_ops_events TO service_role;

-- 3. Three concurrent backtests instead of one -------------------------------
-- The unique "((1))" index physically forbade a second 'processing' backtest.
-- A counted guard inside the existing advisory lock replaces it: dequeue is
-- still serialised, so no two workers can observe the same vacant slot.
DROP INDEX IF EXISTS public.idx_recipe_single_processing_backtest;

DROP FUNCTION IF EXISTS public.pop_next_recipe_job();
DROP FUNCTION IF EXISTS public.pop_next_recipe_job(TEXT);

CREATE OR REPLACE FUNCTION public.pop_next_recipe_job(target_mode TEXT DEFAULT NULL)
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
    backtest_running INTEGER;
    c_max_processing_backtests CONSTANT INTEGER := 3;
BEGIN
    IF target_mode IS NULL OR target_mode = 'backtest' THEN
        PERFORM pg_advisory_xact_lock(hashtext('recipe_backtest_dequeue_lock'));
    END IF;

    -- Recover stalled jobs whose heartbeat (or start time) lapsed > 10 minutes
    UPDATE public.recipe_execution_queue
    SET status = 'pending',
        started_at = NULL,
        heartbeat_at = NULL
    WHERE status = 'processing'
      AND (target_mode IS NULL OR mode = target_mode)
      AND COALESCE(heartbeat_at, started_at) < NOW() - INTERVAL '10 minutes';

    SELECT COUNT(*) INTO backtest_running
    FROM public.recipe_execution_queue
    WHERE mode = 'backtest'
      AND status = 'processing';

    IF target_mode = 'backtest' AND backtest_running >= c_max_processing_backtests THEN
        RETURN;
    END IF;

    SELECT q.id INTO target_id
    FROM public.recipe_execution_queue q
    WHERE q.status = 'pending'
      AND (target_mode IS NULL OR q.mode = target_mode)
      AND (q.mode <> 'backtest' OR backtest_running < c_max_processing_backtests)
    ORDER BY q.priority ASC, q.created_at ASC
    FOR UPDATE SKIP LOCKED
    LIMIT 1;

    IF target_id IS NOT NULL THEN
        UPDATE public.recipe_execution_queue
        SET status = 'processing',
            started_at = NOW(),
            heartbeat_at = NOW(),
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

REVOKE EXECUTE ON FUNCTION public.pop_next_recipe_job(TEXT) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.pop_next_recipe_job(TEXT) TO service_role;

COMMENT ON TABLE public.recipe_public_stats IS
    'Runner-materialised public leaderboard row per recipe (return vs SPY over the same equity window).';
COMMENT ON TABLE public.recipe_ops_events IS
    'Durable scheduler/ops telemetry: enqueue truncation, starvation, paid-provider fallbacks.';
