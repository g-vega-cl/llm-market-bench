-- Fix public.match_decisions after the vector extension moved to the extensions schema.
--
-- 20260507000000_fix_match_decisions_overload.sql recreated this function without a
-- pinned search_path. Because pgvector's `<=>` operator lives in the `extensions`
-- schema (see 20260127190000_fix_remaining_security_warnings.sql), PostgREST sessions
-- fail at runtime with:
--   operator does not exist: extensions.vector <=> extensions.vector
-- which breaks retrieve_for_decision() and therefore Tier 2 RAG.
--
-- This migration mirrors the 20260507 definition while restoring the search_path
-- hardening used by the other match_* functions.

CREATE OR REPLACE FUNCTION public.match_decisions(
  query_embedding extensions.vector,
  match_threshold double precision,
  match_count integer,
  filter_model_name text DEFAULT NULL
)
RETURNS TABLE (
  id uuid,
  ticker text,
  signal text,
  reasoning text,
  model_name text,
  similarity double precision
)
LANGUAGE plpgsql
SET search_path = public, extensions
AS $$
BEGIN
  RETURN QUERY
  SELECT
    d.id,
    d.ticker,
    d.signal,
    d.reasoning,
    d.model_name,
    1 - (d.embedding <=> query_embedding) AS similarity
  FROM public.decisions d
  WHERE 1 - (d.embedding <=> query_embedding) > match_threshold
    AND (filter_model_name IS NULL OR d.model_name = filter_model_name)
  ORDER BY d.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

GRANT EXECUTE ON FUNCTION public.match_decisions(extensions.vector, double precision, integer, text) TO anon, authenticated, service_role;
