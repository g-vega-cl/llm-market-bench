# Free LLM Providers: Account & Key Setup Guide 📋

All providers below feature **permanent free tiers** with **zero credit card required** (curated from [awesome-free-llm-apis](https://github.com/mnfst/awesome-free-llm-apis)).

---

## 1. Zero-Key Providers (Ready Immediately)

You do **not** need to register or configure keys for these; they are active in the proxy right now:

* **Kilo Code**:
  * Website: [app.kilo.ai](https://app.kilo.ai/profile)
  * Free quota: **200 requests/hour**
  * Auto-routing model: `kilo-auto/free`

---

## 2. Fast Setup (1-Minute Sign-in)

### Groq ⚡
* **Signup URL**: [console.groq.com/keys](https://console.groq.com/keys)
* **Login**: Sign in with Google or GitHub.
* **Generate**: Click **Create API Key**.
* **Env Variable**: Set `GROQ_API_KEY=gsk_...` in `apps/free_llm_proxy/.env`.
* **Limits**: ~30 RPM, 1,000 to 7,000 requests/day. Ultra-fast (400–1,200 tok/s).

### Google Gemini 🧠
* **Signup URL**: [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
* **Login**: Sign in with Google account.
* **Generate**: Click **Get API key** -> **Create API key**.
* **Env Variable**: Set `GEMINI_API_KEY=...` in `apps/free_llm_proxy/.env`.
* **Limits**: 15–30 RPM, 500–1,500 requests/day, 1M context window.

### OpenRouter 🌐
* **Signup URL**: [openrouter.ai/keys](https://openrouter.ai/keys)
* **Login**: Sign in with Google or GitHub.
* **Generate**: Click **Create Key**.
* **Env Variable**: Set `OPENROUTER_API_KEY=sk-or-v1-...` in `apps/free_llm_proxy/.env`.
* **Limits**: 20 RPM, 50 requests/day per free model (17 free models available).

### Nous Research Portal 🦉
* **Signup URL**: [portal.nousresearch.com](https://portal.nousresearch.com)
* **API Docs**: [portal.nousresearch.com/api-docs](https://portal.nousresearch.com/api-docs)
* **Env Variable**: Set `NOUS_RESEARCH_KEY=...` in `apps/free_llm_proxy/.env`.
* **Catalog**: Strictly filtered to `:free` models (`qwen/qwen4-max:free`, `tencent/hy4-flash:free`, `meituan/longcat-2.5:free`, `stepfun/step-3.7-flash:free`, `upstage/solar-mini4:free`).
* **Limits**: ~50 RPM, 2,100 requests/hour.

---

## 3. Optional Additional Providers to Expand

### NVIDIA NIM 🟢
* **Signup URL**: [build.nvidia.com/explore/discover](https://build.nvidia.com/explore/discover)
* **Generate**: Sign in with NVIDIA Developer Program (free) -> Select any model -> Click **Get API Key**.
* **Env Variable**: Set `NVIDIA_API_KEY=nvapi-...` in `apps/free_llm_proxy/.env`.
* **Limits**: 40 RPM, 10,000 requests/day, 100+ models (`openai/gpt-oss-20b`, `google/gemma-4-31b-it`, `nvidia/nemotron-3-ultra-550b`).

### Cohere
* **Signup URL**: [dashboard.cohere.com/api-keys](https://dashboard.cohere.com/api-keys)
* **Limits**: 1,000 API calls/month, 20 RPM.
* **Models**: `Command A+ 218B`, `Command R+`.

---

## 4. Paid Optional Provider (Alias-Gated)

### OpenCode Go 💳
* **Signup URL**: [opencode.ai/auth](https://opencode.ai/auth) → subscribe to Go / Go Plus / Go Teams.
* **Env Variable**: Set `OPENCODE_GO_API_KEY=oc_sk_...` in `apps/free_llm_proxy/.env`.
* **Catalog**: Discovered automatically from `GET https://opencode.ai/zen/go/v1/models` (no model list to maintain).
* **Routing**: Reachable only via `auto-go` or explicit `opencode-go/<model>`. It is deliberately excluded from every free alias (`free-auto`, `auto-strata`, `free-fast`, `free-reasoning`) and sits after both healthy and cooling free candidates as a last resort. Its `billing: "paid"` + `auto_aliases` configuration is fail-closed, and dispatch is refused if the live catalog cannot be discovered. The old `strata-auto-go` / `auto-strata-go` aliases are retired; the engine maps them to `auto-go` so rows written before the retirement still run.
* **Money control is routing**: the `auto_aliases` allowlist in `providers.json` is what keeps this tier out of every free alias. A free alias never gets a paid candidate, so no timeout-keyed flag is involved and none can be misconfigured into spend. Explicit `opencode-go/<model>` requests are deliberate charges and are always served.
* **Time bound**: a non-streaming pass is capped at `FREE_PASS_DEADLINE_SECONDS` (120s) plus `PAID_PASS_DEADLINE_SECONDS` (45s), re-checked before every dispatch including cascade retries, and only one metered model may be dispatched per request.
* **Model order inside Go**: plan-included models first (`free_model_patterns`, default `["*free*"]` — `beam-free`, `longcat-2.5-free`, `hy4-flash-free`, `iceman-contributor-free` today), then the single metered `last_resort_model` (`deepseek-v4.1-flash`), then the catalog-resolved model. A retired pin degrades to the catalog-resolved model with a warning rather than a 502.

---

## Output Ceilings & Thinking Budgets

Reasoning tokens count against `max_tokens` / `max_completion_tokens` on every
provider here, so the output ceiling is the thinking ceiling.

* Per-provider ceilings live in `providers.json` → `max_output_tokens`
  (`gemini` 65536, every other cloud provider 32768 — groq is held at 32768 because
  its smaller models cap below 65k). `CLOUD_MAX_OUTPUT_TOKENS` (default 32768) is only the fallback for a
  provider that declares none; Strata is exempt.
* The clamp is `min(requested, ceiling)` — it never inflates a caller's budget.
* `CLOUD_REQUEST_TIMEOUT_SECONDS` (default 90) bounds each non-Strata attempt and
  is also the httpx read window (`client.build_timeout`), so there is no second,
  tighter cap. Keep it below the tightest caller's patience so a failover still
  lands inside their window: the live trader waits 200s, engine instructor clients
  180s. A socket timeout now returns `504 timeout_error`; it used to surface as a
  `503 connection_error`, which the paid guard could not see.
* Thinking params are forwarded only to providers that declare them in
  `providers.json` → `thinking_params` (`gemini`/`groq`: `reasoning_effort`;
  `openrouter`: `reasoning`). Everything else has them stripped, because an
  unknown field there returns 400 and cools a healthy provider for 60s.
* `AUTO_GO_DEFAULT_REASONING_EFFORT` is empty by default, so the provider default
  governs (Gemini 3 = dynamic/high). Set `low`/`medium`/`high` only if you want a
  forced floor on `*-go` aliases.

---

## Dynamic Auto-Discovery

The proxy detects configured keys automatically on startup. Whenever you add a key to `.env`, the provider enters the active candidate pool without code changes.
