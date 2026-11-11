-- Migration: Create daily_stock_baskets and daily_stock_picks tables
-- Purpose: Two-tier relational schema for the Daily Stock Picker Arena (3 Up, 3 Down)
-- Pre-materializes Long/Short spread alpha for Zero Frontend Compute (Principle 9)

CREATE TABLE IF NOT EXISTS public.daily_stock_baskets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    target_date DATE NOT NULL,
    model_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'evaluated', 'cancelled')),
    directional_hit_rate NUMERIC,
    mean_long_return_pct NUMERIC,
    mean_short_return_pct NUMERIC,
    ls_spread_alpha_pct NUMERIC,
    excess_alpha_vs_spy_pct NUMERIC,
    benchmark_spy_return_pct NUMERIC,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    evaluated_at TIMESTAMPTZ,
    CONSTRAINT uq_daily_stock_basket UNIQUE (target_date, model_name)
);

CREATE TABLE IF NOT EXISTS public.daily_stock_picks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    basket_id UUID NOT NULL REFERENCES public.daily_stock_baskets(id) ON DELETE CASCADE,
    target_date DATE NOT NULL,
    model_name TEXT NOT NULL,
    ticker TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('UP', 'DOWN')),
    rank INT NOT NULL CHECK (rank BETWEEN 1 AND 3),
    confidence NUMERIC NOT NULL CHECK (confidence BETWEEN 50.0 AND 100.0),
    expected_return_pct NUMERIC,
    reasoning TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'evaluated', 'cancelled')),
    open_price NUMERIC,
    close_price NUMERIC,
    stock_return_pct NUMERIC,
    position_return_pct NUMERIC,
    is_hit BOOLEAN,
    conviction_points NUMERIC,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    evaluated_at TIMESTAMPTZ,
    CONSTRAINT uq_stock_picks_slot UNIQUE (target_date, model_name, direction, rank),
    CONSTRAINT uq_stock_picks_ticker UNIQUE (target_date, model_name, ticker),
    CONSTRAINT chk_pick_evaluation_invariants CHECK (
      (status = 'pending' AND evaluated_at IS NULL AND is_hit IS NULL AND close_price IS NULL) OR
      (status = 'evaluated' AND open_price IS NOT NULL AND open_price > 0 AND close_price IS NOT NULL AND stock_return_pct IS NOT NULL AND position_return_pct IS NOT NULL AND is_hit IS NOT NULL AND evaluated_at IS NOT NULL) OR
      (status = 'cancelled' AND is_hit IS NULL)
    )
);

-- Performance indices
CREATE INDEX IF NOT EXISTS idx_stock_picks_status ON public.daily_stock_picks(status);
CREATE INDEX IF NOT EXISTS idx_stock_picks_basket ON public.daily_stock_picks(basket_id);
CREATE INDEX IF NOT EXISTS idx_stock_picks_model_date ON public.daily_stock_picks(model_name, target_date);
CREATE INDEX IF NOT EXISTS idx_stock_baskets_target_date ON public.daily_stock_baskets(target_date);
CREATE INDEX IF NOT EXISTS idx_stock_baskets_model_name ON public.daily_stock_baskets(model_name);

-- Row Level Security (RLS)
ALTER TABLE public.daily_stock_baskets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.daily_stock_picks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read stock baskets" ON public.daily_stock_baskets
    FOR SELECT USING (true);

CREATE POLICY "Service role write stock baskets" ON public.daily_stock_baskets
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Public read stock picks" ON public.daily_stock_picks
    FOR SELECT USING (true);

CREATE POLICY "Service role write stock picks" ON public.daily_stock_picks
    FOR ALL TO service_role USING (true) WITH CHECK (true);

GRANT SELECT ON public.daily_stock_baskets, public.daily_stock_picks TO anon, authenticated;
GRANT ALL ON public.daily_stock_baskets, public.daily_stock_picks TO service_role;

COMMENT ON TABLE public.daily_stock_baskets IS 'Daily stock picker arena baskets pre-materializing L/S alpha and hit rates for model tracks.';
COMMENT ON TABLE public.daily_stock_picks IS 'Granular 3 UP and 3 DOWN daily stock picks with execution and conviction scoring.';
