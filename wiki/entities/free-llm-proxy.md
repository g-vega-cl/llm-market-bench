---
tags: [llm, proxy, inference, router, failover, docker]
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

## Model Resolution & Provider Targeting

`Router.resolve_model_for_provider(provider_id, requested_model, available_models)` maps the client-supplied `model` string onto a concrete provider model ID. Resolution order:

1. **Virtual alias** — if `requested_model` is a key in `virtual_aliases` (e.g. `free-auto`), its pattern list is used.
2. **Default/auto** — `default`, `auto`, or the empty string resolve to the `free-auto` patterns.
3. **Exact preferred pattern** — if `requested_model` appears verbatim in the provider's `preferred_patterns`, it is returned unchanged (no catalog lookup required).
4. **Exact catalog match** — if `requested_model` is present in the discovered `available_models`, it is returned unchanged.
5. **Explicit `provider/model` prefix** — the prefix is stripped and the remainder matched against the catalog. The literal `openrouter/free` is special-cased and returned as-is (it is a real OpenRouter model ID, not a `provider/model` pair, so it must never be stripped down to `free`).
6. **Pattern fallback** — otherwise the first `preferred_patterns` entry matching the catalog is used.

`Router.get_candidate_chain(requested_model)` builds the ordered provider attempt list. A request is treated as **explicitly provider-targeted** when either:

- the model contains a `/` and the prefix matches an active provider ID (e.g. `groq/qwen...`), or
- the model string itself equals an active provider ID (e.g. `openrouter`).

In both cases that provider is moved to the front of the candidate chain, with normal tiered failover behind it.

### OpenRouter Free Tier

The `openrouter` provider declares `preferred_patterns: ["openrouter/free", "*:free"]`, so `openrouter/free` is prioritized ahead of generic `:free`-suffixed models when OpenRouter is selected. Requests for `model: "openrouter/free"` route directly to OpenRouter with the model ID passed through unchanged, even before the dynamic catalog has been populated.

---

## Virtual Model Aliases

| Alias | Description | Target Family |
| :--- | :--- | :--- |
| `free-auto` (default) | Best overall model across the healthy active pool | 120B / 70B / Flash / 27B |
| `free-fast` | Sub-second ultra-low latency models | 20B / 8B / Flash-Lite / 7B |
| `free-reasoning` | Deep reasoning / thinking models | R1, reasoning, Flint, Beam |
| Any custom name | Pass-through if present on the provider, otherwise falls back to `free-auto` patterns | — |
| `provider/model` | Explicitly targets a provider first, with normal failover behind it | — |
| `provider` (bare) | Bare active provider ID (e.g. `openrouter`) targets that provider first | — |
| `openrouter/free` | Passed through verbatim to OpenRouter; never stripped to `free` | — |

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

### Docker (recommended — auto-starts on boot)

The proxy ships a self-contained container stack:

- **`apps/free_llm_proxy/Dockerfile`** — `python:3.13-slim` base with pinned dependencies (`fastapi==0.115.11`, `uvicorn[standard]==0.34.0`, `httpx==0.28.1`, `pydantic==2.10.6`, `python-dotenv==1.0.1`). Code is copied to `/app/apps/free_llm_proxy` to preserve the package layout, exposes port `8086`, and launches `python main.py --host 0.0.0.0 --port 8086`.
- **`apps/free_llm_proxy/docker-compose.yml`** — service `free-llm-proxy`, `restart: unless-stopped`, binds `127.0.0.1:8086:8086` (loopback only), loads `.env` via `env_file`, mounts `./data` to persist the SQLite audit database, and caps memory at `128M`.
- **`apps/free_llm_proxy/.dockerignore`** — excludes `__pycache__`, compiled bytecode, `.pytest_cache`, `tests/`, `.env`, and `data/*.db` from the build context.

```bash
# Start via Docker (auto-starts on boot with 128MB limit)
docker compose -f apps/free_llm_proxy/docker-compose.yml up -d

# Follow logs
docker compose -f apps/free_llm_proxy/docker-compose.yml logs -f
```

### Local Python

```bash
# Or start the local server directly
./apps/engine/.venv/bin/python3 apps/free_llm_proxy/main.py [--port 8086] [--host 0.0.0.0] [--reload]
```

### Tests

```bash
# Hermetic test suite (no external network; loopback only)
./apps/engine/.venv/bin/python3 -m pytest apps/free_llm_proxy/tests/test_proxy.py -v
```

The test suite covers master-key auth rejection, the unauthenticated health probe, circuit-breaker tripping on 429, alias resolution against live catalogs, automatic failover when the primary returns 429, SSE streaming pass-through, metrics/models endpoints, and SQLite audit logging. It also verifies `openrouter/free` resolution (never stripped to `free` when the catalog is empty, prioritized as the first OpenRouter preferred pattern, and routed to OpenRouter as the first candidate) and end-to-end chat completion routing for `model: "openrouter/free"`. A `conftest.py` socket guard raises on any non-loopback connection, keeping the suite hermetic per [[concepts/test-coverage]].

---

## Pi Assistant Integration

Pi (`/home/cv/.local/bin/pi`) integrates directly with Free LLM Proxy by configuring a custom OpenAI-compatible provider in `~/.pi/agent/models.json`:

```json
{
  "providers": {
    "free-llm": {
      "baseUrl": "http://127.0.0.1:8086/v1",
      "api": "openai-completions",
      "apiKey": "sk-free-bf2f76aa1b930536367c26c52d86f677814c1fa7e9ac263c",
      "compat": {
        "supportsDeveloperRole": false,
        "supportsReasoningEffort": false
      },
      "models": [
        {
          "id": "free-auto",
          "name": "Free LLM: Auto (Best Available)",
          "input": ["text"],
          "contextWindow": 128000,
          "maxTokens": 8192,
          "type": "chat"
        },
        {
          "id": "free-fast",
          "name": "Free LLM: Fast (Low Latency)",
          "input": ["text"],
          "contextWindow": 32768,
          "maxTokens": 4096,
          "type": "chat"
        },
        {
          "id": "free-reasoning",
          "name": "Free LLM: Reasoning (Thinking/R1)",
          "input": ["text"],
          "contextWindow": 65536,
          "maxTokens": 8192,
          "type": "chat"
        }
      ]
    }
  }
}
```

### Usage in Pi

- **Interactive Cycle**: Press `Ctrl+P` in the Pi TUI to cycle between local quantized models (`strata`, `orcarouter`) and the free models (`free-auto`, `free-fast`, `free-reasoning`).
- **Direct CLI Invocation**:
  ```bash
  pi --provider free-llm --model free-auto "Help refactor this function"
  ```
- **Tool Calling Support**: `free-auto` prioritizes tool-capable models (e.g. Groq Llama 3.3 70B, Google Gemini Flash) so Pi's built-in coding tools (`read`, `bash`, `edit`, `write`) function seamlessly. Structured array message formats (`content: [{"type": "text", ...}]`) are natively parsed in `apps/free_llm_proxy/models.py`.

---

## Related

- [[concepts/tool-first-agency]]
- [[entities/tool-registry]]
- [[entities/wiki-linter]]
- [[concepts/test-coverage]]
- [[concepts/env-based-secrets]]
