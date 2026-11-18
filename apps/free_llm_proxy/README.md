# Free LLM Proxy 🚀

A high-performance, model-agnostic OpenAI-compatible proxy that unifies free LLM inference providers into a single resilient endpoint with dynamic failover, circuit breaking, usage logging, and zero hardcoded model IDs.

---

## Features

- **Single Universal Endpoint**: Connect any OpenAI-compatible chat app, IDE, agent, or script to `http://localhost:8086/v1`.
- **Dynamic Model-Agnostic Discovery**: Queries live provider `/v1/models` catalogs. No broken model strings when providers release or retire checkpoints.
- **Smart Tiered Failover**:
  - **Tier 1 (High Performance)**: Groq (ultra-fast 120B/27B), Gemini (Flash Latest / 3.x Flash), Kilo Code (no key needed).
  - **Tier 2 (Fallback Pool)**: OpenRouter (17 `:free` models), NVIDIA NIM.
- **Zero Hardcoded Model IDs**: Relies on dynamic runtime `/models` discovery, official dynamic provider aliases (`gemini-flash-latest`, `openrouter/free`), and virtual model aliases (`free-auto`, `strata-auto`) to insulate clients from model obsolescence.
- **Circuit Breaker**: On HTTP 429 (rate limit), 5xx downtime, or two consecutive truncated streams, automatically cools down the provider and retries next candidate seamlessly.
- **Streaming & SSE**: Full pass-through token streaming (`stream: true`) with pre-flight failover protection. Bytes are forwarded unchanged, but every response is guaranteed to end with a chunk carrying a non-null `finish_reason` plus `data: [DONE]`, so a provider that dies early cannot leave a strict client staring at a bare EOF. The final `usage` chunk is parsed for telemetry after the stream completes.
- **Reasoning Token Preservation**: Preserves `reasoning` and thinking blocks for thinking models (`gpt-oss-120b`, `flint`, `beam`).
- **Local SQLite Audit DB**: Records every call, latency, token count, failover trace, stream usage availability, time-to-first-token, stream duration, and completion status to `data/free_llm_proxy.db`. Additive migrations preserve existing rows; indexes keep metrics queries fast. Audit rows are retained indefinitely.
- **Zero New Dependencies**: Built entirely with existing repository packages (`fastapi`, `uvicorn`, `httpx`, `pydantic`, `sqlite3`).

---

## Quickstart

### 1. Configure `.env`

Copy `.env.example` to `.env` (already initialized in `apps/free_llm_proxy/.env`):

```bash
PORT=8086
FREE_PROXY_MASTER_KEY=sk-free-proxy-secret-key-12345
GROQ_API_KEY=gsk_...
GEMINI_API_KEY_FREE=...
OPENROUTER_API_KEY=...
OPENCODE_GO_API_KEY=oc_sk_...
```

*Note: The proxy automatically activates whichever providers have keys configured in `.env`. Kilo Code works out of the box with zero keys! OpenCode Go is a paid subscription and is only reachable through the `auto-go` / `auto-strata-go` aliases or explicit `opencode-go/<model>` targeting; it never participates in the free aliases.*

### 2. Start the Server (Docker or Local)

#### Option A: Docker (Recommended - Auto-starts on boot)
```bash
docker compose -f apps/free_llm_proxy/docker-compose.yml up -d
```
To view logs:
```bash
docker compose -f apps/free_llm_proxy/docker-compose.yml logs -f
```

#### Option B: Local Python
```bash
./apps/engine/.venv/bin/python3 apps/free_llm_proxy/main.py
```

Server will start on `http://0.0.0.0:8086`.

---

## Client Usage Examples

### 1. Curl

```bash
curl http://localhost:8086/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-free-proxy-secret-key-12345" \
  -d '{
    "model": "free-auto",
    "messages": [
      {"role": "user", "content": "Explain quantum computing in one sentence."}
    ]
  }'
```

### 2. Python (OpenAI SDK)

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8086/v1",
    api_key="sk-free-proxy-secret-key-12345",
)

response = client.chat.completions.create(
    model="free-auto",  # or "free-fast", "free-reasoning", or "deepseek-chat"
    messages=[{"role": "user", "content": "Hello!"}],
)

print(response.choices[0].message.content)
```

### 3. Chat Apps (Open WebUI, LibreChat, Chatbox, Cursor)

- **Provider**: OpenAI
- **Base URL**: `http://localhost:8086/v1`
- **API Key**: `sk-free-proxy-secret-key-12345` (matches `FREE_PROXY_MASTER_KEY` in `.env`)
- **Model**: `free-auto` (or `free-fast`, `free-reasoning`, or any model name)

---

## Virtual Model Aliases

| Alias | Description | Target Family |
| :--- | :--- | :--- |
| **`free-auto`** (Default) | Best overall model available across healthy active pool (Strata excluded) | 120B / 70B / Flash models |
| **`strata-auto`** | Prioritizes local Strata (localhost:8080); fails over cleanly to auto pool when offline | Local live model / Orcarouter ➔ Auto pool fallback |
| **`auto-strata`** | Adds Strata into the standard Tier 1 round-robin auto rotation pool | Local Strata + Tier 1 providers |
| **`auto-go`** | Free auto pool with OpenCode Go as a last-resort paid fallback (Strata excluded) | Tier 1+2 free providers ➔ OpenCode Go |
| **`auto-strata-go`** | Same as `auto-go`, but Strata joins the Tier 1 rotation | Local Strata + Tier 1+2 free providers ➔ OpenCode Go |
| **`strata-auto-go`** | Strata primary; on failure falls over the free pool, then paid OpenCode Go | Local Strata ➔ Tier 1+2 free providers ➔ OpenCode Go |
| **`strata`** | Strictly targets local Strata; fails fast with error if offline (zero silent cloud fallback) | Whichever model is live on localhost:8080 |
| **`free-fast`** | Sub-second ultra-low latency models | 20B / 8B / Flash-Lite models |
| **`free-reasoning`** | Deep reasoning / thinking models | DeepSeek-R1, Flint, Beam, QwQ |
| **Any Custom Name** | Pass-through or fallback (e.g. `deepseek-chat`, `gpt-4o`) | Automatically routes via `free-auto` |
| **Targeted Provider** | Explicitly target a provider first (e.g. `groq/qwen3.8-27b`) | Routes to specified provider with fallback |

### OpenCode Go (Paid Tier)

`opencode-go` discovers its catalog from `https://opencode.ai/zen/go/v1/models` — there is no model list to maintain. Set `OPENCODE_GO_API_KEY` to activate it. It is **never** part of `free-auto`, `auto-strata`, `free-fast`, or `free-reasoning`; only `auto-go`, `auto-strata-go`, `strata-auto-go`, and explicit `opencode-go/<model>` requests can reach it. Within the `*-go` aliases it sits after both the healthy and cooling free candidates, so a 429 cooldown storm still tries free providers first. If its catalog cannot be read, the proxy fails closed instead of sending a paid request with an ungrounded model name.

Inside Go the order is **plan-included models first, then one metered model**:

1. `free_model_patterns` (`["*free*"]`) matched against the live catalog — today `beam-free`, `longcat-2.5-free`, `hy4-flash-free`, `iceman-contributor-free`. These are covered by the Go subscription, so failing over to them costs nothing extra.
2. `last_resort_model` (`deepseek-v4.1-flash`) — the single metered model this provider is allowed to spend on. If the live catalog no longer lists it, the proxy logs a warning and falls back to the catalog-resolved model rather than inventing an id or turning every request into a 502.
3. The normally resolved model, as a final grounded attempt.

An explicit `opencode-go/<model>` request bypasses this ordering: the caller is deliberately charging that model.

Money control is **routing**, not a timeout branch: `providers.json` gives the paid provider an `auto_aliases` allowlist, and the router admits it only to those aliases (or to an explicit `opencode-go/...` request). A free alias therefore never sees a paid candidate at all — there is no timeout-keyed guard to configure, and none to leak spend through a stale flag. The proxy forwards a client `x-opencode-session` header only after validating it, or derives a stable fallback session ID automatically, since Go requires one on every chat request.

### Thinking Budgets and Output Ceilings

Reasoning tokens are billed inside the completion budget on every OpenAI-compatible
provider, so `max_tokens` / `max_completion_tokens` **is** the thinking cap. The
proxy therefore clamps to a per-provider ceiling instead of a single global number:

| Knob | Default | Effect |
| :--- | :--- | :--- |
| `providers.json` → `max_output_tokens` | gemini `65536`, all other cloud providers `32768` | Provider's own output/thinking ceiling. The clamp is `min(requested, ceiling)` and only ever lowers a caller's budget. |
| `CLOUD_MAX_OUTPUT_TOKENS` | `32768` | Fallback ceiling for providers that declare none. Strata is exempt (keeps its 128k+ budget). |
| `CLOUD_REQUEST_TIMEOUT_SECONDS` | `90.0` | Wall-clock cap per non-Strata attempt; also the httpx read window (`client.build_timeout`), so there is no second hidden cap. Non-streaming only — a streaming response returns its generator as soon as headers arrive. |
| `FREE_ATTEMPT_TIMEOUT_SECONDS` | `45.0` | Tighter per-attempt cap for free candidates (non-streaming), clamped further by what is left of the free budget. |
| `PAID_ATTEMPT_TIMEOUT_SECONDS` | `45.0` | Per-attempt cap for the paid last resort, so one metered call cannot pin the pass. |
| `FREE_PASS_DEADLINE_SECONDS` | `120.0` | Whole free-segment budget (non-streaming). Once spent, remaining free candidates are skipped with a `free pass deadline exhausted` entry in the failover chain and the paid tier runs. Re-checked before every dispatch, including each cascade retry, so a multi-model provider cannot spend it several times over. `0` disables. |
| `PAID_PASS_DEADLINE_SECONDS` | `45.0` | Whole metered-segment budget on top of the free one, so a `*-go` request cannot bill for an unbounded sequence of paid attempts. Worst case for a non-streaming pass is `FREE + PAID` = 165s, inside the engine's 180s caller window. `0` disables. |
| `AUTO_GO_DEFAULT_REASONING_EFFORT` | unset | Optional thinking floor (`low`/`medium`/`high`) applied to `*-go` aliases. Unset keeps the provider default (Gemini 3 = dynamic/high), so the proxy never fabricates a cap. |

Thinking controls are **only forwarded to providers that declare support** in
`providers.json` via `thinking_params`:

- `gemini`, `groq` → `reasoning_effort` (`low`/`medium`/`high`)
- `openrouter` → `reasoning` object; a caller's `reasoning_effort` is normalized into `{"effort": "..."}`
- `nvidia`, `kilo`, `opencode-go` → nothing (these gateways 400 on unknown fields, and a 400 cools a healthy provider for 60s)
- Strata keeps its native `reasoning_budget_tokens`

A Strata-style `reasoning_budget_tokens` sent to a cloud provider is translated
into an effort band (`>8192` → high, `>4096` → medium, else low) rather than
silently deleted, unless the caller also sent an explicit `reasoning_effort`.

### Streaming Usage Telemetry & Terminal-Chunk Guarantee

The proxy forwards provider frames unchanged but refuses to end a response on a
bare EOF:

- **Pre-flight priming.** For `stream: true`, the first chunks are read before the
  `200` is committed. If the provider closes (or raises) before the first content
  delta arrives, the candidate is treated as dead: it is closed, recorded in the
  `failover_chain` as `(stream ended before first token)`, and the next candidate
  is tried. The client never sees a half-open provider.
- **Terminal-chunk synthesis.** Once headers are out, a stream that stops early
  cannot be failed over — so it is completed instead. If no chunk carried a
  `finish_reason`, the proxy appends
  `{"choices":[{"index":0,"delta":{},"finish_reason":"length"}],"x_proxy_truncated":"upstream_eof"}`
  followed by `data: [DONE]`. `length` is the standard OpenAI signal for incomplete
  output, which is what a truncation is, and `x_proxy_truncated` lets a caller tell a
  provider death from a real `max_tokens` cut; strict clients (pi, the OpenAI SDKs)
  otherwise raise `Stream ended without finish_reason`.
- **Exactly one terminator.** The relay is event-framed (LF, CRLF and CR boundaries) and
  terminality is decided from parsed `data:` payloads over whole events, never from byte
  patterns. A `[DONE]` split across TCP chunks, spelled `data:[DONE]`, quoted inside model
  prose, batched in the same event as content, duplicated, or arriving early is normalised
  into exactly one terminating `[DONE]` with nothing after it; a stream that carried
  `finish_reason` but omitted `[DONE]` gets it appended. A well-formed stream is
  byte-identical.
`x_proxy_truncated` values: `upstream_eof` (provider closed), `upstream_error` (provider raised), `degraded` (event too large to frame).
- **Explicit degradation.** If an event grows past `MAX_PARSE_BUFFER_BYTES` (1 MB) the
  relay falls back to raw pass-through and records the stream as truncated with
  `stream degraded: SSE event exceeded N bytes` — never as a clean success.
- **Honest telemetry.** A synthesized end is logged as `stream_completed = 0` with
  `error_message` = `stream truncated: upstream ended without a finish_reason chunk`,
  so it shows up in `incomplete_streams` and `recent_calls[*].error_message`.
- **Two-strike cooldown.** Each truncation calls `CircuitBreaker.record_stream_failure`;
  two consecutive ones cool the provider for `DEFAULT_COOLDOWN_SECONDS`. A client that
  hangs up mid-stream is neutral (neither a strike nor a success), and dispatch-time
  success resets are skipped for streaming calls so a flaky provider cannot reset its
  own strikes before its body is drained.
- It **never injects `stream_options`** and never re-frames a stream that already
  terminates; the final `usage` object is parsed from a bounded buffer after the
  stream ends or the client disconnects.
- Strata, Groq, Kilo, and OpenRouter emit `usage` in their default streaming
  responses; providers that omit it are marked `usage_available = 0` rather than
  silently claiming zero cost.
- `/v1/metrics` exposes `streaming_requests`, `usage_available_requests`, `zero_token_successes`, `token_coverage_pct`, `avg_stream_duration_ms`, `avg_ttft_ms`, and `incomplete_streams`.
- Metrics are **per connector**. The public hostname load-balances between the workstation and MiniPC connectors, so `/v1/metrics` describes whichever connector served the request. Use `connector_id` and `scope: "connector"` to identify it.
- A log-only `security.401_spike` warning fires when unauthorized requests exceed `SECURITY_ALERT_401_THRESHOLD` within `SECURITY_ALERT_WINDOW_SECONDS`. No external alert service is called.

### Retired providers

- **OVHcloud AI Endpoints** (`oai.endpoints.kepler.ai.cloud.ovh.net`) was removed from
  `providers.json`. Measured against pi's `auto-go` traffic it truncated 25 of 79
  streams (32%) — a single role delta, then EOF with no usage and no terminal chunk —
  and its anonymous public endpoint only serves roughly 16k-token prompts while pi
  sends 100k–230k-token contexts. The audit fingerprint for a truncation is a `200`
  streaming row with `usage_available = 0` and `duration_ms == ttft_ms`.

**Long Strata prompts:** Strata may hold an SSE stream open with `: keep-alive` frames while it processes a large prompt. The proxy forwards those frames unchanged and applies **no total duration cap**; it records time-to-first-token and total stream duration, and marks the row `stream_completed = 0` if the client disconnects first. Clients should use `stream: true` for long Strata prompts. If time-to-first-token can exceed 5–10 minutes, use an asynchronous job queue rather than holding a synchronous HTTP request; no timeout value fixes a 100-minute prefill.

---

## Inspection & Health Endpoints

- **Health Check**: `GET http://localhost:8086/health` (unauthenticated). Includes `connector_id`.
- **Live Models Catalog**: `GET http://localhost:8086/v1/models` (requires master key)
- **Metrics & Cooldown Status**: `GET http://localhost:8086/v1/metrics` (requires master key). Includes per-connector token coverage, stream counters, TTFT/duration, and the log-only 401 spike state.

---

## Running Hermetic Tests

```bash
./apps/engine/.venv/bin/python3 -m pytest apps/free_llm_proxy/tests -q
```
