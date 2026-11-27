-- ============================================================================
-- Migration: 20261127191000_guest_mint.sql
-- Description: Guest mint path for the token ledger. A signed cookie value is
--              hashed (sha256 hex) and upserted into guest_sessions; the first
--              mint grants 5 one-time tokens. Re-mints return the same identity
--              and never top a balance back up.
-- Plan: .hermes/plans/2026-11-27-token-architecture.md
-- ============================================================================

BEGIN;

-- Hex text rather than BYTEA so PostgREST/supabase-js do not have to guess at
-- bytea serialization; the conversion happens here, once.
CREATE OR REPLACE FUNCTION public.mint_guest_tokens(
    p_token_hash TEXT,
    p_ip_hash    TEXT DEFAULT NULL
) RETURNS TABLE (guest_id UUID, balance INTEGER, created BOOLEAN)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_hash    BYTEA;
    v_ip      BYTEA;
    v_id      UUID;
    v_created BOOLEAN := FALSE;
    v_balance INTEGER;
BEGIN
    IF p_token_hash IS NULL OR p_token_hash !~ '^[0-9a-f]{64}$' THEN
        RAISE EXCEPTION 'guest token hash must be a lowercase sha256 hex digest';
    END IF;
    v_hash := decode(p_token_hash, 'hex');

    IF p_ip_hash IS NOT NULL THEN
        IF p_ip_hash !~ '^[0-9a-f]{64}$' THEN
            RAISE EXCEPTION 'ip hash must be a lowercase sha256 hex digest';
        END IF;
        v_ip := decode(p_ip_hash, 'hex');
    END IF;

    SELECT g.id INTO v_id FROM public.guest_sessions g WHERE g.token_hash = v_hash;

    IF v_id IS NULL THEN
        INSERT INTO public.guest_sessions (id, token_hash, ip_hash)
        VALUES (gen_random_uuid(), v_hash, v_ip)
        ON CONFLICT (token_hash) DO NOTHING
        RETURNING id INTO v_id;

        IF v_id IS NOT NULL THEN
            v_created := TRUE;
        ELSE
            -- Lost the insert race: adopt the row the other session created.
            SELECT g.id INTO v_id FROM public.guest_sessions g WHERE g.token_hash = v_hash;
        END IF;
    ELSE
        UPDATE public.guest_sessions
           SET last_seen_at = NOW(),
               ip_hash = COALESCE(v_ip, ip_hash)
         WHERE id = v_id;
    END IF;

    IF v_id IS NULL THEN
        RAISE EXCEPTION 'guest session could not be resolved';
    END IF;

    -- Grant once. The ON CONFLICT keeps a re-mint from topping the balance up,
    -- and repairs a session whose balance row was lost.
    INSERT INTO public.token_balances (owner_key, tier, balance, period_start)
    VALUES ('guest:' || v_id::text, 'guest', 5, public.token_week())
    ON CONFLICT (owner_key) DO NOTHING;

    SELECT b.balance INTO v_balance
      FROM public.token_balances b
     WHERE b.owner_key = 'guest:' || v_id::text;

    RETURN QUERY SELECT v_id, COALESCE(v_balance, 0), v_created;
END;
$$;

COMMENT ON FUNCTION public.mint_guest_tokens(TEXT, TEXT) IS
    'Resolves a guest identity from a hashed signed cookie and grants 5 one-time tokens exactly once.';

REVOKE EXECUTE ON FUNCTION public.mint_guest_tokens(TEXT, TEXT) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.mint_guest_tokens(TEXT, TEXT) TO service_role;

NOTIFY pgrst, 'reload schema';

COMMIT;
