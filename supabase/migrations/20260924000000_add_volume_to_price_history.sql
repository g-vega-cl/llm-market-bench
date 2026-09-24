-- Add volume column to price_history so that the volume context pipeline
-- (compute_volume_context / execute_volatility_metrics_tool) can read RVOL
-- from the DB cache rather than only from live API fetches.
ALTER TABLE price_history ADD COLUMN IF NOT EXISTS volume BIGINT;

COMMENT ON COLUMN price_history.volume IS 'Daily share volume for the trading session (EOD bar).';
