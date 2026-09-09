-- Migration: Create dedicated catalyst_radar table for pre-computed concept-calendar collisions
-- Populated by pipeline tasks (update_catalyst_radar.py) to enable sub-50ms reads without vector crunching on page load.

CREATE TABLE IF NOT EXISTS public.catalyst_radar (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    concept_id UUID NOT NULL REFERENCES public.concept_metrics(id) ON DELETE CASCADE,
    concept_name TEXT NOT NULL,
    velocity_score FLOAT NOT NULL DEFAULT 0.0,
    catalyst_id UUID NOT NULL REFERENCES public.memories(id) ON DELETE CASCADE,
    catalyst_title TEXT NOT NULL,
    target_date DATE NOT NULL,
    impact TEXT NOT NULL DEFAULT 'NEUTRAL',
    similarity FLOAT NOT NULL,
    related_tickers JSONB DEFAULT '[]'::jsonb,
    memory_content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT catalyst_radar_concept_catalyst_key UNIQUE(concept_id, catalyst_id)
);

-- Indices for fast target_date filtering and velocity sorting
CREATE INDEX IF NOT EXISTS idx_catalyst_radar_target_date ON public.catalyst_radar (target_date);
CREATE INDEX IF NOT EXISTS idx_catalyst_radar_velocity ON public.catalyst_radar (velocity_score DESC);
CREATE INDEX IF NOT EXISTS idx_catalyst_radar_concept ON public.catalyst_radar (concept_id);

-- Enable Row Level Security
ALTER TABLE public.catalyst_radar ENABLE ROW LEVEL SECURITY;

-- Allow read access for public / anon / authenticated
CREATE POLICY "Allow read access for all on catalyst_radar"
    ON public.catalyst_radar FOR SELECT
    TO public
    USING (true);

-- Allow service role full access
CREATE POLICY "Allow service role full access on catalyst_radar"
    ON public.catalyst_radar FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Explicit grants
GRANT SELECT ON public.catalyst_radar TO anon, authenticated;
GRANT ALL ON public.catalyst_radar TO service_role;

COMMENT ON TABLE public.catalyst_radar IS 'Pre-computed collisions between high-velocity narrative concepts and calendar memories for the Keep an Eye radar.';
