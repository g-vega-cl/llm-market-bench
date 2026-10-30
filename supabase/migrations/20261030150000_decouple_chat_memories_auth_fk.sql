-- Decouple chat_memories.user_id foreign key from local auth.users stub table
-- Auth is managed by Supabase Cloud while data lives in the self-hosted PostgreSQL archive DB.
-- Dropping the foreign key allows cloud-authenticated user UUIDs to be stored directly.

ALTER TABLE public.chat_memories
DROP CONSTRAINT IF EXISTS chat_memories_user_id_fkey;
