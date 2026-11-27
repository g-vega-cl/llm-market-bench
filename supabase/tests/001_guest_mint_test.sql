-- Contract tests for the guest mint path.

\set ON_ERROR_STOP on
SET client_min_messages = notice;

-- 1. the first mint grants five tokens -------------------------------------------
DO $$
DECLARE
    r RECORD;
    h TEXT := repeat('ab', 32);
BEGIN
    DELETE FROM public.token_ledger;
    DELETE FROM public.token_balances;
    DELETE FROM public.guest_sessions;

    SELECT * INTO r FROM public.mint_guest_tokens(h, repeat('cd', 32));
    IF NOT r.created THEN RAISE EXCEPTION 'first mint did not report creation'; END IF;
    IF r.balance <> 5 THEN RAISE EXCEPTION 'first mint granted %', r.balance; END IF;
    IF (SELECT count(*) FROM public.guest_sessions) <> 1 THEN
        RAISE EXCEPTION 'first mint did not create exactly one session';
    END IF;
    IF (SELECT balance FROM public.token_balances WHERE owner_key = 'guest:' || r.guest_id) <> 5 THEN
        RAISE EXCEPTION 'first mint did not persist the balance';
    END IF;
    RAISE NOTICE 'PASS 1 first mint grants five tokens';
END $$;

-- 2. re-minting the same cookie is idempotent and never tops up ------------------
DO $$
DECLARE
    a RECORD;
    b RECORD;
    h TEXT := repeat('ab', 32);
BEGIN
    SELECT * INTO a FROM public.mint_guest_tokens(h, NULL);
    UPDATE public.token_balances
       SET balance = 2
     WHERE owner_key = 'guest:' || a.guest_id;

    SELECT * INTO b FROM public.mint_guest_tokens(h, NULL);
    IF b.created THEN RAISE EXCEPTION 're-mint reported creation'; END IF;
    IF b.guest_id <> a.guest_id THEN RAISE EXCEPTION 're-mint changed identity'; END IF;
    IF b.balance <> 2 THEN RAISE EXCEPTION 're-mint topped the balance to %', b.balance; END IF;
    IF (SELECT count(*) FROM public.guest_sessions) <> 1 THEN
        RAISE EXCEPTION 're-mint duplicated the session';
    END IF;
    RAISE NOTICE 'PASS 2 re-mint is idempotent';
END $$;

-- 3. a different cookie is a different guest -------------------------------------
DO $$
DECLARE
    a RECORD;
    b RECORD;
BEGIN
    SELECT * INTO a FROM public.mint_guest_tokens(repeat('ab', 32), NULL);
    SELECT * INTO b FROM public.mint_guest_tokens(repeat('ef', 32), NULL);
    IF a.guest_id = b.guest_id THEN RAISE EXCEPTION 'two cookies shared one identity'; END IF;
    IF (SELECT count(*) FROM public.guest_sessions) <> 2 THEN
        RAISE EXCEPTION 'second cookie did not create a session';
    END IF;
    RAISE NOTICE 'PASS 3 distinct cookies mint distinct guests';
END $$;

-- 4. malformed hashes are rejected, not truncated --------------------------------
DO $$
DECLARE
    v_raised BOOLEAN := FALSE;
BEGIN
    BEGIN
        PERFORM public.mint_guest_tokens('not-a-hash', NULL);
    EXCEPTION WHEN others THEN
        v_raised := TRUE;
    END;
    IF NOT v_raised THEN RAISE EXCEPTION 'short hash was accepted'; END IF;

    v_raised := FALSE;
    BEGIN
        PERFORM public.mint_guest_tokens(repeat('ab', 32), 'xy');
    EXCEPTION WHEN others THEN
        v_raised := TRUE;
    END;
    IF NOT v_raised THEN RAISE EXCEPTION 'bad ip hash was accepted'; END IF;
    RAISE NOTICE 'PASS 4 malformed hashes rejected';
END $$;

-- 5. the mint does not hand a guest more than the grant --------------------------
DO $$
DECLARE
    r RECORD;
BEGIN
    SELECT * INTO r FROM public.mint_guest_tokens(repeat('12', 32), NULL);
    BEGIN
        UPDATE public.token_balances SET balance = 6 WHERE owner_key = 'guest:' || r.guest_id;
        RAISE EXCEPTION 'guest balance above the grant was accepted';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'PASS 5 guest balance cap holds';
    END;
END $$;
