-- Create generated_newsletters table
CREATE TABLE IF NOT EXISTS public.generated_newsletters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    content TEXT NOT NULL,
    bullet_points JSONB DEFAULT '[]'::jsonb,
    session TEXT NOT NULL CHECK (session IN ('open', 'close')),
    read_time_minutes INTEGER DEFAULT 2,
    source_count INTEGER DEFAULT 0,
    formatted_time TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE public.generated_newsletters ENABLE ROW LEVEL SECURITY;

-- Allow public read access
CREATE POLICY "Allow public read access to generated_newsletters" ON public.generated_newsletters
    FOR SELECT USING (true);

-- Allow service role full access
CREATE POLICY "Allow service role full access to generated_newsletters" ON public.generated_newsletters
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

COMMENT ON TABLE public.generated_newsletters IS 'Synthesized 1-2 minute daily newsletters generated twice daily (market open and close)';
