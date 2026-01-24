-- Create a table to store the history of fetched prices.
CREATE TABLE IF NOT EXISTS price_history (
    ticker TEXT NOT NULL,
    price NUMERIC NOT NULL,
    market_cap NUMERIC NOT NULL,
    fetched_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for efficient querying by ticker and time.
CREATE INDEX IF NOT EXISTS idx_price_history_ticker_fetched_at ON price_history(ticker, fetched_at DESC);

COMMENT ON TABLE price_history IS 'Stores a historical record of stock prices and market caps fetched from providers.';
