-- ============================================================================
-- Migration: 20261120000000_add_recipe_turbo_mode.sql
-- Description: Add Turbo mode (5m cadence for 1h, once per ET trading day per user)
--              for live Strategy Recipes, DB state invariants, queue indexes,
--              and server-time-derived atomic activation RPC.
-- ============================================================================

-- 1. Active Turbo window timestamp + state-machine invariant on strategy_recipes
ALTER TABLE public.strategy_recipes
    ADD COLUMN IF NOT EXISTS turbo_expires_at TIMESTAMPTZ;

UPDATE public.strategy_recipes
SET turbo_expires_at = NULL
WHERE turbo_expires_at IS NOT NULL
  AND (NOT is_live OR archived_at IS NOT NULL);

ALTER TABLE public.strategy_recipes
    DROP CONSTRAINT IF EXISTS strategy_recipes_turbo_requires_live;

ALTER TABLE public.strategy_recipes
    ADD CONSTRAINT strategy_recipes_turbo_requires_live
    CHECK ((is_live = TRUE AND archived_at IS NULL) OR turbo_expires_at IS NULL);

CREATE INDEX IF NOT EXISTS idx_strategy_recipes_turbo_active
    ON public.strategy_recipes (turbo_expires_at)
    WHERE is_live = TRUE AND archived_at IS NULL AND turbo_expires_at IS NOT NULL;

-- 2. Queue indexes for 5m/30m live_turn dedup and replica-lag duplicate protection
CREATE INDEX IF NOT EXISTS idx_recipe_queue_live_turn_created
    ON public.recipe_execution_queue (created_at DESC)
    WHERE mode = 'live_turn' AND status <> 'cancelled';

WITH ranked_open AS (
    SELECT
        id,
        ROW_NUMBER() OVER (
            PARTITION BY recipe_id
            ORDER BY (status = 'processing') DESC, created_at DESC
        ) AS rn
    FROM public.recipe_execution_queue
    WHERE mode = 'live_turn'
      AND status IN ('pending', 'processing')
)
UPDATE public.recipe_execution_queue q
SET status = 'cancelled',
    cancelled_at = COALESCE(q.cancelled_at, NOW())
FROM ranked_open r
WHERE q.id = r.id
  AND r.rn > 1
  AND q.status = 'pending';

CREATE UNIQUE INDEX IF NOT EXISTS idx_recipe_one_open_live_turn_per_recipe
    ON public.recipe_execution_queue (recipe_id)
    WHERE mode = 'live_turn' AND status IN ('pending', 'processing');

-- 3. Per-user daily Turbo allowance tracker (1 activation per ET trading day)
ALTER TABLE public.recipe_user_quotas
    ADD COLUMN IF NOT EXISTS last_turbo_et_date DATE;

-- 4. Atomic Turbo activation deriving ET clock & expiry bounds strictly inside PostgreSQL
DROP FUNCTION IF EXISTS public.activate_recipe_turbo(UUID, UUID, DATE, TIMESTAMPTZ);
DROP FUNCTION IF EXISTS public.activate_recipe_turbo(UUID, UUID);

CREATE OR REPLACE FUNCTION public.activate_recipe_turbo(
    p_user_id UUID,
    p_recipe_id UUID
)
RETURNS TABLE (
    recipe_id UUID,
    turbo_expires_at TIMESTAMPTZ,
    enqueued_job_id UUID
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_now TIMESTAMPTZ := NOW();
    v_et_now TIMESTAMP := v_now AT TIME ZONE 'America/New_York';
    v_et_date DATE := v_et_now::date;
    v_et_time TIME := v_et_now::time;
    v_close_utc TIMESTAMPTZ := (v_et_date::timestamp + TIME '16:00:00') AT TIME ZONE 'America/New_York';
    v_expires_at TIMESTAMPTZ := LEAST(v_now + INTERVAL '1 hour', v_close_utc);
    v_last_turbo_date DATE;
    v_owner_id UUID;
    v_is_live BOOLEAN;
    v_archived_at TIMESTAMPTZ;
    v_existing_job_id UUID;
    v_job_id UUID;
BEGIN
    IF p_user_id IS NULL OR p_recipe_id IS NULL THEN
        RAISE EXCEPTION 'Missing user_id or recipe_id for Turbo activation.';
    END IF;

    IF EXTRACT(ISODOW FROM v_et_date) NOT BETWEEN 1 AND 5
       OR v_et_time < TIME '09:30:00'
       OR v_et_time >= TIME '15:55:00' THEN
        RAISE EXCEPTION 'Turbo is only available during US market hours (Mon-Fri 09:30-15:55 ET).';
    END IF;

    INSERT INTO public.recipe_user_quotas (user_id)
    VALUES (p_user_id)
    ON CONFLICT (user_id) DO NOTHING;

    SELECT q.last_turbo_et_date
    INTO v_last_turbo_date
    FROM public.recipe_user_quotas q
    WHERE q.user_id = p_user_id
    FOR UPDATE;

    IF v_last_turbo_date = v_et_date THEN
        RAISE EXCEPTION 'Daily Turbo limit reached (1/1 used today ET). Try again next market day.';
    END IF;

    SELECT r.user_id, r.is_live, r.archived_at
    INTO v_owner_id, v_is_live, v_archived_at
    FROM public.strategy_recipes r
    WHERE r.id = p_recipe_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Recipe not found: %', p_recipe_id;
    END IF;

    IF v_owner_id <> p_user_id THEN
        RAISE EXCEPTION 'Unauthorized: cannot activate Turbo for another user';
    END IF;

    IF v_archived_at IS NOT NULL THEN
        RAISE EXCEPTION 'This strategy was removed from My Strategies. Restore it before activating Turbo.';
    END IF;

    IF NOT COALESCE(v_is_live, FALSE) THEN
        RAISE EXCEPTION 'Enable Live (30m) on this bot before activating Turbo.';
    END IF;

    UPDATE public.recipe_user_quotas
    SET last_turbo_et_date = v_et_date,
        updated_at = v_now
    WHERE user_id = p_user_id;

    UPDATE public.strategy_recipes
    SET turbo_expires_at = v_expires_at,
        updated_at = v_now
    WHERE id = p_recipe_id;

    -- Trigger the first 5-minute Turbo turn immediately unless one is already open
    SELECT q.id
    INTO v_existing_job_id
    FROM public.recipe_execution_queue q
    WHERE q.recipe_id = p_recipe_id
      AND q.mode = 'live_turn'
      AND q.status IN ('pending', 'processing')
    ORDER BY q.created_at DESC
    LIMIT 1;

    IF v_existing_job_id IS NULL THEN
        INSERT INTO public.recipe_execution_queue (
            recipe_id,
            user_id,
            mode,
            priority,
            status,
            provider,
            model,
            weeks_requested,
            progress_pct
        )
        VALUES (
            p_recipe_id,
            p_user_id,
            'live_turn',
            1,
            'pending',
            'free-llm-proxy',
            'auto-go',
            '[]'::jsonb,
            0
        )
        RETURNING id INTO v_job_id;
    ELSE
        v_job_id := v_existing_job_id;
    END IF;

    RETURN QUERY
    SELECT p_recipe_id, v_expires_at, v_job_id;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.activate_recipe_turbo(UUID, UUID) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.activate_recipe_turbo(UUID, UUID) TO service_role;
