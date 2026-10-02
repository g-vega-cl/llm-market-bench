-- GIN index for high-speed English full-text search on memories content
CREATE INDEX IF NOT EXISTS memories_content_fts_idx 
ON public.memories 
USING gin (to_tsvector('english', content));
