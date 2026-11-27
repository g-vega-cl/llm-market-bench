-- ============================================================================
-- Migration: 20261127193000_refill_this_week.sql
-- Description: Weekly refill without client-side calendar math. The archive DB
--              has no auth.users rows (Supabase Cloud owns auth), so there is
--              no server-side user list to cron over: the app refills the
--              signed-in owner on load, idempotently, inside the current ET week.
-- Plan: .hermes/plans/2026-11-27-token-architecture.md
-- ============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.refill_this_week(
    p_owner  TEXT,
    p_amount INTEGER DEFAULT 15
) RETURNS TABLE (balance INTEGER, applied BOOLEAN)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    RETURN QUERY
    SELECT * FROM public.refill_tokens(p_owner, p_amount, public.token_week());
END;
$$;

COMMENT ON FUNCTION public.refill_this_week(TEXT, INTEGER) IS
    'Idempotent refill for the current ET week; safe to call on every authenticated load.';

REVOKE EXECUTE ON FUNCTION public.refill_this_week(TEXT, INTEGER) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.refill_this_week(TEXT, INTEGER) TO service_role;

NOTIFY pgrst, 'reload schema';

COMMIT;
