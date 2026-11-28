-- ============================================================================
-- Migration: 20261127210000_refill_all_accounts.sql
-- Description: Weekly refill as a scheduled sweep instead of a side effect of
--              page loads.
--
-- 20261127193000_refill_this_week.sql argued there was no user list to cron
-- over, because the archive DB holds no auth.users rows. That is true of the
-- auth tables, but the ledger is already the list: every account that has ever
-- loaded the app has a token_balances row. So the sweep can walk those rows.
--
-- Why a sweep at all, when the on-load refill is idempotent and correct?
--   1. The UI says "refills Monday 09:30 ET". Without a job that is a lie.
--   2. A tab left open across the week boundary never re-runs the load-time
--      refill, so it shows "0 of 15" until a hard reload.
-- The on-load call stays as the fallback for when the engine is down.
--
-- Safety: refill_tokens is already idempotent on period_start, validates the
-- amount and the period, and writes the signed ledger row that keeps
-- balance == sum(delta). This function only chooses *who*, never *how*.
-- Plan: .hermes/plans/2026-11-27-token-architecture.md
-- ============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.refill_all_accounts(
    p_amount INTEGER DEFAULT 15
) RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_week     DATE := public.token_week();
    v_refilled INTEGER := 0;
    v_owner    TEXT;
BEGIN
    IF p_amount < 1 OR p_amount > 15 THEN
        RAISE EXCEPTION 'refill amount out of range for account: %', p_amount;
    END IF;

    -- Ordered so two workers sweeping at once take row locks in the same
    -- order; they still cannot double-grant, because refill_tokens re-reads
    -- period_start under FOR UPDATE.
    FOR v_owner IN
        SELECT b.owner_key
          FROM public.token_balances b
         WHERE b.tier = 'account'
           AND b.period_start < v_week
         ORDER BY b.owner_key
    LOOP
        PERFORM public.refill_tokens(v_owner, p_amount, v_week);
        v_refilled := v_refilled + 1;
    END LOOP;

    RETURN v_refilled;
END;
$$;

COMMENT ON FUNCTION public.refill_all_accounts(INTEGER) IS
    'Weekly sweep: tops every account whose period_start is behind the current ET week up to p_amount, via refill_tokens. Guests are never touched and a repeat run returns 0.';

REVOKE EXECUTE ON FUNCTION public.refill_all_accounts(INTEGER) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.refill_all_accounts(INTEGER) TO service_role;

NOTIFY pgrst, 'reload schema';

COMMIT;
