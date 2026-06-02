-- Migration to add get_memory_chain RPC for fast recursive traversal of memory hierarchies.
-- Resolves N+1 database roundtrips on memory chain detail page.

CREATE OR REPLACE FUNCTION public.get_memory_chain(target_id UUID)
RETURNS SETOF public.memories
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
WITH RECURSIVE memory_ancestors AS (
    -- Anchor: start from the target memory
    SELECT * FROM public.memories WHERE id = target_id
    UNION
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
    UNION
    -- Recursive: find all child memories
    SELECT m.* FROM public.memories m
    INNER JOIN memory_descendants md ON m.parent_id = md.id
)
SELECT DISTINCT * FROM memory_descendants;
$$;

-- Grant execute permissions to standard roles for PostGrest / Supabase API
GRANT EXECUTE ON FUNCTION public.get_memory_chain(UUID) TO anon, authenticated, service_role;
