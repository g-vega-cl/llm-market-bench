---
tags: [infrastructure, minipc, edge, database, replication, failover, tailscale]
category: entity
---

# Secondary MiniPC Edge Gateway & Database Replica

The secondary MiniPC server (`cv-minipc@minipc`) acts as a 24/7 dedicated edge gateway, PostgreSQL streaming read-replica, and reverse proxy for the platform. Connected to the primary workstation (AMD Ryzen 9 7950X) over a Tailscale WireGuard mesh network, this node isolates read traffic and public ingress from local workstation reboots and heavy autoresearch workloads.

## Architectural Topology

```text
┌────────────────────────────────────────────────────────┐
│ Client Traffic (Web App / Supabase SDK / Cloudflare)   │
└───────────────────────────┬────────────────────────────┘
                            │ (HTTPS Ingress)
                            ▼
┌────────────────────────────────────────────────────────┐
│ MiniPC Edge Gateway (:3001)                            │
│  ├── GET/HEAD/OPTIONS ──▶ Local Read-Replica (:3000)   │
│  ├── POST/PATCH/DELETE ─▶ Primary Workstation (:3001)  │
│  └── /api/tape/* ───────▶ live-spy-trader SSE (:8090)  │
└─────────────┬───────────────────────────┬──────────────┘
              │                           │
       (Local Read <1ms)           (Tailscale Mesh)
              ▼                           ▼
┌──────────────────────────┐   ┌──────────────────────────┐
│ PostgreSQL Standby       │   │ Primary Workstation DB   │
│ (archive-db-replica)     │◀──│ (archive-db RW)          │
└──────────────────────────┘   └──────────────────────────┘
```

## Core Components

1. **`docker/archive/docker-compose.secondary.yml`**:
   - Manages five coordinated edge services on the MiniPC:
     - `archive-db-replica` (`ankane/pgvector:latest`): Read-only standby PostgreSQL instance attached to physical replication slot `minipc_standby_slot`.
     - `archive-postgrest` (`postgrest/postgrest:latest`): Connected locally to `archive-db-replica:5432` for fast read querying.
     - `archive-proxy` (`nginx:alpine`): Nginx reverse proxy listening on port 3001, executing method-based routing and upstream failover.
     - `free-llm-proxy` (`archive-free-llm-proxy:latest`): OpenAI-compatible model-agnostic proxy listening on port 8086 with automated circuit-breaking, caller attribution ("Who": client IP, User-Agent) and intent telemetry ("Why": purpose, prompt preview). Includes `extra_hosts` mapping `primary-workstation` to `${PRIMARY_WORKSTATION_IP:-127.0.0.1}` and routes Strata inference via `http://primary-workstation:3001/strata/v1` over Tailscale.
     - `live-spy-trader` (`market-bench-live-spy-trader`): The 24/7 autonomous intraday SPY trading daemon (see [[entities/live-agent-trader]]). Built from `docker/archive/Dockerfile.trader` (context `../..`), `restart: unless-stopped`, 1G memory limit. Runs `python3 -m trading.runner --loop`, executing a 5-minute reasoning turn via local Strata (Tier 1) with fallback to the centralized CLVG proxy (Tier 2), routing paper orders to Alpaca. An `extra_hosts` entry maps `primary-workstation` to `${PRIMARY_WORKSTATION_IP:-127.0.0.1}` so Tailscale routes Strata inference to the developer machine via `http://primary-workstation:3001/strata/v1`. **Credentials are loaded via `env_file: ../../apps/engine/.env`** (Supabase keys, Alpaca keys, `FMP_API_KEY` / `MASSIVE_API_KEY` / `POLYGON_API_KEY`), while only non-secret routing values (`STRATA_BASE_URL`, `FREE_LLM_PROXY_URL`) are set inline under `environment`. Exposes host port `8090:8090` for the intraday tape SSE server (see below).

2. **Smart Method-Based Nginx Routing (`docker/archive/nginx.secondary.conf`)**:
   - Reads (`GET`, `HEAD`, `OPTIONS`) route immediately to the local PostgREST replica without network latency.
   - Writes (`POST`, `PUT`, `PATCH`, `DELETE`) route upstream over Tailscale to the Primary Workstation.
   - If the Primary Workstation is unreachable, writes fail gracefully with an HTTP 503 JSON payload (`{"error": "Primary write node unavailable; read-replica is active"}`), while 100% of the web app's read dashboards remain operational.
   - **Intraday Tape SSE Route**: `location /api/tape/` proxies to the `live-spy-trader` container on port 8090 with `proxy_http_version 1.1`, `proxy_buffering off`, `proxy_cache off`, `chunked_transfer_encoding off`, and `proxy_read_timeout 3600s` so Server-Sent Events stream unbuffered through the edge gateway and Cloudflare tunnel. The upstream is resolved dynamically via `resolver 127.0.0.11 valid=10s ipv6=off;` (Docker's embedded DNS) with a variable `set $tape_backend http://live-spy-trader:8090;` and `proxy_pass $tape_backend$request_uri;`, so Nginx re-resolves the container IP every 10 seconds instead of caching a stale address at startup (which would 502 after a container rebuild). The same route is mirrored in the primary `docker/archive/nginx.conf`.

3. **Replication & Lifecycle Automation**:
   - `docker/archive/setup_primary_replication.sh`: Idempotently provisions the `replicator` role, reserves `minipc_standby_slot`, and configures `pg_hba.conf` on the primary.
   - `docker/archive/bootstrap_replica.sh`: Streams initial `pg_basebackup` with `-R` (standby mode) into `archive_pgdata_replica` on the MiniPC.
   - `docker/archive/promote_to_primary.sh`: Fast manual 1-command promotion script that triggers `pg_ctl promote` and configures Nginx for local write processing during disaster recovery.
   - `docker/archive/deploy_secondary.sh`: Host-to-host synchronization and automated deployment script using `rsync` and SSH. Deploys compose stacks, the trader engine (`apps/engine/`, excluding `.venv`, `tests`, `market`, caches), `packages/config/`, `Dockerfile.trader`, and environment files (`docker/archive/.env`, `apps/engine/.env`, `apps/free_llm_proxy/.env`) to `cv-minipc@minipc`. Immediately after synchronization, step 5 automatically rebuilds and launches the Docker containers on the MiniPC (`docker compose -f docker-compose.secondary.yml up -d --build`) so services are live without requiring manual operator intervention.

## Intraday Tape Streaming Service

The `live-spy-trader` container hosts a lightweight asyncio SSE server (`apps/engine/trading/tape_stream.py`) on port 8090, decoupled from the 5-minute LLM reasoning turn:

- **`TapeBroadcaster`** — in-memory pub/sub broker holding the rolling 60-minute bar window, latest technicals, and a set of subscriber queues.
- **`TapeHttpServer`** — pure `asyncio.start_server` HTTP/1.1 server exposing `/api/tape/health` (JSON status with client and bar counts) and `/api/tape/stream` (Server-Sent Events). Connections receive an immediate `snapshot` event, then `bar` delta events as 1-minute candles form, with 15-second keepalive pings.
- **`run_tape_poller_loop`** — polls Alpaca 1-minute bars every 20 seconds during regular market hours, publishes to the broadcaster, and updates the newest `market_feeling` row's `trades_summary` (`bars`, `bars_count`, `technicals`) via `update_latest_tape_in_db` without touching agent LLM analysis fields.
- **Nginx + Cloudflare** — the `/api/tape/` location streams unbuffered through the edge proxy and Cloudflare tunnel to the browser's `useLiveTapeStream` hook (see [[entities/live-agent-trader]]).

## Operational Workflows

### 1. Initial Setup
On the primary workstation:
```bash
./docker/archive/setup_primary_replication.sh
./docker/archive/deploy_secondary.sh cv-minipc@minipc
```

On the MiniPC:
```bash
ssh cv-minipc@minipc
cd ~/llm-market-bench/docker/archive && ./bootstrap_replica.sh
```

### 2. Dual-Connector Active-Active Cloudflare Tunnel Topology
Both machines run `cloudflared` concurrently as system services attached to tunnel `fedora-home` (`0031a4f9-6ae8-4cd0-9ead-12ede0447e3e`):
- **Fedora Big PC**: Primary connector handling writes and direct reads.
- **MiniPC Server**: Secondary connector handling local replica reads and forwarding writes to Fedora.
Cloudflare Anycast automatically balances traffic between both connectors. If Fedora reboots or goes offline, Cloudflare seamlessly routes 100% of edge traffic to MiniPC with zero downtime.

### 3. Emergency Failover
If the primary workstation suffers a prolonged outage:
```bash
ssh cv-minipc@minipc
cd ~/llm-market-bench/docker/archive && ./promote_to_primary.sh
```

## Related

- [[entities/database]]
- [[entities/free-llm-proxy]]
- [[entities/live-agent-trader]]
- [[entities/rotate-secrets]]
- [[concepts/hybrid-database-archival]]
