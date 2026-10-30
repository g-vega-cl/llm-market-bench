---
tags: [security, secrets, configuration, docker, twelve-factor, netlify]
category: concept
---

The project keeps credentials out of version control by treating them as environment variables injected at runtime, rather than literals embedded in configuration files. This applies to the self-hosted archive database stack (`docker/archive/`), the Supabase credentials consumed by the engine and web app, and the Netlify build environment.

## The Rule

No secret value — database password, JWT signing secret, service-role key — may appear as a literal in a committed file. Configuration files reference variables; a `.env` file (git-ignored) supplies the values; a `.env.example` documents the required keys with empty placeholders.

## How It Is Applied

- **Compose interpolation** — `docker/archive/docker-compose.yml` uses `${POSTGRES_PASSWORD}` and `${PGRST_JWT_SECRET}` with no defaults for secrets (so a missing value fails loudly), and `${VAR:-default}` for non-secret fields like `POSTGRES_DB` and the OpenAPI proxy URI.
- **Template** — `docker/archive/.env.example` lists every required key with blank secret values.
- **Rotation** — [[entities/rotate-secrets]] generates fresh secrets and mints matching PostgREST JWTs, then writes them into the `.env` files for the archive stack, engine, and web app in one pass.
- **Regression guard** — `apps/engine/tests/test_docker_archive_secrets.py` fails the build if a known leaked secret reappears in the compose file or if the `${...}` references are removed.

## Netlify Secrets Scanning

Netlify runs a build-time secret scanner that fails deploys when it detects values matching known secret patterns in the build output or repository. Because this project intentionally references many credential *names* (and ships test fixtures, wiki pages, and docker configs that contain placeholder or example values), the scanner would otherwise produce false positives that block deploys.

`apps/web/netlify.toml` configures the scanner via two `[build.environment]` variables:

- **`SECRETS_SCAN_OMIT_KEYS`** — a comma-separated list of environment-variable *names* the scanner should not treat as leaked secrets. It covers the archive DB and Supabase Auth URL/key pairs (`ARCHIVE_DB_URL`, `VITE_ARCHIVE_DB_URL`, `SUPABASE_AUTH_URL`, `VITE_SUPABASE_AUTH_URL`, `SUPABASE_URL`, `VITE_SUPABASE_URL`, `ARCHIVE_DB_ANON_KEY`, `VITE_ARCHIVE_DB_ANON_KEY`, `SUPABASE_AUTH_ANON_KEY`, `VITE_SUPABASE_AUTH_ANON_KEY`) plus the PostHog public host and project token (`VITE_PUBLIC_POSTHOG_HOST`, `VITE_PUBLIC_POSTHOG_PROJECT_TOKEN`). These are public/anon-tier values or names that legitimately appear in the bundle and config.
- **`SECRETS_SCAN_OMIT_PATHS`** — a comma-separated glob list of paths excluded from scanning: `wiki/**`, `docker/**`, `apps/engine/tests/**`, and `apps/web/src/lib/*.test.ts`. These contain documentation, compose templates, and test fixtures with synthetic placeholder credentials that must not trip the scanner.

This is a false-positive suppression layer, not a relaxation of the rule: real secret *values* still never appear in tracked files, and the omit lists reference only variable names and non-secret paths.

## Auth vs Data Credential Separation

The web app consumes two independent credential sets (see [[concepts/auth-db-client-separation]]):

- **Archive DB (Data API)** — `ARCHIVE_DB_URL`, `ARCHIVE_DB_ANON_KEY`, `ARCHIVE_DB_SERVICE_ROLE_KEY` (server) and `VITE_ARCHIVE_DB_URL`, `VITE_ARCHIVE_DB_ANON_KEY` (browser). These point at the self-hosted PostgREST stack (`https://benchify-archive-db.clvg.uk`).
- **Supabase Cloud (Auth only)** — `SUPABASE_AUTH_URL`, `SUPABASE_AUTH_ANON_KEY` (server) and `VITE_SUPABASE_AUTH_URL`, `VITE_SUPABASE_AUTH_ANON_KEY` (browser). These point at the Supabase Cloud project that runs the Auth service.

[[entities/rotate-secrets]] writes only the `ARCHIVE_DB_*` keys into `apps/web/.env` and never overwrites the `SUPABASE_AUTH_*` cloud credentials. `assertValidAuthUrl` in `apps/web/src/lib/auth-client.ts` rejects any Auth URL containing `benchify-archive-db`, so a misconfigured env var fails loudly instead of silently misrouting auth calls to the PostgREST endpoint (`PGRST125`).

## Why It Matters

Secrets committed to a repo are effectively permanent — they persist in git history even after removal. Env-based injection plus a rotation utility means a leaked value can be replaced by re-running the rotation script and redeploying, without editing tracked files. The test suite enforces the invariant so a future edit cannot silently reintroduce a hardcoded credential, and the Netlify scanner omit lists keep the deploy pipeline green without weakening that guarantee.

## Related

- [[entities/rotate-secrets]]
- [[entities/database]]
- [[concepts/auth-db-client-separation]]
- [[concepts/auditability]]
- [[sources/web-deployment-source]]
