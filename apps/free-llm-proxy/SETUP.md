# Free LLM Providers: Account & Key Setup Guide 📋

All providers below feature **permanent free tiers** with **zero credit card required** (curated from [awesome-free-llm-apis](https://github.com/mnfst/awesome-free-llm-apis)).

---

## 1. Zero-Key Providers (Ready Immediately)

You do **not** need to register or configure keys for these; they are active in the proxy right now:

* **Kilo Code**:
  * Website: [app.kilo.ai](https://app.kilo.ai/profile)
  * Free quota: **200 requests/hour**
  * Auto-routing model: `kilo-auto/free`
* **OVHcloud AI Endpoints**:
  * Website: [ovhcloud.com AI Endpoints](https://www.ovhcloud.com/en/public-cloud/ai-endpoints/catalog/)
  * Free quota: **2 requests/minute per IP** (EU hosted open-weights)
  * Models: `gpt-oss-120b`, `gpt-oss-20b`, `Meta-Llama-3_3-70B-Instruct`, `Qwen3.8-27B`

---

## 2. Fast Setup (1-Minute Sign-in)

### Groq ⚡
* **Signup URL**: [console.groq.com/keys](https://console.groq.com/keys)
* **Login**: Sign in with Google or GitHub.
* **Generate**: Click **Create API Key**.
* **Env Variable**: Set `GROQ_API_KEY=gsk_...` in `apps/free-llm-proxy/.env`.
* **Limits**: ~30 RPM, 1,000 to 7,000 requests/day. Ultra-fast (400–1,200 tok/s).

### Google Gemini 🧠
* **Signup URL**: [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
* **Login**: Sign in with Google account.
* **Generate**: Click **Get API key** -> **Create API key**.
* **Env Variable**: Set `GEMINI_API_KEY=...` in `apps/free-llm-proxy/.env`.
* **Limits**: 15–30 RPM, 500–1,500 requests/day, 1M context window.

### OpenRouter 🌐
* **Signup URL**: [openrouter.ai/keys](https://openrouter.ai/keys)
* **Login**: Sign in with Google or GitHub.
* **Generate**: Click **Create Key**.
* **Env Variable**: Set `OPENROUTER_API_KEY=sk-or-v1-...` in `apps/free-llm-proxy/.env`.
* **Limits**: 20 RPM, 50 requests/day per free model (17 free models available).

---

## 3. Optional Additional Providers to Expand

### NVIDIA NIM 🟢
* **Signup URL**: [build.nvidia.com/explore/discover](https://build.nvidia.com/explore/discover)
* **Generate**: Sign in with NVIDIA Developer Program (free) -> Select any model -> Click **Get API Key**.
* **Env Variable**: Set `NVIDIA_API_KEY=nvapi-...` in `apps/free-llm-proxy/.env`.
* **Limits**: 40 RPM, 10,000 requests/day, 100+ models (`openai/gpt-oss-20b`, `google/gemma-4-31b-it`, `nvidia/nemotron-3-ultra-550b`).

### Mistral AI
* **Signup URL**: [console.mistral.ai/api-keys](https://console.mistral.ai/api-keys/)
* **Generate**: Sign in -> Under Free / Experimentation plan -> **Create New Key**.
* **Env Variable**: Set `MISTRAL_API_KEY=...` in `apps/free-llm-proxy/.env`.
* **Models**: `Mistral Medium 3.5 (128B)`, `Mistral Small 4`, `Codestral`.

### Cohere
* **Signup URL**: [dashboard.cohere.com/api-keys](https://dashboard.cohere.com/api-keys)
* **Limits**: 1,000 API calls/month, 20 RPM.
* **Models**: `Command A+ 218B`, `Command R+`.

---

## Dynamic Auto-Discovery

The proxy detects configured keys automatically on startup. Whenever you add a key to `.env`, the provider enters the active candidate pool without code changes.
