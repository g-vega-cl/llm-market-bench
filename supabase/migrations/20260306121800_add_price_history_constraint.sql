-- Add unique constraint to price history to support upsert operations.
-- Also make market_cap nullable since historical data often lacks it.

ALTER TABLE price_history 
ALTER COLUMN market_cap DROP NOT NULL;

-- Remove duplicate entries before adding unique constraint (keeping the latest price per ticker/time)
DELETE FROM price_history a
USING price_history b
WHERE a.ctid < b.ctid
  AND a.ticker = b.ticker
  AND a.fetched_at = b.fetched_at;

ALTER TABLE price_history
ADD CONSTRAINT price_history_ticker_fetched_at_key UNIQUE (ticker, fetched_at);
