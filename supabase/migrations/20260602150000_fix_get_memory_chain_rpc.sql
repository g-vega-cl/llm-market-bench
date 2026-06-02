-- Migration to fix get_memory_chain RPC for non-hashable vector columns.
-- Replaces recursive UNION with UNION ALL, resolving pgvector hashing constraint.

CREATE OR REPLACE FUNCTION public.get_memory_chain(target_id UUID)
RETURNS SETOF public.memories
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
WITH RECURSIVE memory_ancestors AS (
    -- Anchor: start from the target memory
    SELECT * FROM public.memories WHERE id = target_id
    UNION ALL
    -- Recursive: find parent memories
    SELECT m.* FROM public.memories m
    INNER JOIN memory_ancestors ma ON m.id = ma.parent_id
),
root_memory AS (
    -- Find the root memory (the oldest ancestor)
    SELECT * FROM memory_ancestors
    WHERE parent_id IS NULL OR parent_id NOT IN (SELECT id FROM memory_ancestors)
    LIMIT 1
),
memory_descendants AS (
    -- Anchor: start from the root memory
    SELECT * FROM root_memory
    UNION ALL
    -- Recursive: find all child memories
    SELECT m.* FROM public.memories m
    INNER JOIN memory_descendants md ON m.parent_id = md.id
)
-- Deduplicate by matching IDs against the base memories table (avoids hashing vectors)
SELECT * FROM public.memories
WHERE id IN (SELECT id FROM memory_descendants);
$$;

-- Grant execute permissions to standard roles for PostGrest / Supabase API
GRANT EXECUTE ON FUNCTION public.get_memory_chain(UUID) TO anon, authenticated, service_role;
