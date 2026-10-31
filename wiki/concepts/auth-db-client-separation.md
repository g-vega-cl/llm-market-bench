---
tags: [architecture, auth, database, supabase, postgrest, security]
category: concept
---

# Auth / DB Client Separation

The web app splits its Supabase access into two strictly separated client families: an **Auth client** that talks to Supabase Cloud (which runs the Auth service) and a **DB client** that talks to the self-hosted PostgREST archive database (which holds all application data but runs no Auth service). This decoupling prevents the `PGRST125` auth-misrouting failure that occurs when an Auth call is sent to the PostgREST archive endpoint, and keeps cloud authentication independent from local data storage.

## Why It Exists

The platform migrated its data layer to a self-hosted PostgreSQL + PostgREST stack at `https://benchify-archive-db.clvg.uk` (see [[concepts/hybrid-database-archival]]). That stack serves the Data API but does **not** run GoTrue/Auth. Authentication (password login, Google OAuth, session cookies) remains on Supabase Cloud. A single shared client cannot serve both: pointing `auth.getUser()` at the archive DB returns `PGRST125` (invalid path), and pointing data queries at the cloud project reintroduces egress and quota coupling.

## The Two Client Families

### Auth client — Supabase Cloud only

- **`apps/web/src/lib/auth.ts`** — `getAuthServerClient()` builds a `createServerClient` (from `@supabase/ssr`) with cookie `getAll`/`setAll` wired to TanStack Start's `getCookies`/`setCookie`. Reads `SUPABASE_AUTH_URL` (falling back to `SUPABASE_URL`) and `SUPABASE_AUTH_ANON_KEY` (falling back to `SUPABASE_ANON_KEY`).
- **`apps/web/src/lib/auth-client.ts`** — `getAuthBrowserClient()` builds a `createBrowserClient` from `VITE_SUPABASE_AUTH_URL` (falling back to `VITE_SUPABASE_URL`) and `VITE_SUPABASE_AUTH_ANON_KEY` (falling back to `VITE_SUPABASE_ANON_KEY`).
- **`assertValidAuthUrl(url, envVarName)`** — shared guard that throws if the URL is missing or contains `benchify-archive-db`, with an explicit message telling the operator to point the variable at the Supabase Cloud project URL (`https://<project-ref>.supabase.co`).

Auth consumers: `__root.tsx` (`fetchUser`), `_authed.tsx` (`loginFn`), `auth.callback.tsx` (`exchangeCodeFn`), `logout.tsx` (`logoutFn`), `signup.tsx` (`signupFn`), `shared/auth/components/Auth.tsx` (Google OAuth), and the chat server's `auth.getUser()` calls.

### DB client — self-hosted PostgREST archive only

- **`apps/web/src/lib/db.ts`** — `getDbServerClient()`, `getDbAdminClient()`, and `getDbBrowserClient()` build a plain `createClient` (from `@supabase/supabase-js`) against the archive DB.
  - URL: `ARCHIVE_DB_URL` / `VITE_ARCHIVE_DB_URL`, defaulting to `DEFAULT_ARCHIVE_DB_URL = 'https://benchify-archive-db.clvg.uk'`.
  - Regular reads: `getDbServerClient()` uses `ARCHIVE_DB_ANON_KEY` / `VITE_ARCHIVE_DB_ANON_KEY` (falling back to `SUPABASE_ANON_KEY` / `VITE_SUPABASE_ANON_KEY`).
  - Privileged mutations: `getDbAdminClient()` is an explicit dedicated export that strictly requires `ARCHIVE_DB_SERVICE_ROLE_KEY` (falling back to `SUPABASE_SERVICE_ROLE_KEY`) and throws an explicit configuration error rather than falling back to anon. (An explicit export prevents bundler parameter-folding optimizations from dead-code eliminating service_role branches in SSR bundles).
  - In development and SSR builds, `ensureEnvLoaded()` leverages Node 24 `process.loadEnvFile` and `apps/web/vite.config.ts` calls `loadEnv(mode, process.cwd(), '')` to populate `process.env` so server functions access `ARCHIVE_DB_SERVICE_ROLE_KEY` without baking non-`VITE_` variables into client-side bundles.
  - All clients are **stateless**: `auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false }`. The DB client never manages sessions — auth is the Auth client's job.
  - Throws `Missing Archive DB credentials (ARCHIVE_DB_ANON_KEY)` / `(VITE_ARCHIVE_DB_ANON_KEY)` when the key is absent.

DB consumers: every data fetcher across `features/*/api/*` (portfolios, memories, reasoning, today, leaderboard, market-overview, cause-and-effect, earnings, generated-newsletters, daily-predictions, ai-predictions, home barometer/tape/agent-queue, concepts, audits, autoresearch). Privileged server functions like `handleSubmitAgentQueueQuestion` and `chat-server.ts` use `getDbAdminClient()` for schema introspection, `agent_chat_queue` inserts, and `chat_memories` writes/reads.

## Client Call-Site Architecture

Data fetchers import `getDbServerClient` / `getDbBrowserClient` from `apps/web/src/lib/db.ts`. Auth routes import `getAuthServerClient` from `apps/web/src/lib/auth.ts` and `getAuthBrowserClient` from `apps/web/src/lib/auth-client.ts`. Tests mock `~/lib/db` and `~/lib/auth` separately.

## Environment Variables

| Purpose | Server | Browser (Vite) |
| :--- | :--- | :--- |
| Archive DB URL | `ARCHIVE_DB_URL` | `VITE_ARCHIVE_DB_URL` |
| Archive DB anon key | `ARCHIVE_DB_ANON_KEY` | `VITE_ARCHIVE_DB_ANON_KEY` |
| Archive DB service role | `ARCHIVE_DB_SERVICE_ROLE_KEY` | — (never exposed to browser) |
| Supabase Cloud Auth URL | `SUPABASE_AUTH_URL` | `VITE_SUPABASE_AUTH_URL` |
| Supabase Cloud Auth anon key | `SUPABASE_AUTH_ANON_KEY` | `VITE_SUPABASE_AUTH_ANON_KEY` |

[[entities/rotate-secrets]] writes the `ARCHIVE_DB_*` keys into `apps/web/.env` and never overwrites the `SUPABASE_AUTH_*` cloud credentials. See [[concepts/env-based-secrets]].

## Data-Model Consequence

Because Auth lives in Supabase Cloud while data tables live in the archive DB, foreign keys to the local `auth.users` stub table were dropped for user-associated tables:
- `chat_memories.user_id` (migration `20261030150000_decouple_chat_memories_auth_fk.sql`), where cloud-authenticated user UUIDs are stored directly and RLS policies enforce `auth.uid() = user_id`. See [[concepts/private-memory-vault]].
- `agent_chat_queue.user_id` (migration `20261030190000_decouple_agent_chat_queue_auth_fk.sql`), allowing audience question submissions to store cloud user UUIDs directly. Queue mutations are locked down to `service_role` execution via TanStack Start server functions after validating session cookies with Supabase Cloud Auth. See [[entities/live-agent-trader]].

## Related

- [[entities/web-app]] — the dashboard that consumes both client families
- [[concepts/hybrid-database-archival]] — the self-hosted PostgREST stack the DB client targets
- [[concepts/private-memory-vault]] — user-isolated theses whose FK was decoupled
- [[concepts/env-based-secrets]] — env-var injection rules
- [[entities/rotate-secrets]] — secret generation and env-file writes
- [[entities/database]] — schema and RLS details
