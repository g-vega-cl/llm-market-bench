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

## Public Ingress (Cloudflare Tunnel)

The stack is exposed securely via Cloudflare Tunnel (`cloudflared`) routed to `http://localhost:3001`:

- Public URL: `https://benchify-archive-db.clvg.uk`
- Client SDKs connect seamlessly using standard Supabase configuration:
  - `SUPABASE_PROJECT_URL=https://benchify-archive-db.clvg.uk`
  - `SUPABASE_SERVICE_ROLE_KEY=<HS256 JWT with role "service_role">`
  - `SUPABASE_ANON_KEY=<HS256 JWT with role "anon">`
