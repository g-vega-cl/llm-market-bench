-- Migration: Create prediction_market_snapshots table
-- Description: Stores parsed and classification-filtered prediction market data from Polymarket and Kalshi.

CREATE TABLE public.prediction_market_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    market_id TEXT NOT NULL,
    platform TEXT NOT NULL CHECK (platform IN ('polymarket', 'kalshi')),
    question TEXT NOT NULL,
    slug TEXT,
    category TEXT NOT NULL,
    yes_odds NUMERIC NOT NULL CHECK (yes_odds >= 0 AND yes_odds <= 1),
    no_odds NUMERIC NOT NULL CHECK (no_odds >= 0 AND no_odds <= 1),
    volume_usd NUMERIC NOT NULL DEFAULT 0,
    description TEXT,
    ends_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(platform, market_id)
);

-- Enable Row Level Security (RLS)
ALTER TABLE public.prediction_market_snapshots ENABLE ROW LEVEL SECURITY;

-- ────────────────────────────────────────────────────────────────────
-- RLS POLICIES
-- ────────────────────────────────────────────────────────────────────

-- Allow read access for public/anon users (matching other read policies)
CREATE POLICY "Allow public read access" ON public.prediction_market_snapshots
    FOR SELECT USING (true);

-- Allow full access for service role (used by the engine/crawler)
CREATE POLICY "Allow service role full access" ON public.prediction_market_snapshots
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- ────────────────────────────────────────────────────────────────────
-- EXPLICIT GRANTS FOR POSTGREST DATA API ACCESS
-- See: https://supabase.com/docs/guides/database/api#granting-access-to-tables
-- ────────────────────────────────────────────────────────────────────

GRANT SELECT ON public.prediction_market_snapshots TO anon, authenticated;
GRANT ALL ON public.prediction_market_snapshots TO service_role;
