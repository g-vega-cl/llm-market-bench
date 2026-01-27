-- Migration: Fix Remaining Supabase Security Warnings
-- Description: Fixes function search paths, moves vector extension to dedicated schema, and tightens concept_metrics RLS.
-- Created: 2026-01-27

-- 1. Create extensions schema and move vector extension
CREATE SCHEMA IF NOT EXISTS extensions;
ALTER EXTENSION vector SET SCHEMA extensions;

-- Grant usage on the extensions schema
GRANT USAGE ON SCHEMA extensions TO anon, authenticated, service_role;

-- 2. Update functions with fixed search_path and use qualified type names
-- We use extensions.vector to be explicit about the schema since we just moved it.

-- 2a. match_memories
CREATE OR REPLACE FUNCTION public.match_memories(
    query_embedding extensions.vector(768),
    match_threshold float,
    match_count int
) RETURNS TABLE (
    id uuid,
    content text,
    metadata jsonb,
    similarity float
)
LANGUAGE plpgsql
SET search_path = public, extensions
AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id,
        m.content,
        m.metadata,
        1 - (m.embedding <=> query_embedding) AS similarity
    FROM public.memories m
    WHERE 1 - (m.embedding <=> query_embedding) > match_threshold
    ORDER BY m.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- 2b. match_memories_with_time
CREATE OR REPLACE FUNCTION public.match_memories_with_time(
    query_embedding extensions.vector(768),
    match_threshold float,
    match_count int,
    min_time timestamptz
) RETURNS TABLE (
    id uuid,
    content text,
    metadata jsonb,
    created_at timestamptz,
    similarity float
)
LANGUAGE plpgsql
SET search_path = public, extensions
AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id,
        m.content,
        m.metadata,
        m.created_at,
        1 - (m.embedding <=> query_embedding) AS similarity
    FROM public.memories m
    WHERE m.created_at >= min_time
      AND 1 - (m.embedding <=> query_embedding) >= match_threshold
    ORDER BY m.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- 2c. match_concepts
CREATE OR REPLACE FUNCTION public.match_concepts(
    query_embedding extensions.vector(768),
    match_threshold float,
    match_count int
) RETURNS TABLE (
    id uuid,
    concept_name text,
    mention_count int,
    similarity float
)
LANGUAGE plpgsql
SET search_path = public, extensions
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.concept_name,
        c.mention_count,
        1 - (c.concept_vector <=> query_embedding) AS similarity
    FROM public.concept_metrics c
    WHERE 1 - (c.concept_vector <=> query_embedding) >= match_threshold
    ORDER BY c.concept_vector <=> query_embedding
    LIMIT match_count;
END;
$$;

-- 3. Tighten RLS on concept_metrics
DROP POLICY IF EXISTS "Allow service role to manage concept_metrics" ON public.concept_metrics;

CREATE POLICY "Allow service role to manage concept_metrics"
    ON public.concept_metrics FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- Update comments
COMMENT ON FUNCTION public.match_memories IS 'Matches memories based on vector similarity. Search path fixed.';
COMMENT ON FUNCTION public.match_memories_with_time IS 'Matches memories with time filter. Search path fixed.';
COMMENT ON FUNCTION public.match_concepts IS 'Matches concepts for semantic merging. Search path fixed.';
COMMENT ON POLICY "Allow service role to manage concept_metrics" ON public.concept_metrics IS 'Restricts full access to the service role only.';
