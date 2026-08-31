-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create web roles for PostgREST
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'anon') THEN
        CREATE ROLE anon NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'authenticated') THEN
        CREATE ROLE authenticated NOLOGIN;
    END IF;
END
$$;

-- Grant schema usage
GRANT USAGE ON SCHEMA public TO anon, authenticated;

-- Create LLM Reasoning Logs table
CREATE TABLE IF NOT EXISTS public.llm_reasoning_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_type TEXT NOT NULL,
    model_provider TEXT NOT NULL,
    model_name TEXT NOT NULL,
    prompt JSONB NOT NULL,
    response JSONB,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indices for fast lookups
CREATE INDEX IF NOT EXISTS idx_reasoning_logs_task_type ON public.llm_reasoning_logs(task_type);
CREATE INDEX IF NOT EXISTS idx_reasoning_logs_created_at ON public.llm_reasoning_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_reasoning_logs_metadata_source_id ON public.llm_reasoning_logs USING gin (metadata);

-- Grant table access
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO anon, authenticated, postgres;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated, postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO anon, authenticated, postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO anon, authenticated, postgres;
