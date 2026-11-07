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

-- Stub auth.users table for compatibility with user-isolated tables (e.g. chat_memories)
CREATE TABLE IF NOT EXISTS auth.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Grant schema usage
GRANT USAGE ON SCHEMA public, auth TO anon, authenticated, service_role;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA auth TO anon, authenticated, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA auth TO anon, authenticated, service_role;

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

-- Create Gov Macro Liquidity table
CREATE TABLE IF NOT EXISTS public.gov_macro_liquidity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    record_date DATE NOT NULL UNIQUE,
    tga_balance NUMERIC(18, 2),
    tot_pub_debt NUMERIC(18, 2),
    debt_held_public NUMERIC(18, 2),
    intragov_holdings NUMERIC(18, 2),
    monthly_deficit_surplus NUMERIC(18, 2),
    raw_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_gov_macro_liquidity_record_date 
    ON public.gov_macro_liquidity(record_date DESC);

-- Create Gov Contracts table
CREATE TABLE IF NOT EXISTS public.gov_contracts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    country TEXT NOT NULL CHECK (country IN ('US', 'CA', 'OTHER')),
    award_id TEXT NOT NULL,
    recipient_name TEXT NOT NULL,
    award_amount NUMERIC(16, 2) NOT NULL DEFAULT 0.00,
    currency TEXT NOT NULL DEFAULT 'USD',
    description TEXT,
    agency_name TEXT,
    award_date DATE NOT NULL,
    contract_number TEXT,
    source_url TEXT,
    raw_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_gov_contracts UNIQUE (country, award_id, recipient_name, award_date)
);

CREATE INDEX IF NOT EXISTS idx_gov_contracts_country_date 
    ON public.gov_contracts(country, award_date DESC);
CREATE INDEX IF NOT EXISTS idx_gov_contracts_recipient 
    ON public.gov_contracts(recipient_name);
CREATE INDEX IF NOT EXISTS idx_gov_contracts_amount 
    ON public.gov_contracts(award_amount DESC);

-- Create Institutional Whale Stakes table
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

-- Grant table access
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO anon, authenticated, postgres;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated, postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO anon, authenticated, postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO anon, authenticated, postgres;

