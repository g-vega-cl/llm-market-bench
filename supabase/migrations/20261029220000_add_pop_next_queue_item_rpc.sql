-- Migration: Add status 'answered' and atomic pop_next_queue_item RPC function
-- Allows autonomous trader runner to atomically pop pending audience questions (FIFO)
-- using SELECT ... FOR UPDATE SKIP LOCKED without race conditions.

ALTER TABLE public.agent_chat_queue DROP CONSTRAINT IF EXISTS agent_chat_queue_status_check;
ALTER TABLE public.agent_chat_queue ADD CONSTRAINT agent_chat_queue_status_check
    CHECK (status IN ('pending', 'injected', 'answered', 'archived', 'rejected'));

CREATE OR REPLACE FUNCTION public.pop_next_queue_item()
RETURNS SETOF public.agent_chat_queue
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    UPDATE public.agent_chat_queue
    SET status = 'injected',
        injected_turn_at = NOW()
    WHERE id = (
        SELECT id
        FROM public.agent_chat_queue
        WHERE status = 'pending'
        ORDER BY created_at ASC
        FOR UPDATE SKIP LOCKED
        LIMIT 1
    )
    RETURNING *;
END;
$$;

-- Explicit grants
GRANT EXECUTE ON FUNCTION public.pop_next_queue_item() TO authenticated, service_role;
