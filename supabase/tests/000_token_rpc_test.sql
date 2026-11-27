-- Contract tests for the token ledger RPCs.
-- Every block raises on failure; the runner passes only on a clean exit.

\set ON_ERROR_STOP on
SET client_min_messages = notice;

-- 1. reserve spends exactly one -------------------------------------------------
DO $$
DECLARE v RECORD;
BEGIN
    DELETE FROM public.token_ledger;
    DELETE FROM public.token_balances;
    DELETE FROM public.guest_budget_daily;
    INSERT INTO public.token_balances (owner_key, tier, balance, period_start)
    VALUES ('user:a', 'account', 5, CURRENT_DATE);

    SELECT * INTO v FROM public.reserve_token(
        'user:a', 'backtest', '11111111-1111-1111-1111-111111111111');
    IF NOT v.ok OR v.balance <> 4 OR v.code <> 'ok' THEN
        RAISE EXCEPTION 'reserve spends one: ok=% balance=% code=%', v.ok, v.balance, v.code;
    END IF;
    RAISE NOTICE 'PASS 1 reserve spends one';
END $$;

-- 2. retried reserve with the same ref never double-spends ----------------------
DO $$
DECLARE v RECORD;
BEGIN
    SELECT * INTO v FROM public.reserve_token(
        'user:a', 'backtest', '11111111-1111-1111-1111-111111111111');
    IF NOT v.ok OR v.balance <> 4 OR v.code <> 'already_reserved' THEN
        RAISE EXCEPTION 'idempotent reserve: ok=% balance=% code=%', v.ok, v.balance, v.code;
    END IF;
    IF (SELECT count(*) FROM public.token_ledger WHERE owner_key = 'user:a') <> 1 THEN
        RAISE EXCEPTION 'idempotent reserve wrote a second ledger row';
    END IF;
    RAISE NOTICE 'PASS 2 reserve idempotent on ref_id';
END $$;

-- 3. zero balance refuses -------------------------------------------------------
DO $$
DECLARE v RECORD;
BEGIN
    UPDATE public.token_balances SET balance = 0 WHERE owner_key = 'user:a';
    SELECT * INTO v FROM public.reserve_token(
        'user:a', 'backtest', '22222222-2222-2222-2222-222222222222');
    IF v.ok OR v.code <> 'no_tokens' THEN
        RAISE EXCEPTION 'empty balance: ok=% code=%', v.ok, v.code;
    END IF;
    RAISE NOTICE 'PASS 3 empty balance refuses';
END $$;

-- 4. guest daily budget refuses the 21st backtest -------------------------------
DO $$
DECLARE
    i INTEGER;
    g TEXT;
    v RECORD;
BEGIN
    DELETE FROM public.token_ledger;
    DELETE FROM public.token_balances;
    DELETE FROM public.guest_budget_daily;

    -- Four guests x five tokens each = the whole 20/day budget.
    FOREACH g IN ARRAY ARRAY['guest:g1', 'guest:g2', 'guest:g3', 'guest:g4', 'guest:g5'] LOOP
        INSERT INTO public.token_balances (owner_key, tier, balance, period_start)
        VALUES (g, 'guest', 5, public.token_week());
    END LOOP;

    FOR i IN 1..20 LOOP
        g := 'guest:g' || (((i - 1) / 5) + 1)::text;
        SELECT * INTO v FROM public.reserve_token(g, 'backtest', gen_random_uuid());
        IF NOT v.ok THEN
            RAISE EXCEPTION 'guest reserve % refused with %', i, v.code;
        END IF;
    END LOOP;

    -- g5 still holds tokens, but the platform's day is spent.
    SELECT * INTO v FROM public.reserve_token('guest:g5', 'backtest', gen_random_uuid());
    IF v.ok OR v.code <> 'guest_budget' THEN
        RAISE EXCEPTION 'guest budget not enforced: ok=% code=%', v.ok, v.code;
    END IF;
    IF (SELECT balance FROM public.token_balances WHERE owner_key = 'guest:g5')
       IS DISTINCT FROM 5 THEN
        RAISE EXCEPTION 'refused spend still debited the guest';
    END IF;
    RAISE NOTICE 'PASS 4 guest daily budget';
END $$;

-- 5. a failed backtest refunds exactly once -------------------------------------
DO $$
DECLARE
    v RECORD;
    r RECORD;
BEGIN
    DELETE FROM public.token_ledger;
    DELETE FROM public.token_balances;
    INSERT INTO public.token_balances (owner_key, tier, balance, period_start)
    VALUES ('user:b', 'account', 3, CURRENT_DATE);

    SELECT * INTO v FROM public.reserve_token(
        'user:b', 'backtest', '33333333-3333-3333-3333-333333333333');
    IF v.balance <> 2 THEN RAISE EXCEPTION 'seed spend wrong: %', v.balance; END IF;

    SELECT * INTO r FROM public.settle_token('33333333-3333-3333-3333-333333333333', 'failed');
    IF NOT r.refunded THEN RAISE EXCEPTION 'failed backtest did not refund'; END IF;
    IF (SELECT balance FROM public.token_balances WHERE owner_key = 'user:b') <> 3 THEN
        RAISE EXCEPTION 'refund did not restore the balance';
    END IF;

    SELECT * INTO r FROM public.settle_token('33333333-3333-3333-3333-333333333333', 'failed');
    IF r.refunded THEN RAISE EXCEPTION 'second settle refunded again'; END IF;
    RAISE NOTICE 'PASS 5 failed backtest refunds once';
END $$;

-- 6. a paused live week is not refundable ---------------------------------------
DO $$
DECLARE
    v RECORD;
    r RECORD;
BEGIN
    SELECT * INTO v FROM public.reserve_token(
        'user:b', 'live_week', '44444444-4444-4444-4444-444444444444');
    IF NOT v.ok OR v.balance <> 2 THEN
        RAISE EXCEPTION 'live reserve: ok=% balance=%', v.ok, v.balance;
    END IF;

    SELECT * INTO r FROM public.settle_token('44444444-4444-4444-4444-444444444444', 'paused');
    IF r.refunded THEN RAISE EXCEPTION 'paused live week refunded'; END IF;
    IF (SELECT balance FROM public.token_balances WHERE owner_key = 'user:b') <> 2 THEN
        RAISE EXCEPTION 'paused live week moved the balance';
    END IF;
    RAISE NOTICE 'PASS 6 paused live week not refundable';
END $$;

-- 7. refill is idempotent inside a period and applies once on the next ----------
DO $$
DECLARE
    r RECORD;
    v_week DATE := public.token_week();
BEGIN
    DELETE FROM public.token_ledger WHERE owner_key = 'user:c';
    DELETE FROM public.token_balances WHERE owner_key = 'user:c';

    SELECT * INTO r FROM public.refill_tokens('user:c', 15, v_week);
    IF NOT r.applied OR r.balance <> 15 THEN
        RAISE EXCEPTION 'first refill: applied=% balance=%', r.applied, r.balance;
    END IF;

    SELECT * INTO r FROM public.refill_tokens('user:c', 15, v_week);
    IF r.applied OR r.balance <> 15 THEN
        RAISE EXCEPTION 'same-week refill applied twice: applied=%', r.applied;
    END IF;

    -- A later week is simulated by ageing the stored period, because accepting
    -- a future p_period is itself the defect (see test 12).
    UPDATE public.token_balances SET period_start = v_week - 7 WHERE owner_key = 'user:c';
    SELECT * INTO r FROM public.refill_tokens('user:c', 15, v_week);
    IF NOT r.applied OR r.balance <> 15 THEN
        RAISE EXCEPTION 'new-week refill: applied=% balance=%', r.applied, r.balance;
    END IF;

    -- The ledger must reconstruct the balance, or it cannot detect a leak.
    IF (SELECT COALESCE(sum(delta), 0) FROM public.token_ledger WHERE owner_key = 'user:c')
       IS DISTINCT FROM (SELECT balance FROM public.token_balances WHERE owner_key = 'user:c') THEN
        RAISE EXCEPTION 'ledger does not reconcile to balance for user:c';
    END IF;
    RAISE NOTICE 'PASS 7 refill idempotency + ledger reconciliation';
END $$;

-- 8. expiry sweep pauses lapsed bots, and only when no turn is really in flight
DO $$
DECLARE
    n INTEGER;
BEGIN
    DELETE FROM public.recipe_execution_queue;
    DELETE FROM public.strategy_recipes;
    INSERT INTO public.strategy_recipes (id, is_live, live_expires_at) VALUES
        ('aaaaaaaa-0000-0000-0000-000000000001', TRUE, NOW() - INTERVAL '1 hour'),
        ('aaaaaaaa-0000-0000-0000-000000000002', TRUE, NOW() + INTERVAL '1 day'),
        ('aaaaaaaa-0000-0000-0000-000000000003', TRUE, NOW() - INTERVAL '1 hour'),
        ('aaaaaaaa-0000-0000-0000-000000000004', TRUE, NOW() - INTERVAL '1 hour');
    -- 3: a live turn is really running (fresh heartbeat) → must survive.
    -- 4: a worker died mid-turn (stale heartbeat) → must not immunise the bot.
    INSERT INTO public.recipe_execution_queue (recipe_id, status, heartbeat_at) VALUES
        ('aaaaaaaa-0000-0000-0000-000000000003', 'processing', NOW()),
        ('aaaaaaaa-0000-0000-0000-000000000004', 'processing', NOW() - INTERVAL '2 hours');

    n := public.expire_live_bots();
    IF n <> 2 THEN RAISE EXCEPTION 'sweep paused % bots, expected 2', n; END IF;
    IF (SELECT is_live FROM public.strategy_recipes WHERE id = 'aaaaaaaa-0000-0000-0000-000000000001') THEN
        RAISE EXCEPTION 'expired bot still live';
    END IF;
    IF NOT (SELECT is_live FROM public.strategy_recipes WHERE id = 'aaaaaaaa-0000-0000-0000-000000000002') THEN
        RAISE EXCEPTION 'fresh bot was paused';
    END IF;
    IF NOT (SELECT is_live FROM public.strategy_recipes WHERE id = 'aaaaaaaa-0000-0000-0000-000000000003') THEN
        RAISE EXCEPTION 'bot with a live turn in flight was paused';
    END IF;
    IF (SELECT is_live FROM public.strategy_recipes WHERE id = 'aaaaaaaa-0000-0000-0000-000000000004') THEN
        RAISE EXCEPTION 'stale processing row immunised the bot against expiry';
    END IF;
    IF public.expire_live_bots() <> 0 THEN
        RAISE EXCEPTION 'sweep is not idempotent';
    END IF;
    RAISE NOTICE 'PASS 8 expiry sweep + heartbeat staleness';
END $$;

-- 9. a live row cannot exist without an expiry -----------------------------------
DO $$
BEGIN
    BEGIN
        INSERT INTO public.strategy_recipes (id, is_live) VALUES (gen_random_uuid(), TRUE);
        RAISE EXCEPTION 'live row without expiry was accepted';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'PASS 9 live rows require an expiry';
    END;
END $$;

-- 10. balance can never go negative ---------------------------------------------
DO $$
BEGIN
    BEGIN
        UPDATE public.token_balances SET balance = -1 WHERE owner_key = 'user:c';
        RAISE EXCEPTION 'negative balance was accepted';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'PASS 10 balance floor';
    END;
END $$;

-- 11. a refunded ref is terminal — no free re-run --------------------------------
DO $$
DECLARE
    v RECORD;
    r RECORD;
    v_ref UUID := '77777777-7777-7777-7777-777777777777';
BEGIN
    DELETE FROM public.token_ledger;
    DELETE FROM public.token_balances;
    INSERT INTO public.token_balances (owner_key, tier, balance, period_start)
    VALUES ('user:d', 'account', 3, public.token_week());

    SELECT * INTO v FROM public.reserve_token('user:d', 'backtest', v_ref);
    IF v.balance <> 2 THEN RAISE EXCEPTION 'seed spend wrong: %', v.balance; END IF;

    SELECT * INTO r FROM public.settle_token(v_ref, 'failed');
    IF NOT r.refunded THEN RAISE EXCEPTION 'refund failed'; END IF;

    SELECT * INTO v FROM public.reserve_token('user:d', 'backtest', v_ref);
    IF v.ok OR v.code <> 'refunded' THEN
        RAISE EXCEPTION 'refunded ref was re-spent for free: ok=% code=%', v.ok, v.code;
    END IF;
    IF (SELECT balance FROM public.token_balances WHERE owner_key = 'user:d') <> 3 THEN
        RAISE EXCEPTION 'terminal-ref retry moved the balance';
    END IF;
    RAISE NOTICE 'PASS 11 refunded ref cannot be re-reserved';
END $$;

-- 12. refill rejects a far-future period instead of freezing the owner -----------
DO $$
DECLARE
    v_raised BOOLEAN := FALSE;
BEGIN
    BEGIN
        PERFORM public.refill_tokens('user:e', 15, public.token_week() + 28);
    EXCEPTION WHEN others THEN
        v_raised := TRUE;
    END;
    IF NOT v_raised THEN
        RAISE EXCEPTION 'far-future refill period was accepted';
    END IF;

    v_raised := FALSE;
    BEGIN
        PERFORM public.refill_tokens('user:e', 15, public.token_week() + 7);
    EXCEPTION WHEN others THEN
        v_raised := TRUE;
    END;
    IF NOT v_raised THEN
        RAISE EXCEPTION 'next-Monday refill period was accepted';
    END IF;

    v_raised := FALSE;
    BEGIN
        PERFORM public.refill_tokens('user:e', 15, public.token_week() + 3);
    EXCEPTION WHEN others THEN
        v_raised := TRUE;
    END;
    IF NOT v_raised THEN
        RAISE EXCEPTION 'non-Monday refill period was accepted';
    END IF;

    v_raised := FALSE;
    BEGIN
        PERFORM public.refill_tokens('user:e', 0, public.token_week());
    EXCEPTION WHEN others THEN
        v_raised := TRUE;
    END;
    IF NOT v_raised THEN
        RAISE EXCEPTION 'zero refill amount was accepted';
    END IF;
    RAISE NOTICE 'PASS 12 refill period validation';
END $$;

-- 13. a weekly job cannot refill a guest -----------------------------------------
DO $$
DECLARE
    r RECORD;
BEGIN
    DELETE FROM public.token_balances WHERE owner_key = 'guest:r';
    INSERT INTO public.token_balances (owner_key, tier, balance, period_start)
    VALUES ('guest:r', 'guest', 5, public.token_week());

    SELECT * INTO r FROM public.refill_tokens('guest:r', 15, public.token_week());
    IF r.applied OR r.balance <> 5 THEN
        RAISE EXCEPTION 'guest was refilled: applied=% balance=%', r.applied, r.balance;
    END IF;
    RAISE NOTICE 'PASS 13 guests are never refilled';
END $$;

-- 14. a refund for a missing balance row still credits ---------------------------
DO $$
DECLARE
    v RECORD;
    r RECORD;
    v_ref UUID := '88888888-8888-8888-8888-888888888888';
BEGIN
    DELETE FROM public.token_ledger;
    DELETE FROM public.token_balances;

    -- Seed through the ledger, because a balance with no matching refill row is
    -- corrupt data and the refund path deliberately refuses to reconcile it.
    PERFORM public.refill_tokens('user:m', 2, public.token_week());

    SELECT * INTO v FROM public.reserve_token('user:m', 'backtest', v_ref);
    IF v.balance <> 1 THEN RAISE EXCEPTION 'seed spend wrong: %', v.balance; END IF;

    DELETE FROM public.token_balances WHERE owner_key = 'user:m';

    SELECT * INTO r FROM public.settle_token(v_ref, 'failed');
    IF NOT r.refunded THEN RAISE EXCEPTION 'refund with missing row was dropped'; END IF;
    IF (SELECT balance FROM public.token_balances WHERE owner_key = 'user:m')
       IS DISTINCT FROM 2 THEN
        RAISE EXCEPTION 'refund did not recreate the balance from the ledger';
    END IF;
    RAISE NOTICE 'PASS 14 missing balance row is materialised on refund';
END $$;

-- 15. a failed guest run returns its daily budget slot ---------------------------
DO $$
DECLARE
    v RECORD;
    r RECORD;
    v_ref UUID := '99999999-9999-9999-9999-999999999999';
BEGIN
    DELETE FROM public.token_ledger;
    DELETE FROM public.token_balances;
    DELETE FROM public.guest_budget_daily;
    INSERT INTO public.token_balances (owner_key, tier, balance, period_start)
    VALUES ('guest:b', 'guest', 5, public.token_week());

    SELECT * INTO v FROM public.reserve_token('guest:b', 'backtest', v_ref);
    IF NOT v.ok OR v.balance <> 4 THEN
        RAISE EXCEPTION 'guest reserve: ok=% balance=%', v.ok, v.balance;
    END IF;
    IF (SELECT backtests FROM public.guest_budget_daily WHERE day = public.token_day()) <> 1 THEN
        RAISE EXCEPTION 'budget did not record the guest spend';
    END IF;

    SELECT * INTO r FROM public.settle_token(v_ref, 'failed');
    IF NOT r.refunded THEN RAISE EXCEPTION 'guest refund failed'; END IF;
    IF (SELECT backtests FROM public.guest_budget_daily WHERE day = public.token_day()) <> 0 THEN
        RAISE EXCEPTION 'failed guest run kept its budget slot';
    END IF;
    IF (SELECT balance FROM public.token_balances WHERE owner_key = 'guest:b') <> 5 THEN
        RAISE EXCEPTION 'guest token was not returned';
    END IF;
    RAISE NOTICE 'PASS 15 failed guest run returns token and budget';
END $$;

-- 16. the ledger rejects a nonsensical delta -------------------------------------
DO $$
BEGIN
    BEGIN
        INSERT INTO public.token_ledger (owner_key, kind, delta, ref_id)
        VALUES ('user:x', 'backtest', 5, gen_random_uuid());
        RAISE EXCEPTION 'positive backtest delta was accepted';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'PASS 16 ledger delta contract';
    END;
END $$;
