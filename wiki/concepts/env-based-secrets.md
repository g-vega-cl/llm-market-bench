---
tags: [security, secrets, configuration, docker, twelve-factor]
category: concept
---

# Env-Based Secrets

The project keeps credentials out of version control by treating them as environment variables injected at runtime, rather than literals embedded in configuration files. This applies to the self-hosted archive database stack (`docker/archive/`) and the Supabase credentials consumed by the engine and web app.

## The Rule

No secret value — database password, JWT signing secret, service-role key — may appear as a literal in a committed file. Configuration files reference variables; a `.env` file (git-ignored) supplies the values; a `.env.example` documents the required keys with empty placeholders.

## How It Is Applied

- **Compose interpolation** — `docker/archive/docker-compose.yml` uses `${POSTGRES_PASSWORD}` and `${PGRST_JWT_SECRET}` with no defaults for secrets (so a missing value fails loudly), and `${VAR:-default}` for non-secret fields like `POSTGRES_DB` and the OpenAPI proxy URI.
- **Template** — `docker/archive/.env.example` lists every required key with blank secret values.
- **Rotation** — [[entities/rotate-secrets]] generates fresh secrets and mints matching PostgREST JWTs, then writes them into the `.env` files for the archive stack, engine, and web app in one pass.
- **Regression guard** — `apps/engine/tests/test_docker_archive_secrets.py` fails the build if a known leaked secret reappears in the compose file or if the `${...}` references are removed.

## Why It Matters

Secrets committed to a repo are effectively permanent — they persist in git history even after removal. Env-based injection plus a rotation utility means a leaked value can be replaced by re-running the rotation script and redeploying, without editing tracked files. The test suite enforces the invariant so a future edit cannot silently reintroduce a hardcoded credential.

## Related

- [[entities/rotate-secrets]]
- [[entities/database]]
- [[concepts/auditability]]
