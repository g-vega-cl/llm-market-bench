-- Migration: Add model_name filter to match_decisions RPC
-- This allows per-agent RAG scoping so the verifier only sees
-- past decisions from the same agent, reducing cross-contamination.

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;

CREATE OR REPLACE FUNCTION match_decisions (
  query_embedding extensions.vector(768),
  match_threshold FLOAT,
  match_count INT,
  filter_model_name TEXT DEFAULT NULL
)
RETURNS TABLE (
  id UUID,
  ticker TEXT,
  signal TEXT,
  reasoning TEXT,
  model_name TEXT,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    decisions.id,
    decisions.ticker,
    decisions.signal,
    decisions.reasoning,
    decisions.model_name,
    1 - (decisions.embedding <=> query_embedding) AS similarity
  FROM decisions
  WHERE 1 - (decisions.embedding <=> query_embedding) > match_threshold
    AND (filter_model_name IS NULL OR decisions.model_name = filter_model_name)
  ORDER BY decisions.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
