# Self-Hosted Archive Database Stack

This directory contains the Docker Compose environment, initialization scripts, and Nginx proxy configuration for running the local PostgreSQL + PostgREST database stack.

## Architecture

The stack consists of three coordinated containers on the `archive-net` bridge network:

1. **`archive-db` (`ankane/pgvector:latest`)**:
   - PostgreSQL 16 database running on host port `5433` (container port `5432`).
   - Extensions enabled: `vector`, `uuid-ossp`, `pgcrypto` across `public` and `extensions` schemas.
   - Storage volume: `archive-data` (persisted on host Docker volume).

2. **`archive-postgrest` (`postgrest/postgrest:latest`)**:
   - PostgREST 12 REST API engine running internally on container port `3000`.
   - Connected to `archive-db` via internal Docker network.
   - Requires cryptographically signed HS256 JWT tokens for all requests (`PGRST_JWT_SECRET`).
   - Maps claims to PostgreSQL roles (`service_role`, `anon`) with full Row-Level Security (RLS) enforcement.

3. **`archive-proxy` (`nginx:alpine`)**:
   - Nginx reverse proxy listening on host port `3001`.
   - Provides drop-in compatibility with the `@supabase/supabase-js` and `supabase-py` SDKs by stripping `/rest/v1/` from incoming requests and rewriting to PostgREST root (`/*`).
   - Forwards client headers (`Authorization`, `apikey`, `Prefer`, `Range`, `Content-Profile`).

## Directory Contents

- `docker-compose.yml`: Defines the 3 services, volume, and bridge network.
- `init.sql`: Bootstrap initialization script setting up roles (`anon`, `authenticated`, `service_role`), schemas, and extension paths.
- `nginx.conf`: Nginx configuration implementing URL rewriting and CORS handling.

## Running the Stack

To start or restart the stack in the background:

```bash
docker compose -f docker/archive/docker-compose.yml up -d
```

To view logs:

```bash
docker compose -f docker/archive/docker-compose.yml logs -f
```

To stop the stack:

```bash
docker compose -f docker/archive/docker-compose.yml down
```

## Secondary Edge Server (MiniPC) & Streaming Replica

For 24/7 uptime and edge isolation, a secondary MiniPC (`cv-minipc@minipc`) runs as an edge gateway and streaming read-replica connected to the primary workstation over Tailscale.

### Edge Topology
1. **`archive-db-replica` (`ankane/pgvector:latest`)**:
   - Streaming standby replica receiving WAL records asynchronously via physical replication slot `minipc_standby_slot`.
   - Read-only queries execute locally on MiniPC with `<1ms` latency.
2. **`archive-proxy` (`nginx:alpine` on port `3001`)**:
   - Inspects HTTP methods (`GET`/`HEAD`/`OPTIONS` routed locally to PostgREST; `POST`/`PATCH`/`PUT`/`DELETE` reverse-proxied over Tailscale to the Primary Workstation).
   - If the Primary Workstation is offline or rebooting, all reads continue serving without interruption while mutations return HTTP 503.
3. **`free-llm-proxy` (port `8086`)**:
   - 24/7 model-agnostic failover proxy running alongside on MiniPC.

### Deployment & Operations

1. **Configure Primary for Replication** (run once on primary workstation):
   ```bash
   ./docker/archive/setup_primary_replication.sh
   ```

2. **Sync and Deploy to MiniPC** (run from workstation):
   ```bash
   ./docker/archive/deploy_secondary.sh cv-minipc@minipc
   ```

3. **Bootstrap Replica** (run on MiniPC via SSH):
   ```bash
   cd ~/llm-market-bench/docker/archive && ./bootstrap_replica.sh
   ```

4. **Emergency Failover (1-Command Promotion)** (run on MiniPC if primary is permanently down):
   ```bash
   cd ~/llm-market-bench/docker/archive && ./promote_to_primary.sh
   ```

---

## Public Ingress (Dual-Connector Cloudflare Anycast HA)

The stack is exposed securely via an **Active-Active Dual-Connector Cloudflare Tunnel** running concurrently on both machines:
- **Fedora Big PC** (Primary connector)
- **MiniPC Server** (Secondary edge connector)

Cloudflare Anycast automatically load-balances and routes incoming traffic to the nearest/healthiest connector. If either node reboots or goes offline, traffic routes to the survivor seamlessly with zero DNS propagation delay:

- Public Archive DB API: `https://benchify-archive-db.clvg.uk`
- Public Free LLM Proxy: `https://llm.clvg.uk`
- Client SDKs connect seamlessly using standard Supabase configuration:
  - `SUPABASE_PROJECT_URL=https://benchify-archive-db.clvg.uk`
  - `SUPABASE_SERVICE_ROLE_KEY=<HS256 JWT with role "service_role">`
  - `SUPABASE_ANON_KEY=<HS256 JWT with role "anon">`

## Secret Rotation & Security

The stack uses cryptographically signed HS256 JWTs with a shared secret (`PGRST_JWT_SECRET`). To rotate secrets:

```bash
./apps/engine/.venv/bin/python3 docker/archive/rotate_secrets.py
docker compose -f docker/archive/docker-compose.yml up -d --force-recreate
```

### Important Operational Considerations:

1. **Persistent PostgreSQL Volumes (`archive_pgdata`)**:
   Standard PostgreSQL Docker images only read `POSTGRES_PASSWORD` to create the superuser during initial cluster creation. On existing volumes, changing `POSTGRES_PASSWORD` in `.env` does not alter existing database users. `rotate_secrets.py` automatically executes `ALTER USER postgres WITH PASSWORD ...` if `market-bench-archive-db` is running. If rotated while the container is down, run the alter command manually once started, otherwise PostgREST will fail authentication against PostgreSQL.

2. **Frontend Security Boundary (Netlify vs Backend)**:
   - **Netlify**: `VITE_SUPABASE_ANON_KEY` and `SUPABASE_ANON_KEY` **must only receive the `anon` JWT**. Vite bakes all `VITE_*` environment variables directly into client-side JavaScript bundles served to public browsers.
   - **GitHub Actions Secrets & Engine**: `SUPABASE_SERVICE_ROLE_KEY` receives the `service_role` JWT (which bypasses RLS for background ingestion and analysis jobs). Never expose `service_role` in public frontend configurations.

