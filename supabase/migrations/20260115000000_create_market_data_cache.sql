-- Create a cache table for market data to reduce API calls and enable LLM tool-calling validation.
CREATE TABLE IF NOT EXISTS market_data_cache (
    ticker TEXT PRIMARY KEY,
    price NUMERIC NOT NULL,
    market_cap NUMERIC NOT NULL,
    fetched_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for efficient expiration checks and cleanup
CREATE INDEX IF NOT EXISTS idx_market_data_cache_fetched_at ON market_data_cache(fetched_at);

-- Add a column for the currency if needed, though FMP/yfinance default to USD for US stocks
-- For now, we assume USD as per project requirements (S&P 500 benchmarking)

COMMENT ON TABLE market_data_cache IS 'Stores a temporary cache of stock prices and market caps for validation.';
