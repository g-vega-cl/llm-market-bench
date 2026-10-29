-- Create agent_chat_queue table for audience interaction with the autonomous live trader
CREATE TABLE IF NOT EXISTS public.agent_chat_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    display_name TEXT NOT NULL DEFAULT 'Visitor',
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'injected', 'archived', 'rejected')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    injected_turn_at TIMESTAMPTZ,
    agent_response TEXT
);

-- Indices for queue polling and timeline display
CREATE INDEX IF NOT EXISTS idx_agent_chat_queue_status_created ON public.agent_chat_queue (status, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_agent_chat_queue_created_at ON public.agent_chat_queue (created_at DESC);

-- Enable Row Level Security (RLS)
ALTER TABLE public.agent_chat_queue ENABLE ROW LEVEL SECURITY;

-- Allow public and authenticated users to read queue items
CREATE POLICY "Allow public read on agent_chat_queue"
ON public.agent_chat_queue FOR SELECT
TO public
USING (true);

-- Allow public and authenticated users to submit questions into the queue
CREATE POLICY "Allow public insert on agent_chat_queue"
ON public.agent_chat_queue FOR INSERT
TO public
WITH CHECK (true);

-- Allow service role full administrative access
CREATE POLICY "Allow service role full access on agent_chat_queue"
ON public.agent_chat_queue FOR ALL
TO service_role
USING (true);

-- Explicit grants
GRANT SELECT, INSERT ON public.agent_chat_queue TO anon, authenticated;
GRANT ALL ON public.agent_chat_queue TO service_role;
