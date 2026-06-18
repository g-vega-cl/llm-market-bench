-- Migration: Add secure function to fetch referenced newsletter snapshots
-- Description: Creates a SECURITY DEFINER function to retrieve newsletter snippets that are linked to a promoted memory.
-- Rationale: Protects the newsletter_snapshots table from arbitrary public queries while allowing users to see the news context behind their memories.

CREATE OR REPLACE FUNCTION public.get_referenced_newsletter_snapshots(target_source_ids TEXT[])
RETURNS TABLE (
    source_id TEXT,
    sender TEXT,
    subject TEXT,
    content TEXT,
    date TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT ns.source_id, ns.sender, ns.subject, ns.content, ns.date
    FROM public.newsletter_snapshots ns
    WHERE ns.source_id = ANY(target_source_ids)
      AND EXISTS (
          SELECT 1 FROM public.memories m
          WHERE 
            -- Check if source_id is inside metadata.source_ids JSON array
            (m.metadata->'source_ids' IS NOT NULL AND m.metadata->'source_ids' ? ns.source_id)
            OR
            -- Check if source_id is exactly equal to metadata.source_id (if single string)
            (m.metadata->>'source_id' = ns.source_id)
      );
END;
$$;

-- Grant execution to public roles
GRANT EXECUTE ON FUNCTION public.get_referenced_newsletter_snapshots(TEXT[]) TO anon, authenticated;
