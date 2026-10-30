---
tags: [llm, proxy, inference, router, failover, docker]
category: entity
---

# Free LLM Proxy

A model-agnostic, OpenAI-compatible proxy server located at `apps/free_llm_proxy` that pools permanent free-tier LLM inference providers into a single resilient endpoint. It features dynamic model catalog discovery, tiered round-robin load balancing, circuit-breaker cooldowns on rate limits, cloud output-token clamping, and full token usage logging.

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
       │  (discovery.py)      │  strata-auto, auto-strata, strata, or dynamic provider models)
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

- **Dynamic Catalog Discovery (`apps/free_llm_proxy/discovery.py`)**: Queries each active provider's `GET /models` endpoint at runtime. Avoids hardcoded model IDs so provider version rollouts (e.g. `qwen3.8-27b`, `gpt-oss-120b`) work automatically without code edits. Results are cached per provider (`ModelDiscovery`, default 3600s TTL) and matched against prioritized `fnmatch` patterns. Discovery requests use a short connect timeout (`httpx.Timeout(4.0, connect=2.0)`) so an offline provider (e.g. local Strata) fails fast instead of stalling the catalog refresh.
- **Circuit Breaker (`apps/free_llm_proxy/circuit_breaker.py`)**: Reacts to HTTP 429 rate limits or repeated 5xx errors by placing the failed provider into cooldown (respecting `Retry-After` if sent). A 429 trips the breaker immediately; two consecutive 5xx errors trip it. `record_success` resets the consecutive-failure counter, and `get_status_overview` exposes per-provider health, cooldown remaining, failure count, and rate-limit hit count.
- **Tiered Router (`apps/free_llm_proxy/router.py`)**: Distributes traffic across Tier 1 providers using round-robin counters to balance free-tier request limits. Healthy providers are tried before cooling-down ones; cooling providers are used only as a last resort when no healthy candidate remains. An explicit `provider/model` prefix in the request moves that provider to the front of the chain. Providers declaring `enabled_in_auto: false` (such as local Strata) are excluded from the standard auto rotation unless explicitly targeted or opted in via `auto-strata`.
- **Cloud Output-Token Clamping (`apps/free_llm_proxy/server.py`)**: Before dispatch, requests routed to any non-Strata (cloud) provider have `max_tokens` and `max_completion_tokens` clamped down to `CLOUD_MAX_OUTPUT_TOKENS` (default `8192`), because cloud free-tier providers enforce an 8k output ceiling. Strata is exempt and preserves the caller's full budget (e.g. 131,072 tokens).
- **Audit Database (`apps/free_llm_proxy/db.py`)**: Persists call traces, prompt tokens, completion tokens, latency, failover chains, and caller attribution to a local SQLite database (`data/free_llm_proxy.db`). Captures "Who" (`client_ip` via Cloudflare `CF-Connecting-IP`, `X-Forwarded-For`, or socket host, and `user_agent`) and "Why" (`purpose` via `X-Purpose` / `X-Client-Id` and `prompt_preview` containing a 60-character snippet of the user prompt). `get_metrics()` aggregates total/successful requests, success rate, token totals, average latency, per-provider stats, and the 10 most recent calls. Auto-migrates existing tables seamlessly.
- **Streaming & SSE (`apps/free_llm_proxy/client.py`)**: Streams `text/event-stream` chunks directly to chat clients with pre-flight failover protection — the connection is probed first so an initial 429/5xx fails over before any chunk is yielded.
- **Connection Error Resilience (`apps/free_llm_proxy/client.py`)**: `execute_completion` wraps both the non-streaming `POST` and the streaming `build_request`/`send` probe in `try/except httpx.RequestError`. A connection refusal, DNS failure, or connect timeout is converted into a structured `503` response (`{"error": {"message": "Provider connection error: ...", "type": "connection_error"}}`) rather than propagating an unhandled exception. This lets the router cleanly fail over to the next candidate provider (e.g. `strata-auto` falling back to the auto pool when local Strata is offline). The default client uses `httpx.Timeout(60.0, connect=3.0)` so an unreachable provider is detected within 3 seconds.
- **Provider Registry (`apps/free_llm_proxy/providers.json`)**: Declarative provider definitions (`base_url`, `env_key`, `tier`, `requires_auth`, `preferred_patterns`, optional `extra_headers`, optional `enabled_in_auto`) plus the virtual alias pattern map. Providers with `requires_auth: false` (Kilo Code, OVHcloud, local Strata) are active with zero keys; keyed providers activate automatically when their env var is present.

---

## Model Resolution & Provider Targeting

`Router.resolve_model_for_provider(provider_id, requested_model, available_models)` maps the client-supplied `model` string onto a concrete provider model ID. Resolution order:

1. **Local Strata** — when `provider_id == "strata"`, a `strata/<model>` prefix is stripped and matched against the live catalog; otherwise the requested model is used if present in the catalog, else the first live model, else the literal `"strata"`. This lets the proxy target whichever model the local Strata server currently has loaded.
2. **Virtual alias** — if `requested_model` is a key in `virtual_aliases` (e.g. `free-auto`), its pattern list is used.
3. **Default/auto** — `default`, `auto`, or the empty string resolve to the `free-auto` patterns.
4. **Exact preferred pattern** — if `requested_model` appears verbatim in the provider's `preferred_patterns`, it is returned unchanged (no catalog lookup required).
5. **Exact catalog match** — if `requested_model` is present in the discovered `available_models`, it is returned unchanged.
6. **Explicit `provider/model` prefix** — the prefix is stripped and the remainder matched against the catalog. The literal `openrouter/free` is special-cased and returned as-is (it is a real OpenRouter model ID, not a `provider/model` pair, so it must never be stripped down to `free`).
7. **Pattern fallback** — otherwise the first `preferred_patterns` entry matching the catalog is used.

`Router.get_candidate_chain(requested_model)` builds the ordered provider attempt list. A request is treated as **explicitly provider-targeted** when either:

- the model contains a `/` and the prefix matches an active provider ID (e.g. `groq/qwen...`), or
- the model string itself equals an active provider ID (e.g. `openrouter`).

In both cases that provider is moved to the front of the candidate chain, with normal tiered failover behind it.

### Local Strata Targeting

Local Strata (`strata` provider, `base_url` from `STRATA_BASE_URL`, default `http://localhost:8080/v1`) is a Tier 1 provider with `requires_auth: false` and `enabled_in_auto: false`, so it is excluded from the standard `free-auto` rotation. Three aliases control how it participates:

- **`strata-auto`** — Strata is placed first in the candidate chain; if Strata is offline or cooling down, the request fails over cleanly to the normal auto pool.
- **`auto-strata`** — Strata is added into the standard Tier 1 round-robin rotation alongside the cloud providers.
- **`strata`** (and `strata/<model>`) — strict targeting: the candidate chain contains **only** Strata. If Strata is offline the request fails (HTTP 502) with zero silent cloud fallback.

When Strata is in circuit-breaker cooldown, `strata-auto` skips it immediately and routes to healthy auto providers.

In the dual-connector edge topology (MiniPC edge gateway and primary Fedora workstation), the MiniPC proxy container routes Strata requests over Tailscale to `http://primary-workstation:3001/strata/v1`. The primary workstation's Nginx reverse proxy forwards `/strata/` to `http://172.17.0.1:8080/` with `Host: localhost` to satisfy Strata's DNS rebinding protection while bypassing host firewall restrictions. On the primary workstation, the local Docker proxy reaches Strata via `http://host.docker.internal:8080/v1`.

### OpenRouter Zero-Cost Isolation

The `openrouter` provider operates as a mixed marketplace of paid and free models. To guarantee that no account credits are ever billed unintentionally:
- **Discovered Catalog Filtering (`discovery.py`)**: Models fetched from OpenRouter's live `/models` endpoint are strictly filtered at ingestion time to keep only zero-cost variants ending with `:free` or equaling `openrouter/free`. Paid models are stripped before pattern matching can evaluate them.
- **Resolution Safety Gate (`router.py`)**: Virtual aliases (such as `free-auto`) and provider patterns are restricted to `:free` variants. If an explicit paid model is targeted or no pattern matches, the router coerces the model to `openrouter/free`.
- **Server Dispatch Guard (`server.py`)**: Pre-flight verification enforces that requests dispatched to OpenRouter must end with `:free` or equal `openrouter/free`, ensuring 100% hermetic zero-cost inference.
- **Attribution Headers**: Requests to OpenRouter pass `HTTP-Referer: https://llm.clvg.uk` and `X-Title: Pi / Free LLM Proxy`.

---

## Cloud Output-Token Clamping

Cloud free-tier providers enforce an 8,000-token output ceiling. To prevent upstream 400/422 rejections when a client (e.g. Pi configured with a 131,072-token budget for Strata) sends an oversized `max_tokens`, `chat_completions` in `apps/free_llm_proxy/server.py` clamps the payload **after** model resolution and **before** `execute_completion`:

```python
# Cloud free-tier providers enforce an 8k token limit; clamp when routing to cloud
if p_id != "strata":
    if "max_tokens" in payload and payload["max_tokens"] is not None:
        if payload["max_tokens"] > config.CLOUD_MAX_OUTPUT_TOKENS:
            payload["max_tokens"] = config.CLOUD_MAX_OUTPUT_TOKENS
    if (
        "max_completion_tokens" in payload
        and payload["max_completion_tokens"] is not None
    ):
        if payload["max_completion_tokens"] > config.CLOUD_MAX_OUTPUT_TOKENS:
            payload["max_completion_tokens"] = config.CLOUD_MAX_OUTPUT_TOKENS
```

Behavioral rules:

- **Strata is exempt** — requests routed to the `strata` provider keep the caller's full budget (e.g. `max_tokens: 131072`), since local inference has no cloud ceiling.
- **All cloud providers are clamped** — `free-auto`, `free-fast`, `free-reasoning`, `provider/model` targets, and any other non-Strata route are clamped to `CLOUD_MAX_OUTPUT_TOKENS`.
- **Both parameter names are handled** — `max_tokens` and `max_completion_tokens` are clamped independently, and `None` values are left untouched.
- **Clamping only lowers** — values already at or below the ceiling pass through unchanged.

This is verified by `test_max_tokens_unclamped_for_strata_and_clamped_for_cloud` in `apps/free_llm_proxy/tests/test_proxy.py`, which asserts a 131,072-token request survives intact on the `strata` route and is clamped to `8192` on the `free-auto` route.

---

## Virtual Model Aliases

| Alias | Description | Target Family |
| :--- | :--- | :--- |
| `free-auto` (default) | Best overall model across the healthy active pool (Strata excluded) | 120B / 70B / Flash / 27B |
| `strata-auto` | Prioritizes local Strata (localhost:8080); fails over cleanly to auto pool when offline | Local live model / Strata ➔ Auto fallback |
| `auto-strata` | Adds Strata into the standard Tier 1 round-robin auto rotation pool | Local Strata + Tier 1 providers |
| `strata` | Strictly targets local Strata; fails fast with error if offline (zero silent cloud fallback) | Whichever model is live on localhost:8080 |
| `free-fast` | Sub-second ultra-low latency models | 20B / 8B / Flash-Lite / 7B |
| `free-reasoning` | Deep reasoning / thinking models | R1, reasoning, Flint, Beam |
| Any custom name | Pass-through if present on the provider, otherwise falls back to `free-auto` patterns | — |
| `provider/model` | Explicitly targets a provider first, with normal failover behind it | — |
| `provider` (bare) | Bare active provider ID (e.g. `openrouter`) targets that provider first (`strata` is strict with no fallback) | — |
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
| `STRATA_BASE_URL` | `http://localhost:8080/v1` | Local Strata OpenAI-compatible endpoint URL |
| `ENABLE_STRATA` | `true` | Toggle inclusion of local Strata provider in proxy pool |
| `CLOUD_MAX_OUTPUT_TOKENS` | `8192` | Output-token ceiling enforced on all non-Strata (cloud) routes; Strata is exempt |
| `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `NVIDIA_API_KEY` | unset | Provider credentials; unset providers are simply excluded from the active pool |

`ENABLE_STRATA` is parsed leniently — `0`, `false`, and `no` (case-insensitive) disable the provider. When disabled, `load_providers_config()` removes the `strata` entry from the provider map entirely. When enabled, `STRATA_BASE_URL` overrides the `strata` provider's `base_url` at load time.

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

The test suite covers master-key auth rejection, the unauthenticated health probe, circuit-breaker tripping on 429, alias resolution against live catalogs, automatic failover when the primary returns 429, SSE streaming pass-through, metrics/models endpoints, and SQLite audit logging. It also verifies `openrouter/free` resolution (never stripped to `free` when the catalog is empty, prioritized as the first OpenRouter preferred pattern, and routed to OpenRouter as the first candidate) and end-to-end chat completion routing for `model: "openrouter/free"`. Additional coverage validates OpenRouter zero-cost isolation (paid models filtered from discovery, coerced to `openrouter/free` at resolution and dispatch), the Strata alias chains (`strata-auto` first, `auto-strata` in rotation, strict `strata` with no fallback), Strata cooldown bypass, `ENABLE_STRATA=false` provider removal, graceful `503` handling of `httpx.RequestError` connection failures, and cloud output-token clamping (`test_max_tokens_unclamped_for_strata_and_clamped_for_cloud`). A `conftest.py` socket guard raises on any non-loopback connection, keeping the suite hermetic per [[concepts/test-coverage]].

---

## Pi Assistant Integration

Pi (`/home/cv/.local/bin/pi`) integrates directly with Free LLM Proxy by configuring a custom OpenAI-compatible provider in `~/.pi/agent/models.json`:

```json
{
  "providers": {
    "free-llm": {
      "baseUrl": "https://llm.clvg.uk/v1",
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
          "id": "strata-auto",
          "name": "Free LLM: Strata Primary (Auto Fallback)",
          "input": ["text"],
          "contextWindow": 262144,
          "maxTokens": 131072,
          "type": "chat"
        },
        {
          "id": "auto-strata",
          "name": "Free LLM: Auto with Strata Rotated",
          "input": ["text"],
          "contextWindow": 262144,
          "maxTokens": 131072,
          "type": "chat"
        },
        {
          "id": "strata",
          "name": "Free LLM: Strata (Strict / No Fallback)",
          "input": ["text"],
          "contextWindow": 262144,
          "maxTokens": 131072,
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
- **Strata Token Budgets**: The Strata aliases declare `maxTokens: 131072` so Pi can request deep reasoning budgets; the proxy preserves them on the Strata route and clamps them to `CLOUD_MAX_OUTPUT_TOKENS` if the request fails over to a cloud provider.

---

## Related

- [[concepts/tool-first-agency]]
- [[entities/tool-registry]]
- [[entities/wiki-linter]]
- [[concepts/test-coverage]]
- [[concepts/env-based-secrets]]
