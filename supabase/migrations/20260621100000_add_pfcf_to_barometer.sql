-- Migration to add pfcf_ratio column to market_barometer_history
ALTER TABLE public.market_barometer_history
ADD COLUMN IF NOT EXISTS pfcf_ratio NUMERIC;

COMMENT ON COLUMN public.market_barometer_history.pfcf_ratio IS 'Cap-weighted S&P 500 Price-to-Free-Cash-Flow ratio (excluding constituents with negative FCF).';
