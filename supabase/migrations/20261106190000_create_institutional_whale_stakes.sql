-- Migration: Create institutional whale stakes table
-- Tracks Schedule 13D and 13G beneficial ownership disclosures (>5% blocks,
-- activist entries, and institutional whale accumulations/liquidations).

CREATE TABLE IF NOT EXISTS public.institutional_whale_stakes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol TEXT NOT NULL,
    filer_name TEXT NOT NULL,
    filer_cik TEXT,
    filing_date DATE NOT NULL,
    accepted_date DATE,
    percent_of_class NUMERIC(6, 2) NOT NULL DEFAULT 0.00,
    shares_beneficially_owned NUMERIC(16, 2) NOT NULL DEFAULT 0.00,
    reporting_type TEXT,
    filing_type TEXT NOT NULL DEFAULT '13G' CHECK (filing_type IN ('13D', '13G', '13F', 'OTHER')),
    is_exit BOOLEAN NOT NULL DEFAULT false,
    source_url TEXT,
    raw_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_institutional_whale_stake UNIQUE (symbol, filer_name, filing_date, percent_of_class)
);

CREATE INDEX IF NOT EXISTS idx_whale_stakes_symbol 
    ON public.institutional_whale_stakes(symbol, filing_date DESC);
CREATE INDEX IF NOT EXISTS idx_whale_stakes_filer 
    ON public.institutional_whale_stakes(filer_name);
CREATE INDEX IF NOT EXISTS idx_whale_stakes_filing_date 
    ON public.institutional_whale_stakes(filing_date DESC);

ALTER TABLE public.institutional_whale_stakes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read for institutional_whale_stakes" 
    ON public.institutional_whale_stakes
    FOR SELECT USING (true);

CREATE POLICY "Allow service_role full access for institutional_whale_stakes" 
    ON public.institutional_whale_stakes
    FOR ALL USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

GRANT SELECT ON public.institutional_whale_stakes TO anon, authenticated;
GRANT ALL ON public.institutional_whale_stakes TO service_role;
