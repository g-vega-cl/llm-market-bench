-- Migration: Create earnings alpha and sector bellwether tables
-- Tracks Post-Earnings Announcement Drift (PEAD), Standardized Unexpected Earnings (SUE),
-- Sloan accrual quality, analyst revision momentum, and sector bellwether diffusion.

CREATE TABLE IF NOT EXISTS public.earnings_alpha_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_date DATE NOT NULL,
    ticker TEXT NOT NULL,
    sector TEXT NOT NULL,
    report_date DATE,
    actual_eps NUMERIC,
    estimated_eps NUMERIC,
    eps_surprise NUMERIC,
    revenue_actual NUMERIC,
    revenue_estimated NUMERIC,
    revenue_surprise_pct NUMERIC,
    sue_score NUMERIC,
    is_top_decile_sue BOOLEAN DEFAULT FALSE,
    quarters_analyzed_count INTEGER DEFAULT 0,
    has_sufficient_earnings_history BOOLEAN DEFAULT FALSE,
    sloan_accrual_ratio NUMERIC,
    is_sloan_accrual_clean BOOLEAN DEFAULT TRUE,
    has_extreme_pre_earnings_runup BOOLEAN DEFAULT FALSE,
    pre_earnings_20d_return_pct NUMERIC,
    days_since_earnings_report INTEGER,
    post_earnings_drift_pct NUMERIC,
    post_earnings_alpha_vs_spy NUMERIC,
    analyst_consensus TEXT,
    analyst_coverage_count INTEGER DEFAULT 0,
    analyst_buy_ratio_pct NUMERIC,
    target_consensus_price NUMERIC,
    target_consensus_upside_pct NUMERIC,
    created_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_earnings_alpha_snapshot UNIQUE (snapshot_date, ticker)
);

CREATE INDEX IF NOT EXISTS idx_earnings_alpha_date ON public.earnings_alpha_snapshots(snapshot_date DESC);
CREATE INDEX IF NOT EXISTS idx_earnings_alpha_ticker ON public.earnings_alpha_snapshots(ticker);
CREATE INDEX IF NOT EXISTS idx_earnings_alpha_sector ON public.earnings_alpha_snapshots(sector);
CREATE INDEX IF NOT EXISTS idx_earnings_alpha_sue ON public.earnings_alpha_snapshots(sue_score DESC);

ALTER TABLE public.earnings_alpha_snapshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read for earnings_alpha_snapshots" ON public.earnings_alpha_snapshots
    FOR SELECT USING (true);

CREATE POLICY "Allow service_role full access for earnings_alpha_snapshots" ON public.earnings_alpha_snapshots
    FOR ALL USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

GRANT SELECT ON public.earnings_alpha_snapshots TO anon, authenticated;
GRANT ALL ON public.earnings_alpha_snapshots TO service_role;


CREATE TABLE IF NOT EXISTS public.sector_bellwether_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_date DATE NOT NULL,
    sector TEXT NOT NULL,
    ticker TEXT NOT NULL,
    classification TEXT NOT NULL, -- 'EARLY_BELLWETHER', 'DOWNSTREAM_PEER'
    market_cap NUMERIC,
    market_cap_rank INTEGER,
    report_date DATE,
    cycle_report_day INTEGER,
    is_reported BOOLEAN DEFAULT FALSE,
    is_active_bellwether_signal BOOLEAN DEFAULT FALSE,
    sue_score NUMERIC,
    revenue_surprise_pct NUMERIC,
    operating_margin_surprise_delta NUMERIC,
    created_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_sector_bellwether_signal UNIQUE (snapshot_date, sector, ticker)
);

CREATE INDEX IF NOT EXISTS idx_sector_bellwether_date ON public.sector_bellwether_signals(snapshot_date DESC);
CREATE INDEX IF NOT EXISTS idx_sector_bellwether_sector ON public.sector_bellwether_signals(sector);
CREATE INDEX IF NOT EXISTS idx_sector_bellwether_active ON public.sector_bellwether_signals(is_active_bellwether_signal);

ALTER TABLE public.sector_bellwether_signals ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read for sector_bellwether_signals" ON public.sector_bellwether_signals
    FOR SELECT USING (true);

CREATE POLICY "Allow service_role full access for sector_bellwether_signals" ON public.sector_bellwether_signals
    FOR ALL USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

GRANT SELECT ON public.sector_bellwether_signals TO anon, authenticated;
GRANT ALL ON public.sector_bellwether_signals TO service_role;
