-- Add OHLC columns to price_history so that the evaluation pipeline can
-- determine intraday high/low relative to open without discarding data that
-- FMP already provides in historical-price-eod/full responses.
--
-- All columns are nullable so that:
--   • Existing rows (which pre-date this migration) are unaffected.
--   • Callers that only need `price` continue to work unchanged.
--   • fetch_intraday_prices() gracefully falls back to close when NULL.

ALTER TABLE price_history ADD COLUMN IF NOT EXISTS open  NUMERIC;
ALTER TABLE price_history ADD COLUMN IF NOT EXISTS high  NUMERIC;
ALTER TABLE price_history ADD COLUMN IF NOT EXISTS low   NUMERIC;
ALTER TABLE price_history ADD COLUMN IF NOT EXISTS close NUMERIC;

COMMENT ON COLUMN price_history.open  IS 'Opening price for the trading session (EOD bar).';
COMMENT ON COLUMN price_history.high  IS 'Intraday high price for the trading session (EOD bar).';
COMMENT ON COLUMN price_history.low   IS 'Intraday low price for the trading session (EOD bar).';
COMMENT ON COLUMN price_history.close IS 'Closing price for the trading session; mirrors the existing price column.';
