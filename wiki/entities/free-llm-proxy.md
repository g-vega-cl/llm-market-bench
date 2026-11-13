--- 
tags: [llm, proxy, inference, router, free-tier] 
category: entity 
---

# Free LLM Proxy

A model-agnostic, OpenAI-compatible proxy server located at `apps/free_llm_proxy` that pools permanent free-tier LLM inference providers into a single resilient endpoint, with an opt-in paid OpenCode Go fallback tier. It features dynamic model catalog discovery, tiered round-robin load balancing, circuit-breaker cooldowns on rate limits, cloud output-token clamping, and full token usage logging.

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
       ┌─────────────────────────────────────────────────────────────┐
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
       │           │ all free candidates exhausted                   │
       │           ▼ (*-go aliases only)                             │
       │  Tier 3: [OpenCode Go] (paid, last resort)                  │
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

## Key Components

### Dynamic Catalog Discovery (`apps/free_llm_proxy/discovery.py`)**: Queries each active provider's `GET /models` endpoint at runtime. Avoids hardcoded model IDs so provider version rollouts (e.g. `qwen3.8-27b`, `gpt-oss-120b`) work automatically without code edits. Results are cached per provider (`ModelDiscovery`, default 3600s TTL) and matched against prioritized `fnmatch` patterns. Discovery requests use a short connect timeout (`httpx.Timeout(4.0, connect=2.0)`) so an offline provider (e.g. local Strata) fails fast instead of stalling the catalog refresh.

### Circuit Breaker (`apps/free_llm_proxy/circuit_breaker.py`)**: Reacts to HTTP 429 rate limits or repeated 5xx errors by placing the failed provider into cooldown (respecting `Retry-After` if sent). Deterministic 4xx responses (400/403/408/409/413/422) are treated like rate limits — a provider that returns a 413 payload-too-large is cooled down so it is skipped on the next request instead of being re-probed first on every oversized call. A 429 trips the breaker immediately; two consecutive 5xx errors trip it. `record_success` resets the consecutive-failure counter, and `get_status_overview` exposes per-provider health, cooldown remaining, failure count, and rate-limit hit count.

### Tiered Router (`apps/free_llm_proxy/router.py`)**: Distributes traffic across Tier 1 providers using round-robin counters to balance free-tier request limits. Healthy providers are tried before cooling-down ones; for free-only aliases, cooling providers are used only as a last resort when no healthy candidate remains. Routing is split into free and paid cost segments: for `*-go` aliases the order is free healthy ➔ free cooling ➔ paid healthy ➔ paid cooling, so a rate-limit storm can never promote the paid provider ahead of a still-usable free one. An explicit `provider/model` prefix moves that provider to the front of its segment. Providers declaring `enabled_in_auto: false` (such as local Strata) are excluded from the standard auto rotation unless explicitly targeted or opted in: `strata-auto` and `strata-auto-go` move Strata to the front of the free segment, while `auto-strata` and `auto-strata-go` add it to the Tier 1 rotation. Paid providers declare `billing: "paid"` and an `auto_aliases` allowlist; eligibility is fail-closed, so a missing or edited `enabled_in_auto` flag cannot leak paid spend into a free alias. Tier buckets are created dynamically from each provider's normalized integer `tier` value (malformed values fall back to the default rather than crashing), and the paid OpenCode Go pool sits at Tier 3.

### Cloud Output-Token Clamping (`apps/free_llm_proxy/server.py`)**: Before dispatch, requests routed to any non-Strata (cloud) provider have `max_tokens` and `max_completion_tokens` clamped down to `CLOUD_MAX_OUTPUT_TOKENS` (default `16384`), because cloud free-tier providers enforce a 16k output ceiling. Strata is exempt and preserves the caller's full budget (e.g. 131,072 tokens). Cloud routes also have the Strata-specific `reasoning_budget_tokens` key stripped from the payload, since cloud gateways (Gemini, OVHCloud) reject it with a 400.

### Audit Database (`apps/free_llm_proxy/db.py`)**: Persists call traces, prompt tokens, completion tokens, latency, failover chains, caller attribution, and stream telemetry (`is_stream`, `usage_available`, `ttft_ms`, `duration_ms`, `stream_completed`) to a local SQLite database (`data/free_llm_proxy.db`). Captures "Who" (`client_ip` via Cloudflare `CF-Connecting-IP`, `X-Forwarded-For`, or socket host, and `user_agent`) and "Why" (`purpose` via `X-Purpose` / `X-Client-Id` and `prompt_preview` containing a 60-character snippet of the user prompt). Logs failed authentication attempts (status 401) with caller IP and user agent to monitor unauthorized probes. `get_metrics()` aggregates total/successful/unauthorized requests, success rate, token totals, average latency, per-provider stats, the 10 most recent calls, and the token-coverage fields `streaming_requests`, `usage_available_requests`, `zero_token_successes`, `token_coverage_pct`, `avg_stream_duration_ms`, `avg_ttft_ms`, and `incomplete_streams`. Additive migrations preserve existing rows, and indexes on `timestamp`, `status_code`, and `client_ip` keep metrics queries fast. Audit rows are retained indefinitely (no retention job).

### Streaming & SSE (`apps/free_llm_proxy/streaming.py`, `client.py`)**: Streams `text/event-stream` chunks directly to chat clients with pre-flight failover protection — the connection is probed first so an initial 429/5xx fails over before any chunk is yielded. The SSE bytes are never rewritten. `audited_sse_stream` parses only `data:` lines in a bounded buffer and logs the final `usage` object after the stream completes, errors, or the client disconnects; it never injects `stream_options` and never changes a provider payload. Strata, Groq, Kilo, and OpenRouter already emit usage in their default streaming responses; providers that omit it are marked `usage_available = 0` instead of silently claiming zero tokens. Strata may hold an SSE stream open with `: keep-alive` frames while processing a large prompt; the proxy forwards those frames unchanged, applies **no total duration cap**, records TTFT and total duration, and marks the row `stream_completed = 0` if the client disconnects first. Clients should use `stream: true` for long Strata prompts; if time-to-first-token can exceed 5–10 minutes, use an asynchronous job queue rather than a synchronous HTTP request.

### Unauthorized Spike Monitor (`apps/free_llm_proxy/security.py`)**: Keeps a rolling in-memory window of 401 attempts and emits one structured `security.401_spike` warning when the configured threshold is crossed. It is log-only (no external calls) and exposes `unauthorized_last_5m`, `unauthorized_window_seconds`, and `security_alert_active` in metrics.

### Connection Error Resilience (`apps/free_llm_proxy/client.py`)**: `execute_completion` wraps both the non-streaming `POST` and the streaming `build_request`/`send` probe in `try/except httpx.RequestError`. A connection refusal, DNS failure, or connect timeout is converted into a structured `503` response (`{"error": {"message": "Provider connection error: ...", "type": "connection_error"}}`) rather than propagating an unhandled exception. This lets the router cleanly fail over to the next candidate provider (e.g. `strata-auto` falling back to the auto pool when local Strata is offline). The default client uses `httpx.Timeout(60.0, connect=3.0)` so an unreachable provider is detected within 3 seconds.

## Dynamic Model Discovery & Anti-Hardcoding Philosophy

A foundational architectural principle of Free LLM Proxy is **zero hardcoded model pinning**:

1. **Model Obsolescence Rate**: Frontier and fast-tier LLM models churn rapidly. Checkpoint names are sunset and replaced on weeks-long cadences (e.g., Google advancing from Gemini 1.5 to 2.0 to 3.x Flash, Groq updating Qwen and Llama checkpoints). Hardcoding specific model strings in clients or configurations creates constant maintenance friction, broken upstream calls, and silent degradation.
2. **Dynamic Provider Catalog Ingestion (`discovery.py`)**: The proxy queries each active provider's live `/models` endpoint at runtime and caches the catalog. New models released by providers are immediately discovered and become available to the router without requiring code commits or proxy restarts.
3. **Official Provider Dynamic Aliases**: Wherever an upstream provider supports an official moving pointer (such as Google's official `gemini-flash-latest` or OpenRouter's `openrouter/free`), the proxy targets the alias as the primary pattern. This ensures downstream callers automatically receive newly promoted versions without intervention.
4. **Resilient In-Provider Fallback**: If an upstream bleeding-edge model experiences high-demand spikes (e.g. Google HTTP 503 on `gemini-flash-latest`), the proxy cascades down through adjacent active generation variants (e.g. `gemini-3.6-flash`, `gemini-3.5-flash`) before tripping circuit breakers.
5. **Virtual Alias Abstraction**: Callers (such as the Pi agent or background prediction routines) consume generic virtual aliases (`free-auto`, `strata-auto`, `free-fast`, `free-reasoning`). Clients never specify brittle upstream IDs, allowing the routing engine to swap, balance, and heal underlying model targets transparently.

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

### Gemini Free-Flash Dynamic Routing & Legacy Exclusion
The `gemini` provider is restricted to modern free Flash models (defaulting to Google's official dynamic alias `gemini-flash-latest` and the Gemini 3.x Flash series):
- **Catalog pre-filter** — when `provider_id == "gemini"`, the discovered `available_models` list is narrowed to entries containing `flash` (case-insensitive) while strictly stripping obsolete 1.x and 2.x versions (`1.5`, `2.0`, `2.5`).
- **Dynamic alias preference** — matches Google's official dynamic alias `gemini-flash-latest`, followed by `gemini-3.8-flash` and modern 3.x Flash models.
- **Prefix resolution** — if a `provider/model` prefix resolves to a non-Flash or legacy Gemini model (e.g. `gemini/gemini-1.5-pro`), the router re-matches against the modern Flash candidate list, falling back to `gemini-flash-latest`.
- **Exact catalog match** — a requested model that is a legacy or Pro model is rejected from the exact-match path and coerced to modern Flash.
- **In-provider demand spike cascade** — if the bleeding-edge model (`gemini-flash-latest` or `gemini-3.8-flash`) encounters a temporary Google HTTP 503 high-demand spike or 429 rate limit, the proxy automatically attempts modern stable variants (`gemini-3.6-flash`, `gemini-3.5-flash`) before falling over to Groq.
- **Wildcard sanitization** — all resolved model strings are stripped of raw pattern wildcards (`*`).
This guarantees zero compute cost while preventing breaking changes when Google promotes new Flash iterations. Verified by `test_gemini_strictly_filters_out_legacy_models` and `test_gemini_in_provider_cascade_on_503_spike` in `apps/free_llm_proxy/tests/test_proxy.py`.

### Local Strata Targeting
Local Strata (`strata` provider, `base_url` from `STRATA_BASE_URL`, default `http://localhost:8080/v1`) is a Tier 1 provider with `requires_auth: false` and `enabled_in_auto: false`, so it is excluded from the standard `free-auto` rotation. Three aliases control how it participates:
- **`strata-auto`** — Strata is placed first in the candidate chain; if Strata is offline or cooling down, the request fails over cleanly to the normal auto pool.
- **`auto-strata`** — Strata is added into the standard Tier 1 round-robin rotation alongside the cloud providers.
- **`strata`** (and `strata/<model>`) — strict targeting: the candidate chain contains **only** Strata. If Strata is offline the request fails (HTTP 502) with zero silent cloud fallback.
When Strata is in circuit-breaker cooldown, `strata-auto` skips it immediately and routes to healthy auto providers.

In the dual-connector edge topology (MiniPC edge gateway and primary Fedora workstation), the MiniPC proxy container routes Strata requests over Tailscale to `http://primary-workstation:3001/strata/v1`. The primary workstation's Nginx reverse proxy forwards `/strata/` to `http://172.17.0.1:8080/` with `Host: localhost` to satisfy Strata's DNS rebinding protection while bypassing host firewall restrictions. On the primary workstation, the local Docker proxy reaches Strata via `http://host.docker.internal:8080/v1`.

#### Prompt-size provider caps

Providers declare an optional `max_prompt_tokens` in `providers.json` (e.g. Groq: 8000). Before dispatch the router estimates the prompt size (~4 chars/token) and drops any provider whose ceiling is below it from the candidate chain, so a deterministic 413 never triggers a wasted round trip. Combined with the circuit breaker's deterministic-4xx cooldown, an oversized provider is excluded proactively and skipped after any 4xx rejection.

### OpenRouter Zero-Cost Isolation
The `openrouter` provider operates as a mixed marketplace of paid and free models. To guarantee that no account credits are ever billed unintentionally:
- **Discovered Catalog Filtering (`discovery.py`)**: Models fetched from OpenRouter's live `/models` endpoint are strictly filtered at ingestion time to keep only zero-cost variants ending with `:free` or equaling `openrouter/free`. Paid models are stripped before pattern matching can evaluate them.
- **Resolution Safety Gate (`router.py`)**: Virtual aliases (such as `free-auto`) and provider patterns are restricted to `:free` variants. If an explicit paid model is targeted or no pattern matches, the router coerces the model to `openrouter/free`.
- **Server Dispatch Guard (`server.py`)**: Pre-flight verification enforces that requests dispatched to OpenRouter must end with `:free` or equal `openrouter/free`, ensuring 100% hermetic zero-cost inference.
- **Attribution Headers**: Requests to OpenRouter pass `HTTP-Referer: https://llm.clvg.uk` and `X-Title: Pi / Free LLM Proxy`.

### Kilo Code Zero-Cost Isolation
The `kilo` provider (`requires_auth: false`) also operates as a mixed marketplace of free and paid models. To prevent HTTP 401 `PAID_MODEL_AUTH_REQUIRED` failures:
- **Discovered Catalog Filtering (`discovery.py`)**: Strips paid models and retains only zero-cost variants (`:free`, `*-free`, or `kilo-auto/free`).
- **Resolution Safety Gate (`router.py`)**: Prioritizes `kilo-auto/free` and coerces unrecognized models to `kilo-auto/free` before dispatch.
- **In-Provider Cascade (`server.py`)**: If a specific model returns 401/429/503, the proxy falls back through `kilo-auto/free`, `reflection/beam-free`, and `nvidia/nemotron-3.5-super-vl:free` before leaving the provider.

### OpenCode Go Paid-Tier Isolation
OpenCode Go (`opencode-go`) is a paid `$10/month` subscription, not a free-tier provider, so it is isolated from every zero-cost alias:
- **Alias gating (`router.py`)**: `billing: "paid"` plus an `auto_aliases` allowlist makes eligibility fail-closed. Go is only added to the candidate chain for `auto-go`, `auto-strata-go`, and `strata-auto-go` (or when explicitly targeted). `free-auto`, `auto-strata`, `free-fast`, `free-reasoning`, `strata-auto`, `auto`, and `default` never include it, even if an `enabled_in_auto` flag is edited away.
- **Last-resort placement (`tier: 3`)**: The router builds separate free and paid cost segments and appends Go after both the healthy and cooling free candidates, so the free pool is exhausted before any paid request is made — including during a 429 cooldown storm.
- **Key-gated activation**: The provider has `requires_auth: true` and `env_key: OPENCODE_GO_API_KEY`. With no key configured, it disappears from `get_active_providers()` and the `*-go` aliases degrade transparently to the free pool.
- **Fail-closed dispatch**: If Go's live `/models` catalog cannot be read, the proxy refuses to dispatch a paid request rather than sending an ungrounded model name.
- **Dynamic catalog**: `base_url` is `https://opencode.ai/zen/go/v1`; the live roster is discovered from `GET /models`, so no model names are hardcoded.
- **Session affinity (`session.py`)**: Go rejects requests without `x-opencode-session`. The proxy forwards a client-supplied header when it matches a short header-safe charset, otherwise derives a stable `fllm-<sha256>` ID from caller identity plus the first user message so multi-turn conversations keep the same routing/caching session.
- **Explicit targeting**: `opencode-go/<model>` (or bare `opencode-go`) moves the provider to the front of the chain for deliberate per-model use, with normal failover behind it.

### Resilient In-Provider Demand-Spike Cascades
When an upstream endpoint returns temporary errors (503 high-demand spike, 404 deprecated function, or 429 rate limit), the proxy automatically cascades through alternative models on the *same* provider before tripping circuit breakers and moving to the next provider:
- **Google Gemini**: Cascades from `gemini-flash-latest` ➔ `gemini-3.8-flash` ➔ `gemini-3.6-flash` ➔ `gemini-3.5-flash`.
- **OpenRouter**: Cascades from the primary model ➔ `openrouter/free` ➔ `nemotron-3-ultra-550b:free` ➔ `nemotron-3.5-super-vl:free`.
- **NVIDIA NIM**: Cascades from the primary model ➔ `minimax-m3.1-flash` ➔ `nemotron-3.5-super-vl-120b` ➔ `nemotron-3-ultra-550b` ➔ `mistral-large`.
- **Kilo Code**: Cascades from the primary model ➔ `kilo-auto/free` ➔ `reflection/beam-free` ➔ `nemotron-3.5-super-vl:free`.

## Cloud Output-Token Clamping
Cloud free-tier providers enforce an output-token ceiling. To prevent upstream 400/422 rejections when a client (e.g. Pi configured with a 131,072-token budget for Strata) sends an oversized `max_tokens`, `chat_completions` in `apps/free_llm_proxy/server.py` clamps the payload **after** model resolution and **before** `execute_completion`:

```python
# Cloud free-tier providers enforce an output token limit; clamp when routing to cloud
if p_id != "strata":
    # Strip Strata-specific kwargs that cloud gateways (Gemini, OVHCloud) reject with 400
    payload.pop("reasoning_budget_tokens", None)
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
- **Strata is exempt** — requests routed to the `strata` provider keep the caller's full budget (e.g. `max_tokens: 131072`) and any `reasoning_budget_tokens` value, since local inference has no cloud ceiling and understands the reasoning-budget kwarg.
- **All cloud providers are clamped** — `free-auto`, `free-fast`, `free-reasoning`, `provider/model` targets, and any other non-Strata route are clamped to `CLOUD_MAX_OUTPUT_TOKENS` (default `16384`).
- **`reasoning_budget_tokens` is stripped on cloud routes** — the Strata-specific reasoning-budget kwarg is removed from the payload before dispatch to any non-Strata provider, because cloud gateways (Gemini, OVHCloud) reject the unknown field with a 400.
- **Both parameter names are handled** — `max_tokens` and `max_completion_tokens` are clamped independently, and `None` values are left untouched.
- **Clamping only lowers** — values already at or below the ceiling pass through unchanged.
This is verified by `test_max_tokens_unclamped_for_strata_and_clamped_for_cloud` in `apps/free_llm_proxy/tests/test_proxy.py`, which asserts a 131,072-token request (with `reasoning_budget_tokens: 12288`) survives intact on the `strata` route and is clamped to `16384` with `reasoning_budget_tokens` stripped on the `free-auto` route.

## Virtual Model Aliases

| Alias | Description | Target Family |
| :--- | :--- | :--- |
| `auto-strata` (default) | Adds Strata into the standard Tier 1 round-robin auto rotation pool | Local Strata + Tier 1 providers |
| `auto-go` | Free auto pool with OpenCode Go as a paid last-resort tier; Strata excluded | Tier 1+2 free providers ➔ OpenCode Go |
| `auto-strata-go` | Same as `auto-go`, but Strata joins the Tier 1 rotation | Local Strata + Tier 1+2 free providers ➔ OpenCode Go |
| `strata-auto-go` | Strata primary; on failure falls over the free pool, then paid OpenCode Go | Local Strata ➔ Tier 1+2 free providers ➔ OpenCode Go |
| `free-auto` | Best overall model across the healthy cloud pool (Strata excluded) | 120B / 70B / Flash / 27B |
| `strata-auto` | Prioritizes local Strata (localhost:8080); fails over cleanly to auto pool when offline | Local live model / Strata ➔ Auto fallback |
| `strata` | Strictly targets local Strata; fails fast with error if offline (zero silent cloud fallback) | Whichever model is live on localhost:8080 |
| `free-fast` | Sub-second ultra-low latency models | 20B / 8B / Flash-Lite / 7B |
| `free-reasoning` | Deep reasoning / thinking models | R1, reasoning, Flint, Beam |
| Any custom name | Pass-through if present on the provider, otherwise falls back to `free-auto` patterns | — |
| `provider/model` | Explicitly targets a provider first, with normal failover behind it | — |
| `provider` (bare) | Bare active provider ID (e.g. `openrouter`) targets that provider first (`strata` is strict with no fallback) | — |
| `openrouter/free` | Passed through verbatim to OpenRouter; never stripped to `free` | — |

## Endpoints

| Endpoint | Method | Auth | Description |
| :--- | :--- | :--- | :--- |
| `/v1/chat/completions` | `POST` | Bearer Token | Standard OpenAI chat completion (streaming + non-streaming) |
| `/v1/models` | `GET` | Bearer Token | Discovered live models and virtual aliases |
| `/v1/metrics` (alias `/stats`) | `GET` | Bearer Token | Total requests, token counts, latency, per-provider stats, circuit breaker status, stream usage coverage, connector scope, and unauthorized-spike state |
| `/health` | `GET` | None | Service readiness, connector ID, and active provider list |

Because the public hostname load-balances across the workstation and MiniPC connectors, `/v1/metrics` describes whichever connector served the request. Use `connector_id` and `scope: "connector"`; sum across connectors for global totals.

## Configuration

Environment variables (loaded strictly from `apps/free_llm_proxy/.env` to isolate secrets from `apps/engine/.env`):

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
| `CLOUD_MAX_OUTPUT_TOKENS` | `16384` | Output-token ceiling enforced on all non-Strata (cloud) routes; Strata is exempt |
| `CONNECTOR_ID` | hostname | Connector identity returned by `/health` and `/v1/metrics`; compose sets `workstation` / `secondary` |
| `SECURITY_ALERT_401_THRESHOLD` | `20` | Unauthorized requests within the window required to emit one `security.401_spike` warning (`0` disables) |
| `SECURITY_ALERT_WINDOW_SECONDS` | `300` | Rolling window for the log-only 401 spike monitor |
| `GROQ_API_KEY`, `GEMINI_API_KEY_FREE`, `OPENROUTER_API_KEY`, `NVIDIA_API_KEY`, `OPENCODE_GO_API_KEY` | unset | Provider credentials; unset providers are simply excluded from the active pool. `OPENCODE_GO_API_KEY` activates the paid Tier 3 fallback used only by `auto-go` / `auto-strata-go` / `strata-auto-go`. |

`ENABLE_STRATA` is parsed leniently — `0`, `false`, and `no` (case-insensitive) disable the provider. When disabled, `load_providers_config()` removes the `strata` entry from the provider map entirely. When enabled, `STRATA_BASE_URL` overrides the `strata` provider's `base_url` at load time.

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

The test suite covers master-key auth rejection, the unauthenticated health probe, circuit-breaker tripping on 429, alias resolution against live catalogs, automatic failover when the primary returns 429, SSE streaming pass-through, metrics/models endpoints, and SQLite audit logging. It also verifies `openrouter/free` resolution (never stripped to `free` when the catalog is empty, prioritized as the first OpenRouter preferred pattern, and routed to OpenRouter as the first candidate) and end-to-end chat completion routing for `model: "openrouter/free"`. Additional coverage validates OpenRouter zero-cost isolation (paid models filtered from discovery, coerced to `openrouter/free` at resolution and dispatch), the Strata alias chains (`strata-auto` first, `auto-strata` in rotation, strict `strata` with no fallback), Strata cooldown bypass, `ENABLE_STRATA=false` provider removal, graceful `503` handling of `httpx.RequestError` connection failures, cloud output-token clamping (`test_max_tokens_unclamped_for_strata_and_clamped_for_cloud` — including `reasoning_budget_tokens` preservation on Strata and stripping on cloud routes), unauthorized 401 audit logging (`test_unauthorized_call_is_logged_in_audit_db`), Gemini Pro→Flash coercion (`test_gemini_pro_model_is_coerced_to_free_flash`), and the `GEMINI_API_KEY_FREE` provider key (`test_gemini_uses_gemini_api_key_free`). OpenCode Go coverage verifies that `auto-go` places `opencode-go` last and excludes Strata, `auto-strata-go` includes both Strata and Go, `strata-auto-go` puts Strata first and Go last, every free alias stays Go-free even with a key configured, the provider disappears without `OPENCODE_GO_API_KEY`, alias/prefix resolution works against a discovered catalog, and an end-to-end `auto-go` request exhausts free providers before calling Go exactly once (`test_auto_go_end_to_end_falls_back_to_go`), including forwarding the client `x-opencode-session` and preserving the Go `User-Agent`. An end-to-end `strata-auto-go` request proves the full `Strata ➔ free pool ➔ Go` failover path (`test_strata_auto_go_end_to_end_fails_over_strata_then_free_then_go`). Additional regressions prove that a full free-pool cooldown still tries cooling free candidates before paid Go, paid routing fails closed if its `auto_aliases` allowlist disappears, malformed `tier` values do not crash the router, and paid dispatch is refused when the live catalog is unavailable. Session affinity derivation (client-header passthrough, sanitization of control characters and oversized IDs, stable multi-turn fallback, multimodal text extraction, caller-identity fallback) is covered by `apps/free_llm_proxy/tests/test_session.py`, and an autouse fixture resets the shared circuit breaker between tests. Stream telemetry in `apps/free_llm_proxy/tests/test_streaming.py`, `apps/free_llm_proxy/tests/test_streaming_integration.py`, and `apps/free_llm_proxy/tests/test_db_telemetry.py` verifies byte-for-byte SSE pass-through, usage parsing across chunk boundaries, malformed/oversized-frame resilience, callback failures, mid-stream errors, end-to-end Strata and cloud usage logging, the absence of any injected `stream_options`, legacy schema migration, and token-coverage metrics. Log-only 401 spike detection and connector-scoped metrics are covered by `apps/free_llm_proxy/tests/test_security.py`. A `conftest.py` socket guard raises on any non-loopback connection, keeping the suite hermetic per [[concepts/test-coverage]].

## Pi Assistant Integration
Pi (`/home/cv/.local/bin/pi`) integrates directly with Free LLM Proxy by configuring a custom OpenAI-compatible provider in `~/.pi/agent/models.json`:

```json
{
  "providers": {
    "free-llm": {
      "baseUrl": "https://llm.clvg.uk/v1",
      "api": "openai-completions",
      "apiKey": "<FREE_PROXY_MASTER_KEY>",
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
          "maxTokens": 16384,
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
          "id": "auto-go",
          "name": "Free LLM: Auto + OpenCode Go (Paid Last Resort)",
          "input": ["text"],
          "contextWindow": 262144,
          "maxTokens": 16384,
          "type": "chat"
        },
        {
          "id": "auto-strata-go",
          "name": "Free LLM: Auto + Strata + OpenCode Go",
          "input": ["text"],
          "contextWindow": 262144,
          "maxTokens": 16384,
          "type": "chat"
        },
        {
          "id": "strata-auto-go",
          "name": "Free LLM: Strata Primary + OpenCode Go",
          "input": ["text"],
          "contextWindow": 262144,
          "maxTokens": 16384,
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
          "maxTokens": 16384,
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

## Related
- [[concepts/tool-first-agency]]
- [[entities/tool-registry]]
- [[entities/wiki-linter]]
- [[concepts/test-coverage]]
- [[concepts/env-based-secrets]]
