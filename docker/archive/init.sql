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
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'service_role') THEN
        CREATE ROLE service_role NOLOGIN BYPASSRLS;
    ELSE
        ALTER ROLE service_role BYPASSRLS;
    END IF;
END
$$;

-- Create auth schema mock for compatibility with Supabase RLS policies
CREATE SCHEMA IF NOT EXISTS auth;
CREATE OR REPLACE FUNCTION auth.role() RETURNS text AS $$
    SELECT coalesce(
        current_setting('request.jwt.claim.role', true),
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role')
    );
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid AS $$
    SELECT coalesce(
        nullif(current_setting('request.jwt.claim.sub', true), '')::uuid,
        nullif(current_setting('request.jwt.claims', true)::jsonb ->> 'sub', '')::uuid
    );
$$ LANGUAGE sql STABLE;

-- Grant schema usage
GRANT USAGE ON SCHEMA public, auth TO anon, authenticated, service_role;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA auth TO anon, authenticated, service_role;

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

-- Create Tool Execution Logs table
CREATE TABLE IF NOT EXISTS public.tool_execution_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_name TEXT NOT NULL,
    model_name TEXT,
    tool_args JSONB NOT NULL DEFAULT '{}'::jsonb,
    tool_result TEXT,
    duration_ms INTEGER,
    status TEXT DEFAULT 'success',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indices for tool execution queries
CREATE INDEX IF NOT EXISTS idx_tool_logs_tool_name ON public.tool_execution_logs(tool_name);
CREATE INDEX IF NOT EXISTS idx_tool_logs_created_at ON public.tool_execution_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_tool_logs_model_name ON public.tool_execution_logs(model_name);

-- Grant table access
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO anon, authenticated, postgres;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated, postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO anon, authenticated, postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO anon, authenticated, postgres;

