-- Migration for Step 9: Trend & Concept Momentum Analysis
-- Creates the concept_metrics table for tracking semantic trends.

CREATE TABLE IF NOT EXISTS public.concept_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    concept_name TEXT UNIQUE NOT NULL,
    concept_vector VECTOR(768) NOT NULL,
    mention_count INTEGER DEFAULT 1,
    first_mention_at TIMESTAMPTZ DEFAULT now(),
    last_mention_at TIMESTAMPTZ DEFAULT now(),
    velocity_score FLOAT DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Enable RLS
ALTER TABLE public.concept_metrics ENABLE ROW LEVEL SECURITY;

-- Allow read access to all users
CREATE POLICY "Allow public read access on concept_metrics"
    ON public.concept_metrics FOR SELECT
    USING (true);

-- Allow service role to manage
CREATE POLICY "Allow service role to manage concept_metrics"
    ON public.concept_metrics FOR ALL
    USING (true)
    WITH CHECK (true);

-- Index for vector similarity search
CREATE INDEX IF NOT EXISTS concept_metrics_vector_idx ON public.concept_metrics
    USING hnsw (concept_vector vector_cosine_ops);

-- RPC for vector similarity search with time filter
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
    WHERE m.created_at >= min_time
      AND 1 - (m.embedding <=> query_embedding) >= match_threshold
    ORDER BY m.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;
