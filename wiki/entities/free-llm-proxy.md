---
tags: [llm, proxy, inference, router, failover]
category: entity
---

# Free LLM Proxy

A model-agnostic, OpenAI-compatible proxy server located at `apps/free_llm_proxy` that pools permanent free-tier LLM inference providers into a single resilient endpoint. It features dynamic model catalog discovery, tiered round-robin load balancing, circuit-breaker cooldowns on rate limits, and full token usage logging.

---

## Architecture & Lifecycle

The proxy binds by default to `http://0.0.0.0:8086` and accepts standard `POST /v1/chat/completions` requests with master key authentication (`Authorization: Bearer <FREE_PROXY_MASTER_KEY>`).

```text
[Chat App / IDE / Engine Task]
                 │  POST /v1/chat/completions
                 ▼
       ┌──────────────────────┐
       │     FastAPI App      │ (apps/free_llm_proxy/server.py)
       │ (Master Key Auth)    │
       └──────────┬───────────┘
                  │
                  ▼
       ┌──────────────────────┐
       │    Model Resolver    │ (free-auto, free-fast, free-reasoning,
       │  (discovery.py)      │  or dynamic provider models)
       └──────────┬───────────┘
                  │
                  ▼
       ┌─────────────────────────────────────────────────────────────┐
       │                      Router & Failover                      │
       │                                                             │
       │  Tier 1: [Groq] ⇄ [Gemini] ⇄ [Kilo Code] (Round-Robin)      │
       │           │ 429 / 5xx / Timeout                             │
       │           ▼ (Trip Circuit Breaker)                          │
       │  Tier 2: [OVHcloud] ⇄ [OpenRouter] ⇄ [NVIDIA NIM]          │
       └──────────────────────────────┬──────────────────────────────┘
                                      │
                                      ▼
                       ┌─────────────────────────────┐
                       │       Audit Database        │
                       │ (data/free_llm_proxy.db)    │
                       │ - Latency & token metrics   │
                       │ - Failover trace history    │
                       └─────────────────────────────┘
```

---

## Key Components

- **Dynamic Catalog Discovery (`apps/free_llm_proxy/discovery.py`)**: Queries each active provider's `GET /models` endpoint at runtime. Avoids hardcoded model IDs so provider version rollouts (e.g. `qwen3.8-27b`, `gpt-oss-120b`) work automatically without code edits. Results are cached per provider (`ModelDiscovery`, default 3600s TTL) and matched against prioritized `fnmatch` patterns.
- **Circuit Breaker (`apps/free_llm_proxy/circuit_breaker.py`)**: Reacts to HTTP 429 rate limits or repeated 5xx errors by placing the failed provider into cooldown (respecting `Retry-After` if sent). A 429 trips the breaker immediately; two consecutive 5xx errors trip it. `record_success` resets the consecutive-failure counter, and `get_status_overview` exposes per-provider health, cooldown remaining, failure count, and rate-limit hit count.
- **Tiered Router (`apps/free_llm_proxy/router.py`)**: Distributes traffic across Tier 1 providers using round-robin counters to balance free-tier request limits. Healthy providers are tried before cooling-down ones; cooling providers are used only as a last resort when no healthy candidate remains. An explicit `provider/model` prefix in the request moves that provider to the front of the chain.
- **Audit Database (`apps/free_llm_proxy/db.py`)**: Persists call traces, prompt tokens, completion tokens, latency, and failover chains to a local SQLite database (`data/free_llm_proxy.db`). `get_metrics()` aggregates total/successful requests, success rate, token totals, average latency, per-provider stats, and the 10 most recent calls.
- **Streaming & SSE (`apps/free_llm_proxy/client.py`)**: Streams `text/event-stream` chunks directly to chat clients with pre-flight failover protection — the connection is probed first so an initial 429/5xx fails over before any chunk is yielded.
- **Provider Registry (`apps/free_llm_proxy/providers.json`)**: Declarative provider definitions (`base_url`, `env_key`, `tier`, `requires_auth`, `preferred_patterns`, optional `extra_headers`) plus the virtual alias pattern map. Providers with `requires_auth: false` (Kilo Code, OVHcloud) are active with zero keys; keyed providers activate automatically when their env var is present.

---

## Virtual Model Aliases

| Alias | Description | Target Family |
| :--- | :--- | :--- |
| `free-auto` (default) | Best overall model across the healthy active pool | 120B / 70B / Flash / 27B |
| `free-fast` | Sub-second ultra-low latency models | 20B / 8B / Flash-Lite / 7B |
| `free-reasoning` | Deep reasoning / thinking models | R1, reasoning, Flint, Beam |
| Any custom name | Pass-through if present on the provider, otherwise falls back to `free-auto` patterns | — |
| `provider/model` | Explicitly targets a provider first, with normal failover behind it | — |

---

## Endpoints

| Endpoint | Method | Auth | Description |
| :--- | :--- | :--- | :--- |
| `/v1/chat/completions` | `POST` | Bearer Token | Standard OpenAI chat completion (streaming + non-streaming) |
| `/v1/models` | `GET` | Bearer Token | Discovered live models and virtual aliases |
| `/v1/metrics` (alias `/stats`) | `GET` | Bearer Token | Total requests, token counts, latency, per-provider stats, and circuit breaker status |
| `/health` | `GET` | None | Service readiness and active provider list |

---

## Configuration

Environment variables (loaded from `apps/free_llm_proxy/.env`, falling back to `apps/engine/.env`):

| Variable | Default | Meaning |
| :--- | :--- | :--- |
| `PORT` | `8086` | Listen port |
| `HOST` | `127.0.0.1` | Bind host |
| `FREE_PROXY_MASTER_KEY` | `sk-free-proxy-secret-key-12345` | Bearer token clients must present |
| `DEFAULT_COOLDOWN_SECONDS` | `60` | Circuit-breaker cooldown when no `Retry-After` is sent |
| `MAX_FAILOVER_RETRIES` | `4` | Failover retry budget |
| `SQLITE_DB_PATH` | `data/free_llm_proxy.db` | Audit database location (`:memory:` supported for tests) |
| `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `NVIDIA_API_KEY` | unset | Provider credentials; unset providers are simply excluded from the active pool |

---

## Running & Testing

```bash
# Start via Docker (auto-starts on boot with 128MB limit)
docker compose -f apps/free_llm_proxy/docker-compose.yml up -d

# Or start the local server directly
./apps/engine/.venv/bin/python3 apps/free_llm_proxy/main.py [--port 8086] [--host 0.0.0.0] [--reload]

# Hermetic test suite (no external network; loopback only)
./apps/engine/.venv/bin/python3 -m pytest apps/free_llm_proxy/tests/test_proxy.py -v
```

The test suite covers master-key auth rejection, the unauthenticated health probe, circuit-breaker tripping on 429, alias resolution against live catalogs, automatic failover when the primary returns 429, SSE streaming pass-through, metrics/models endpoints, and SQLite audit logging. A `conftest.py` socket guard raises on any non-loopback connection, keeping the suite hermetic per [[concepts/test-coverage]].

---

## Related

- [[concepts/tool-first-agency]]
- [[entities/tool-registry]]
- [[entities/wiki-linter]]
- [[concepts/test-coverage]]
