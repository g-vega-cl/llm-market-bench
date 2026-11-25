---
tags: [llm, proxy, inference, router, free-tier]
category: entity
---

# Free LLM Proxy

A model-agnostic, OpenAI-compatible proxy server located at `apps/free_llm_proxy` that pools permanent free-tier LLM inference providers into a single resilient endpoint, with an opt-in paid OpenCode Go fallback tier. It features dynamic model catalog discovery, per-provider free-model allowlists (`allowed_model_patterns`), catalog-driven in-provider cascades (`cascade_statuses`), tiered round-robin load balancing, circuit-breaker cooldowns on rate limits, failure-priority preservation across cascades, per-provider output/thinking ceilings declared in `providers.json`, declared-only reasoning-parameter passthrough, per-attempt wall-clock timeouts with whole-segment deadlines, plan-included-model-first ordering inside paid providers, billing provenance on every audit row, a paginated `/v1/logs` audit endpoint, and full token usage logging.

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
       └──────────┬─────────────────────────────────────────────────┘
                  │
                  ▼
       ┌─────────────────────────────────────────────────────────────┐
       │                      Router & Failover                      │
       │                                                             │
       │  Tier 1: [Groq] ⇄ [Gemini] ⇄ [Kilo Code] ⇄ [Nous Research]  │
       │           │ 429 / 5xx / Timeout / 504 wall-clock cap       │
       │           ▼ (Trip Circuit Breaker)                          │
       │  Tier 2: [OpenRouter] ⇄ [NVIDIA NIM]                        │
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
                       │ - Billing provenance        │
                       └─────────────────────────────┘
```

## Key Components

### Dynamic Catalog Discovery (`apps/free_llm_proxy/discovery.py`)

Queries each active provider's `GET /models` endpoint at runtime. Avoids hardcoded model IDs so provider version rollouts (e.g. `qwen3.8-27b`, `gpt-oss-120b`) work automatically without code edits. Results are cached per provider (`ModelDiscovery`, default 3600s TTL) and matched against prioritized `fnmatch` patterns. Discovery requests use a short connect timeout (`httpx.Timeout(4.0, connect=2.0)`) so an offline provider (e.g. local Strata) fails fast instead of stalling the catalog refresh. An empty cached list is a valid cache hit (`if cached is not None`), so a provider that legitimately exposes zero allowed models is not re-fetched on every request.

#### Per-Provider Free-Model Allowlists (`allowed_model_patterns`)

Zero-cost isolation is no longer hardcoded per provider. A provider may declare `allowed_model_patterns` in `providers.json`; `ModelDiscovery.configure_allowed_patterns(providers)` loads them at router construction, and `fetch_live_models` filters the discovered catalog through `filter_allowed_models(models, patterns)` before caching. The helpers are pure and shared by the router and the failover layer:

- **`is_allowed_model(model, allowed_patterns)`** — true only for a *concrete* model ID. It rejects empty strings, IDs starting with `:` or `-`, and any string containing `*`, `?`, or `[` (a pattern is not a model). `None` means "no allowlist" (allow everything); an **empty list fails closed** (allow nothing). Matching is case-insensitive `fnmatch`.
- **`filter_allowed_models(models, allowed_patterns)`** — filters a live catalog down to allowed concrete IDs.
- **`filter_allowed_patterns(patterns, allowed_patterns)`** — filters a provider's `preferred_patterns` list (which may contain globs) to entries scoped by the allowlist, dropping the bare `*` wildcard.

Declared allowlists: `openrouter` → `["*:free", "openrouter/free"]`, `kilo` → `["*:free", "*-free", "kilo-auto/free"]`, `nous` → `["*:free"]`. A provider that declares no allowlist keeps the previous unrestricted behavior.

#### `dynamic_fallback_model`

A provider with an allowlist may also declare a `dynamic_fallback_model` (`kilo` → `kilo-auto/free`, `openrouter` → `openrouter/free`) that the router and server fall back to when the live catalog is empty or no allowed model resolves. Providers without one (e.g. `nous`) fail closed instead of inventing a checkpoint.

### Circuit Breaker (`apps/free_llm_proxy/circuit_breaker.py`)

Reacts to HTTP 429 rate limits or repeated 5xx errors by placing the failed provider into cooldown (respecting `Retry-After` if sent). Deterministic 4xx responses (400/403/408/409/413/422) are treated like rate limits — a provider that returns a 413 payload-too-large is cooled down so it is skipped on the next request instead of being re-probed first on every oversized call. A 429 trips the breaker immediately; two consecutive 5xx errors trip it, and `record_stream_failure` applies the same two-strike rule to streams that die mid-flight. `record_success` resets the consecutive-failure counter, and `get_status_overview` exposes per-provider health, cooldown remaining, failure count, and rate-limit hit count.

**Failure-priority preservation.** When an in-provider cascade ends without a `200`, the proxy reports the *highest-priority* failure rather than the last one tried: `429` (priority 4) > deterministic 4xx (3) > `5xx` (2) > anything else (1). A trailing `404` or `504` from a fallback model therefore never masks the `429` that should trip the breaker, so `rate_limit_hits` and cooldown state stay accurate.

### Tiered Router (`apps/free_llm_proxy/router.py`)

Distributes traffic across Tier 1 providers using round-robin counters to balance free-tier request limits. Healthy providers are tried before cooling-down ones; for free-only aliases, cooling providers are used only as a last resort when no healthy candidate remains. Routing is split into free and paid cost segments: for `*-go` aliases the order is free healthy ➔ free cooling ➔ paid healthy ➔ paid cooling, so a rate-limit storm can never promote the paid provider ahead of a still-usable free one. An explicit `provider/model` prefix moves that provider to the front of its segment. Providers declaring `enabled_in_auto: false` (such as local Strata) are excluded from the standard auto rotation unless explicitly targeted or opted in: `strata-auto` and `strata-auto-go` move Strata to the front of the free segment, while `auto-strata` and `auto-strata-go` add it to the Tier 1 rotation. Paid providers declare `billing: "paid"` and an `auto_aliases` allowlist; eligibility is fail-closed, so a missing or edited `enabled_in_auto` flag cannot leak paid spend into a free alias. Tier buckets are created dynamically from each provider's normalized integer `tier` value (malformed values fall back to the default rather than crashing), and the paid OpenCode Go pool sits at Tier 3.

Model resolution is allowlist-driven and provider-agnostic. `_filter_provider_candidates` narrows both the live catalog and the provider's `preferred_patterns` through the allowlist (falling back to `dynamic_fallback_model` when the pattern list empties), and the resolution helpers `_fallback_model`, `_resolve_prefixed_model`, and `_finalize_resolved_model` re-validate every candidate — including an explicitly prefixed `provider/model` request — against the allowlist before dispatch. Gemini keeps its dedicated `_is_modern_gemini_flash` guard (Flash-only, legacy 1.5/2.0/2.5 excluded) layered on top of the generic allowlist path.

### Provider Output Ceilings & Thinking Passthrough (`apps/free_llm_proxy/server.py`, `providers.json`)

Before dispatch, requests routed to any non-Strata (cloud) provider are rewritten by two helpers. `apply_output_ceiling` clamps `max_tokens` and `max_completion_tokens` to `min(requested, p_cfg["max_output_tokens"])` — the provider's own declared ceiling (`gemini`, `nous`, `kilo`, `openrouter`, `nvidia`, and `opencode-go` all declare `65536`; `groq` is held at `32768` because its smaller models reject 65536 with HTTP 400), falling back to `CLOUD_MAX_OUTPUT_TOKENS` (default `65536`) only for a provider that declares none. Because reasoning tokens are billed inside the completion budget, this ceiling **is** the thinking budget: the previous global `16384` clamp silently truncated chain-of-thought-heavy answers, and every engine caller already requested exactly that ceiling. Strata is exempt from the clamp and keeps the caller's full budget (e.g. 131,072 tokens); its `providers.json` entry declares `max_output_tokens: 65536` for documentation parity, but the exemption means that value is never applied. `apply_thinking_params` strips every thinking key (`reasoning_effort`, `reasoning`, `reasoning_budget_tokens`) and re-adds only those the provider declares in `thinking_params` — `reasoning_effort` for `gemini`/`groq`, a normalized `{"effort": ...}` object for `openrouter`/`nous`, nothing for gateways that 400 on unknown fields (`nvidia`, `kilo`, `opencode-go`). A Strata-style `reasoning_budget_tokens` sent to a cloud provider is translated into an effort band (`>8192` high, `>4096` medium, else low) instead of being silently dropped, and `AUTO_GO_DEFAULT_REASONING_EFFORT` (default unset) can impose an explicit floor on `*-go` aliases.

### Failover Policy Module (`apps/free_llm_proxy/failover.py`)

Pure policy, no I/O: everything here is a decision about *what to do next*, which is what makes the never-unanswered contract testable without a socket.

The guarantee is deliberately precise: a **non-streaming** request ends in an answer or a real error inside its own per-request budget (free segment plus paid segment). Streams keep their unbounded relay semantics, because the head of a stream is what an interactive caller is waiting on and cutting it loses work that was already billed upstream.

One request-scoped deadline is enforced at *every* dispatch — the attempt loop and the in-provider cascade both recompute what is left before firing — so no provider can silently spend the budget several times over.

Key constructs:
- `AttemptBudget` — either `skip` (segment budget spent, do not dispatch) or `cap_s` (wall-clock cap for this one attempt). `UNCAPPED` is used for Strata and when the kill switch is disabled.
- `attempt_budget(provider_cfg, remaining_s)` — returns the cap for one attempt inside the currently-spending segment. The free segment passes its own remaining budget; the paid segment passes the paid budget, so the sum of every attempt in a pass can never exceed `FREE_PASS_DEADLINE_SECONDS + PAID_PASS_DEADLINE_SECONDS`.
- `plan_models(provider_cfg, available_models)` — catalog models covered by the provider's own plan, discovered live. Order follows `free_model_patterns` so the cheapest declared pattern wins first. Model ids are never hardcoded.
- `is_plan_model(provider_cfg, model)` — true when `model` is covered by the provider's plan, not metered.
- `last_resort_model(provider_cfg, available_models)` — the single metered model this provider may spend on, grounded in the catalog. A retired or renamed pin falls back to the catalog-resolved model instead of turning every request into a 502.
- `opencode_go_attempts(provider_cfg, available_models, resolved_model)` — ordered `(model, metered)` attempts for a plan-bearing provider: plan-included models first, then exactly one metered model.
- `is_futile_rate_limit(status_code, body)` — true for a 429 that a same-provider retry cannot clear (daily/plan quota, TPD, exhausted free-tier requests). The cascade re-checks this before *every* retry.
- `cascade_candidates(provider_id, provider_cfg, status_code, target_model, available_models)` — returns the ordered allowed fallback model IDs for an in-provider retry. Static `IN_PROVIDER_CASCADES` entries still apply where declared (Gemini, OpenRouter, NVIDIA NIM, Kilo Code); otherwise a provider may declare `cascade_statuses` (e.g. `nous` → `[400, 429, 503]`) and the cascade is built from the live catalog, ordered by `preferred_patterns` so retired checkpoints are never hardcoded. Dynamic cascades are capped at `_MAX_DYNAMIC_CASCADE_RETRIES` (2) models, and every candidate is re-validated against the provider's allowlist.
- `IN_PROVIDER_CASCADES` — declarative table of adjacent models per provider for transient failures (Gemini, OpenRouter, NVIDIA NIM, Kilo Code).

### Cloud Wall-Clock Dispatch Timeout (`_dispatch_with_timeout`, `apps/free_llm_proxy/server.py`)

Every upstream attempt on a non-Strata route is wrapped in `asyncio.wait_for(..., timeout=CLOUD_REQUEST_TIMEOUT_SECONDS)` (default `90.0`s, deliberately below the caller's own patience — live trader 200s, engine instructor clients 180s — so one failover still fits in the caller's window). A provider that accepts the connection but never finishes — a hung socket, a silently stalled stream, or an aggressively throttled gateway — is cancelled and converted into a `504` `timeout_error`, the same shape `client.build_timeout` produces on a real `httpx.TimeoutException`, so the failover chain advances instead of pinning the request.

`_dispatch_with_timeout` now accepts an optional `budget_s` parameter that tightens the configured cap for this one attempt (the free segment's remaining budget, or the paid tier's own smaller cap). `None` keeps the provider-wide default.

Strata and any non-positive timeout are exempt and dispatched unwrapped, preserving deep local reasoning runs that legitimately exceed the cloud cap. Non-streaming passes are bounded by one deadline per segment, and the deadline is re-checked before *every* dispatch — the attempt loop and each in-provider cascade retry both recompute what is left, so a four-model cascade cannot spend the budget four times over. `FREE_PASS_DEADLINE_SECONDS` (120s) bounds the free segment, `PAID_PASS_DEADLINE_SECONDS` (45s) bounds the metered one, and `FREE_ATTEMPT_TIMEOUT_SECONDS` / `PAID_ATTEMPT_TIMEOUT_SECONDS` (45s each) cap a single attempt. A remainder below `MIN_ATTEMPT_SECONDS` (2s) is skipped rather than dispatched, so a harness deadline is never recorded as provider misbehaviour. Total worst case is 165s, inside the engine's 180s caller timeout, instead of the 272-721s observed before the bound. Streaming keeps the unbounded semantics, because the head of a stream is what an interactive caller is waiting on.

Money control is routing, not a timeout flag: the paid provider's `auto_aliases` allowlist keeps it out of every free alias. There is no `PAID_TIMEOUT_GUARD` flag to configure or misconfigure.

### Fail-Closed Candidate Resolution (`_resolve_candidate_model`)

Before any request is sent, `chat_completions` resolves the target model through `_resolve_candidate_model(p_id, p_cfg, requested_model, available_models, is_paid=...)` and re-validates it against the provider's allowlist. It refuses dispatch — recording a `failover_chain` entry and continuing to the next candidate — when:

- a **paid** provider's live catalog is unavailable (`<provider> (catalog unavailable; paid dispatch refused)`);
- a **free-only** provider (allowlist declared, no `dynamic_fallback_model`) has an unavailable catalog (`<provider> (catalog unavailable; free-only dispatch refused)`);
- no allowed model resolves (`<provider> (no allowed free model resolved)`).

A declared `dynamic_fallback_model` is substituted when the resolved model is disallowed, so `openrouter`/`kilo` degrade to their known free alias instead of failing. Providers without one fail closed rather than dispatching an ungrounded model name.

### Audit Database (`apps/free_llm_proxy/db.py`)

Persists call traces, prompt tokens, completion tokens, latency, failover chains, caller attribution, stream telemetry (`is_stream`, `usage_available`, `ttft_ms`, `duration_ms`, `stream_completed`), and **billing provenance** (`billing`) to a local SQLite database (`data/free_llm_proxy.db`). Captures "Who" (`client_ip` via Cloudflare `CF-Connecting-IP`, `X-Forwarded-For`, or socket host, and `user_agent`) and "Why" (`purpose` via `X-Purpose` / `X-Client-Id` and `prompt_preview` containing a 60-character snippet of the user prompt). Logs failed authentication attempts (status 401) with caller IP and user agent to monitor unauthorized probes. `get_metrics()` aggregates total/successful/unauthorized requests, success rate, token totals, average latency, per-provider stats, the 10 most recent calls, the token-coverage fields `streaming_requests`, `usage_available_requests`, `zero_token_successes`, `token_coverage_pct`, `avg_stream_duration_ms`, `avg_ttft_ms`, and `incomplete_streams`, plus the paid-usage fields `paid_calls_total`, `paid_calls_24h`, and `paid_tokens_24h`. Additive migrations preserve existing rows, and indexes on `timestamp`, `status_code`, and `client_ip` keep metrics queries fast. Audit rows are retained indefinitely (no retention job).

#### Paginated Audit Reads (`get_logs`)

`AuditDB.get_logs(limit=50, offset=0, status_code=None, provider=None, billing=None)` backs the `GET /v1/logs` endpoint (see [[entities/llm-logs]]). It clamps `limit` to `1..200` and `offset` to `>= 0`, builds static `WHERE` clauses for the active filters (`status_code = ?`, `routed_provider = ?`, `billing = ?`), runs a `COUNT(*)` for the unfiltered-by-page `total`, and selects the audit row projection ordered `timestamp DESC, rowid DESC` so the newest call is always first. The stored `failover_chain` JSON string is parsed into a list before returning (falling back to `[]` on malformed JSON or a non-list value), so callers never decode it themselves. The response shape is `{ total, limit, offset, logs }`.

#### Billing Provenance (`billing`)

Every `call_logs` row records which cost class actually served the request, so "our paid spend is capped" becomes a number an operator can read rather than an assumption.

- **Column** — `billing TEXT DEFAULT 'free'`, added through the additive `migrations` dict in `AuditDB` (the same `ALTER TABLE ... ADD COLUMN` path used for `ttft_ms`, `duration_ms`, and `stream_completed`), so an existing database upgrades in place with no data loss.
- **Write path** — `log_call(..., billing: str = "free")` persists the value, and `chat_completions` passes `billing=str(p_cfg.get("billing") or "free")` on **both** the streaming and non-streaming success paths. A provider that declares `billing: "paid"` in `providers.json` (currently `opencode-go`) is therefore labelled `paid`; every other provider defaults to `free`.
- **Startup backfill** — `AuditDB.backfill_paid_billing(paid_providers)` relabels rows written before the column existed: `UPDATE call_logs SET billing = 'paid' WHERE billing = 'free' AND routed_provider IN (...)`, with the provider list built from `router.providers` entries whose `billing == "paid"`. `server.py` runs it once at import time inside a `try/except` so startup hygiene can never block serving traffic, and an empty provider list is a no-op returning `0`.
- **Metrics** — `get_metrics()` returns `paid_calls_total` (all-time paid rows), `paid_calls_24h`, and `paid_tokens_24h`. The 24-hour cutoff is computed as `(datetime.now(UTC) - timedelta(hours=24)).isoformat()` and compared directly against the stored `timestamp` string, because `timestamp` is a lexicographically sortable ISO-8601 value with a `T` separator — SQLite's `datetime()` form uses a space and would over-count the window by up to a day.

### Streaming & SSE (`apps/free_llm_proxy/streaming.py`, `client.py`)

Streams `text/event-stream` chunks directly to chat clients, but never ends a response on a bare EOF. `prime_sse_stream` reads the first chunks *before* the `200` is committed: a provider that closes (or raises) before its first content delta is closed, logged in the `failover_chain` as `(stream ended before first token)`, struck on the breaker, and the next candidate is dispatched instead. Once headers are out the proxy can no longer fail over, so `audited_sse_stream` guarantees a terminal chunk: streams are relayed as whole SSE events (LF, CRLF or CR framed, never re-framed from byte patterns), a `finish_reason` frame that arrives without `[DONE]` gets the terminator appended, and a stream with no `finish_reason` at all is closed with `{"choices":[{"index":0,"delta":{},"finish_reason":"length"}],"x_proxy_truncated":"upstream_eof"}` plus `data: [DONE]` while being recorded as `stream_completed = 0` with `error_message = "stream truncated: upstream ended without a finish_reason chunk"` and a `CircuitBreaker.record_stream_failure` strike (two consecutive truncations cool the provider). Duplicate, early, batched-with-content and split `[DONE]` markers are normalised to exactly one terminator with nothing after it. A stream that cannot be framed — one event exceeding `MAX_PARSE_BUFFER_BYTES` — degrades explicitly to raw pass-through and is logged as truncated (`stream degraded: SSE event exceeded N bytes`), never as a success; a client that hangs up mid-stream is recorded as cancelled and is neutral for the breaker. Dispatch-time success resets are skipped for streaming calls so a flaky provider cannot clear its own strikes before its body drains, and the upstream stream is always closed on exit (including disconnect), so an abandoned httpx response is never left to the garbage collector. Strict OpenAI clients (pi, the OpenAI SDKs) otherwise raise `Stream ended without finish_reason` on exactly this failure, which is what produced pi's `auto-go` error storm before this contract existed. A stream that already terminates is byte-identical: the parser reads `data:` lines from a bounded buffer and logs the final `usage` object after the stream completes, errors, or the client disconnects; it never injects `stream_options` and never re-frames a provider payload. Strata, Groq, Kilo, and OpenRouter already emit usage in their default streaming responses; providers that omit it are marked `usage_available = 0` instead of silently claiming zero tokens. Strata may hold an SSE stream open with `: keep-alive` frames while processing a large prompt; the proxy forwards those frames unchanged, applies **no total duration cap**, records TTFT and total duration, and marks the row `stream_completed = 0` if the client disconnects first. Clients should use `stream: true` for long Strata prompts; if time-to-first-token can exceed 5–10 minutes, use an asynchronous job queue rather than a synchronous HTTP request.

### Unauthorized Spike Monitor (`apps/free_llm_proxy/security.py`)

Keeps a rolling in-memory window of 401 attempts and emits one structured `security.401_spike` warning when the configured threshold is crossed. It is log-only (no external calls) and exposes `unauthorized_last_5m`, `unauthorized_window_seconds`, and `security_alert_active` in metrics.

### Connection Error Resilience (`apps/free_llm_proxy/client.py`)

`execute_completion` wraps both the non-streaming `POST` and the streaming `build_request`/`send` probe in `try/except httpx.RequestError`. A connection refusal, DNS failure, or connect timeout is converted into a structured `503` response (`{"error": {"message": "Provider connection error: ...", "type": "connection_error"}}`) rather than propagating an unhandled exception. This lets the router cleanly fail over to the next candidate provider (e.g. `strata-auto` falling back to the auto pool when local Strata is offline). The default client uses `httpx.Timeout(60.0, connect=3.0)` so an unreachable provider is detected within 3 seconds.

## Cloud Wall-Clock Request Timeout

`httpx` read timeouts only catch a socket that goes quiet. A cloud provider can keep the connection warm, emit keep-alives or a slow trickle of bytes, and never deliver a usable completion — which pins a proxy request for the full read window while every other candidate sits idle. `_dispatch_with_timeout` bounds the *whole* attempt in wall-clock terms instead.

### Behavior

```python
async def _dispatch_with_timeout(
    provider_id, provider_cfg, payload, stream,
    budget_s: float | None = None,
) -> tuple[int, Any, dict[str, str]]:
```

- **Applies to every cloud attempt** — the primary dispatch plus each in-provider cascade step (Gemini, OpenRouter, NVIDIA NIM, Kilo Code, and catalog-driven cascades such as Nous) routes through `_dispatch_with_timeout`, so a hung fallback model is bounded exactly like the primary one.
- **`budget_s` tightens the cap** — the free segment passes its remaining budget; the paid segment passes its own smaller cap. `None` keeps the provider-wide default.
- **Returns `504`, not an exception** — the synthesized `504` `timeout_error` body flows through the normal status-code handling, so the router advances to the next candidate and the attempt is recorded in the audit `failover_chain` as `<provider> (HTTP 504)`.
- **Empty non-streaming completions fail over (`is_empty_completion` in `failover.py`)** — if a non-streaming upstream returns HTTP `200` with no usable output (blank or ` thinking`-only `content` across all choices and no `tool_calls`, `function_call`, `refusal`, or `audio`, e.g., from reasoning exhaustion or a silent 0-token response), `_dispatch_with_timeout` converts it to `503 empty_completion` and records `<provider> (empty completion)` in `failover_chain` so in-provider cascades and cross-provider failover advance instead of returning `200` with empty text.
- **Strata is exempt** — local inference legitimately runs for minutes on deep reasoning prompts, so `provider_id == "strata"` bypasses the wrapper entirely and keeps its full budget with no total duration cap.
- **Kill switch** — setting `CLOUD_REQUEST_TIMEOUT_SECONDS` to `0` (or any non-positive value) disables the cap for all providers, restoring the plain `execute_completion` path.

### Configuration

| Variable | Default | Meaning |
| :--- | :--- | :--- |
| `CLOUD_REQUEST_TIMEOUT_SECONDS` | `90.0` | Wall-clock cap applied to each non-Strata provider attempt, and the httpx read window (`client.build_timeout`). On expiry the attempt returns `504 timeout_error` and failover continues. Strata exempt; `<= 0` disables |
| `FREE_ATTEMPT_TIMEOUT_SECONDS` | `45.0` | Tighter non-streaming cap for a free candidate, further clamped by the remaining free budget. |
| `PAID_ATTEMPT_TIMEOUT_SECONDS` | `45.0` | Non-streaming cap for the paid last resort, so one metered call cannot pin the pass. |
| `FREE_PASS_DEADLINE_SECONDS` | `120.0` | Whole free-segment budget for non-streaming calls, re-checked at every dispatch including cascade retries. Once spent, remaining free candidates are skipped with a `free pass deadline exhausted` entry in the failover chain and the paid tier runs. `<= 0` disables. |
| `PAID_PASS_DEADLINE_SECONDS` | `45.0` | Whole metered-segment budget on top of the free one; worst case for a non-streaming pass is `FREE + PAID` = 165s. `<= 0` disables. |
| `CLOUD_MAX_OUTPUT_TOKENS` | `65536` | Fallback clamp for providers that declare no `max_output_tokens` in `providers.json`. |
| `AUTO_GO_DEFAULT_REASONING_EFFORT` | unset | Optional `low`/`medium`/`high` thinking floor for `*-go` aliases; only sent to providers declaring `thinking_params` |

## Dynamic Model Discovery & Anti-Hardcoding Philosophy

A foundational architectural principle of Free LLM Proxy is **zero hardcoded model pinning**:

1. **Model Obsolescence Rate**: Frontier and fast-tier LLM models churn rapidly. Checkpoint names are sunset and replaced on weeks-long cadences (e.g., Google advancing from Gemini 1.5 to 2.0 to 3.x Flash, Groq updating Qwen and Llama checkpoints). Hardcoding specific model strings in clients or configurations creates constant maintenance friction, broken upstream calls, and silent degradation.
2. **Dynamic Provider Catalog Ingestion (`discovery.py`)**: The proxy queries each active provider's live `/models` endpoint at runtime and caches the catalog. New models released by providers are immediately discovered and become available to the router without requiring code commits or proxy restarts.
3. **Official Provider Dynamic Aliases**: Wherever an upstream provider supports an official moving pointer (such as Google's official `gemini-flash-latest` or OpenRouter's `openrouter/free`), the proxy targets the alias as the primary pattern. This ensures downstream callers automatically receive newly promoted versions without intervention.
4. **Resilient In-Provider Fallback**: If an upstream bleeding-edge model experiences high-demand spikes (e.g. Google HTTP 503 on `gemini-flash-latest`), the proxy cascades down through adjacent active generation variants (e.g. `gemini-3.6-flash`, `gemini-3.5-flash`) before tripping circuit breakers. Providers that declare `cascade_statuses` get the same behavior built from their live catalog rather than a hardcoded list.
5. **Virtual Alias Abstraction**: Callers (such as the Pi agent or background prediction routines) consume generic virtual aliases (`free-auto`, `strata-auto`, `free-fast`, `free-reasoning`). Clients never specify brittle upstream IDs, allowing the routing engine to swap, balance, and heal underlying model targets transparently.

## Model Resolution & Provider Targeting

`Router.resolve_model_for_provider(provider_id, requested_model, available_models)` maps the client-supplied `model` string onto a concrete provider model ID. Resolution order:

1. **Local Strata** — when `provider_id == "strata"`, a `strata/<model>` prefix is stripped and matched against the live catalog; otherwise the requested model is used if present in the catalog, else the first live model, else the literal `"strata"`.
2. **Virtual alias** — if `requested_model` is a key in `virtual_aliases` (e.g. `free-auto`), its pattern list is used.
3. **Default/auto** — `default`, `auto`, or the empty string resolve to the `free-auto` patterns.
4. **Exact catalog match** — if `requested_model` is present in the discovered `available_models`, it is returned after allowlist re-validation.
5. **Explicit `provider/model` prefix** — the prefix is stripped and the remainder matched against the catalog. The literal `openrouter/free` is special-cased and returned as-is (it is a real OpenRouter model ID, not a `provider/model` pair, so it must never be stripped down to `free`). A stripped model that violates the provider's allowlist (or Gemini's Flash-only guard) falls back through `_fallback_model`.
6. **Pattern fallback** — otherwise the first `preferred_patterns` entry matching the catalog is used, then `_finalize_resolved_model` re-validates the result against the allowlist and Gemini's Flash guard.

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

This guarantees zero compute cost while preventing breaking changes when Google promotes new Flash iterations.

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

The `openrouter` provider operates as a mixed marketplace of paid and free models. Zero-cost isolation is expressed declaratively through `allowed_model_patterns: ["*:free", "openrouter/free"]` plus `dynamic_fallback_model: "openrouter/free"`:
- **Discovered Catalog Filtering (`discovery.py`)**: Models fetched from OpenRouter's live `/models` endpoint are filtered at ingestion time by the allowlist, so only zero-cost variants ending with `:free` or equaling `openrouter/free` survive. Paid models are stripped before pattern matching can evaluate them.
- **Resolution Safety Gate (`router.py`)**: Virtual aliases (such as `free-auto`) and provider patterns are restricted to `:free` variants. If an explicit paid model is targeted or no pattern matches, the router coerces the model to `openrouter/free`.
- **Server Dispatch Guard (`server.py`)**: `_resolve_candidate_model` re-validates the resolved model against the allowlist and substitutes `dynamic_fallback_model` when it is disallowed, ensuring 100% hermetic zero-cost inference.
- **Attribution Headers**: Requests to OpenRouter pass `HTTP-Referer: https://llm.clvg.uk` and `X-Title: Pi / Free LLM Proxy`.

### Kilo Code Zero-Cost Isolation

The `kilo` provider (`requires_auth: false`) also operates as a mixed marketplace of free and paid models. It declares `allowed_model_patterns: ["*:free", "*-free", "kilo-auto/free"]` and `dynamic_fallback_model: "kilo-auto/free"`, which prevents HTTP 401 `PAID_MODEL_AUTH_REQUIRED` failures:
- **Discovered Catalog Filtering (`discovery.py`)**: Strips paid models and retains only zero-cost variants (`:free`, `*-free`, or `kilo-auto/free`).
- **Resolution Safety Gate (`router.py`)**: Prioritizes `kilo-auto/free` and coerces unrecognized models to `kilo-auto/free` before dispatch.
- **In-Provider Cascade (`server.py`)**: If a specific model returns 401/429/503, the proxy falls back through `kilo-auto/free`, `reflection/beam-free`, and `nvidia/nemotron-3.5-super-vl:free` before leaving the provider.

### Nous Research (`nous`)

Tier 1 provider at `https://inference-api.nousresearch.com/v1`, activated by `NOUS_RESEARCH_KEY` (`requires_auth: true`). It is a mixed marketplace, so it declares `allowed_model_patterns: ["*:free"]` and is filtered to zero-cost models only (`qwen/qwen4-max:free`, `tencent/hy4-flash:free`, `meituan/longcat-2.5:free`, `stepfun/step-3.7-flash:free`, `upstage/solar-mini4:free` at the time of writing). `preferred_patterns` orders the catalog `qwen4-max` → `hy4-flash` → `longcat-2.5` → any `:free`.

- **Thinking passthrough** — declares `thinking_params: ["reasoning"]`, so a caller's `reasoning_effort` is normalized into `{"effort": ...}` exactly as for OpenRouter.
- **Output ceiling** — `max_output_tokens: 65536`.
- **Catalog-driven cascade** — `cascade_statuses: [400, 429, 503]` enables in-provider cascades built from the live catalog. A `400` on one `:free` model (e.g. a missing-tags rejection) retries the next allowed `:free` model instead of cooling the whole provider.
- **Fail-closed** — with no `dynamic_fallback_model`, an empty or paid-only catalog is refused (`nous (catalog unavailable; free-only dispatch refused)`) rather than dispatching an ungrounded model name.
- **Rotation** — `nous` participates in the Tier 1 rotation for `free-auto`, `auto-strata`, and `auto-go` whenever `NOUS_RESEARCH_KEY` is set; without the key it disappears from `get_active_providers()`.

### OpenCode Go Paid-Tier Isolation

OpenCode Go (`opencode-go`) is a paid `$10/month` subscription, not a free-tier provider, so it is isolated from every zero-cost alias:
- **Alias gating (`router.py`)**: `billing: "paid"` plus an `auto_aliases` allowlist makes eligibility fail-closed. Go is only added to the candidate chain for `auto-go`, `auto-strata-go`, and `strata-auto-go` (or when explicitly targeted). `free-auto`, `auto-strata`, `free-fast`, `free-reasoning`, `strata-auto`, `auto`, and `default` never include it, even if an `enabled_in_auto` flag is edited away.
- **Last-resort placement (`tier: 3`)**: The router builds separate free and paid cost segments and appends Go after both the healthy and cooling free candidates, so the free pool is exhausted before any paid request is made — including during a 429 cooldown storm.
- **Key-gated activation**: The provider has `requires_auth: true` and `env_key: OPENCODE_GO_API_KEY`. With no key configured, it disappears from `get_active_providers()` and the `*-go` aliases degrade transparently to the free pool.
- **Fail-closed dispatch**: If Go's live `/models` catalog cannot be read, the proxy refuses to dispatch a paid request rather than sending an ungrounded model name.
- **Dynamic catalog**: `base_url` is `https://opencode.ai/zen/go/v1`; the live roster is discovered from `GET /models`, so no model names are hardcoded.
- **Session affinity (`session.py`)**: Go rejects requests without `x-opencode-session`. The proxy forwards a client-supplied header when it matches a short header-safe charset, otherwise derives a stable `fllm-<sha256>` ID from caller identity plus the first user message so multi-turn conversations keep the same routing/caching session.
- **Free-plan models before metered ones (`free_model_patterns`)**: Inside Go the attempt order is subscription-included models first — `free_model_patterns` (default `["*free*"]` — `beam-free`, `longcat-2.5-free`, `hy4-flash-free`, `iceman-contributor-free` at the time of writing) matched against the live catalog — so failing over inside the plan costs nothing extra. `last_resort_model` (`deepseek-v4.1-flash`) is the single metered model the provider may spend on, tried after every free-plan model; at most one metered model is dispatched per request, so a failed metered attempt is never followed by a second paid model. A retired pin logs a warning and degrades to the catalog-resolved model instead of turning every `*-go` request into a 502; a plan pattern that matches nothing logs a warning too, so a renamed free model cannot silently make the provider "spend first"; an empty catalog still refuses the paid dispatch.
- **Explicit targeting**: `opencode-go/<model>` (or bare `opencode-go`) moves the provider to the front of the chain for deliberate per-model use, with normal failover behind it, and bypasses the free-first reordering because the charge is intentional.
- **Billing provenance**: every Go-served request is written to `call_logs` with `billing = 'paid'`, which is what feeds `paid_calls_total` / `paid_calls_24h` / `paid_tokens_24h` in `/v1/metrics`.

Money control is **routing**, not a timeout branch: `providers.json` gives the paid provider an `auto_aliases` allowlist, and the router admits it only to those aliases (or to an explicit `opencode-go/...` request). A free alias therefore never sees a paid candidate at all — there is no timeout-keyed guard to configure, and none to leak spend through a stale flag.

### Resilient In-Provider Demand-Spike Cascades

When an upstream endpoint returns temporary errors (503 high-demand spike, 404 deprecated function, 429 rate limit, or a proxy-level 504 wall-clock timeout), the proxy automatically cascades through alternative models on the *same* provider before tripping circuit breakers and moving to the next provider:
- **Google Gemini**: Cascades from `gemini-flash-latest` ➔ `gemini-3.8-flash` ➔ `gemini-3.6-flash` ➔ `gemini-3.5-flash`.
- **OpenRouter**: Cascades from the primary model ➔ `openrouter/free` ➔ `nvidia/nemotron-3-ultra-550b-a55b:free` ➔ `nvidia/nemotron-3.5-super-vl:free` ➔ `nvidia/nemotron-3.5-lightning:free`.
- **NVIDIA NIM**: Cascades from the primary model ➔ `minimaxai/minimax-m3.1-flash` ➔ `nvidia/nemotron-3.5-super-vl-120b-a12b` ➔ `nvidia/nemotron-3-ultra-550b-a55b` ➔ `mistralai/mistral-large-4-1t-a52b`.
- **Kilo Code**: Cascades from the primary model ➔ `kilo-auto/free` ➔ `reflection/beam-free` ➔ `nvidia/nemotron-3.5-super-vl:free`.
- **Nous Research** (catalog-driven): On `400`/`429`/`503`, cascades through up to 2 further allowed `:free` models ordered by `preferred_patterns`.

The cascade re-checks the segment budget before *every* retry, so a multi-model provider cannot spend the request budget several times over, and quota-dead 429s stop the cascade mid-way instead of only at its start. When no fallback answers, the highest-priority failure status is preserved (see Circuit Breaker) so a trailing `404`/`504` never masks a `429`.

- **Server & Request Helpers (`apps/free_llm_proxy/server.py`, `request_helpers.py`)** — `server.py` owns HTTP routes, auth, dispatch, and audit logging, while `request_helpers.py` holds pure thinking-param stripping/passthrough, output-ceiling clamping, candidate resolution, and prompt/client metadata extraction.

## Provider Output Ceilings & Thinking Passthrough (Behavioral Rules)

Reasoning tokens are billed inside the completion budget on every OpenAI-compatible provider, so an output clamp **is** a thinking cap. The proxy therefore clamps to a per-provider ceiling declared in `providers.json` instead of a single global number, and forwards reasoning controls only to providers that declare support for them.

```python
# server.py, after model resolution and before execute_completion
if p_id != "strata":
    apply_thinking_params(payload, p_cfg, req.model)
    apply_output_ceiling(payload, p_cfg)
```

Behavioral rules:
- **Strata is exempt** — requests routed to the `strata` provider keep the caller's full budget (e.g. `max_tokens: 131072`) and the native `reasoning_budget_tokens` kwarg, since local inference has no cloud ceiling and understands it. Its `providers.json` entry declares `max_output_tokens: 65536`, but the exemption means the clamp never applies it.
- **Per-provider ceilings** — `max_output_tokens` in `providers.json` (`gemini`, `nous`, `kilo`, `openrouter`, `nvidia`, and `opencode-go` all declare `65536`; `groq` declares `32768` because it rejects 65536 with HTTP 400) is applied as `min(requested, ceiling)`. `CLOUD_MAX_OUTPUT_TOKENS` (default `65536`) covers only providers that declare nothing.
- **Clamping only lowers** — values at or below the ceiling pass through unchanged, and `None` is untouched. Both `max_tokens` and `max_completion_tokens` are handled independently.
- **Declared-only thinking passthrough** — `reasoning_effort` reaches `gemini`/`groq`; `openrouter` and `nous` receive it normalized to `{"effort": ...}` or get an explicit `reasoning` object verbatim; `nvidia`, `kilo`, and `opencode-go` never see any thinking key, because those gateways 400 on unknown fields and a deterministic 400 cools a healthy provider for the cooldown window.
- **Budget translation, not deletion** — a Strata-style `reasoning_budget_tokens` sent to a cloud provider is banded into `high` / `medium` / `low` (thresholds `REASONING_BUDGET_BANDS`, `>8192`/`>4096`) unless the caller also passed an explicit `reasoning_effort`, which always wins.
- **Optional floor** — `AUTO_GO_DEFAULT_REASONING_EFFORT` is empty by default so the provider default governs (Gemini 3 = dynamic/high); setting it applies a floor to `*-go` aliases only.

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
| `/v1/metrics` (alias `/stats`) | `GET` | Bearer Token | Total requests, token counts, latency, per-provider stats, circuit breaker status, stream usage coverage, paid-usage counters (`paid_calls_total`, `paid_calls_24h`, `paid_tokens_24h`), connector scope, and unauthorized-spike state |
| `/v1/logs` | `GET` | Bearer Token | Paginated `call_logs` audit stream. Query params: `limit` (clamped `1..200`, default `50`), `offset`, `status_code`, `provider` (matches `routed_provider`), `billing`. Returns `{ total, limit, offset, logs }` ordered newest-first, with `failover_chain` already parsed into a list. Backs the private `/llm-logs` page (see [[entities/llm-logs]]) |
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
| `CLOUD_MAX_OUTPUT_TOKENS` | `65536` | Fallback output-token ceiling for cloud providers that declare no `max_output_tokens`; Strata is exempt |
| `CLOUD_REQUEST_TIMEOUT_SECONDS` | `90.0` | Wall-clock cap on each non-Strata provider attempt (and the httpx read window); on expiry the attempt yields `504 timeout_error` and failover continues. Strata exempt; `<= 0` disables |
| `FREE_ATTEMPT_TIMEOUT_SECONDS` | `45.0` | Per-attempt cap for free candidates on non-streaming calls |
| `PAID_ATTEMPT_TIMEOUT_SECONDS` | `45.0` | Per-attempt cap for the paid last resort on non-streaming calls |
| `FREE_PASS_DEADLINE_SECONDS` | `120.0` | Whole free-segment budget for non-streaming calls, re-checked at every dispatch; past it, candidates are skipped with a logged reason. `<= 0` disables |
| `PAID_PASS_DEADLINE_SECONDS` | `45.0` | Whole metered-segment budget on top of the free one; worst case for a non-streaming pass is `FREE + PAID` = 165s. `<= 0` disables |
| `AUTO_GO_DEFAULT_REASONING_EFFORT` | unset | Optional `low`/`medium`/`high` thinking floor for `*-go` aliases; only sent to providers declaring `thinking_params` |
| `CONNECTOR_ID` | hostname | Connector identity returned by `/health` and `/v1/metrics`; compose sets `workstation` / `secondary` |
| `SECURITY_ALERT_401_THRESHOLD` | `20` | Unauthorized requests within the window required to emit one `security.401_spike` warning (`0` disables) |
| `SECURITY_ALERT_WINDOW_SECONDS` | `300` | Rolling window for the log-only 401 spike monitor |
| `GROQ_API_KEY`, `GEMINI_API_KEY_FREE`, `OPENROUTER_API_KEY`, `NOUS_RESEARCH_KEY`, `NVIDIA_API_KEY`, `OPENCODE_GO_API_KEY` | unset | Provider credentials; unset providers are simply excluded from the active pool. `NOUS_RESEARCH_KEY` activates the Nous Research Tier 1 provider (strictly `:free` models). `OPENCODE_GO_API_KEY` activates the paid Tier 3 fallback used only by `auto-go` / `auto-strata-go` / `strata-auto-go`. |

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

The test suite covers master-key auth rejection, the unauthenticated health probe, circuit-breaker tripping on 429, alias resolution against live catalogs, automatic failover when the primary returns 429, SSE streaming pass-through, metrics/models endpoints, and SQLite audit logging. It also verifies `openrouter/free` resolution (never stripped to `free` when the catalog is empty, prioritized as the first OpenRouter preferred pattern, and routed to OpenRouter as the first candidate) and end-to-end chat completion routing for `model: "openrouter/free"`. Additional coverage validates OpenRouter zero-cost isolation (paid models filtered from discovery, coerced to `openrouter/free` at resolution and dispatch), the Strata alias chains (`strata-auto` first, `auto-strata` in rotation, strict `strata` with no fallback), Strata cooldown bypass, `ENABLE_STRATA=false` provider removal, graceful `503` handling of `httpx.RequestError` connection failures, cloud output-token clamping (`test_max_tokens_unclamped_for_strata_and_clamped_for_cloud` — including `reasoning_budget_tokens` preservation on Strata and stripping on cloud routes), unauthorized 401 audit logging (`test_unauthorized_call_is_logged_in_audit_db`), Gemini Pro→Flash coercion (`test_gemini_pro_model_is_coerced_to_free_flash`), and the `GEMINI_API_KEY_FREE` provider key (`test_gemini_uses_gemini_api_key_free`). OpenCode Go coverage verifies that `auto-go` places `opencode-go` last and excludes Strata, `auto-strata-go` includes both Strata and Go, `strata-auto-go` puts Strata first and Go last, every free alias stays Go-free even with a key configured, the provider disappears without `OPENCODE_GO_API_KEY`, alias/prefix resolution works against a discovered catalog, and an end-to-end `auto-go` request exhausts free providers before calling Go exactly once (`test_auto_go_end_to_end_falls_back_to_go`), including forwarding the client `x-opencode-session` and preserving the Go `User-Agent`. An end-to-end `strata-auto-go` request proves the full `Strata ➔ free pool ➔ Go` failover path (`test_strata_auto_go_end_to_end_fails_over_strata_then_free_then_go`). Additional regressions prove that a full free-pool cooldown still tries cooling free candidates before paid Go, paid routing fails closed if its `auto_aliases` allowlist disappears, malformed `tier` values do not crash the router, and paid dispatch is refused when the live catalog is unavailable. Cloud wall-clock timeout coverage lives in `test_cloud_provider_timeout_triggers_504_failover` (a slow cloud candidate yields `504` and the request still succeeds via the next provider) and `test_strata_provider_exempt_from_cloud_wall_clock_timeout` (Strata is never cancelled by the cap). Session affinity derivation (client-header passthrough, sanitization of control characters and oversized IDs, stable multi-turn fallback, multimodal text extraction, caller-identity fallback) is covered by `apps/free_llm_proxy/tests/test_session.py`, and an autouse fixture resets the shared circuit breaker between tests. Stream telemetry in `apps/free_llm_proxy/tests/test_streaming.py`, `apps/free_llm_proxy/tests/test_streaming_integration.py`, and `apps/free_llm_proxy/tests/test_db_telemetry.py` verifies byte-for-byte SSE pass-through, usage parsing across chunk boundaries, malformed/oversized-frame resilience, callback failures, mid-stream errors, end-to-end Strata and cloud usage logging, the absence of any injected `stream_options`, legacy schema migration, and token-coverage metrics. Log-only 401 spike detection and connector-scoped metrics are covered by `apps/free_llm_proxy/tests/test_security.py`. `apps/free_llm_proxy/tests/test_stream_truncation.py` pins the terminal-chunk contract: byte-identical pass-through for complete streams, synthesized `finish_reason: length` + `[DONE]` for `only, clean-EOF and mid-stream-error cases, pre-token failover with the `(stream ended before first token)` chain entry, `502` when every candidate dies before its first token, truncation recorded as `incomplete_streams` and struck against the breaker, and the retired-provider catalog check. `apps/free_llm_proxy/tests/test_audit_billing.py` pins billing provenance: `log_call(..., billing=...)` persists the value and `get_metrics()` counts `paid_calls_total` / `paid_calls_24h` / `paid_tokens_24h`, an omitted `billing` defaults to `free`, and a paid row backdated 40 hours is excluded from the 24-hour window (guarding the ISO `T`-separator vs SQLite `datetime()` comparison). `apps/free_llm_proxy/tests/test_logs_endpoint.py` pins the `/v1/logs` contract: `401` without a master key, newest-first ordering, `provider` / `status_code` / `billing` filters, and `limit`/`offset` pagination reporting the unfiltered `total`. `apps/free_llm_proxy/tests/test_output_ceiling.py` pins the clamp semantics: a 64k request is lowered to a 32k provider ceiling, left alone on a 64k provider, never raised from a smaller request, clamped on both `max_tokens` and `max_completion_tokens`, falls back to `CLOUD_MAX_OUTPUT_TOKENS` for a provider that declares nothing, and ignores boolean/junk values. A `conftest.py` socket guard raises on any non-loopback connection, keeping the suite hermetic per [[concepts/test-coverage]].

Nous Research and the generic allowlist/cascade machinery are covered by `test_discovery_filters_nous_to_free_models_only` (discovery strips non-`:free` models), `test_nous_never_resolves_to_paid_model` (paid coercion, case-insensitive/whitespace prefix handling, wildcard rejection, empty-allowlist fail-closed, and ungrounded-catalog fail-closed), `test_nous_fail_closed_when_catalog_empty` (no dispatch when the catalog has no `:free` models), `test_nous_in_rotation_paid_coercion_and_reasoning_translation` (`nous` in the `free-auto`/`auto-strata`/`auto-go` chains, paid model coerced, `reasoning_effort` translated to `{"effort": "medium"}`), `test_nous_in_provider_cascade_on_400` (catalog-driven cascade across `:free` models), `test_cascade_preserves_429_when_fallback_returns_404`, and `test_multihop_cascade_503_then_429_then_404_preserves_429` (failure-priority preservation keeps the breaker tripped on the 429 and records one `rate_limit_hits`).

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
- [[concepts/auto-go-utility-llm]] — the engine-side consolidation that routes utility LLM calls through this proxy's `auto-go` alias
- [[entities/auto-wiki]] — the pre-commit documentation agent whose primary tier is this proxy's `auto-go` alias
- [[entities/live-agent-trader]] — the daemon whose inference path uses `query_multi_tier_llm` against this proxy
- [[entities/llm-logs]] — the private `/llm-logs` page that reads the `/v1/logs` audit endpoint
- [[entities/secondary-minipc-edge]] — hosts the `free-llm-proxy` container on port 8086
- [[concepts/test-coverage]] — hermetic testing mandates that apply to the proxy test suite
- [[concepts/env-based-secrets]] — secret-handling rules for `FREE_PROXY_MASTER_KEY` and provider credentials
