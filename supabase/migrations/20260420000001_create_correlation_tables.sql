-- Correlation Matrix Tables
-- Stores weekly rolling correlation computations for uncorrelated asset discovery
-- Used by AI Wall Street agents and displayed on /market-overview page

-- Tracks each weekly correlation computation run
CREATE TABLE correlation_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_date DATE NOT NULL,  -- Sunday of the run week
    created_at TIMESTAMPTZ DEFAULT NOW(),
    window_days INTEGER NOT NULL DEFAULT 90,  -- Rolling window (90 days)
    num_assets INTEGER NOT NULL,  -- Number of assets in universe
    tickers JSONB NOT NULL  -- Array of all tickers included
);

-- Unique constraint on run_date to prevent duplicates
CREATE UNIQUE INDEX idx_correlation_runs_run_date ON correlation_runs(run_date);

-- Index for fast lookups
CREATE INDEX idx_correlation_runs_created_at ON correlation_runs(created_at DESC);

-- Full 46x46 correlation matrix stored as individual pairs
-- ticker_a < ticker_b (alphabetical ordering to avoid duplicates)
CREATE TABLE correlation_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES correlation_runs(id) ON DELETE CASCADE,

    -- Asset pair
    ticker_a TEXT NOT NULL,
    ticker_b TEXT NOT NULL,

    -- Correlation coefficients
    pearson_corr FLOAT,
    spearman_corr FLOAT,

    -- 90-day trailing returns for each asset
    returns_a_90d FLOAT,  -- percentage
    returns_b_90d FLOAT,  -- percentage

    -- Metadata
    data_points INTEGER,  -- Number of observations used

    CONSTRAINT correlation_data_pair UNIQUE (run_id, ticker_a, ticker_b)
);

-- Indexes for efficient querying
CREATE INDEX idx_correlation_data_run_id ON correlation_data(run_id);
CREATE INDEX idx_correlation_data_pearson ON correlation_data(pearson_corr);
CREATE INDEX idx_correlation_data_spearman ON correlation_data(spearman_corr);
CREATE INDEX idx_correlation_data_ticker ON correlation_data(ticker_a, ticker_b);

-- RLS policies (public read for dashboard)
ALTER TABLE correlation_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE correlation_data ENABLE ROW LEVEL SECURITY;

-- Public can read
CREATE POLICY "Public can read correlation_runs" ON correlation_runs
    FOR SELECT USING (true);

CREATE POLICY "Public can read correlation_data" ON correlation_data
    FOR SELECT USING (true);

-- Service role can write (engine uses service_role key)
CREATE POLICY "Service role can write correlation_runs" ON correlation_runs
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can write correlation_data" ON correlation_data
    FOR ALL USING (auth.role() = 'service_role');

-- Cleanup job: Delete runs older than 180 days (approx 6 months)
-- This keeps correlation history for regime analysis but prevents unbounded growth
CREATE OR REPLACE FUNCTION cleanup_old_correlation_runs()
RETURNS void AS $$
BEGIN
    DELETE FROM correlation_runs WHERE run_date < NOW() - INTERVAL '180 days';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON TABLE correlation_runs IS 'Tracks weekly correlation matrix computation runs';
COMMENT ON TABLE correlation_data IS 'Full 46x46 correlation matrix stored as pairs with Pearson and Spearman coefficients';
COMMENT ON COLUMN correlation_data.pearson_corr IS 'Pearson correlation coefficient (-1 to 1)';
COMMENT ON COLUMN correlation_data.spearman_corr IS 'Spearman rank correlation coefficient (-1 to 1)';
COMMENT ON COLUMN correlation_data.returns_a_90d IS '90-day trailing return for ticker_a (percentage)';
COMMENT ON FUNCTION cleanup_old_correlation_runs IS 'Cleans up correlation runs older than 180 days';