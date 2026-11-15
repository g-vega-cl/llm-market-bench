-- ============================================================================
-- Migration: 20261114000000_create_recipe_intraday_bars.sql
-- Description: Restore recipe_intraday_bars archive table for 3x/day ET
--              hourly/snapshot bar caching, and align strategy_recipes
--              defaults to 3h cadence & Long-Only 4x25% concurrency.
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.recipe_intraday_bars (
    ticker TEXT NOT NULL,
    bar_time_utc TIMESTAMPTZ NOT NULL,
    open NUMERIC(12, 4) NOT NULL,
    high NUMERIC(12, 4) NOT NULL,
    low NUMERIC(12, 4) NOT NULL,
    close NUMERIC(12, 4) NOT NULL,
    volume BIGINT NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'fmp',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (ticker, bar_time_utc)
);

CREATE INDEX IF NOT EXISTS idx_recipe_intraday_bars_time
    ON public.recipe_intraday_bars (ticker, bar_time_utc DESC);

ALTER TABLE public.recipe_intraday_bars ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow public read on recipe_intraday_bars" ON public.recipe_intraday_bars;
CREATE POLICY "Allow public read on recipe_intraday_bars"
    ON public.recipe_intraday_bars FOR SELECT
    USING (true);

DROP POLICY IF EXISTS "Allow service_role full access on recipe_intraday_bars" ON public.recipe_intraday_bars;
CREATE POLICY "Allow service_role full access on recipe_intraday_bars"
    ON public.recipe_intraday_bars FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

GRANT SELECT ON public.recipe_intraday_bars TO anon, authenticated;
GRANT ALL ON public.recipe_intraday_bars TO service_role;

DO $$
DECLARE
    chk RECORD;
BEGIN
    FOR chk IN
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'public.strategy_recipes'::regclass
          AND contype = 'c'
          AND pg_get_constraintdef(oid) ILIKE '%cadence%'
    LOOP
        EXECUTE format('ALTER TABLE public.strategy_recipes DROP CONSTRAINT %I', chk.conname);
    END LOOP;
END $$;

ALTER TABLE public.strategy_recipes
    ADD CONSTRAINT strategy_recipes_cadence_check CHECK (cadence IN ('5m', '3h', '1d'));

ALTER TABLE public.strategy_recipes
    ALTER COLUMN cadence SET DEFAULT '3h';

ALTER TABLE public.strategy_recipes
    ALTER COLUMN concurrency_config SET DEFAULT '{"max_open_trades": 4, "max_equity_pct_per_trade": 25.0}'::jsonb;
