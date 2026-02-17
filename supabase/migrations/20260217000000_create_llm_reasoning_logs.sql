-- Create LLM Reasoning Logs table for research/audit
CREATE TABLE IF NOT EXISTS public.llm_reasoning_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_type TEXT NOT NULL, -- e.g., 'INGESTION', 'CONSENSUS', 'VERIFICATION'
    model_provider TEXT NOT NULL,
    model_name TEXT NOT NULL,
    prompt JSONB NOT NULL, -- Full message history sent to LLM
    response JSONB, -- Final structured or text response
    metadata JSONB DEFAULT '{}'::jsonb, -- Ticker, source_id, etc.
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indices for research queries
CREATE INDEX IF NOT EXISTS idx_reasoning_logs_task_type ON public.llm_reasoning_logs(task_type);
CREATE INDEX IF NOT EXISTS idx_reasoning_logs_created_at ON public.llm_reasoning_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_reasoning_logs_metadata_source_id ON public.llm_reasoning_logs USING gin (metadata);

-- Enable RLS
ALTER TABLE public.llm_reasoning_logs ENABLE ROW LEVEL SECURITY;

-- Allow service role full access
CREATE POLICY "Service role has full access" ON public.llm_reasoning_logs
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Allow authenticated/anon read access for research visibility
CREATE POLICY "Allow public read access for research" ON public.llm_reasoning_logs
    FOR SELECT
    USING (true);
