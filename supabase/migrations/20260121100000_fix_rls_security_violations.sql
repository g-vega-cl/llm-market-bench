-- Migration: Fix RLS Security Violations
-- Description: Enables Row Level Security (RLS) and adds default policies for tables reported by Supabase Linter.
-- Created: 2026-01-21

-- 1. market_data_cache
ALTER TABLE public.market_data_cache ENABLE ROW LEVEL SECURITY;

-- Allow read access for all (for dashboard visibility/tooling)
CREATE POLICY "Allow read access for all on market_data_cache" 
    ON public.market_data_cache FOR SELECT 
    USING (true);

-- Allow service role full access
CREATE POLICY "Allow service role full access to market_data_cache" 
    ON public.market_data_cache FOR ALL 
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');


-- 2. trades
ALTER TABLE public.trades ENABLE ROW LEVEL SECURITY;

-- Allow read access for all
CREATE POLICY "Allow read access for all on trades" 
    ON public.trades FOR SELECT 
    USING (true);

-- Allow service role full access
CREATE POLICY "Allow service role full access to trades" 
    ON public.trades FOR ALL 
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- Comment for record
COMMENT ON TABLE public.market_data_cache IS 'Stores a temporary cache of stock prices and market caps. RLS enabled.';
COMMENT ON TABLE public.trades IS 'Immutable execution ledger. RLS enabled.';
