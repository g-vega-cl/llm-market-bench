---
tags: [security, secrets, docker, jwt, postgrest, tooling]
category: entity
---

# Rotate Secrets

`docker/archive/rotate_secrets.py` is a utility script that generates cryptographically secure secrets for the self-hosted archive database stack and mints the HS256 PostgREST JWTs that Supabase SDKs expect. It exists so that no plaintext credentials live in `docker-compose.yml` — the compose file references environment variables, and this script populates the `.env` files that supply them.

## What It Does

`rotate_all()` performs four steps in one pass:

1. **Generate secrets** — `secrets.token_hex(32)` for the PostgREST JWT secret, plus alphanumeric urlsafe tokens for the Postgres password and the streaming-replication password (`REPLICATION_PASSWORD`).
2. **Mint tokens** — `generate_token(secret, role)` signs an HS256 JWT with `role`, `iss: "supabase"`, `iat`, and a 10-year `exp`. Two tokens are produced: `anon` and `service_role`.
3. **Sync database role** — `update_postgres_role_password(password)` executes `ALTER USER postgres WITH PASSWORD` in `market-bench-archive-db` via `docker exec`. Standard PostgreSQL Docker images only apply `POSTGRES_PASSWORD` when creating fresh volumes; existing volumes (`archive_pgdata`) preserve credentials, requiring an explicit SQL update so PostgREST retains connectivity.
4. **Write env files** — `update_env_file()` rewrites or appends keys in place (regex-matched per key, preserving unrelated lines) across:
   - `docker/archive/.env` — `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `PGRST_JWT_SECRET`, `PGRST_OPENAPI_SERVER_PROXY_URI`, and the replication trio `REPLICATION_USER` (`replicator`), `REPLICATION_PASSWORD`, `REPLICATION_SLOT` (`minipc_standby_slot`)
   - `apps/engine/.env` — `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`, `SUPABASE_PROJECT_URL`
   - `apps/web/.env` — `SUPABASE_ANON_KEY`, `VITE_SUPABASE_ANON_KEY`, `SUPABASE_URL`, `VITE_SUPABASE_URL`

Engine and web env files are only touched if they already exist. The returned dict includes `REPLICATION_PASSWORD` alongside the Postgres password, JWT secret, and minted anon/service-role tokens.

## Replication Credentials

The `REPLICATION_*` keys feed the secondary MiniPC edge stack (see [[entities/secondary-minipc-edge]]):

- `REPLICATION_USER` — the `replicator` role created with `REPLICATION LOGIN` by `setup_primary_replication.sh`.
- `REPLICATION_PASSWORD` — the password for that role, consumed by `bootstrap_replica.sh` (`PGPASSWORD`) and by the `archive-db-replica` service in `docker-compose.secondary.yml`.
- `REPLICATION_SLOT` — the physical replication slot name (`minipc_standby_slot`) reserved on the primary.

Rotating secrets therefore also rotates the replication credential; the replica must be re-bootstrapped (or the role password re-synced) after a rotation.

## Security Boundaries

The stack enforces strict credential separation across deployment targets:

- **Frontend / Netlify**: `apps/web` and Netlify must strictly use `VITE_SUPABASE_ANON_KEY` mapped to the `anon` token. Vite compiles `VITE_*` variables directly into public static JavaScript bundles.
- **Backend / Pipelines**: GitHub Actions Secrets and `apps/engine/.env` use `SUPABASE_SERVICE_ROLE_KEY`. In `docker/archive/init.sql`, `service_role` has `BYPASSRLS` privileges for ingestion and analysis pipelines. Leaking this token grants unrestricted write and delete capabilities.
- **Replication**: `REPLICATION_PASSWORD` grants WAL-streaming access to the primary and must never be exposed to the web bundle or committed to git.

## Token Format

`generate_token` produces tokens compatible with the Supabase JS/Python clients and PostgREST's `PGRST_JWT_SECRET` validation. The `iss` claim is fixed to `supabase` and the role claim drives PostgREST's `PGRST_DB_ANON_ROLE` behavior.

## Compose Integration

`docker/archive/docker-compose.yml` consumes these values via `${VAR}` interpolation with sensible defaults for non-secret fields:

- `POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}` (no default — must be supplied)
- `PGRST_JWT_SECRET: ${PGRST_JWT_SECRET}` (no default — must be supplied)
- `PGRST_DB_URI` composes the connection string from `${POSTGRES_USER}`, `${POSTGRES_PASSWORD}`, `${POSTGRES_DB}`
- `BIND_ADDRESS` (default `0.0.0.0`) controls the host bind for the Postgres (`5433`) and Nginx (`3001`) ports, so the primary can accept Tailscale replication and proxy traffic from the MiniPC.

`docker/archive/.env.example` documents the required keys with empty secret values.

## Tests

`apps/engine/tests/test_docker_archive_secrets.py` guards against regressions:

- Asserts the compose file contains no hardcoded JWT secret or Postgres password and references `${PGRST_JWT_SECRET}` / `${POSTGRES_PASSWORD}`.
- Round-trips `generate_token` output through `jwt.decode` to confirm HS256 signing and the `role` / `iss` claims.
- Validates `update_postgres_role_password` docker execution, returncode handling, and `sync_db` behavior.
- Verifies `.gitguardian.yaml` exists and ignores test credential definitions to prevent false positive security detector alerts. All mock password literals in the test suite are annotated with `# ggignore` and use synthetic placeholders.

`apps/engine/tests/test_secondary_cluster_config.py` additionally asserts that `docker-compose.secondary.yml` interpolates `${POSTGRES_PASSWORD}` / `${PGRST_JWT_SECRET}` and contains no literal secrets.

## Related

- [[concepts/env-based-secrets]]
- [[entities/database]]
- [[entities/secondary-minipc-edge]]
- [[concepts/hybrid-database-archival]]
