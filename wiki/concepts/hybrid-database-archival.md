---
tags: [database, postgresql, supabase, archival, cloudflare, docker]
category: concept
---

# Hybrid Database Archival

The platform uses a hybrid storage model to operate within cloud database free tiers while retaining massive historical datasets for research, auditing, and backtesting.

## Overview

Supabase serves as the hot, low-latency transactional database for live trading state and UI rendering, while an on-premise PostgreSQL instance backed by local multi-terabyte storage acts as the cold analytical archive.

```
┌─────────────────────────────────────────────────────────────┐
│                       SUPABASE (Cloud)                      │
│                  Hot / Live / Web Serving                   │
│  - portfolios / holdings / performance                      │
│  - current active consensus & decisions                     │
│  - recent llm_reasoning_logs (<= 14 days)                   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                      [ Python Engine / Web ]
                               │
┌──────────────────────────────┴──────────────────────────────┐
│                  LOCAL ARCHIVE STACK (Docker)                │
│              Cold / Bulk / Analytical / Storage             │
│  - llm_reasoning_logs (> 14 days)                           │
│  - historical market logs / backtest results                │
└──────────────────────────────▲──────────────────────────────┘
                               │
                   Cloudflare Tunnel (cloudflared)
                   (https://benchify-archive-db.clvg.uk)
```

## Architecture & Components

### 1. Hot Tier (Supabase PostgreSQL)
- Keeps live state: `portfolios`, `portfolio_positions`, `portfolio_performance`, `trades`, and `decisions`.
- Retains only the most recent **14 days** of verbose trace logs (`llm_reasoning_logs`).
- Keeps the cloud database footprint well within the 500MB free quota (~239 MB).

### 2. Cold Archive Tier (Local Docker Postgres + PostgREST)
- Managed via `docker/archive/docker-compose.yml` with persistent storage on local disk (`/mnt/docker-data`).
- Runs `ankane/pgvector` on port 5433 for direct local SQL connections.
- Runs `postgrest/postgrest` on port 3001 to expose a native HTTP REST API matching Supabase's API format.

### 3. Remote Ingress via Cloudflare Tunnel
- Exposes the local PostgREST instance via Cloudflare Tunnel at `https://benchify-archive-db.clvg.uk`.
- Provides TLS encryption, zero router port forwarding, and seamless remote connectivity for web frontend and CI runners.

### 4. Transparent Fallback Querying
- The frontend client (`fetchReasoningLogs` in `apps/web/src/features/reasoning/api/fetch-reasoning-logs.ts`) queries Supabase first.
- When paginating past the hot 14-day window (`cursor > 14 days`), the client automatically queries the archive endpoint without requiring user intervention or broken UI states.

## Archival Workflow

The script `apps/engine/scripts/archive_reasoning_logs.py` handles the data migration:
1. Streams records older than `cutoff_days` (default 14) from Supabase.
2. Upserts records into the local archive PostgREST endpoint.
3. Deletes migrated records from Supabase by primary key ID.
4. Physical disk space on Supabase is reclaimed by executing `VACUUM FULL public.llm_reasoning_logs;` in the Supabase SQL editor.

## Maintenance & Operational Lifecycle

### System Restarts & Boot Persistence
- **Docker Containers**: Both `market-bench-archive-db` and `market-bench-archive-postgrest` use `restart: unless-stopped`. Since `docker.service` is enabled at boot, Docker automatically spins up both services within seconds of rebooting.
- **Cloudflare Tunnel**: `cloudflared.service` is enabled via systemd, ensuring `https://benchify-archive-db.clvg.uk` connects automatically upon boot.

### Health Verification
- Check container status: `docker ps --filter "name=market-bench-archive"`
- Check public HTTPS endpoint: `curl -s "https://benchify-archive-db.clvg.uk/llm_reasoning_logs?limit=1"`

### On-Demand Archival Procedure
When Supabase storage grows near limits:
1. Run migration: `./apps/engine/.venv/bin/python3 apps/engine/scripts/archive_reasoning_logs.py --cutoff-days 14`
2. Run SQL in Supabase Dashboard: `VACUUM FULL public.llm_reasoning_logs;`

## Related

- [[entities/database]] — Core database schema and entity reference
- [[entities/engine]] — Engine pipeline and data logging
- [[concepts/performance-auditing-strategy]] — Zero-load query optimization
