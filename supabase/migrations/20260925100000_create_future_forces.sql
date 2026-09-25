-- Migration: Create future_forces table for Multi-Horizon Thematic Forces & Catalysts (sys-future-forces)
-- Stores forward-looking forces across 7 archetypes (2 to 24 month horizons), target milestones, and explicit invalidation triggers.

CREATE TABLE IF NOT EXISTS public.future_forces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID REFERENCES public.portfolios(id) ON DELETE CASCADE,
    force_title TEXT NOT NULL,
    archetype TEXT NOT NULL, -- 'geopolitical_chokepoint', 'government_agenda', 'sleeping_giant', 'distribution_turnon', 'secular_tollroad', 'tam_explosion', 'mega_event', 'deep_value_turnaround'
    thesis TEXT NOT NULL,
    catalyst_event TEXT NOT NULL,
    horizon_months INT NOT NULL DEFAULT 3, -- 2 to 24 months
    target_date DATE,
    invalidation_triggers TEXT NOT NULL,
    transmission_mechanism TEXT,
    tickers JSONB NOT NULL DEFAULT '[]'::jsonb, -- e.g. ["FRO", "STNG"] or ["CRWD", "PANW"]
    conviction_score INT NOT NULL DEFAULT 4, -- 1 to 5
    status TEXT NOT NULL DEFAULT 'active', -- 'active', 'pending_liquidation', 'invalidated', 'realized'
    invalidation_reason TEXT,
    audited_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT future_forces_title_key UNIQUE(force_title)
);

-- Indices for fast lookups
CREATE INDEX IF NOT EXISTS idx_future_forces_portfolio_id ON public.future_forces (portfolio_id);
CREATE INDEX IF NOT EXISTS idx_future_forces_status ON public.future_forces (status);
CREATE INDEX IF NOT EXISTS idx_future_forces_archetype ON public.future_forces (archetype);

-- Enable Row Level Security
ALTER TABLE public.future_forces ENABLE ROW LEVEL SECURITY;

-- Allow read access for all
CREATE POLICY "Allow read access for all on future_forces"
    ON public.future_forces FOR SELECT
    TO public
    USING (true);

-- Allow service role full access
CREATE POLICY "Allow service role full access on future_forces"
    ON public.future_forces FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Explicit grants
GRANT SELECT ON public.future_forces TO anon, authenticated;
GRANT ALL ON public.future_forces TO service_role;

COMMENT ON TABLE public.future_forces IS 'Multi-horizon future market forces (2-24 months), catalyst milestones, and falsification triggers for sys-future-forces.';
