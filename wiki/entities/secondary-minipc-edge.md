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
   - Manages six coordinated edge services on the MiniPC:
     - `archive-db-replica` (`ankane/pgvector:latest`): Read-only standby PostgreSQL instance attached to physical replication slot `minipc_standby_slot`.
     - `archive-postgrest` (`postgrest/postgrest:latest`): Connected locally to `archive-db-replica:5432` for fast read querying.
     - `archive-proxy` (`nginx:alpine`): Nginx reverse proxy listening on port 3001, executing method-based routing and upstream failover.
     - `free-llm-proxy` (`archive-free-llm-proxy:latest`): OpenAI-compatible model-agnostic proxy listening on port 8086 with automated circuit-breaking, caller attribution ("Who": client IP, User-Agent) and intent telemetry ("Why": purpose, prompt preview). Includes `extra_hosts` mapping `primary-workstation` to `${PRIMARY_WORKSTATION_IP:-127.0.0.1}` and routes Strata inference via `http://primary-workstation:3001/strata/v1` over Tailscale.
     - `live-spy-trader` (`market-bench-live-spy-trader`): The 24/7 autonomous intraday SPY trading daemon (see [[entities/live-agent-trader]]). Built from `docker/archive/Dockerfile.trader` (context `../..`), `restart: unless-stopped`, 1G memory limit. Runs `python3 -m trading.runner --loop`, executing a 5-minute reasoning turn (plus decoupled 5m Q&A and 30m news synthesis) directly against the centralized CLVG free proxy (`FREE_LLM_PROXY_URL=https://llm.clvg.uk/v1`, `FREE_PROXY_MODEL=auto-go`) without touching Strata, routing paper orders to Alpaca. **Credentials are loaded via `env_file: ../../apps/engine/.env`** (Supabase keys, Alpaca keys, `FREE_PROXY_MASTER_KEY`, `FMP_API_KEY` / `MASSIVE_API_KEY` / `POLYGON_API_KEY`), while non-secret routing values (`STRATA_BASE_URL`, `FREE_LLM_PROXY_URL`, `FREE_PROXY_MODEL`) are set inline under `environment`. Exposes host port `8090:8090` for the intraday tape SSE server (see below).
     - `recipe-worker` (`market-bench-recipe-worker`): Recipe Studio 30-minute market-hours scheduler, 5-minute Turbo enqueuer, and 5-second queue poller (`python3 -m recipes.runner --loop`). Built from `docker/archive/Dockerfile.trader` with a **512M memory limit** (raised from 256M to accommodate async job processing, batched queue inserts, and live news sync) and the same `apps/engine/.env` + `STRATA_BASE_URL` / `FREE_LLM_PROXY_URL` routing. Syncs live news into `recipe_news_corpus`, enqueues `live_turn` jobs for Push v2 `is_live = true` recipes every 30 minutes during US market hours (`09:30`–`16:00 ET`, plus 5-minute Turbo ticks for active `turbo_expires_at` windows), and drains each lane independently: `live_turn` via bounded `asyncio.gather` concurrency (`RECIPE_LIVE_CONCURRENCY`, default `10`) and `backtest` via counted concurrency (`RECIPE_BACKTEST_CONCURRENCY`, default `3`). See [[entities/recipe-studio]].

   On the **primary** workstation, `docker/archive/docker-compose.yml` gives the `archive-proxy` service an `extra_hosts` entry mapping `minipc` to `${MINIPC_IP:-100.119.63.53}` (the MiniPC's Tailscale address), so the primary Nginx can reach the MiniPC-hosted trader SSE server by hostname without relying on Docker's embedded DNS.

2. **Smart Method-Based Nginx Routing (`docker/archive/nginx.secondary.conf`)**:
   - Reads (`GET`, `HEAD`, `OPTIONS`) route immediately to the local PostgREST replica without network latency.
   - Writes (`POST`, `PUT`, `PATCH`, `DELETE`) route upstream over Tailscale to the Primary Workstation.
   - If the Primary Workstation is unreachable, writes fail gracefully with an HTTP 503 JSON payload (`{"error": "Primary write node unavailable; read-replica is active"}`), while 100% of the web app's read dashboards remain operational.
   - **Enlarged response-header buffers**: `proxy_buffer_size 128k`, `proxy_buffers 4 256k`, `proxy_busy_buffers_size 256k`, and `large_client_header_buffers 4 32k` sit in the `http {}` block (mirrored in `docker/archive/nginx.conf` and `docker/archive/nginx.web.conf`). PostgREST/JWT responses and SSR pages exceed nginx's 4k/8k defaults, which otherwise surfaces as `upstream sent too big header` and a **502 for authenticated clients only** — anonymous traffic keeps getting 200. A replica whose `archive-proxy` container predates this block is the classic stale-inode symptom documented under [[entities/self-hosted-web-deployment]].
   - **Intraday Tape SSE Route**: `location /api/tape/` proxies to the `live-spy-trader` container on port 8090 with `proxy_http_version 1.1`, `proxy_buffering off`, `proxy_cache off`, `chunked_transfer_encoding off`, and `proxy_read_timeout 3600s` so Server-Sent Events stream unbuffered through the edge gateway and Cloudflare tunnel. On the MiniPC the upstream is resolved dynamically via `resolver 127.0.0.11 valid=10s ipv6=off;` (Docker's embedded DNS) with a variable `set $tape_backend http://live-spy-trader:8090;` and `proxy_pass $tape_backend$request_uri;`, so Nginx re-resolves the container IP every 10 seconds instead of caching a stale address at startup (which would 502 after a container rebuild). In the primary `docker/archive/nginx.conf`, the same route uses a static upstream `proxy_pass http://minipc:8090;` — the `minipc` hostname is resolved through the `archive-proxy` service's `extra_hosts` entry (`${MINIPC_IP:-100.119.63.53}`) over Tailscale — so both Cloudflare Anycast ingress connectors stream identical live tape.

3. **Replication & Lifecycle Automation**:
   - `docker/archive/setup_primary_replication.sh`: Idempotently provisions the `replicator` role, reserves `minipc_standby_slot`, and configures `pg_hba.conf` on the primary.
   - `docker/archive/bootstrap_replica.sh`: Streams initial `pg_basebackup` with `-R` (standby mode) into `archive_pgdata_replica` on the MiniPC.
   - `docker/archive/promote_to_primary.sh`: Fast manual 1-command promotion script that triggers `pg_ctl promote`, polls `pg_is_in_recovery` until the server is genuinely read-write (no fixed sleep), rewrites `nginx.secondary.conf` to route every method to the local replica, rebinds the proxy through `ensure_proxy_config.sh` (validate → recreate → assert, because the single-file bind mount ignores `nginx -s reload`), writes the `.promoted` sentinel, and only then prints `Failover Complete!`. **Every gate fails closed.** The standby check uses `docker inspect --format '{{.State.Running}}'` rather than a name grep, and the recovery state is a `case` over `t`/`f`/anything-else — an unreadable value aborts instead of being treated as "already primary". The routing rewrite is asserted after the `sed`s: `grep -q 'default local_read_backend'` must succeed and at most one `primary_write_backend` reference may remain (the now-unused `upstream` block), otherwise the script exits before the sentinel/rebind and tells the operator to fix `nginx.secondary.conf` by hand. The sentinel is written *before* the rebind so even a failed rebind cannot be reverted by a later deploy, and the rebind failure message names the sentinel explicitly. Any failed step exits non-zero, so a half-finished failover is never reported as success.
   - `docker/archive/deploy_secondary.sh`: Host-to-host synchronization and automated deployment script using `rsync` and SSH, printing six numbered steps (`[1/6]` SSH reachability → `[6/6]` read-health verification). It deploys compose stacks, the trader engine (`apps/engine/`, excluding `.venv`, `tests`, `market`, caches), `packages/config/`, `Dockerfile.trader`, `ensure_proxy_config.sh`, and environment files (`docker/archive/.env`, `apps/engine/.env`, `apps/free_llm_proxy/.env`) to `cv-minipc@minipc`. Routing config is synced **only while the MiniPC is not promoted**, and that check fails closed: when `test -f .promoted` returns non-1 (ssh 255, DNS or Tailscale blip) the script prints `cannot determine failover state ... refusing to sync nginx.secondary.conf` and exits 1, because a blind sync could revert a live failover. When the sentinel exists it prints a warning and skips `nginx.secondary.conf`, so a routine deploy cannot silently revert a live failover to standby routing. Immediately after synchronization, step 5 runs `ensure_proxy_config.sh --validate-only` **before** `docker compose up -d --build` (so compose's own recreate can never be the first consumer of an unparsed config), then the full `ensure_proxy_config.sh` rebind guard on `archive-proxy`, then restarts `archive-postgrest` to force-reload the PostgREST schema cache (necessary because physical PostgreSQL replication does not propagate `NOTIFY` events). Step 6 verifies local read health (`curl http://localhost:3001/rest/v1/`) and **aborts the deploy with exit 1** on failure — the replica being up but not serving reads is not a warning, it is a failed deploy.

## Intraday Tape Streaming Service

The `live-spy-trader` container hosts a lightweight asyncio SSE server (`apps/engine/trading/tape_stream.py`) on port 8090, decoupled from the 5-minute LLM reasoning turn:

- **`TapeBroadcaster`** — in-memory pub/sub broker holding the rolling 60-minute bar window, latest technicals, and a set of subscriber queues.
- **`TapeHttpServer`** — pure `asyncio.start_server` HTTP/1.1 server exposing `/api/tape/health` (JSON status with client and bar counts) and `/api/tape/stream` (Server-Sent Events). Connections receive an immediate `snapshot` event, then `bar` delta events as 1-minute candles form, with 15-second keepalive pings.
- **`run_tape_poller_loop`** — polls Alpaca 1-minute bars every 10 seconds during regular market hours, publishes to the broadcaster, and updates the newest `market_feeling` row's `trades_summary` (`bars`, `bars_count`, `technicals`) via `update_latest_tape_in_db` without touching agent LLM analysis fields. Pre-seeds state from database on startup so initial SSE client connections immediately receive the rolling 60-minute window.
- **Nginx + Cloudflare** — the `/api/tape/` location streams unbuffered through the edge proxy and Cloudflare tunnel to the browser's `useLiveTapeStream` hook (see [[entities/live-agent-trader]]).

## Operational Workflows

> [!NOTE]
> **Tailscale SSH Authentication**: SSH/rsync to `cv-minipc@minipc` runs over Tailscale SSH (outside the terminal sandbox) and fails if a Tailscale check-mode browser login is pending. Check with `ssh -o BatchMode=yes cv-minipc@minipc true`; if authentication is required, have the operator run `ssh cv-minipc@minipc` manually to complete the Tailscale auth URL before invoking `deploy_secondary.sh`.

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

The script exits 0 only when three gates pass: the standby reports `pg_is_in_recovery = false`, the routing rewrite verifiably landed (`default local_read_backend` present, at most one `primary_write_backend` reference left, i.e. the now-unused upstream block), and the running `archive-proxy` container is verified to serve that rewritten file. An unreadable recovery state aborts rather than being treated as "already primary", and a crash-looping proxy is refused rather than recreated blind. The split-brain probe is advisory only — it resolves `primary-workstation` **inside the proxy container** with `getent hosts` (the name is an `extra_hosts` alias, not a host-level name) and then curls the resolved IP from the host on `:3001`, warning if the workstation still answers. If the name does not resolve at all it prints a `NOTE ... split-brain check skipped`; either way it never changes the exit code. Promotion leaves `docker/archive/.promoted` behind (git-ignored); that sentinel is what makes the state survive the next `deploy_secondary.sh`.

**Demotion is manual and one-way by design.** Once the workstation is healthy again, run these four steps in order — the order matters, because steps 1-2 are the ones that stop you having two writable primaries:

```bash
# 1. stop the MiniPC write surface
docker compose -f docker-compose.secondary.yml stop archive-postgrest

# 2. demote + re-sync the data (both discard failover-era writes — export first)
#    either pg_rewind against the recovered primary, or bootstrap_replica.sh, which
#    wipes /var/lib/postgresql/data inside the volume before pg_basebackup
./bootstrap_replica.sh

# 3. clear the failover sentinel so deploys may sync routing again
rm -f ~/llm-market-bench/docker/archive/.promoted

# 4. from the workstation: restore standby routing + rebind the proxy
./docker/archive/deploy_secondary.sh cv-minipc@minipc
```

No `demote.sh` exists yet; the sequence is deliberately operator-run.

## Related

- [[entities/database]]
- [[entities/free-llm-proxy]]
- [[entities/live-agent-trader]]
- [[entities/recipe-studio]]
- [[entities/rotate-secrets]]
- [[entities/self-hosted-web-deployment]]
- [[concepts/hybrid-database-archival]]
