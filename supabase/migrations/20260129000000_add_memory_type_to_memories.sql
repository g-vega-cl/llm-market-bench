-- Migration to add memory_type to memories and categorize existing memories
-- This allows distinguishing between market events, government incentives, and lessons learned.

-- 1. Add memory_type column
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='memories' AND column_name='memory_type') THEN
        ALTER TABLE public.memories ADD COLUMN memory_type TEXT DEFAULT 'MARKET_EVENT';
    END IF;
END $$;

-- 2. Add index for performance
CREATE INDEX IF NOT EXISTS memories_memory_type_idx ON public.memories (memory_type);

-- 3. Update match_memories RPC to include memory_type and filtering support
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
    1 - (memories.embedding <=> query_embedding) AS similarity
  FROM memories
  WHERE 1 - (memories.embedding <=> query_embedding) > match_threshold
    AND (filter_memory_types IS NULL OR memories.memory_type = ANY(filter_memory_types))
  ORDER BY memories.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
