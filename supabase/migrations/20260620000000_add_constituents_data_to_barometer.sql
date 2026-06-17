-- Migration to add constituents_data JSONB column to market_barometer_history
ALTER TABLE public.market_barometer_history
ADD COLUMN IF NOT EXISTS constituents_data JSONB;

COMMENT ON COLUMN public.market_barometer_history.constituents_data IS 'Detailed constituent-level metrics (market cap, P/E, etc.) used to calculate aggregates.';
