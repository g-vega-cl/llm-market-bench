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
│  └── POST/PATCH/DELETE ─▶ Primary Workstation (:3001)  │
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
     - `live-spy-trader` (`market-bench-live-spy-trader`): The 24/7 autonomous intraday SPY trading daemon (see [[entities/live-agent-trader]]). Built from `docker/archive/Dockerfile.trader` (context `../..`), `restart: unless-stopped`, 1G memory limit. Runs `python3 -m trading.runner --loop`, executing a 5-minute reasoning turn via local Strata (Tier 1) with fallback to the centralized CLVG proxy (Tier 2), routing paper orders to Alpaca. An `extra_hosts` entry maps `primary-workstation` to `${PRIMARY_WORKSTATION_IP:-127.0.0.1}` so Tailscale routes Strata inference to the developer machine via `http://primary-workstation:3001/strata/v1`. Environment includes `STRATA_BASE_URL`, `FREE_LLM_PROXY_URL`, Supabase keys, Alpaca keys, and `FMP_API_KEY` / `MASSIVE_API_KEY` / `POLYGON_API_KEY`.

2. **Smart Method-Based Nginx Routing (`docker/archive/nginx.secondary.conf`)**:
   - Reads (`GET`, `HEAD`, `OPTIONS`) route immediately to the local PostgREST replica without network latency.
   - Writes (`POST`, `PUT`, `PATCH`, `DELETE`) route upstream over Tailscale to the Primary Workstation.
   - If the Primary Workstation is unreachable, writes fail gracefully with an HTTP 503 JSON payload (`{"error": "Primary write node unavailable; read-replica is active"}`), while 100% of the web app's read dashboards remain operational.

3. **Replication & Lifecycle Automation**:
   - `docker/archive/setup_primary_replication.sh`: Idempotently provisions the `replicator` role, reserves `minipc_standby_slot`, and configures `pg_hba.conf` on the primary.
   - `docker/archive/bootstrap_replica.sh`: Streams initial `pg_basebackup` with `-R` (standby mode) into `archive_pgdata_replica` on the MiniPC.
   - `docker/archive/promote_to_primary.sh`: Fast manual 1-command promotion script that triggers `pg_ctl promote` and configures Nginx for local write processing during disaster recovery.
   - `docker/archive/deploy_secondary.sh`: Host-to-host synchronization script using `rsync` and SSH to deploy compose stacks, the trader engine (`apps/engine/`, excluding `.venv`, `tests`, `market`, caches), `packages/config/`, `Dockerfile.trader`, and environment files (`docker/archive/.env`, `apps/engine/.env`, `apps/free_llm_proxy/.env`) to `cv-minipc@minipc`. After syncing it sets execute permissions on the remote helper scripts and instructs the operator to bring the stack up with `docker compose -f docker-compose.secondary.yml up -d --build`.

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
