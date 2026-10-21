---
tags: [security, secrets, docker, jwt, postgrest, tooling]
category: entity
---

# Rotate Secrets

`docker/archive/rotate_secrets.py` is a utility script that generates cryptographically secure secrets for the self-hosted archive database stack and mints the HS256 PostgREST JWTs that Supabase SDKs expect. It exists so that no plaintext credentials live in `docker-compose.yml` — the compose file references environment variables, and this script populates the `.env` files that supply them.

## What It Does

`rotate_all()` performs three steps in one pass:

1. **Generate secrets** — `secrets.token_hex(32)` for the PostgREST JWT secret and `secrets.token_urlsafe(32)` for the Postgres password.
2. **Mint tokens** — `generate_token(secret, role)` signs an HS256 JWT with `role`, `iss: "supabase"`, `iat`, and a 10-year `exp`. Two tokens are produced: `anon` and `service_role`.
3. **Write env files** — `update_env_file()` rewrites or appends keys in place (regex-matched per key, preserving unrelated lines) across:
   - `docker/archive/.env` — `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `PGRST_JWT_SECRET`, `PGRST_OPENAPI_SERVER_PROXY_URI`
   - `apps/engine/.env` — `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`, `SUPABASE_PROJECT_URL`
   - `apps/web/.env` — `SUPABASE_ANON_KEY`, `VITE_SUPABASE_ANON_KEY`, `SUPABASE_URL`, `VITE_SUPABASE_URL`

Engine and web env files are only touched if they already exist.

## Token Format

`generate_token` produces tokens compatible with the Supabase JS/Python clients and PostgREST's `PGRST_JWT_SECRET` validation. The `iss` claim is fixed to `supabase` and the role claim drives PostgREST's `PGRST_DB_ANON_ROLE` behavior.

## Compose Integration

`docker/archive/docker-compose.yml` consumes these values via `${VAR}` interpolation with sensible defaults for non-secret fields:

- `POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}` (no default — must be supplied)
- `PGRST_JWT_SECRET: ${PGRST_JWT_SECRET}` (no default — must be supplied)
- `PGRST_DB_URI` composes the connection string from `${POSTGRES_USER}`, `${POSTGRES_PASSWORD}`, `${POSTGRES_DB}`

`docker/archive/.env.example` documents the required keys with empty secret values.

## Tests

`apps/engine/tests/test_docker_archive_secrets.py` guards against regressions:

- Asserts the compose file contains no hardcoded JWT secret or Postgres password and references `${PGRST_JWT_SECRET}` / `${POSTGRES_PASSWORD}`.
- Round-trips `generate_token` output through `jwt.decode` to confirm HS256 signing and the `role` / `iss` claims.

## Related

- [[concepts/env-based-secrets]]
- [[entities/database]]
- [[concepts/hybrid-database-archival]]
