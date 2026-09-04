-- Create dedicated chat_memories table for user-curated research theses
-- Strictly isolated from public benchmark memories and automated engine pipelines

CREATE TABLE IF NOT EXISTS public.chat_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    ticker TEXT,
    thesis TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    importance_score INT DEFAULT 7 CHECK (importance_score BETWEEN 1 AND 10),
    source_query TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indices for fast user lookups, ticker queries, and timeline sorting
CREATE INDEX IF NOT EXISTS idx_chat_memories_user_id ON public.chat_memories (user_id);
CREATE INDEX IF NOT EXISTS idx_chat_memories_user_ticker ON public.chat_memories (user_id, ticker);
CREATE INDEX IF NOT EXISTS idx_chat_memories_user_created ON public.chat_memories (user_id, created_at DESC);

-- Enable Row Level Security (RLS)
ALTER TABLE public.chat_memories ENABLE ROW LEVEL SECURITY;

-- RLS: Users can only read their own private chat memories
CREATE POLICY "Users can only read own chat memories"
ON public.chat_memories FOR SELECT
USING (auth.uid() = user_id);

-- RLS: Users can only insert their own chat memories
CREATE POLICY "Users can only insert own chat memories"
ON public.chat_memories FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- RLS: Users can only update their own chat memories
CREATE POLICY "Users can only update own chat memories"
ON public.chat_memories FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- RLS: Users can only delete their own chat memories
CREATE POLICY "Users can only delete own chat memories"
ON public.chat_memories FOR DELETE
USING (auth.uid() = user_id);

-- Explicit grants following the convention in [[concepts/supabase-grant-convention]]
GRANT SELECT, INSERT, UPDATE, DELETE ON public.chat_memories TO authenticated;
GRANT ALL ON public.chat_memories TO service_role;
