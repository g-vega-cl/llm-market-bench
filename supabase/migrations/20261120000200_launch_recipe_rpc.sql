-- One atomic launch: create the recipe, apply the live state, check every cap and
-- enqueue one job, under a single row lock. Two tabs, a double click and a reload
-- after a lost response all replay the first outcome instead of creating bots.

CREATE TABLE IF NOT EXISTS public.recipe_launch_requests (
    user_id UUID NOT NULL,
    idempotency_key TEXT NOT NULL,
    recipe_id UUID REFERENCES public.strategy_recipes(id) ON DELETE CASCADE,
    job_id UUID,
    live_state TEXT NOT NULL CHECK (live_state IN ('live', 'denied', 'not-requested')),
    reason TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_launch_requests_created
    ON public.recipe_launch_requests (created_at);

ALTER TABLE public.recipe_launch_requests ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role reads launch requests" ON public.recipe_launch_requests;
CREATE POLICY "Service role reads launch requests"
    ON public.recipe_launch_requests FOR ALL TO service_role USING (true) WITH CHECK (true);

REVOKE ALL ON public.recipe_launch_requests FROM anon, authenticated;
GRANT ALL ON public.recipe_launch_requests TO service_role;

CREATE OR REPLACE FUNCTION public.launch_recipe(
    p_user_id UUID,
    p_graph JSONB,
    p_name TEXT,
    p_description TEXT,
    p_live_wanted BOOLEAN,
    p_idempotency_key TEXT
) RETURNS TABLE (recipe_id UUID, job_id UUID, live_state TEXT, reason TEXT)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    q RECORD;
    replay RECORD;
    v_recipe UUID;
    v_job UUID;
    v_live TEXT := 'not-requested';
    v_reason TEXT := 'ok';
    v_settled INT;
    v_inflight INT;
    v_global INT;
    v_live_used INT;
    v_first BOOLEAN;
BEGIN
    IF p_user_id IS NULL OR p_idempotency_key IS NULL OR btrim(p_idempotency_key) = '' THEN
        RAISE EXCEPTION 'launch_recipe: user and idempotency key are required';
    END IF;

    -- Serialise every request for the same key: the replay read below is a plain
    -- snapshot read, so without this lock two concurrent submits both miss it and
    -- both create a bot. The lock is transaction-scoped and released at COMMIT.
    PERFORM pg_advisory_xact_lock(hashtextextended(p_user_id::text || ':' || p_idempotency_key, 0));

    -- Replay before any work: a repeated submit returns exactly what the first one did.
    SELECT * INTO replay FROM recipe_launch_requests
     WHERE user_id = p_user_id AND idempotency_key = p_idempotency_key;
    -- Only a launch that actually queued a run may be replayed. A blocked outcome
    -- must be re-evaluated, or a concurrent-cap at 09:31 blocks the user until
    -- midnight even though the queue drained at 09:35.
    IF FOUND AND replay.reason = 'ok' THEN
        -- The recorded reason, not a literal: a replayed cap must still read as a cap.
        RETURN QUERY SELECT replay.recipe_id, replay.job_id, replay.live_state, replay.reason;
        RETURN;
    END IF;

    -- NULL-safe: `jsonb_typeof(NULL) <> 'array'` is NULL, which an IF would skip.
    IF p_graph IS NULL
       OR COALESCE(jsonb_typeof(p_graph -> 'stages'), '') <> 'array'
       OR COALESCE(jsonb_array_length(p_graph -> 'stages'), 0) <> 1
       OR COALESCE(jsonb_typeof(p_graph -> 'stages' -> 0 -> 'blocks'), '') <> 'array'
       OR COALESCE(jsonb_array_length(p_graph -> 'stages' -> 0 -> 'blocks'), 0) = 0
       OR (p_graph -> 'stages' -> 0 -> 'blocks' -> -1 ->> 'type') IS DISTINCT FROM 'output_format'
    THEN
        RETURN QUERY SELECT NULL::UUID, NULL::UUID, 'not-requested'::TEXT, 'invalid-graph'::TEXT;
        RETURN;
    END IF;

    -- The row is created lazily and read under lock, so two concurrent launches
    -- cannot both see "0 live" and both go live.
    INSERT INTO recipe_user_quotas (user_id) VALUES (p_user_id)
    ON CONFLICT (user_id) DO NOTHING;
    SELECT * INTO q FROM recipe_user_quotas WHERE user_id = p_user_id FOR UPDATE;

    -- Mirrors fetchRecipeQuotaStatus: a settled run burns allowance, a cancelled
    -- run only if it had started, a provider failure never does.
    -- Must match fetchRecipeQuotaStatus exactly: a run that started burns allowance
    -- whether it is still processing, completed or cancelled; a provider failure is
    -- refunded. Counting only completed/cancelled let the RPC admit a run the UI
    -- would have refused.
    SELECT count(*) INTO v_settled FROM recipe_execution_queue
     WHERE user_id = p_user_id AND mode = 'backtest'
       AND created_at > NOW() - INTERVAL '24 hours'
       AND status <> 'failed'
       AND (status = 'completed' OR started_at IS NOT NULL);
    SELECT count(*) INTO v_inflight FROM recipe_execution_queue
     WHERE user_id = p_user_id AND mode = 'backtest' AND status IN ('pending', 'processing');
    SELECT count(*) INTO v_global FROM recipe_execution_queue
     WHERE mode = 'backtest' AND status IN ('pending', 'processing');
    SELECT count(*) INTO v_live_used FROM strategy_recipes
     WHERE user_id = p_user_id AND is_live;

    INSERT INTO strategy_recipes (user_id, name, description, graph_json, cadence, is_public)
    VALUES (p_user_id, COALESCE(p_name, ''), COALESCE(p_description, ''), p_graph, '3h', FALSE)
    RETURNING id INTO v_recipe;

    IF p_live_wanted AND v_live_used < COALESCE(q.max_live_recipes, 3) THEN
        UPDATE strategy_recipes SET is_live = TRUE, updated_at = NOW() WHERE id = v_recipe;
        v_live := 'live';
    ELSIF p_live_wanted THEN
        -- Live denied, backtest still allowed: 'denied' with a queued job is the
        -- honest outcome, and the run the user asked for is not collateral.
        v_live := 'denied';
    END IF;

    IF v_reason = 'ok' THEN
        IF v_settled >= COALESCE(q.daily_backtest_limit, 2) THEN
            v_reason := 'daily-cap';
        ELSIF v_inflight >= COALESCE(q.max_concurrent_backtests, 1) THEN
            v_reason := 'concurrent-cap';
        ELSIF v_global >= 20 THEN
            v_reason := 'queue-full';
        ELSE
            SELECT NOT EXISTS (
                SELECT 1 FROM recipe_execution_queue
                 WHERE user_id = p_user_id AND mode = 'backtest' AND status = 'completed'
            ) INTO v_first;

            INSERT INTO recipe_execution_queue (recipe_id, user_id, mode, status, priority,
                provider, model, weeks_requested, progress_pct)
            VALUES (v_recipe, p_user_id, 'backtest', 'pending',
                CASE WHEN v_first THEN 0 ELSE 10 END,
                'free-llm-proxy', 'auto-go', '[]'::JSONB, 0)
            RETURNING id INTO v_job;
        END IF;
    END IF;

    -- A refused run must not leave a live bot behind: is_live was applied before
    -- the cap checks, so undo it here rather than trade an untested recipe.
    IF v_reason <> 'ok' AND v_live = 'live' THEN
        UPDATE strategy_recipes SET is_live = FALSE, updated_at = NOW() WHERE id = v_recipe;
        v_live := 'denied';
    END IF;

    -- A refused launch must not leave a recipe row behind: nothing runs, and an
    -- empty launch would otherwise be an unbounded way to grow strategy_recipes.
    IF v_reason <> 'ok' THEN
        DELETE FROM strategy_recipes WHERE id = v_recipe;
        v_recipe := NULL;
    END IF;

    INSERT INTO recipe_launch_requests (user_id, idempotency_key, recipe_id, job_id, live_state, reason)
    VALUES (p_user_id, p_idempotency_key, v_recipe, v_job, v_live, v_reason)
    ON CONFLICT (user_id, idempotency_key) DO NOTHING;

    RETURN QUERY SELECT v_recipe, v_job, v_live, v_reason;
END;
$$;

REVOKE ALL ON FUNCTION public.launch_recipe(UUID, JSONB, TEXT, TEXT, BOOLEAN, TEXT)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.launch_recipe(UUID, JSONB, TEXT, TEXT, BOOLEAN, TEXT)
    TO service_role;

NOTIFY pgrst, 'reload schema';
