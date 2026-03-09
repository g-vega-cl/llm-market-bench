-- Migration to add importance_score to memories
-- This allows ranking events by their intrinsic significance (1-10)

-- 1. Add importance_score column
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='memories' AND column_name='importance_score') THEN
        ALTER TABLE public.memories ADD COLUMN importance_score INT DEFAULT 5;
    END IF;
END $$;

-- 2. Add index for performance in sorted retrieval
CREATE INDEX IF NOT EXISTS memories_importance_score_idx ON public.memories (importance_score DESC);

-- 3. Update match_memories RPC to consider importance_score if requested
-- We'll keep the existing signature but internally we could adjust how similarity is calculated if needed.
-- For now, let's just make sure the column is included in the result.

-- Handle row type changes by dropping existing functions first
DROP FUNCTION IF EXISTS match_memories(VECTOR(768), FLOAT, INT);
DROP FUNCTION IF EXISTS match_memories(VECTOR(768), FLOAT, INT, TEXT[]);

CREATE OR REPLACE FUNCTION match_memories (
  query_embedding VECTOR(768),
  match_threshold FLOAT,
  match_count INT,
  filter_memory_types TEXT[] DEFAULT NULL
)
RETURNS TABLE (
  id UUID,
  content TEXT,
  metadata JSONB,
  memory_type TEXT,
  importance_score INT,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    memories.id,
    memories.content,
    memories.metadata,
    memories.memory_type,
    memories.importance_score,
    1 - (memories.embedding <=> query_embedding) AS similarity
  FROM memories
  WHERE 1 - (memories.embedding <=> query_embedding) > match_threshold
    AND (filter_memory_types IS NULL OR memories.memory_type = ANY(filter_memory_types))
  ORDER BY memories.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
