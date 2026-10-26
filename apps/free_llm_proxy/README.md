# Free LLM Proxy 🚀

A high-performance, model-agnostic OpenAI-compatible proxy that unifies free LLM inference providers into a single resilient endpoint with dynamic failover, circuit breaking, usage logging, and zero hardcoded model IDs.

---

## Features

- **Single Universal Endpoint**: Connect any OpenAI-compatible chat app, IDE, agent, or script to `http://localhost:8086/v1`.
- **Dynamic Model-Agnostic Discovery**: Queries live provider `/v1/models` catalogs. No broken model strings when providers release or retire checkpoints.
- **Smart Tiered Failover**:
  - **Tier 1 (High Performance)**: Groq (ultra-fast 120B/27B), Gemini (Flash 3.8 / 2.5), Kilo Code (no key needed).
  - **Tier 2 (Fallback Pool)**: OVHcloud (anonymous EU), OpenRouter (17 `:free` models), NVIDIA NIM.
- **Circuit Breaker**: On HTTP 429 (rate limit) or 5xx downtime, automatically cools down the provider and retries next candidate seamlessly.
- **Streaming & SSE**: Full pass-through token streaming (`stream: true`) with pre-flight failover protection.
- **Reasoning Token Preservation**: Preserves `reasoning` and thinking blocks for thinking models (`gpt-oss-120b`, `flint`, `beam`).
- **Local SQLite Audit DB**: Records every call, latency, token count, and failover trace to `data/free_llm_proxy.db`.
- **Zero New Dependencies**: Built entirely with existing repository packages (`fastapi`, `uvicorn`, `httpx`, `pydantic`, `sqlite3`).

---

## Quickstart

### 1. Configure `.env`

Copy `.env.example` to `.env` (already initialized in `apps/free_llm_proxy/.env`):

```bash
PORT=8086
FREE_PROXY_MASTER_KEY=sk-free-proxy-secret-key-12345
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=...
OPENROUTER_API_KEY=...
```

*Note: The proxy automatically activates whichever providers have keys configured in `.env`. Kilo Code and OVHcloud work out of the box with zero keys!*

### 2. Start the Server

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
| **`free-auto`** (Default) | Best overall model available across healthy active pool | 120B / 70B / Flash models |
| **`free-fast`** | Sub-second ultra-low latency models | 20B / 8B / Flash-Lite models |
| **`free-reasoning`** | Deep reasoning / thinking models | DeepSeek-R1, Flint, Beam, QwQ |
| **Any Custom Name** | Pass-through or fallback (e.g. `deepseek-chat`, `gpt-4o`) | Automatically routes via `free-auto` |
| **Targeted Provider** | Explicitly target a provider first (e.g. `groq/qwen3.8-27b`) | Routes to specified provider with fallback |

---

## Inspection & Health Endpoints

- **Health Check**: `GET http://localhost:8086/health` (unauthenticated)
- **Live Models Catalog**: `GET http://localhost:8086/v1/models` (requires master key)
- **Metrics & Cooldown Status**: `GET http://localhost:8086/v1/metrics` (requires master key)

---

## Running Hermetic Tests

```bash
./apps/engine/.venv/bin/python3 -m pytest apps/free_llm_proxy/tests/test_proxy.py -v
```
