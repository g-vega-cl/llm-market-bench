-- Atomic live-schedule switch RPC: pauses the conflicting live bot, cancels its
-- pending live_turn jobs, and enables the target bot in a single transaction.

DROP FUNCTION IF EXISTS public.switch_live_schedule(UUID, UUID, UUID);

CREATE OR REPLACE FUNCTION public.switch_live_schedule(
    p_user_id UUID,
    p_pause_recipe_id UUID,
    p_enable_recipe_id UUID
)
RETURNS TABLE (
    paused_id UUID,
    enabled_id UUID,
    is_live BOOLEAN
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_now TIMESTAMPTZ := NOW();
    v_first_id UUID := LEAST(p_pause_recipe_id, p_enable_recipe_id);
    v_second_id UUID := GREATEST(p_pause_recipe_id, p_enable_recipe_id);
    v_pause_owner UUID;
    v_enable_owner UUID;
    v_enable_archived TIMESTAMPTZ;
    v_max_live INTEGER := 3;
    v_other_live_count INTEGER := 0;
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

    SELECT r.user_id
    INTO v_pause_owner
    FROM public.strategy_recipes r
    WHERE r.id = p_pause_recipe_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Recipe not found: %', p_pause_recipe_id;
    END IF;

    IF v_pause_owner <> p_user_id THEN
        RAISE EXCEPTION 'Unauthorized: cannot modify live schedule for another user';
    END IF;

    SELECT r.user_id, r.archived_at
    INTO v_enable_owner, v_enable_archived
    FROM public.strategy_recipes r
    WHERE r.id = p_enable_recipe_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Recipe not found: %', p_enable_recipe_id;
    END IF;

    IF v_enable_owner <> p_user_id THEN
        RAISE EXCEPTION 'Unauthorized: cannot modify live schedule for another user';
    END IF;

    IF v_enable_archived IS NOT NULL THEN
        RAISE EXCEPTION 'This strategy was removed from My Strategies. Save it to restore before scheduling it live.';
    END IF;

    SELECT COALESCE(q.max_live_recipes, 3)
    INTO v_max_live
    FROM public.recipe_user_quotas q
    WHERE q.user_id = p_user_id;

    SELECT COUNT(*)
    INTO v_other_live_count
    FROM public.strategy_recipes r
    WHERE r.user_id = p_user_id
      AND r.is_live = TRUE
      AND r.id NOT IN (p_pause_recipe_id, p_enable_recipe_id);

    IF v_other_live_count >= COALESCE(v_max_live, 3) THEN
        RAISE EXCEPTION 'Scheduled live limit reached (%/%). Pause an existing live recipe first.',
            v_other_live_count + 1, COALESCE(v_max_live, 3);
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

    UPDATE public.strategy_recipes
    SET is_live = TRUE,
        updated_at = v_now
    WHERE id = p_enable_recipe_id
      AND user_id = p_user_id;

    RETURN QUERY
    SELECT p_pause_recipe_id, p_enable_recipe_id, TRUE;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.switch_live_schedule(UUID, UUID, UUID) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.switch_live_schedule(UUID, UUID, UUID) TO service_role;
