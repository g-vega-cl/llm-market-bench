-- Migration for Polish Pass: Step 9
-- Adds the match_concepts RPC for semantic merging in concept_metrics.

-- RPC for concept similarity search
CREATE OR REPLACE FUNCTION match_concepts(
    query_embedding VECTOR(768),
    match_threshold FLOAT,
    match_count INT
) RETURNS TABLE (
    id UUID,
    concept_name TEXT,
    mention_count INTEGER,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.concept_name,
        c.mention_count,
        1 - (c.concept_vector <=> query_embedding) AS similarity
    FROM concept_metrics c
    WHERE 1 - (c.concept_vector <=> query_embedding) >= match_threshold
    ORDER BY c.concept_vector <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;
