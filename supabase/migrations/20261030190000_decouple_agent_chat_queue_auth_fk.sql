-- Decouple agent_chat_queue.user_id foreign key from local auth.users stub table
-- Auth is managed by Supabase Cloud while data lives in the self-hosted PostgreSQL archive DB.
-- Dropping the foreign key allows cloud-authenticated user UUIDs to be stored directly.

ALTER TABLE public.agent_chat_queue
DROP CONSTRAINT IF EXISTS agent_chat_queue_user_id_fkey;

-- Restrict queue insertion strictly to server-side validated requests (service_role)
-- Preventing unauthenticated or direct PostgREST client injection
DROP POLICY IF EXISTS "Allow public insert on agent_chat_queue" ON public.agent_chat_queue;
REVOKE INSERT ON public.agent_chat_queue FROM anon;

-- Explicit grants
GRANT SELECT ON public.agent_chat_queue TO anon, authenticated;
GRANT ALL ON public.agent_chat_queue TO service_role;
