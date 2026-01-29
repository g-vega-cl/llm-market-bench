-- Migration: Add embedding to decisions table and create match_decisions RPC
-- Created: 2026-01-28

-- 1. Add embedding column to decisions
ALTER TABLE public.decisions ADD COLUMN IF NOT EXISTS embedding VECTOR(768);

-- 2. Create HNSW index for efficient similarity search
CREATE INDEX IF NOT EXISTS decisions_embedding_idx ON decisions USING hnsw (embedding vector_cosine_ops);

-- 3. Create RPC for matching decisions based on vector similarity
CREATE OR REPLACE FUNCTION match_decisions (
  query_embedding VECTOR(768),
  match_threshold FLOAT,
  match_count INT
)
RETURNS TABLE (
  id UUID,
  ticker TEXT,
  signal TEXT,
  reasoning TEXT,
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
    1 - (decisions.embedding <=> query_embedding) AS similarity
  FROM decisions
  WHERE 1 - (decisions.embedding <=> query_embedding) > match_threshold
  ORDER BY decisions.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Comment for documentation
COMMENT ON COLUMN decisions.embedding IS 'Vector embedding of the reasoning text for RAG retrieval.';
