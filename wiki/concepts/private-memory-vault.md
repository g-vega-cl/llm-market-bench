---
tags: [memory, user-theses, isolation, rls]
category: concept
---

# Private Memory Vault for User-Curated Theses

A dedicated, user-isolated storage system for promoting assistant answers into structured private market theses. Users can distill a chat exchange into a ticker, thesis, tags, and importance score (1-10), edit the result, and save it to their personal `chat_memories` table. The vault is strictly isolated from the automated engine's public benchmark memories to prevent prompt injection into trading pipelines.

## Workflow

1. **Distillation.** Clicking "Promote to Memory" on any assistant message triggers a server-side call (`distillChatMemoryFn`) that sends the user query and assistant response to DeepSeek with a structured extraction prompt. The result is a JSON object with ticker, thesis, tags, and importance_score.
2. **Review modal.** The user sees a modal prefilled with the distilled fields. They can freely edit the ticker, thesis, tags, and score, add or remove tags, and optionally provide a refinement instruction to re-distill with a different focus.
3. **Save.** On save (`saveChatMemoryFn`), the thesis is written to the `chat_memories` table with the authenticated user's ID. Row-level security ensures users can only access their own records.
4. **Tool access.** The `get_my_saved_theses` tool (registered in the chat tool suite) lets the agent retrieve the user's own saved theses, optionally filtered by ticker. The tool is only available when authenticated and always scoped to `user_id`.

## Isolation Guarantees

- **RLS policies.** Four separate policies (`SELECT`, `INSERT`, `UPDATE`, `DELETE`) enforce `auth.uid() = user_id`.
- **Schema boundary.** The `chat_memories` table is a separate public table with `user_id UUID NOT NULL`. Engine agents query `memories` (the public benchmark table) and never touch `chat_memories`.
- **No cross-contamination.** Automated pipelines, daily predictors, and autoresearch loops operate on `user_id IS NULL` records only.

## Auth / Data Decoupling

Authentication is managed by Supabase Cloud while `chat_memories` lives in the self-hosted PostgreSQL archive DB (see [[concepts/auth-db-client-separation]] and [[concepts/hybrid-database-archival]]). Because the archive DB does not run an Auth service, the `chat_memories.user_id` foreign key to the local `auth.users` stub was dropped in migration `20261030150000_decouple_chat_memories_auth_fk.sql`. Cloud-authenticated user UUIDs are stored directly in `user_id`, and RLS still enforces `auth.uid() = user_id` at the archive DB. The chat server resolves the user via `getAuthServerClient()` (Supabase Cloud) and performs `chat_memories` reads/writes via `getDbServerClient({ useServiceRole: true })` (archive DB).

## Related

- [[entities/investment-chat-gateway]]
- [[entities/database]]
- [[concepts/memory-feedback]]
- [[concepts/auditability]]
- [[concepts/supabase-grant-convention]]
- [[concepts/auth-db-client-separation]]
