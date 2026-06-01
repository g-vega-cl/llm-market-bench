-- Migration to add pre-calculated macro volatility columns to the market_data_cache table
-- This allows the serverless loader and the LLM engine to fetch volatility statistics
-- with zero price_history network query overhead.

ALTER TABLE public.market_data_cache
ADD COLUMN IF NOT EXISTS today_pct_change NUMERIC DEFAULT 0,
ADD COLUMN IF NOT EXISTS stdev_pct NUMERIC DEFAULT 0,
ADD COLUMN IF NOT EXISTS regime_flag TEXT DEFAULT 'Normal';

COMMENT ON COLUMN public.market_data_cache.today_pct_change IS 'Pre-calculated daily percentage change compared to the previous day close.';
COMMENT ON COLUMN public.market_data_cache.stdev_pct IS 'Pre-calculated 30-day dynamic standard deviation of returns.';
COMMENT ON COLUMN public.market_data_cache.regime_flag IS 'Volatility regime flag (Normal, UNUSUAL, or HIGHLY UNUSUAL).';
