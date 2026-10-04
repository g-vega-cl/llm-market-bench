---
tags: [concept, database, archival, postgres, supabase]
category: concept
---

# Hybrid Database Archival

The platform splits persistence between Supabase (hot transactional path) and a self-hosted Postgres archive (cold analytical path). This keeps Supabase storage quota consumption low while retaining full auditability of tool execution and analytical history.

## Architecture

Supabase serves as the hot, low-latency transactional database for live trading data, while a local archive Postgres instance absorbs high-volume analytical and audit records.

### 1. Supabase (Hot Path)

- Hosts live trading tables (`trades`, `portfolio_positions`, `daily_predictions`, etc.) with RLS enforcement.
- Uses pgvector for semantic search over memories and newsletters.
- Storage quota is preserved by offloading high-volume audit and analytical writes.

### 2. Local Archive Postgres (Cold Path)

- Managed via `docker/archive/docker-compose.yml` with persistent storage on local disk (`/mnt/docker-data`).
- Runs `ankane/pgvector` on port 5433 for direct local SQL connections.
- Runs `postgrest/postgrest` on port 3001 to expose a native HTTP REST API matching Supabase's API format.
- Exposes `tool_execution_logs` for non-blocking audit logging of analytical and macro suite tool calls across all phases (volatility, valuation, screening, research, and daily predictor macro context) via [[entities/tool-audit]], with zero Supabase storage quota consumption.

### 3. Remote Ingress via Cloudflare Tunnel

- The archive PostgREST endpoint is exposed remotely through a Cloudflare Tunnel (`https://benchify-archive-db.clvg.uk`), allowing the engine to write audit records from anywhere without opening inbound ports.

## Related

- [[entities/tool-audit]] — The audit logging layer that writes to the archive
- [[entities/database]] — The Supabase schema and migrations
- [[entities/daily-market-predictor]] — A Phase 4 consumer of archive-backed auditing
