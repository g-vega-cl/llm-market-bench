-- ============================================================================
-- Migration: 20261119020000_recipe_desk_summary_feed_and_builder_usage.sql
-- Description:
--   1. public.recipe_desk_summary — single materialised row (live count, beat-SPY
--      count, median return) so the homepage header is a read, not a computation.
--   2. public.recipe_desk_feed — materialised "today" tape of executed signals,
--      written by the runner from the same results it already reads.
--   3. public.recipe_builder_usage + consume_builder_compile() — per-user daily
--      cap on /build compiles, which spend real proxy tokens.
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.recipe_desk_summary (
    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    live_count INTEGER NOT NULL DEFAULT 0,
    beat_spy_count INTEGER NOT NULL DEFAULT 0,
    median_return_pct NUMERIC(10, 4),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.recipe_desk_summary ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow public read on recipe_desk_summary" ON public.recipe_desk_summary;
CREATE POLICY "Allow public read on recipe_desk_summary"
    ON public.recipe_desk_summary FOR SELECT USING (true);
DROP POLICY IF EXISTS "Allow service_role full access on recipe_desk_summary" ON public.recipe_desk_summary;
CREATE POLICY "Allow service_role full access on recipe_desk_summary"
    ON public.recipe_desk_summary FOR ALL TO service_role USING (true) WITH CHECK (true);
GRANT SELECT ON public.recipe_desk_summary TO anon, authenticated;
GRANT ALL ON public.recipe_desk_summary TO service_role;

CREATE TABLE IF NOT EXISTS public.recipe_desk_feed (
    id BIGSERIAL PRIMARY KEY,
    recipe_id UUID NOT NULL,
    recipe_name TEXT NOT NULL,
    action TEXT NOT NULL,
    ticker TEXT NOT NULL,
    at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recipe_desk_feed_at ON public.recipe_desk_feed (at DESC);

ALTER TABLE public.recipe_desk_feed ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow public read on recipe_desk_feed" ON public.recipe_desk_feed;
CREATE POLICY "Allow public read on recipe_desk_feed"
    ON public.recipe_desk_feed FOR SELECT USING (true);
DROP POLICY IF EXISTS "Allow service_role full access on recipe_desk_feed" ON public.recipe_desk_feed;
CREATE POLICY "Allow service_role full access on recipe_desk_feed"
    ON public.recipe_desk_feed FOR ALL TO service_role USING (true) WITH CHECK (true);
GRANT SELECT ON public.recipe_desk_feed TO anon, authenticated;
GRANT ALL ON public.recipe_desk_feed TO service_role;

CREATE TABLE IF NOT EXISTS public.recipe_builder_usage (
    user_id UUID NOT NULL,
    usage_day DATE NOT NULL DEFAULT ((NOW() AT TIME ZONE 'utc')::date),
    compiles INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, usage_day)
);

ALTER TABLE public.recipe_builder_usage ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow service_role full access on recipe_builder_usage" ON public.recipe_builder_usage;
CREATE POLICY "Allow service_role full access on recipe_builder_usage"
    ON public.recipe_builder_usage FOR ALL TO service_role USING (true) WITH CHECK (true);
GRANT ALL ON public.recipe_builder_usage TO service_role;

-- Atomically spends one compile and returns the running total for today, so two
-- concurrent requests can never both slip under the cap.
CREATE OR REPLACE FUNCTION public.consume_builder_compile(p_user UUID)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    new_count INTEGER;
BEGIN
    INSERT INTO public.recipe_builder_usage (user_id, usage_day, compiles)
    VALUES (p_user, (NOW() AT TIME ZONE 'utc')::date, 1)
    ON CONFLICT (user_id, usage_day)
    DO UPDATE SET compiles = public.recipe_builder_usage.compiles + 1,
                  updated_at = NOW()
    RETURNING compiles INTO new_count;
    RETURN new_count;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.consume_builder_compile(UUID) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.consume_builder_compile(UUID) TO service_role;

COMMENT ON TABLE public.recipe_desk_summary IS 'Runner-materialised homepage header counts.';
COMMENT ON TABLE public.recipe_desk_feed IS 'Runner-materialised same-day executed-signal tape.';
COMMENT ON TABLE public.recipe_builder_usage IS 'Per-user daily /build compile spend.';
