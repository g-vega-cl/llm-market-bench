-- Migration: Fix match_decisions function overload ambiguity
-- The previous migration (20260506000000) added a 4-param overload without
-- dropping the original 3-param version, causing PostgREST to return
-- HTTP 300 Multiple Choices. This follows the same DROP+CREATE pattern
-- used by match_memories in 20260305000000.

-- Drop ALL overloads to eliminate ambiguity
DROP FUNCTION IF EXISTS match_decisions(VECTOR(768), FLOAT, INT);
DROP FUNCTION IF EXISTS match_decisions(VECTOR(768), FLOAT, INT, TEXT);
DROP FUNCTION IF EXISTS match_decisions(extensions.vector(768), FLOAT, INT);
DROP FUNCTION IF EXISTS match_decisions(extensions.vector(768), FLOAT, INT, TEXT);

-- Recreate with the 4-parameter signature
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
