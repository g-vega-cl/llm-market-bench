-- Migration: Create frontier_themes table for Frontier Tech Supercycle tracking (sys-frontier-tech)
-- Stores qualified gestation themes, pure-play tickers, 5-point rubric scores, and catalysts.

CREATE TABLE IF NOT EXISTS public.frontier_themes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES public.portfolios(id) ON DELETE CASCADE,
    theme_name TEXT NOT NULL,
    thesis TEXT NOT NULL,
    catalysts TEXT NOT NULL,
    rubric_score INT NOT NULL DEFAULT 3,
    status TEXT NOT NULL DEFAULT 'active', -- 'active', 'archived', 'invalidated'
    tickers JSONB NOT NULL DEFAULT '[]'::jsonb, -- array of ticker strings: ["POET", "LWLG"]
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT frontier_themes_portfolio_theme_key UNIQUE(portfolio_id, theme_name)
);

-- Indices for fast lookups
CREATE INDEX IF NOT EXISTS idx_frontier_themes_portfolio_id ON public.frontier_themes (portfolio_id);
CREATE INDEX IF NOT EXISTS idx_frontier_themes_status ON public.frontier_themes (status);

-- Enable Row Level Security
ALTER TABLE public.frontier_themes ENABLE ROW LEVEL SECURITY;

-- Allow read access for all
CREATE POLICY "Allow read access for all on frontier_themes"
    ON public.frontier_themes FOR SELECT
    TO public
    USING (true);

-- Allow service role full access
CREATE POLICY "Allow service role full access on frontier_themes"
    ON public.frontier_themes FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Explicit grants
GRANT SELECT ON public.frontier_themes TO anon, authenticated;
GRANT ALL ON public.frontier_themes TO service_role;

COMMENT ON TABLE public.frontier_themes IS 'Qualified frontier technology supercycle themes and constituent pure-play tickers for sys-frontier-tech.';
