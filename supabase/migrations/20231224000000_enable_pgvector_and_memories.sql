-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create memories table
CREATE TABLE IF NOT EXISTS memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding VECTOR(768), -- text-embedding-004 uses 768 dimensions
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure content is unique to prevent duplicate background info
    CONSTRAINT unique_content UNIQUE (content)
);

-- Create an HNSW index for efficient similarity search
CREATE INDEX IF NOT EXISTS memories_embedding_idx ON memories USING hnsw (embedding vector_cosine_ops);

-- Function to match memories based on vector similarity
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
    1 - (memories.embedding <=> query_embedding) AS similarity
  FROM memories
  WHERE 1 - (memories.embedding <=> query_embedding) > match_threshold
  ORDER BY memories.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Enable RLS
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;

-- Policy to allow the service role to do everything
CREATE POLICY "Allow service role full access" ON memories
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');
