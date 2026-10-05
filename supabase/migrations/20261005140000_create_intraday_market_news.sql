-- Create intraday_market_news table for Jev-vetted market-moving catalysts
CREATE TABLE IF NOT EXISTS public.intraday_market_news (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    headline TEXT NOT NULL,
    summary TEXT,
    source TEXT NOT NULL,
    url TEXT,
    tickers JSONB DEFAULT '[]'::jsonb,
    event_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    jev_choice TEXT NOT NULL DEFAULT 'MARKET_MOVING',
    jev_confidence NUMERIC(5, 2) NOT NULL,
    source_id_hash TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index by event_timestamp descending for fast feed retrieval
CREATE INDEX IF NOT EXISTS idx_intraday_news_event_time ON public.intraday_market_news(event_timestamp DESC);

-- Enable RLS
ALTER TABLE public.intraday_market_news ENABLE ROW LEVEL SECURITY;

-- Allow public read access
CREATE POLICY "Allow public read access to intraday_market_news" ON public.intraday_market_news
    FOR SELECT USING (true);

-- Allow service role full access
CREATE POLICY "Allow service role full access to intraday_market_news" ON public.intraday_market_news
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

GRANT SELECT ON public.intraday_market_news TO anon, authenticated;
GRANT ALL ON public.intraday_market_news TO service_role;

COMMENT ON TABLE public.intraday_market_news IS 'Real-time intraday market-moving catalysts and economic releases vetted by TypeSafe Jev';
