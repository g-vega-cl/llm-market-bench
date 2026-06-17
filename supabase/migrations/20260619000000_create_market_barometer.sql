-- Create a table for storing daily historical snapshots of S&P 500 aggregate metrics (Market Health Barometer).
CREATE TABLE IF NOT EXISTS public.market_barometer_history (
    date DATE PRIMARY KEY,
    pe_ratio NUMERIC,
    forward_pe NUMERIC,
    pb_ratio NUMERIC,
    ps_ratio NUMERIC,
    earnings_surprise_momentum NUMERIC, -- percentage of beats (e.g. 78.5)
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security (RLS)
ALTER TABLE public.market_barometer_history ENABLE ROW LEVEL SECURITY;

-- Allow read access for all
CREATE POLICY "Allow read access for all on market_barometer_history"
    ON public.market_barometer_history FOR SELECT TO public USING (true);

-- Allow service role full access
CREATE POLICY "Allow service role full access to market_barometer_history"
    ON public.market_barometer_history FOR ALL TO service_role USING (true);

-- Grant select permission to anonymous and authenticated users, and all permissions to service_role
GRANT SELECT ON public.market_barometer_history TO anon, authenticated;
GRANT ALL ON public.market_barometer_history TO service_role;

COMMENT ON TABLE public.market_barometer_history IS 'Stores historical aggregate valuation and earnings metrics for the S&P 500 index.';
