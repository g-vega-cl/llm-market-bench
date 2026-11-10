-- Migration: Create company research reports and newsletter mentions junction table
-- Supports individual stock & sector research dossiers extracted from daily briefings with smart deduplication.

CREATE TABLE IF NOT EXISTS company_research_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker TEXT NOT NULL,
    company_name TEXT NOT NULL,
    sector TEXT,
    is_sector_etf BOOLEAN DEFAULT FALSE,
    entity_type TEXT DEFAULT 'stock' CHECK (entity_type IN ('stock', 'etf')),
    session TEXT NOT NULL CHECK (session IN ('open', 'close', 'on_demand')),
    date DATE NOT NULL,
    verdict TEXT NOT NULL CHECK (verdict IN ('bullish', 'bearish', 'neutral')),
    conviction_score INTEGER NOT NULL CHECK (conviction_score BETWEEN 1 AND 100),
    risk_reward_score NUMERIC(3,1),
    target_horizon TEXT NOT NULL,
    spot_price_at_report NUMERIC(12,4),
    forward_5d_return NUMERIC(6,4),
    forward_20d_return NUMERIC(6,4),
    valuation_summary TEXT,
    buffett_moat_analysis JSONB DEFAULT '{}'::jsonb,
    options_sentiment_summary TEXT,
    catalyst_context TEXT,
    falsification_triggers JSONB DEFAULT '[]'::jsonb,
    full_report_markdown TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_company_report_session UNIQUE (ticker, date, session)
);

-- Junction table linking newsletters to research reports for N:N deduplication and cross-reference
CREATE TABLE IF NOT EXISTS newsletter_company_mentions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    newsletter_id UUID NOT NULL REFERENCES generated_newsletters(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    research_report_id UUID REFERENCES company_research_reports(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_newsletter_ticker UNIQUE (newsletter_id, ticker)
);

CREATE INDEX IF NOT EXISTS idx_company_research_ticker ON company_research_reports(ticker);
CREATE INDEX IF NOT EXISTS idx_company_research_date ON company_research_reports(date DESC);
CREATE INDEX IF NOT EXISTS idx_company_research_verdict ON company_research_reports(verdict);
CREATE INDEX IF NOT EXISTS idx_mentions_newsletter ON newsletter_company_mentions(newsletter_id);
CREATE INDEX IF NOT EXISTS idx_mentions_ticker ON newsletter_company_mentions(ticker);

-- Enable RLS with public read policies
ALTER TABLE company_research_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE newsletter_company_mentions ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'company_research_reports' AND policyname = 'Allow public read access on company_research_reports'
    ) THEN
        CREATE POLICY "Allow public read access on company_research_reports"
            ON company_research_reports FOR SELECT
            USING (true);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'newsletter_company_mentions' AND policyname = 'Allow public read access on newsletter_company_mentions'
    ) THEN
        CREATE POLICY "Allow public read access on newsletter_company_mentions"
            ON newsletter_company_mentions FOR SELECT
            USING (true);
    END IF;
END $$;

GRANT SELECT ON public.company_research_reports TO anon, authenticated;
GRANT ALL ON public.company_research_reports TO service_role;

GRANT SELECT ON public.newsletter_company_mentions TO anon, authenticated;
GRANT ALL ON public.newsletter_company_mentions TO service_role;
