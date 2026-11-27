-- ============================================================================
-- Migration: 20261127190000_token_architecture.sql
-- Description: Token ledger — one token buys one backtest or one live-bot
--              week. Guest balances (one-time 5, cookie-keyed, capped by a
--              global daily budget) and account balances (15/week, Monday
--              09:30 ET, no rollover). Adds live_expires_at so a live bot
--              can lapse without an owner present.
-- Plan: .hermes/plans/2026-11-27-token-architecture.md
-- ============================================================================

BEGIN;

-- 1. Balances -----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.token_balances (
    owner_key    TEXT PRIMARY KEY CHECK (owner_key ~ '^(user|guest):[A-Za-z0-9-]{1,64}$'),
    tier         TEXT NOT NULL CHECK (tier IN ('guest', 'account')),
    balance      INTEGER NOT NULL DEFAULT 0 CHECK (balance >= 0),
    period_start DATE NOT NULL,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- tier is derived state: make the mismatched pairing unrepresentable.
    CONSTRAINT token_balances_tier_matches_key
        CHECK ((owner_key LIKE 'guest:%') = (tier = 'guest')),
    -- a guest grant is one-time and never grows.
    CONSTRAINT token_balances_guest_cap CHECK (tier <> 'guest' OR balance <= 5)
);

COMMENT ON TABLE public.token_balances IS
    'Current token balance per owner. owner_key = user:<uuid> | guest:<uuid>. period_start is the Monday of the refill week (ET).';

-- 2. Append-only ledger -------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.token_ledger (
    id         BIGSERIAL PRIMARY KEY,
    owner_key  TEXT NOT NULL,
    kind       TEXT NOT NULL CHECK (kind IN ('backtest', 'live_week', 'refund', 'refill')),
    delta      INTEGER NOT NULL,
    ref_id     UUID,
    reason     TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- signs are part of the contract: a spend only ever costs one token.
    -- refill is a signed adjustment so balance always equals sum(delta).
    CONSTRAINT token_ledger_delta_matches_kind CHECK (
        (kind IN ('backtest', 'live_week') AND delta = -1)
        OR (kind = 'refund' AND delta = 1)
        OR (kind = 'refill')
    )
);

COMMENT ON TABLE public.token_ledger IS
    'Append-only token movements. (owner_key, kind, ref_id) is unique so a retried reserve or settle is a no-op.';

CREATE UNIQUE INDEX IF NOT EXISTS idx_token_ledger_idempotent
    ON public.token_ledger (owner_key, kind, ref_id)
    WHERE ref_id IS NOT NULL;

-- settle_token looks up by (kind, ref_id) with no owner key; the index above
-- leads on owner_key and cannot serve it.
CREATE INDEX IF NOT EXISTS idx_token_ledger_kind_ref ON public.token_ledger (kind, ref_id);

-- A ref belongs to exactly one owner. Without this two owners could each hold a
-- spend for the same ref and a refund would credit whichever row sorted first.
CREATE UNIQUE INDEX IF NOT EXISTS idx_token_ledger_ref_unique
    ON public.token_ledger (kind, ref_id)
    WHERE ref_id IS NOT NULL AND kind IN ('backtest', 'live_week', 'refund');

CREATE INDEX IF NOT EXISTS idx_token_ledger_owner_created
    ON public.token_ledger (owner_key, created_at DESC);

-- 3. Guest sessions -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.guest_sessions (
    id           UUID PRIMARY KEY,
    token_hash   BYTEA NOT NULL UNIQUE,
    ip_hash      BYTEA,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.guest_sessions IS
    'Logged-out identities. token_hash is a hash of the signed cookie value; ip_hash is a hash of CF-Connecting-IP, never the raw address.';

CREATE INDEX IF NOT EXISTS idx_guest_sessions_ip ON public.guest_sessions (ip_hash);

-- 4. Global guest budget ------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.guest_budget_daily (
    day        DATE PRIMARY KEY,
    backtests  INTEGER NOT NULL DEFAULT 0 CHECK (backtests >= 0),
    live_weeks INTEGER NOT NULL DEFAULT 0 CHECK (live_weeks >= 0)
);

COMMENT ON TABLE public.guest_budget_daily IS
    'Global daily ceiling on guest spend. Per-identity caps cannot bound a rotating IP; this can.';

-- 5. Feedback inbox -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.feedback_requests (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_key  TEXT NOT NULL,
    body       TEXT NOT NULL CHECK (length(body) BETWEEN 1 AND 4000),
    ip_hash    BYTEA,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.feedback_requests IS
    'Tokens-exhausted feedback inbox. Tokens are never granted from here; it exists to read intent.';

CREATE INDEX IF NOT EXISTS idx_feedback_requests_created
    ON public.feedback_requests (created_at DESC);

-- 6. Live expiry --------------------------------------------------------------
ALTER TABLE public.strategy_recipes
    ADD COLUMN IF NOT EXISTS live_expires_at TIMESTAMPTZ;

COMMENT ON COLUMN public.strategy_recipes.live_expires_at IS
    'Deadline of the token-funded live week. Set when the bot goes live; kept after expiry as the pause evidence.';

-- Backfill BEFORE the constraint, or the two live bots abort the migration.
UPDATE public.strategy_recipes
   SET live_expires_at = NOW() + INTERVAL '7 days'
 WHERE is_live = TRUE
   AND live_expires_at IS NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.strategy_recipes'::regclass
          AND conname = 'strategy_recipes_live_expiry_required'
    ) THEN
        ALTER TABLE public.strategy_recipes
            ADD CONSTRAINT strategy_recipes_live_expiry_required
            CHECK (is_live = FALSE OR live_expires_at IS NOT NULL);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_strategy_recipes_live_expiry
    ON public.strategy_recipes (live_expires_at)
    WHERE is_live = TRUE AND archived_at IS NULL;

-- The sweep's NOT EXISTS probes this pair; without it every sweep scans the queue.
CREATE INDEX IF NOT EXISTS idx_recipe_queue_recipe_status
    ON public.recipe_execution_queue (recipe_id, status);

-- 7. RLS: service-role only ---------------------------------------------------
-- Written explicitly per table: apps/engine/tests/test_migration_grants.py
-- greps for literal statements, so a dynamic DO-loop would pass the database
-- and fail the guard.
ALTER TABLE public.token_balances ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS service_role_all_token_balances ON public.token_balances;
CREATE POLICY service_role_all_token_balances ON public.token_balances
    FOR ALL TO service_role USING (true) WITH CHECK (true);
REVOKE ALL ON public.token_balances FROM PUBLIC, anon, authenticated;
GRANT ALL ON public.token_balances TO service_role;

ALTER TABLE public.token_ledger ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS service_role_all_token_ledger ON public.token_ledger;
CREATE POLICY service_role_all_token_ledger ON public.token_ledger
    FOR ALL TO service_role USING (true) WITH CHECK (true);
REVOKE ALL ON public.token_ledger FROM PUBLIC, anon, authenticated;
GRANT ALL ON public.token_ledger TO service_role;

ALTER TABLE public.guest_sessions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS service_role_all_guest_sessions ON public.guest_sessions;
CREATE POLICY service_role_all_guest_sessions ON public.guest_sessions
    FOR ALL TO service_role USING (true) WITH CHECK (true);
REVOKE ALL ON public.guest_sessions FROM PUBLIC, anon, authenticated;
GRANT ALL ON public.guest_sessions TO service_role;

ALTER TABLE public.guest_budget_daily ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS service_role_all_guest_budget_daily ON public.guest_budget_daily;
CREATE POLICY service_role_all_guest_budget_daily ON public.guest_budget_daily
    FOR ALL TO service_role USING (true) WITH CHECK (true);
REVOKE ALL ON public.guest_budget_daily FROM PUBLIC, anon, authenticated;
GRANT ALL ON public.guest_budget_daily TO service_role;

ALTER TABLE public.feedback_requests ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS service_role_all_feedback_requests ON public.feedback_requests;
CREATE POLICY service_role_all_feedback_requests ON public.feedback_requests
    FOR ALL TO service_role USING (true) WITH CHECK (true);
REVOKE ALL ON public.feedback_requests FROM PUBLIC, anon, authenticated;
GRANT ALL ON public.feedback_requests TO service_role;

GRANT USAGE, SELECT ON SEQUENCE public.token_ledger_id_seq TO service_role;

-- 7b. Business clock ---------------------------------------------------------
-- One calendar for the ledger: budget days and refill weeks are ET, matching
-- the market session, not UTC. Guests were previously resetting at 20:00 ET.
CREATE OR REPLACE FUNCTION public.token_day() RETURNS DATE
LANGUAGE sql STABLE
AS $$ SELECT (NOW() AT TIME ZONE 'America/New_York')::date $$;

CREATE OR REPLACE FUNCTION public.token_week() RETURNS DATE
LANGUAGE sql STABLE
AS $$ SELECT date_trunc('week', NOW() AT TIME ZONE 'America/New_York')::date $$;

COMMENT ON FUNCTION public.token_day() IS 'Business day (America/New_York) used for the guest daily budget.';
COMMENT ON FUNCTION public.token_week() IS 'Monday anchor (America/New_York) used for the weekly refill period.';

REVOKE EXECUTE ON FUNCTION public.token_day() FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.token_week() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.token_day() TO service_role;
GRANT EXECUTE ON FUNCTION public.token_week() TO service_role;

-- 8. reserve_token ------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.reserve_token(
    p_owner TEXT,
    p_kind  TEXT,
    p_ref   UUID
) RETURNS TABLE (ok BOOLEAN, balance INTEGER, code TEXT)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_balance  INTEGER;
    v_tier     TEXT;
    v_day      DATE := public.token_day();
    v_prior    INTEGER;
    v_refunded INTEGER;
    v_updated  INTEGER;
BEGIN
    IF p_kind NOT IN ('backtest', 'live_week') THEN
        RETURN QUERY SELECT FALSE, 0, 'bad_kind';
        RETURN;
    END IF;

    -- Lock first so two concurrent spends cannot both read the same balance.
    SELECT b.balance, b.tier INTO v_balance, v_tier
      FROM public.token_balances b
     WHERE b.owner_key = p_owner
       FOR UPDATE;

    -- A refunded ref is terminal: re-running it would be a free execution.
    SELECT count(*) FILTER (WHERE l.kind = p_kind),
           count(*) FILTER (WHERE l.kind = 'refund')
      INTO v_prior, v_refunded
      FROM public.token_ledger l
     WHERE l.owner_key = p_owner
       AND l.ref_id = p_ref;

    IF v_refunded > 0 THEN
        RETURN QUERY SELECT FALSE, COALESCE(v_balance, 0), 'refunded';
        RETURN;
    END IF;

    -- Retry of a spend that already landed: report it, never charge again.
    IF v_prior > 0 THEN
        RETURN QUERY SELECT TRUE, COALESCE(v_balance, 0), 'already_reserved';
        RETURN;
    END IF;

    IF v_balance IS NULL OR v_balance < 1 THEN
        RETURN QUERY SELECT FALSE, COALESCE(v_balance, 0), 'no_tokens';
        RETURN;
    END IF;

    IF v_tier = 'guest' THEN
        INSERT INTO public.guest_budget_daily (day) VALUES (v_day)
        ON CONFLICT (day) DO NOTHING;

        IF p_kind = 'backtest' THEN
            UPDATE public.guest_budget_daily
               SET backtests = backtests + 1
             WHERE day = v_day AND backtests < 20;
        ELSE
            UPDATE public.guest_budget_daily
               SET live_weeks = live_weeks + 1
             WHERE day = v_day AND live_weeks < 2;
        END IF;

        GET DIAGNOSTICS v_updated = ROW_COUNT;
        IF v_updated = 0 THEN
            RETURN QUERY SELECT FALSE, v_balance, 'guest_budget';
            RETURN;
        END IF;
    END IF;

    UPDATE public.token_balances
       SET balance = public.token_balances.balance - 1, updated_at = NOW()
     WHERE owner_key = p_owner;

    INSERT INTO public.token_ledger (owner_key, kind, delta, ref_id)
    VALUES (p_owner, p_kind, -1, p_ref);

    RETURN QUERY SELECT TRUE, v_balance - 1, 'ok';
END;
$$;

COMMENT ON FUNCTION public.reserve_token(TEXT, TEXT, UUID) IS
    'Atomically spends one token for a backtest or live week. Idempotent on (owner, kind, ref_id); guest spends also consume the global daily budget.';

-- 9. settle_token -------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.settle_token(
    p_ref     UUID,
    p_outcome TEXT
) RETURNS TABLE (refunded BOOLEAN)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_owner    TEXT;
    v_ledger   BIGINT;
    v_spent_at TIMESTAMPTZ;
    v_recon    INTEGER;
BEGIN
    -- Only a failed or expired backtest comes back. A paused live week is spent.
    IF p_outcome NOT IN ('failed', 'expired') THEN
        RETURN QUERY SELECT FALSE;
        RETURN;
    END IF;

    SELECT l.owner_key, l.created_at INTO v_owner, v_spent_at
      FROM public.token_ledger l
     WHERE l.kind = 'backtest'
       AND l.ref_id = p_ref
     ORDER BY l.id
     LIMIT 1;

    IF v_owner IS NULL THEN
        RETURN QUERY SELECT FALSE;
        RETURN;
    END IF;

    -- Materialise the row when it is missing (account created between crons),
    -- then lock it. The recreated balance is the ledger's own sum, not zero:
    -- starting from zero would credit a token against a negative history and
    -- leave the row permanently unreconciled.
    PERFORM 1 FROM public.token_balances b WHERE b.owner_key = v_owner FOR UPDATE;
    IF NOT FOUND THEN
        SELECT COALESCE(sum(l.delta), 0) INTO v_recon
          FROM public.token_ledger l
         WHERE l.owner_key = v_owner;

        IF v_recon < 0 THEN
            RAISE EXCEPTION 'refund would reconcile a negative balance for %', v_owner;
        END IF;

        INSERT INTO public.token_balances (owner_key, tier, balance, period_start)
        VALUES (
            v_owner,
            CASE WHEN v_owner LIKE 'guest:%' THEN 'guest' ELSE 'account' END,
            v_recon,
            -- Epoch Monday: any real weekly refill still satisfies
            -- period_start < EXCLUDED.period_start and therefore applies.
            DATE '1970-01-05'
        )
        ON CONFLICT (owner_key) DO NOTHING;
        PERFORM 1 FROM public.token_balances b WHERE b.owner_key = v_owner FOR UPDATE;
    END IF;

    INSERT INTO public.token_ledger (owner_key, kind, delta, ref_id, reason)
    VALUES (v_owner, 'refund', 1, p_ref, p_outcome)
    ON CONFLICT (owner_key, kind, ref_id) WHERE ref_id IS NOT NULL DO NOTHING
    RETURNING public.token_ledger.id INTO v_ledger;

    IF v_ledger IS NULL THEN
        RETURN QUERY SELECT FALSE;
        RETURN;
    END IF;

    UPDATE public.token_balances
       SET balance = public.token_balances.balance + 1, updated_at = NOW()
     WHERE owner_key = v_owner;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'refund credited no balance row for %', v_owner;
    END IF;

    -- A guest whose run failed should not lose the day's budget slot too.
    IF v_owner LIKE 'guest:%' THEN
        UPDATE public.guest_budget_daily
           SET backtests = GREATEST(backtests - 1, 0)
         WHERE day = (v_spent_at AT TIME ZONE 'America/New_York')::date
           AND backtests > 0;
    END IF;

    RETURN QUERY SELECT TRUE;
END;
$$;

COMMENT ON FUNCTION public.settle_token(UUID, TEXT) IS
    'Refunds one token for a failed/expired backtest, at most once per run. Live weeks are never refunded.';

-- 10. refill_tokens -----------------------------------------------------------
-- Signature changed from the first draft (p_tier dropped): tier is derived from
-- the owner key so a caller cannot refill a guest as an account.
DROP FUNCTION IF EXISTS public.refill_tokens(TEXT, INTEGER, DATE, TEXT);

CREATE OR REPLACE FUNCTION public.refill_tokens(
    p_owner  TEXT,
    p_amount INTEGER,
    p_period DATE
) RETURNS TABLE (balance INTEGER, applied BOOLEAN)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_tier    TEXT;
    v_applied INTEGER;
    v_balance INTEGER;
    v_old     INTEGER;
    v_ledger  BIGINT;
    v_current DATE := public.token_week();
BEGIN
    v_tier := CASE WHEN p_owner LIKE 'guest:%' THEN 'guest' ELSE 'account' END;

    IF v_tier = 'account' AND (p_amount < 1 OR p_amount > 15) THEN
        RAISE EXCEPTION 'refill amount out of range for %: %', v_tier, p_amount;
    END IF;

    -- Guests are granted once at mint; a weekly job must never refill them.
    IF v_tier = 'guest' THEN
        SELECT b.balance INTO v_balance
          FROM public.token_balances b WHERE b.owner_key = p_owner;
        RETURN QUERY SELECT COALESCE(v_balance, 0), FALSE;
        RETURN;
    END IF;

    -- Only the current week is a legal period. Accepting the next Monday let a
    -- single early call advance period_start past the real cron's predicate and
    -- freeze the owner for that week.
    IF p_period <> v_current THEN
        RAISE EXCEPTION 'refill period % is not the current week (%)', p_period, v_current;
    END IF;

    v_old := NULL;
    SELECT b.balance INTO v_old
      FROM public.token_balances b
     WHERE b.owner_key = p_owner
       FOR UPDATE;
    IF NOT FOUND THEN
        v_old := 0;
    END IF;

    -- Sets, never adds: a missed cron week cannot stack into a windfall.
    INSERT INTO public.token_balances (owner_key, tier, balance, period_start)
    VALUES (p_owner, v_tier, p_amount, p_period)
    ON CONFLICT (owner_key) DO UPDATE
        SET balance = EXCLUDED.balance,
            period_start = EXCLUDED.period_start,
            updated_at = NOW()
      WHERE public.token_balances.period_start < EXCLUDED.period_start
        AND public.token_balances.tier = 'account';

    GET DIAGNOSTICS v_applied = ROW_COUNT;

    -- Ledger stays reconcilable: balance must equal sum(delta), so the refill
    -- row records the adjustment the balance actually moved by.
    IF v_applied > 0 THEN
        INSERT INTO public.token_ledger (owner_key, kind, delta, ref_id, reason)
        VALUES (p_owner, 'refill', p_amount - v_old, NULL, p_period::text)
        RETURNING public.token_ledger.id INTO v_ledger;
    END IF;

    SELECT b.balance INTO v_balance FROM public.token_balances b WHERE b.owner_key = p_owner;

    RETURN QUERY SELECT COALESCE(v_balance, 0), v_applied > 0;
END;
$$;

COMMENT ON FUNCTION public.refill_tokens(TEXT, INTEGER, DATE) IS
    'Idempotent weekly refill for accounts, keyed on period_start and always ledgered. Guests are never refilled.';

-- 11. expire_live_bots --------------------------------------------------------
CREATE OR REPLACE FUNCTION public.expire_live_bots()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_count INTEGER;
BEGIN
    UPDATE public.strategy_recipes r
       SET is_live = FALSE,
           updated_at = NOW()
     WHERE r.is_live = TRUE
       AND r.live_expires_at IS NOT NULL
       AND r.live_expires_at <= NOW()
       AND r.archived_at IS NULL
       AND NOT EXISTS (
           SELECT 1 FROM public.recipe_execution_queue q
            WHERE q.recipe_id = r.id
              AND q.status = 'processing'
              -- A freshly claimed row may not have beaten yet; its created_at is
              -- the claim time, so NULL never reads as "dead".
              AND COALESCE(q.heartbeat_at, q.created_at) > NOW() - INTERVAL '30 minutes'
       );

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$;

COMMENT ON FUNCTION public.expire_live_bots() IS
    'Pauses live bots whose token week lapsed, skipping any bot with a live turn in flight. Idempotent.';

-- 12. Execute grants ----------------------------------------------------------
REVOKE EXECUTE ON FUNCTION public.reserve_token(TEXT, TEXT, UUID) FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.settle_token(UUID, TEXT) FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.refill_tokens(TEXT, INTEGER, DATE) FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.expire_live_bots() FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION public.reserve_token(TEXT, TEXT, UUID) TO service_role;
GRANT EXECUTE ON FUNCTION public.settle_token(UUID, TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION public.refill_tokens(TEXT, INTEGER, DATE) TO service_role;
GRANT EXECUTE ON FUNCTION public.expire_live_bots() TO service_role;

-- PostgREST caches the schema per connection; the replica does not receive
-- NOTIFY, so it still needs deploy_secondary.sh + a live probe.
NOTIFY pgrst, 'reload schema';

COMMIT;
