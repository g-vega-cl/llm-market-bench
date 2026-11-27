-- Contract tests for live-week funding.

\set ON_ERROR_STOP on
SET client_min_messages = notice;

-- 1. going live spends one token and writes a deadline ---------------------------
DO $$
DECLARE
    r RECORD;
    v_recipe UUID := 'c0000000-0000-4000-8000-000000000001';
    v_user UUID := 'd0000000-0000-4000-8000-000000000001';
BEGIN
    DELETE FROM public.token_ledger;
    DELETE FROM public.token_balances;
    DELETE FROM public.recipe_user_quotas;
    DELETE FROM public.recipe_execution_queue;
    DELETE FROM public.strategy_recipes;

    PERFORM public.refill_tokens('user:' || v_user, 15, public.token_week());
    INSERT INTO public.strategy_recipes (id, user_id, is_live) VALUES (v_recipe, v_user, FALSE);

    SELECT * INTO r FROM public.start_live_week(v_user, v_recipe);
    IF NOT r.is_live THEN RAISE EXCEPTION 'bot did not go live'; END IF;
    IF r.live_expires_at IS NULL THEN RAISE EXCEPTION 'no expiry written'; END IF;
    IF r.live_expires_at < NOW() + INTERVAL '6 days 23 hours'
       OR r.live_expires_at > NOW() + INTERVAL '7 days 1 hour' THEN
        RAISE EXCEPTION 'expiry is not seven calendar days out: %', r.live_expires_at;
    END IF;
    IF r.token_balance <> 14 THEN
        RAISE EXCEPTION 'live week cost % tokens instead of 1', 15 - r.token_balance;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM public.token_ledger
         WHERE kind = 'live_week' AND ref_id = v_recipe AND delta = -1
    ) THEN
        RAISE EXCEPTION 'no live_week ledger row for the recipe';
    END IF;
    RAISE NOTICE 'PASS 1 going live spends one token and sets the deadline';
END $$;

-- 2. re-enabling an already-live bot buys no second week -------------------------
DO $$
DECLARE
    r RECORD;
    v_first TIMESTAMPTZ;
    v_recipe UUID := 'c0000000-0000-4000-8000-000000000001';
    v_user UUID := 'd0000000-0000-4000-8000-000000000001';
BEGIN
    SELECT live_expires_at INTO v_first FROM public.strategy_recipes WHERE id = v_recipe;

    SELECT * INTO r FROM public.start_live_week(v_user, v_recipe);
    IF r.token_balance <> 14 THEN
        RAISE EXCEPTION 're-enable charged again: balance %', r.token_balance;
    END IF;
    IF r.live_expires_at <> v_first THEN
        RAISE EXCEPTION 're-enable moved the deadline';
    END IF;
    RAISE NOTICE 'PASS 2 re-enable is free and idempotent';
END $$;

-- 3. no tokens means no live bot, and the recipe stays paused --------------------
DO $$
DECLARE
    v_recipe UUID := 'c0000000-0000-4000-8000-000000000002';
    v_user UUID := 'd0000000-0000-4000-8000-000000000002';
    v_raised BOOLEAN := FALSE;
    v_msg TEXT;
BEGIN
    INSERT INTO public.strategy_recipes (id, user_id, is_live) VALUES (v_recipe, v_user, FALSE);

    BEGIN
        PERFORM public.start_live_week(v_user, v_recipe);
    EXCEPTION WHEN others THEN
        v_raised := TRUE;
        v_msg := SQLERRM;
    END;

    IF NOT v_raised THEN RAISE EXCEPTION 'went live with zero tokens'; END IF;
    IF v_msg NOT LIKE '%TOKEN:no_tokens%' THEN
        RAISE EXCEPTION 'unexpected refusal message: %', v_msg;
    END IF;
    IF (SELECT is_live FROM public.strategy_recipes WHERE id = v_recipe) THEN
        RAISE EXCEPTION 'a refused spend still flipped the bot live';
    END IF;
    RAISE NOTICE 'PASS 3 refuses without tokens and leaves the bot paused';
END $$;

-- 4. the live cap still applies -------------------------------------------------
DO $$
DECLARE
    v_first UUID := 'c0000000-0000-4000-8000-000000000003';
    v_second UUID := 'c0000000-0000-4000-8000-000000000004';
    v_user UUID := 'd0000000-0000-4000-8000-000000000003';
    v_raised BOOLEAN := FALSE;
BEGIN
    PERFORM public.refill_tokens('user:' || v_user, 15, public.token_week());
    INSERT INTO public.recipe_user_quotas (user_id, max_live_recipes) VALUES (v_user, 1);
    INSERT INTO public.strategy_recipes (id, user_id, is_live) VALUES
        (v_first, v_user, FALSE), (v_second, v_user, FALSE);

    PERFORM public.start_live_week(v_user, v_first);
    BEGIN
        PERFORM public.start_live_week(v_user, v_second);
    EXCEPTION WHEN others THEN
        v_raised := TRUE;
    END;
    IF NOT v_raised THEN RAISE EXCEPTION 'second live bot ignored the cap'; END IF;
    IF (SELECT balance FROM public.token_balances WHERE owner_key = 'user:' || v_user) <> 14 THEN
        RAISE EXCEPTION 'refused second bot still spent a token';
    END IF;
    RAISE NOTICE 'PASS 4 live cap holds and a refusal costs nothing';
END $$;

-- 5. switching pauses, funds and enables in one transaction ---------------------
DO $$
DECLARE
    r RECORD;
    v_old UUID := 'c0000000-0000-4000-8000-000000000005';
    v_new UUID := 'c0000000-0000-4000-8000-000000000006';
    v_user UUID := 'd0000000-0000-4000-8000-000000000004';
BEGIN
    DELETE FROM public.recipe_user_quotas WHERE user_id = v_user;
    PERFORM public.refill_tokens('user:' || v_user, 15, public.token_week());
    INSERT INTO public.strategy_recipes (id, user_id, is_live) VALUES
        (v_old, v_user, FALSE), (v_new, v_user, FALSE);
    PERFORM public.start_live_week(v_user, v_old);

    SELECT * INTO r FROM public.switch_live_schedule(v_user, v_old, v_new);
    IF r.paused_id <> v_old OR r.enabled_id <> v_new THEN
        RAISE EXCEPTION 'switch returned the wrong ids';
    END IF;
    IF NOT r.is_live THEN RAISE EXCEPTION 'switch did not enable the new bot'; END IF;
    IF (SELECT is_live FROM public.strategy_recipes WHERE id = v_old) THEN
        RAISE EXCEPTION 'switch did not pause the old bot';
    END IF;
    IF r.token_balance <> 13 THEN
        RAISE EXCEPTION 'switch did not spend exactly one token: %', r.token_balance;
    END IF;
    RAISE NOTICE 'PASS 5 switch pause + fund + enable';
END $$;

-- 6. an unfunded switch rolls the pause back ------------------------------------
DO $$
DECLARE
    v_old UUID := 'c0000000-0000-4000-8000-000000000007';
    v_new UUID := 'c0000000-0000-4000-8000-000000000008';
    v_user UUID := 'd0000000-0000-4000-8000-000000000005';
    v_raised BOOLEAN := FALSE;
BEGIN
    PERFORM public.refill_tokens('user:' || v_user, 1, public.token_week());
    INSERT INTO public.strategy_recipes (id, user_id, is_live) VALUES
        (v_old, v_user, FALSE), (v_new, v_user, FALSE);
    PERFORM public.start_live_week(v_user, v_old);

    BEGIN
        PERFORM public.switch_live_schedule(v_user, v_old, v_new);
    EXCEPTION WHEN others THEN
        v_raised := TRUE;
    END;
    IF NOT v_raised THEN RAISE EXCEPTION 'switch succeeded with zero tokens'; END IF;
    IF NOT (SELECT is_live FROM public.strategy_recipes WHERE id = v_old) THEN
        RAISE EXCEPTION 'failed switch still paused the running bot';
    END IF;
    RAISE NOTICE 'PASS 6 failed switch rolls back the pause';
END $$;
