-- Quota limits are tier defaults with an optional per-user override, not copies
-- of constants frozen into every row.
--
-- A NULL now means "use BETA_STARTER_LIMITS", which is what
-- fetchRecipeQuotaStatus() already assumes (`override.max_live_recipes ?? ...`).
-- Before this, activate_recipe_turbo() inserted only (user_id) and inherited the
-- table defaults, so one Turbo activation silently downgraded a beta_starter user
-- from 3 live recipes to 1, and from an unlimited daily live-turn budget
-- (Number.POSITIVE_INFINITY in code) to 3.

ALTER TABLE public.recipe_user_quotas
    ALTER COLUMN max_concurrent_backtests DROP NOT NULL,
    ALTER COLUMN max_concurrent_backtests DROP DEFAULT,
    ALTER COLUMN daily_backtest_limit DROP NOT NULL,
    ALTER COLUMN daily_backtest_limit DROP DEFAULT,
    ALTER COLUMN daily_live_turn_limit DROP NOT NULL,
    ALTER COLUMN daily_live_turn_limit DROP DEFAULT,
    ALTER COLUMN max_live_recipes DROP NOT NULL,
    ALTER COLUMN max_live_recipes DROP DEFAULT;

COMMENT ON COLUMN public.recipe_user_quotas.max_concurrent_backtests IS
    'NULL = tier default. Non-NULL is an explicit per-user override.';
COMMENT ON COLUMN public.recipe_user_quotas.daily_backtest_limit IS
    'NULL = tier default. Non-NULL is an explicit per-user override.';
COMMENT ON COLUMN public.recipe_user_quotas.daily_live_turn_limit IS
    'NULL = tier default. Non-NULL is an explicit per-user override.';
COMMENT ON COLUMN public.recipe_user_quotas.max_live_recipes IS
    'NULL = tier default. Non-NULL is an explicit per-user override.';

-- Rows that still carry every legacy default and were never annotated are the
-- ones the Turbo RPC created by accident. A row that only differs in one column
-- is left alone: that shape is a deliberate override.
DO $$
DECLARE
    v_rows integer;
BEGIN
    UPDATE public.recipe_user_quotas
       SET max_concurrent_backtests = NULL,
           daily_backtest_limit = NULL,
           daily_live_turn_limit = NULL,
           max_live_recipes = NULL,
           updated_at = NOW()
     WHERE tier = 'beta_starter'
       AND notes = ''
       AND max_concurrent_backtests = 1
       AND daily_backtest_limit = 2
       AND daily_live_turn_limit = 3
       AND max_live_recipes = 1;

    GET DIAGNOSTICS v_rows = ROW_COUNT;
    RAISE NOTICE 'recipe_user_quotas: cleared % rows carrying the legacy defaults', v_rows;
END $$;
