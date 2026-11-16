-- ============================================================================
-- Migration: 20261116000000_recipe_beta_quotas_and_dual_lane.sql
-- Description: Beta per-user quota overrides, queue job cancellation &
--              heartbeat leasing, and dual-lane pop_next_recipe_job RPC
--              serializing backtests (max 1 active) without blocking live turns.
-- ============================================================================

-- 1. Extend recipe_execution_queue status constraint & add heartbeat / cancel timestamps
DO $$
DECLARE
    chk RECORD;
BEGIN
    FOR chk IN
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'public.recipe_execution_queue'::regclass
          AND contype = 'c'
          AND pg_get_constraintdef(oid) ILIKE '%status%'
    LOOP
        EXECUTE format('ALTER TABLE public.recipe_execution_queue DROP CONSTRAINT %I', chk.conname);
    END LOOP;
END $$;

ALTER TABLE public.recipe_execution_queue
    ADD CONSTRAINT recipe_execution_queue_status_check
    CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled'));

ALTER TABLE public.recipe_execution_queue
    ADD COLUMN IF NOT EXISTS heartbeat_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_recipe_queue_pending_mode
    ON public.recipe_execution_queue (mode, priority ASC, created_at ASC)
    WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_recipe_queue_active_mode
    ON public.recipe_execution_queue (mode, status)
    WHERE status IN ('pending', 'processing');

CREATE INDEX IF NOT EXISTS idx_recipe_queue_user_mode_created
    ON public.recipe_execution_queue (user_id, mode, created_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_recipe_single_processing_backtest
    ON public.recipe_execution_queue ((1))
    WHERE mode = 'backtest' AND status = 'processing';

-- 2. Per-user quota & tier overrides table (decoupled from auth.users)
CREATE TABLE IF NOT EXISTS public.recipe_user_quotas (
    user_id UUID PRIMARY KEY,
    tier TEXT NOT NULL DEFAULT 'beta_starter',
    max_concurrent_backtests INTEGER NOT NULL DEFAULT 1,
    daily_backtest_limit INTEGER NOT NULL DEFAULT 2,
    daily_live_turn_limit INTEGER NOT NULL DEFAULT 3,
    max_live_recipes INTEGER NOT NULL DEFAULT 1,
    notes TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.recipe_user_quotas ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow users to read own recipe_user_quotas" ON public.recipe_user_quotas;
CREATE POLICY "Allow users to read own recipe_user_quotas"
    ON public.recipe_user_quotas FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Allow service_role full access on recipe_user_quotas" ON public.recipe_user_quotas;
CREATE POLICY "Allow service_role full access on recipe_user_quotas"
    ON public.recipe_user_quotas FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

GRANT SELECT ON public.recipe_user_quotas TO authenticated;
GRANT ALL ON public.recipe_user_quotas TO service_role;

-- 3. Dual-lane atomic dequeue RPC with heartbeat lease & single-backtest guard
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
    backtest_running BOOLEAN;
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

    SELECT EXISTS (
        SELECT 1
        FROM public.recipe_execution_queue
        WHERE mode = 'backtest'
          AND status = 'processing'
    ) INTO backtest_running;

    IF target_mode = 'backtest' AND backtest_running THEN
        RETURN;
    END IF;

    SELECT q.id INTO target_id
    FROM public.recipe_execution_queue q
    WHERE q.status = 'pending'
      AND (target_mode IS NULL OR q.mode = target_mode)
      AND (q.mode <> 'backtest' OR NOT backtest_running)
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
