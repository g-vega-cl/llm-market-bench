-- Create cause_and_effect table
CREATE TABLE IF NOT EXISTS public.cause_and_effect (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES public.memories(id) ON DELETE CASCADE,
    analysis TEXT NOT NULL,
    market_outcome TEXT,
    confidence INT CHECK (confidence >= 0 AND confidence <= 100),
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Enable RLS
ALTER TABLE public.cause_and_effect ENABLE ROW LEVEL SECURITY;

-- Public read access
CREATE POLICY "Allow public read access for cause_and_effect"
ON public.cause_and_effect
FOR SELECT
TO anon, authenticated
USING (true);

-- Service role full access
CREATE POLICY "Allow service_role full access for cause_and_effect"
ON public.cause_and_effect
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Index for faster lookups by event_id
CREATE INDEX IF NOT EXISTS idx_cause_and_effect_event_id ON public.cause_and_effect(event_id);
