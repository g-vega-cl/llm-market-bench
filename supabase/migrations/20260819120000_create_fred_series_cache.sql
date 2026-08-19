-- Create a cache table for FRED macroeconomic series observations to reduce API calls,
-- speed up LLM tool execution, and share data across workers and backtests.
CREATE TABLE IF NOT EXISTS fred_series_cache (
    series_id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT '',
    units TEXT NOT NULL DEFAULT '',
    frequency TEXT NOT NULL DEFAULT '',
    latest_date TEXT NOT NULL DEFAULT '',
    latest_value NUMERIC,
    observations JSONB NOT NULL DEFAULT '[]'::jsonb,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for efficient expiration checks and cleanup
CREATE INDEX IF NOT EXISTS idx_fred_series_cache_fetched_at ON fred_series_cache(fetched_at);

-- Enable RLS and add public read policy if needed
ALTER TABLE fred_series_cache ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'fred_series_cache' AND policyname = 'Allow public read access to fred_series_cache'
    ) THEN
        CREATE POLICY "Allow public read access to fred_series_cache"
            ON fred_series_cache FOR SELECT
            TO anon, authenticated, service_role
            USING (true);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'fred_series_cache' AND policyname = 'Allow service role full access to fred_series_cache'
    ) THEN
        CREATE POLICY "Allow service role full access to fred_series_cache"
            ON fred_series_cache FOR ALL
            TO service_role
            USING (true)
            WITH CHECK (true);
    END IF;
END $$;

-- Explicit Grants
GRANT SELECT ON fred_series_cache TO anon, authenticated;
GRANT ALL ON fred_series_cache TO service_role;

COMMENT ON TABLE fred_series_cache IS 'Stores temporary and historical cached readings from the FRED macroeconomic API.';
