-- ============================================================================
-- Migration: 20261127192000_live_week_funding.sql
-- Description: Couples going live to the token ledger. `start_live_week` spends
--              one live_week token and writes live_expires_at in the same
--              transaction, so a bot cannot go live without a funded week and
--              cannot stay live past one. `switch_live_schedule` delegates its
--              enable step here, because the live_expiry CHECK now rejects an
--              is_live=TRUE row with no deadline.
-- Plan: .hermes/plans/2026-11-27-token-architecture.md
-- ============================================================================

BEGIN;

-- 1. start_live_week ----------------------------------------------------------
CREATE OR REPLACE FUNCTION public.start_live_week(
    p_user_id   UUID,
    p_recipe_id UUID
) RETURNS TABLE (
    is_live         BOOLEAN,
    live_expires_at TIMESTAMPTZ,
    token_balance   INTEGER
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_now      TIMESTAMPTZ := NOW();
    v_owner    UUID;
    v_archived TIMESTAMPTZ;
    v_already  BOOLEAN;
    v_max      INTEGER := 3;
    v_live     INTEGER := 0;
    v_expires  TIMESTAMPTZ;
    v_balance  INTEGER;
    v_spend    RECORD;
BEGIN
    IF p_user_id IS NULL OR p_recipe_id IS NULL THEN
        RAISE EXCEPTION 'Missing user_id or recipe_id.';
    END IF;

    SELECT r.user_id, r.archived_at, r.is_live
      INTO v_owner, v_archived, v_already
      FROM public.strategy_recipes r
     WHERE r.id = p_recipe_id
       FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Recipe not found: %', p_recipe_id;
    END IF;
    IF v_owner <> p_user_id THEN
        RAISE EXCEPTION 'Unauthorized: cannot modify live schedule for another user';
    END IF;
    IF v_archived IS NOT NULL THEN
        RAISE EXCEPTION 'This strategy was removed from My Strategies. Save it to restore before scheduling it live.';
    END IF;

    -- Re-enabling an already-live bot must not buy a second week.
    IF v_already THEN
        SELECT r.live_expires_at INTO v_expires
          FROM public.strategy_recipes r WHERE r.id = p_recipe_id;
        SELECT b.balance INTO v_balance
          FROM public.token_balances b WHERE b.owner_key = 'user:' || p_user_id;
        RETURN QUERY SELECT TRUE, v_expires, COALESCE(v_balance, 0);
        RETURN;
    END IF;

    SELECT COALESCE(q.max_live_recipes, 3) INTO v_max
      FROM public.recipe_user_quotas q
     WHERE q.user_id = p_user_id;

    SELECT COUNT(*) INTO v_live
      FROM public.strategy_recipes r
     WHERE r.user_id = p_user_id
       AND r.is_live = TRUE
       AND r.id <> p_recipe_id;

    IF v_live >= COALESCE(v_max, 3) THEN
        RAISE EXCEPTION 'Scheduled live limit reached (%/%). Pause an existing live recipe first.',
            v_live + 1, COALESCE(v_max, 3);
    END IF;

    -- Spend before flipping the flag: a refusal aborts the whole transaction, so
    -- a bot never runs on a week nobody paid for.
    SELECT * INTO v_spend
      FROM public.reserve_token('user:' || p_user_id, 'live_week', p_recipe_id);

    IF NOT v_spend.ok THEN
        RAISE EXCEPTION 'TOKEN:%', v_spend.code;
    END IF;

    v_expires := v_now + INTERVAL '7 days';

    UPDATE public.strategy_recipes
       SET is_live = TRUE,
           live_expires_at = v_expires,
           updated_at = v_now
     WHERE id = p_recipe_id
       AND user_id = p_user_id;

    RETURN QUERY SELECT TRUE, v_expires, v_spend.balance;
END;
$$;

COMMENT ON FUNCTION public.start_live_week(UUID, UUID) IS
    'Spends one live_week token and sets live_expires_at in the same transaction. Idempotent for an already-live bot.';

-- 2. switch_live_schedule delegates the enable step ---------------------------
-- The return type grows, so the function is replaced rather than redefined.
DROP FUNCTION IF EXISTS public.switch_live_schedule(UUID, UUID, UUID);

CREATE OR REPLACE FUNCTION public.switch_live_schedule(
    p_user_id UUID,
    p_pause_recipe_id UUID,
    p_enable_recipe_id UUID
)
RETURNS TABLE (
    paused_id       UUID,
    enabled_id      UUID,
    is_live         BOOLEAN,
    live_expires_at TIMESTAMPTZ,
    token_balance   INTEGER
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_now TIMESTAMPTZ := NOW();
    v_first_id UUID := LEAST(p_pause_recipe_id, p_enable_recipe_id);
    v_second_id UUID := GREATEST(p_pause_recipe_id, p_enable_recipe_id);
    v_pause_owner UUID;
    v_enable_owner UUID;
    v_enable_archived TIMESTAMPTZ;
    v_enabled RECORD;
BEGIN
    IF p_user_id IS NULL OR p_pause_recipe_id IS NULL OR p_enable_recipe_id IS NULL THEN
        RAISE EXCEPTION 'Missing user_id, pause_recipe_id, or enable_recipe_id.';
    END IF;

    IF p_pause_recipe_id = p_enable_recipe_id THEN
        RAISE EXCEPTION 'Cannot switch a live bot with itself.';
    END IF;

    -- Lock both rows in deterministic UUID order to avoid deadlocks.
    PERFORM 1
    FROM public.strategy_recipes r
    WHERE r.id IN (v_first_id, v_second_id)
    ORDER BY r.id
    FOR UPDATE;

    SELECT r.user_id INTO v_pause_owner
      FROM public.strategy_recipes r WHERE r.id = p_pause_recipe_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Recipe not found: %', p_pause_recipe_id;
    END IF;
    IF v_pause_owner <> p_user_id THEN
        RAISE EXCEPTION 'Unauthorized: cannot modify live schedule for another user';
    END IF;

    SELECT r.user_id, r.archived_at INTO v_enable_owner, v_enable_archived
      FROM public.strategy_recipes r WHERE r.id = p_enable_recipe_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Recipe not found: %', p_enable_recipe_id;
    END IF;
    IF v_enable_owner <> p_user_id THEN
        RAISE EXCEPTION 'Unauthorized: cannot modify live schedule for another user';
    END IF;
    IF v_enable_archived IS NOT NULL THEN
        RAISE EXCEPTION 'This strategy was removed from My Strategies. Save it to restore before scheduling it live.';
    END IF;

    UPDATE public.strategy_recipes
       SET is_live = FALSE,
           turbo_expires_at = NULL,
           updated_at = v_now
     WHERE id = p_pause_recipe_id
       AND user_id = p_user_id;

    UPDATE public.recipe_execution_queue
       SET status = 'cancelled',
           cancelled_at = v_now
     WHERE recipe_id = p_pause_recipe_id
       AND user_id = p_user_id
       AND mode = 'live_turn'
       AND status = 'pending';

    -- Spend + enable + expiry, all inside this transaction: a refused token
    -- rolls the pause back too.
    SELECT * INTO v_enabled FROM public.start_live_week(p_user_id, p_enable_recipe_id);

    RETURN QUERY
    SELECT p_pause_recipe_id, p_enable_recipe_id, v_enabled.is_live,
           v_enabled.live_expires_at, v_enabled.token_balance;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.start_live_week(UUID, UUID) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.start_live_week(UUID, UUID) TO service_role;

REVOKE EXECUTE ON FUNCTION public.switch_live_schedule(UUID, UUID, UUID) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.switch_live_schedule(UUID, UUID, UUID) TO service_role;

NOTIFY pgrst, 'reload schema';

COMMIT;
