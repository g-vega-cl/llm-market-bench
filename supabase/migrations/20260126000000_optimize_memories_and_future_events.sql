-- Migration to optimize memories and track future events
-- 1. Add relevance_score to memories
ALTER TABLE public.memories ADD COLUMN IF NOT EXISTS relevance_score FLOAT DEFAULT 1.0;

-- 2. Create future_events table
CREATE TABLE IF NOT EXISTS public.future_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_name TEXT NOT NULL,
    target_date TEXT, -- Storing as text to support "by next summer", etc.
    description TEXT,
    source_memory_id UUID REFERENCES public.memories(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Enable RLS for future_events
ALTER TABLE public.future_events ENABLE ROW LEVEL SECURITY;

-- Allow public read access on future_events
CREATE POLICY "Allow public read access on future_events"
    ON public.future_events FOR SELECT
    USING (true);

-- Allow service role to manage future_events
CREATE POLICY "Allow service role to manage future_events"
    ON public.future_events FOR ALL
    USING (true)
    WITH CHECK (true);

-- 3. Update match_memories to filter by status and consider relevance_score
CREATE OR REPLACE FUNCTION match_memories (
  query_embedding VECTOR(768),
  match_threshold FLOAT,
  match_count INT
)
RETURNS TABLE (
  id UUID,
  content TEXT,
  metadata JSONB,
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
    (1 - (memories.embedding <=> query_embedding)) * memories.relevance_score AS similarity
  FROM memories
  WHERE memories.status = 'ACTIVE'
    AND (1 - (memories.embedding <=> query_embedding)) > match_threshold
  ORDER BY similarity DESC
  LIMIT match_count;
END;
$$;

-- 4. Update match_memories_with_time to filter by status
CREATE OR REPLACE FUNCTION match_memories_with_time(
    query_embedding VECTOR(768),
    match_threshold FLOAT,
    match_count INT,
    min_time TIMESTAMPTZ
) RETURNS TABLE (
    id UUID,
    content TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id,
        m.content,
        m.metadata,
        m.created_at,
        1 - (m.embedding <=> query_embedding) AS similarity
    FROM memories m
    WHERE m.status = 'ACTIVE'
      AND m.created_at >= min_time
      AND 1 - (m.embedding <=> query_embedding) >= match_threshold
    ORDER BY m.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;
