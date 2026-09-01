-- Create a cache table for options chain snapshots and derived sentiment metrics
CREATE TABLE IF NOT EXISTS options_data_cache (
    ticker TEXT PRIMARY KEY,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    contracts JSONB NOT NULL DEFAULT '[]'::jsonb,
    fetched_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for expiration checks and cleanup
CREATE INDEX IF NOT EXISTS idx_options_data_cache_fetched_at ON options_data_cache(fetched_at);

COMMENT ON TABLE options_data_cache IS 'Stores temporary cache of Massive/Polygon options snapshots and derived sentiment metrics.';

GRANT SELECT ON public.options_data_cache TO anon, authenticated;
GRANT ALL ON public.options_data_cache TO service_role;
