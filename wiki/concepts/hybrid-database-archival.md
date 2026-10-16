---
tags: [concept, database, archival, postgres, supabase]
category: concept
---

# Hybrid Database Archival & Self-Hosted PostgREST Stack

The platform operates on a unified self-hosted PostgreSQL database with pgvector, fronted by PostgREST and an Nginx reverse proxy exposed through a Cloudflare Zero Trust Tunnel. Originally designed as a cold analytical archive alongside cloud-hosted Supabase, the stack now serves as the primary database backend for local engines, GitHub Actions CI/CD workflows, and production website server-side rendering (`https://www.benchify.dev`), completely eliminating cloud database storage and egress quotas.

## Architecture Overview

```
                      +---------------------------------------+
                      |  Public Internet / Cloud CI / Web SSR |
                      |    - GitHub Actions Workflows         |
                      |    - Netlify SSR (benchify.dev)       |
                      |    - Remote Engine CLI                |
                      +-------------------+-------------------+
                                          |
                                          | HTTPS (TLS)
                                          v
                      +---------------------------------------+
                      |   Cloudflare Edge Ingress             |
                      |   https://benchify-archive-db.clvg.uk |
                      |   - Cloudflare Tunnel (cloudflared)   |
                      +-------------------+-------------------+
                                          |
                                          | Local Ingress (Port 3001)
                                          v
                      +---------------------------------------+
                      |   Nginx REST Reverse Proxy            |
                      |   (docker/archive/nginx.conf)         |
                      |   - Rewrites /rest/v1/* -> /*         |
                      |   - Strips Supabase prefix            |
                      |   - Preserves CORS, Auth & Range hdrs |
                      +-------------------+-------------------+
                                          |
                                          | HTTP (Port 3000)
                                          v
                      +---------------------------------------+
                      |   PostgREST API Engine                |
                      |   (postgrest/postgrest:latest)        |
                      |   - Validates HS256 JWT signatures    |
                      |   - Maps claims to Postgres roles     |
                      |   - Generates dynamic REST endpoints  |
                      +-------------------+-------------------+
                                          |
                                          | PostgreSQL (Port 5432)
                                          v
                      +---------------------------------------+
                      |   PostgreSQL 16 with pgvector         |
                      |   (ankane/pgvector:latest, port 5433) |
                      |   - Full schema parity (94 migrations)|
                      |   - Row-Level Security (RLS) on tables|
                      |   - Native vector similarity RPCs     |
                      +---------------------------------------+
```

### Components

1. **PostgreSQL 16 with pgvector (`archive-db`)**:
   - Container: `ankane/pgvector:latest`
   - Host Port: `127.0.0.1:5433` (container port 5432)
   - Database: `market_bench_archive`
   - Extensions: `vector`, `uuid-ossp`, `pgcrypto` installed in `extensions` and `public` search paths.
   - Migrations: 100% schema parity with Supabase through `supabase/migrations/*.sql`.

2. **PostgREST Engine (`archive-postgrest`)**:
   - Container: `postgrest/postgrest:latest`
   - Internal Port: `3000` (bridged on Docker network `archive-net`)
   - JWT Secret: Shared HMAC-SHA256 secret (`PGRST_JWT_SECRET`) matching keys issued for client access.
   - Schema: Exposes `public` schema tables and RPC functions.

3. **Nginx Reverse Proxy (`archive-proxy`)**:
   - Container: `nginx:alpine`
   - Host Port: `127.0.0.1:3001`
   - Configuration: `docker/archive/nginx.conf`
   - Crucial Path Translation: Supabase client SDKs (`@supabase/supabase-js`, `supabase-py`) automatically prepend `/rest/v1/` to all API endpoints. Nginx strips `/rest/v1/` and routes requests to the PostgREST root (`/*`) while forwarding all query parameters and authentication headers (`apikey`, `Authorization`, `Prefer`, `Range`).

4. **Cloudflare Tunnel (`cloudflared`)**:
   - Hostname: `benchify-archive-db.clvg.uk`
   - Target: `http://localhost:3001`
   - Provides TLS termination and global ingress without opening router ports or exposing IP addresses.

## Security & Row-Level Security (RLS)

- **Cryptographic JWT Authentication**: All PostgREST endpoints require valid HS256 JWT tokens with role claims. Unauthorized or unauthenticated requests are rejected with `HTTP 401 Unauthorized` (`PGRST301`).
- **Anon Role (`anon`)**: Used by frontend applications (`apps/web` and Netlify). Strictly constrained by PostgreSQL RLS to `SELECT` operations on public benchmark views and tables. Write operations (`INSERT`, `UPDATE`, `DELETE`) fail with permission error `42501`.
- **Service Role (`service_role`)**: Possesses `BYPASSRLS` privileges for automated pipelines, data ingestion, backfilling, and GitHub Actions CI tasks.
- **WAF Best Practices**: Because serverless and CI runners (Netlify AWS instances, GitHub Actions runners) execute server-side API requests, Cloudflare Free "Bot Fight Mode" should be disabled for the domain `clvg.uk` to avoid blocking legitimate server-to-server TLS calls. Standard Cloudflare Rate Limiting rules can be applied if request throttling is required.

## Operational Verification

Verify the entire stack end-to-end using standard CLI tools:

```bash
# 1. Test local proxy health
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3001/rest/v1/

# 2. Test public Cloudflare tunnel endpoint with anon JWT
curl -s -H "apikey: $SUPABASE_ANON_KEY" \
     -H "Authorization: Bearer $SUPABASE_ANON_KEY" \
     "https://benchify-archive-db.clvg.uk/rest/v1/decisions?limit=1"

# 3. Test RPC execution (pgvector match_memories)
curl -s -X POST \
     -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
     -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
     -H "Content-Type: application/json" \
     -d '{"query_embedding": [0.01, 0.02, 0.03], "match_threshold": 0.0, "match_count": 1}' \
     "https://benchify-archive-db.clvg.uk/rest/v1/rpc/match_memories"
```

## Related

- [[entities/database]] — Schema definitions, table roles, and migration history
- [[entities/tool-audit]] — Tool execution audit logging
- [[entities/daily-market-predictor]] — Market prediction pipeline consuming database storage
