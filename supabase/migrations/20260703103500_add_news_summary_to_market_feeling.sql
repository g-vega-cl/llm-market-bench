-- Add news_summary column to market_feeling
ALTER TABLE public.market_feeling ADD COLUMN news_summary TEXT;
COMMENT ON COLUMN public.market_feeling.news_summary IS 'Synthesized summary of today''s news/newsletters ingested during the session';
