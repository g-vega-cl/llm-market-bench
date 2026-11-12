"""TDD test suite for Free LLM Proxy."""

import pytest
from fastapi.testclient import TestClient

from apps.free_llm_proxy.server import app
from apps.free_llm_proxy.circuit_breaker import CircuitBreaker
from apps.free_llm_proxy.config import load_providers_config
from apps.free_llm_proxy.db import AuditDB
from apps.free_llm_proxy.router import Router


@pytest.fixture
def client():
    return TestClient(app)


def test_auth_missing_header(client):
    """Verify 401 Unauthorized when no Authorization header is provided."""
    resp = client.post(
        "/v1/chat/completions",
        json={"model": "free-auto", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert resp.status_code == 401
    assert "Invalid or missing master API key" in resp.text


def test_auth_invalid_key(client):
    """Verify 401 Unauthorized when an incorrect Bearer token is provided."""
    headers = {"Authorization": "Bearer wrong-key"}
    resp = client.post(
        "/v1/chat/completions",
        headers=headers,
        json={"model": "free-auto", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert resp.status_code == 401


def test_health_endpoint(client):
    """Verify health endpoint is accessible without authentication."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "active_providers" in data


def test_circuit_breaker_trips_on_429():
    """Verify circuit breaker trips when receiving 429 and honors cooldown."""
    cb = CircuitBreaker(default_cooldown_seconds=60)
    assert cb.is_healthy("groq")

    # Trip breaker on 429
    cb.record_failure("groq", status_code=429, retry_after=120)
    assert not cb.is_healthy("groq")
    assert cb.get_cooldown_remaining("groq") > 60

    # Reset
    cb.reset("groq")
    assert cb.is_healthy("groq")


def test_router_model_alias_resolution():
    """Verify virtual aliases resolve against provider catalogs."""
    router = Router()
    resolved = router.resolve_model_for_provider(
        "groq", "free-auto", ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
    )
    assert resolved == "openai/gpt-oss-120b"

    resolved_fast = router.resolve_model_for_provider(
        "groq", "free-fast", ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
    )
    assert resolved_fast == "openai/gpt-oss-20b"


def test_failover_when_primary_fails(client, monkeypatch):
    """Verify router automatically fails over to secondary provider when primary returns 429."""
    call_history = []

    async def mock_execute(provider_cfg, payload, stream=False):
        prov_name = provider_cfg["name"]
        call_history.append(prov_name)
        if prov_name == "Groq":
            # Simulate 429 rate limit
            return (
                429,
                {"error": {"message": "Rate limit exceeded"}},
                {"retry-after": "30"},
            )
        # Secondary provider succeeds
        mock_response = {
            "id": "chatcmpl-mock",
            "object": "chat.completion",
            "created": 1700000000,
            "model": "gemini-3.8-flash",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Success from fallback!",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
        return 200, mock_response, {}

    monkeypatch.setattr("apps.free_llm_proxy.server.execute_completion", mock_execute)

    headers = {"Authorization": "Bearer sk-test-master-key"}
    resp = client.post(
        "/v1/chat/completions",
        headers=headers,
        json={"model": "free-auto", "messages": [{"role": "user", "content": "test"}]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["choices"][0]["message"]["content"] == "Success from fallback!"
    assert len(call_history) >= 2


def test_streaming_sse_pass_through(client, monkeypatch):
    """Verify streaming response delivers SSE chunks."""

    async def mock_stream_execute(provider_cfg, payload, stream=True):
        async def mock_chunks():
            yield b'data: {"choices": [{"delta": {"content": "Hello"}}]}\n\n'
            yield b'data: {"choices": [{"delta": {"content": " World"}}]}\n\n'
            yield b"data: [DONE]\n\n"

        return 200, mock_chunks(), {}

    monkeypatch.setattr(
        "apps.free_llm_proxy.server.execute_completion", mock_stream_execute
    )

    headers = {"Authorization": "Bearer sk-test-master-key"}
    resp = client.post(
        "/v1/chat/completions",
        headers=headers,
        json={
            "model": "free-auto",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": True,
        },
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    body_text = resp.text
    assert "Hello" in body_text
    assert "World" in body_text
    assert "[DONE]" in body_text


def test_metrics_endpoint(client):
    """Verify metrics endpoint returns counts and circuit status."""
    headers = {"Authorization": "Bearer sk-test-master-key"}
    resp = client.get("/v1/metrics", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_requests" in data
    assert "circuit_breaker" in data
    assert "providers" in data


def test_models_endpoint(client, monkeypatch):
    """Verify models endpoint returns aliases and discovered provider models."""

    async def mock_fetch(provider_id, base_url, headers):
        return ["model-v1", "model-v2"]

    monkeypatch.setattr(
        "apps.free_llm_proxy.server.discovery.fetch_live_models", mock_fetch
    )

    headers = {"Authorization": "Bearer sk-test-master-key"}
    resp = client.get("/v1/models", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    model_ids = [m["id"] for m in data["data"]]
    assert "free-auto" in model_ids
    assert "free-fast" in model_ids
    assert any("groq/" in m for m in model_ids)


def test_audit_db_logging():
    """Verify SQLite audit database records calls and calculates metrics."""
    db = AuditDB(db_path=":memory:")
    db.log_call(
        requested_model="free-auto",
        routed_provider="groq",
        routed_model="openai/gpt-oss-120b",
        prompt_tokens=20,
        completion_tokens=10,
        total_tokens=30,
        latency_ms=85.5,
        status_code=200,
        failover_chain=["gemini (429)", "groq (200)"],
    )

    metrics = db.get_metrics()
    assert metrics["total_requests"] == 1
    assert metrics["total_tokens"] == 30
    assert metrics["providers"]["groq"]["requests"] == 1


def test_audit_db_schema_migration(tmp_path):
    """Verify AuditDB auto-migrates existing SQLite tables lacking attribution columns."""
    import sqlite3

    db_file = str(tmp_path / "legacy.db")
    # Create old table without new columns
    conn = sqlite3.connect(db_file)
    conn.execute(
        """
        CREATE TABLE call_logs (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            requested_model TEXT NOT NULL,
            routed_provider TEXT NOT NULL,
            routed_model TEXT NOT NULL,
            prompt_tokens INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            latency_ms REAL NOT NULL,
            status_code INTEGER NOT NULL,
            failover_chain TEXT,
            error_message TEXT
        )
        """
    )
    conn.commit()
    conn.close()

    # Initializing AuditDB should detect and alter table with new columns
    migrated_db = AuditDB(db_path=db_file)
    migrated_db.log_call(
        requested_model="free-fast",
        routed_provider="groq",
        routed_model="llama-3.1-8b-instant",
        client_ip="1.2.3.4",
        user_agent="legacy-test",
        purpose="migration-check",
        prompt_preview="Short prompt",
    )

    metrics = migrated_db.get_metrics()
    assert len(metrics["recent_calls"]) == 1
    call = metrics["recent_calls"][0]
    assert call["client_ip"] == "1.2.3.4"
    assert call["user_agent"] == "legacy-test"
    assert call["purpose"] == "migration-check"
    assert call["prompt_preview"] == "Short prompt"


def test_mistral_not_in_providers():
    """Verify Mistral is excluded from proxy provider catalog due to lack of free tier."""
    config = load_providers_config()
    assert "mistral" not in config.get("providers", {})


def test_openrouter_free_model_resolution():
    """Verify openrouter/free resolves to 'openrouter/free' even when catalog is not yet populated."""
    router = Router()
    # 1. When available_models is None/empty, 'openrouter/free' must NOT be stripped down to 'free'
    assert (
        router.resolve_model_for_provider("openrouter", "openrouter/free", None)
        == "openrouter/free"
    )
    # 2. When openrouter is the provider, preferred_patterns prioritizes openrouter/free
    assert router.providers["openrouter"]["preferred_patterns"][0] == "openrouter/free"
    # 3. Direct request with explicit provider prefix prioritizes openrouter
    candidates = router.get_candidate_chain("openrouter/free")
    assert len(candidates) > 0
    assert candidates[0][0] == "openrouter"


def test_openrouter_free_chat_completion(client, monkeypatch):
    """Verify chat completion request with model 'openrouter/free' routes correctly to OpenRouter."""
    executed_requests = []

    async def mock_execute(provider_cfg, payload, stream=False):
        executed_requests.append((provider_cfg["name"], payload.get("model")))
        return (
            200,
            {
                "id": "chatcmpl-openrouter-free",
                "object": "chat.completion",
                "created": 1700000000,
                "model": "openrouter/free",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "Hello from OpenRouter Free!",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 5,
                    "completion_tokens": 5,
                    "total_tokens": 10,
                },
            },
            {},
        )

    monkeypatch.setattr("apps.free_llm_proxy.server.execute_completion", mock_execute)

    headers = {"Authorization": "Bearer sk-test-master-key"}
    resp = client.post(
        "/v1/chat/completions",
        headers=headers,
        json={
            "model": "openrouter/free",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["choices"][0]["message"]["content"] == "Hello from OpenRouter Free!"
    assert len(executed_requests) == 1
    assert executed_requests[0] == ("OpenRouter", "openrouter/free")


def test_openrouter_never_resolves_to_paid_model():
    """Verify OpenRouter strictly filters out non-free models and only resolves to :free or openrouter/free."""
    router = Router()
    mixed_catalog = [
        "anthropic/claude-3-opus",
        "nvidia/nemotron-3-super-120b-a12b",
        "nvidia/nemotron-3-super-120b-a12b:free",
        "meta-llama/llama-3.3-70b-instruct",
        "meta-llama/llama-3.3-70b-instruct:free",
        "openrouter/free",
    ]
    # For free-auto alias, must pick the :free variant, NEVER the paid variant
    resolved = router.resolve_model_for_provider(
        "openrouter", "free-auto", mixed_catalog
    )
    assert resolved == "nvidia/nemotron-3-super-120b-a12b:free"

    # If requested model is explicit paid model, it must fallback to openrouter/free
    resolved_paid = router.resolve_model_for_provider(
        "openrouter", "openrouter/anthropic/claude-3-opus", mixed_catalog
    )
    assert resolved_paid == "openrouter/free" or resolved_paid.endswith(":free")

    # If catalog has only paid models, it must fallback to openrouter/free
    paid_only = ["anthropic/claude-3-opus", "openai/gpt-4o"]
    resolved_fallback = router.resolve_model_for_provider(
        "openrouter", "free-auto", paid_only
    )
    assert resolved_fallback == "openrouter/free"


@pytest.mark.asyncio
async def test_discovery_filters_openrouter_to_free_models_only():
    """Verify discovery.fetch_live_models strips non-free models when provider is openrouter."""
    from apps.free_llm_proxy.discovery import ModelDiscovery

    discovery = ModelDiscovery()

    class MockResponse:
        status_code = 200

        def json(self):
            return {
                "data": [
                    {"id": "anthropic/claude-3-opus"},
                    {"id": "nvidia/nemotron-3-super-120b-a12b"},
                    {"id": "nvidia/nemotron-3-super-120b-a12b:free"},
                    {"id": "openrouter/free"},
                ]
            }

    class MockAsyncClient:
        async def get(self, url, headers=None):
            return MockResponse()

    models = await discovery.fetch_live_models(
        "openrouter", "https://openrouter.ai/api/v1", {}, client=MockAsyncClient()
    )
    assert "anthropic/claude-3-opus" not in models
    assert "nvidia/nemotron-3-super-120b-a12b" not in models
    assert "nvidia/nemotron-3-super-120b-a12b:free" in models
    assert "openrouter/free" in models


def test_openrouter_paid_request_is_coerced_to_free_in_chat_completion(
    client, monkeypatch
):
    """Verify end-to-end that requesting a paid model on OpenRouter is coerced to openrouter/free."""
    executed_requests = []

    async def mock_execute(provider_cfg, payload, stream=False, client=None):
        executed_requests.append((provider_cfg["name"], payload.get("model")))
        return (
            200,
            {
                "id": "chatcmpl-openrouter-safe",
                "object": "chat.completion",
                "created": 1700000000,
                "model": "openrouter/free",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "Safe free response",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 5,
                    "completion_tokens": 5,
                    "total_tokens": 10,
                },
            },
            {},
        )

    monkeypatch.setattr("apps.free_llm_proxy.server.execute_completion", mock_execute)

    headers = {"Authorization": "Bearer sk-test-master-key"}
    resp = client.post(
        "/v1/chat/completions",
        headers=headers,
        json={
            "model": "openrouter/anthropic/claude-3-opus",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )
    assert resp.status_code == 200
    assert len(executed_requests) == 1
    # Verify OpenRouter was called with openrouter/free and NOT claude-3-opus
    assert executed_requests[0] == ("OpenRouter", "openrouter/free")


def test_structured_array_message_content(client, monkeypatch):
    """Verify that OpenAI-compatible structured array content (Pi format) is accepted."""
    executed = []

    async def mock_execute(provider_cfg, payload, stream=False, client=None):
        executed.append(payload)
        return (
            200,
            {
                "id": "chatcmpl-structured",
                "object": "chat.completion",
                "created": 1700000000,
                "model": payload.get("model"),
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "Structured OK"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                },
            },
            {},
        )

    monkeypatch.setattr("apps.free_llm_proxy.server.execute_completion", mock_execute)

    headers = {"Authorization": "Bearer sk-test-master-key"}
    resp = client.post(
        "/v1/chat/completions",
        headers=headers,
        json={
            "model": "free-auto",
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": "Structured message test"}],
                }
            ],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["choices"][0]["message"]["content"] == "Structured OK"
    assert len(executed) == 1
    assert executed[0]["messages"][0]["content"] == [
        {"type": "text", "text": "Structured message test"}
    ]


def test_caller_attribution_and_purpose_logging(client, monkeypatch):
    """Verify caller IP, user agent, purpose, and 60-char prompt preview are logged."""

    async def mock_execute(provider_cfg, payload, stream=False):
        return (
            200,
            {
                "id": "chatcmpl-test-attribution",
                "object": "chat.completion",
                "created": 1700000000,
                "model": "test-model",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "Attribution logged successfully.",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                },
            },
            {},
        )

    monkeypatch.setattr("apps.free_llm_proxy.server.execute_completion", mock_execute)

    headers = {
        "Authorization": "Bearer sk-test-master-key",
        "User-Agent": "pi/1.4.0 (darwin-arm64)",
        "CF-Connecting-IP": "198.51.100.42",
        "X-Purpose": "code-refactor",
    }
    long_prompt = "Refactor this function to improve latency and maintain hermetic test isolation across all suites"
    resp = client.post(
        "/v1/chat/completions",
        headers=headers,
        json={
            "model": "free-auto",
            "messages": [
                {
                    "role": "user",
                    "content": long_prompt,
                }
            ],
        },
    )
    assert resp.status_code == 200

    metrics_resp = client.get(
        "/v1/metrics", headers={"Authorization": "Bearer sk-test-master-key"}
    )
    assert metrics_resp.status_code == 200
    metrics = metrics_resp.json()
    assert len(metrics["recent_calls"]) > 0
    latest_call = metrics["recent_calls"][0]

    assert latest_call.get("client_ip") == "198.51.100.42"
    assert latest_call.get("user_agent") == "pi/1.4.0 (darwin-arm64)"
    assert latest_call.get("purpose") == "code-refactor"
    # Prompt snippet must be at most 60 chars + "..." if truncated
    assert latest_call.get("prompt_preview") is not None
    assert latest_call["prompt_preview"].startswith(
        "Refactor this function to improve latency"
    )
    assert len(latest_call["prompt_preview"]) <= 63  # 60 chars + "..."


def test_strata_auto_candidate_chain_and_resolution():
    """Verify strata-auto puts strata first, resolves model, and normal free-auto excludes strata."""
    router = Router()
    assert "strata" in router.get_active_providers()

    # 1. free-auto must NOT include strata
    free_auto_chain = [p[0] for p in router.get_candidate_chain("free-auto")]
    assert "strata" not in free_auto_chain

    # 2. strata-auto must put strata FIRST
    strata_auto_chain = [p[0] for p in router.get_candidate_chain("strata-auto")]
    assert len(strata_auto_chain) > 1
    assert strata_auto_chain[0] == "strata"

    # 3. auto-strata must include strata in the candidate rotation
    auto_strata_chain = [p[0] for p in router.get_candidate_chain("auto-strata")]
    assert "strata" in auto_strata_chain

    # 4. Model resolution on strata uses whatever model is running, or falls back to 'strata'
    assert (
        router.resolve_model_for_provider("strata", "strata-auto", ["live-loaded-qwen"])
        == "live-loaded-qwen"
    )
    assert router.resolve_model_for_provider("strata", "strata-auto", None) == "strata"


def test_strata_strict_no_fallback(client, monkeypatch):
    """Verify bare model 'strata' strictly targets Strata and NEVER falls back to free pool."""
    router = Router()

    # 1. Candidate chain for strict 'strata' must ONLY contain strata
    strata_strict_chain = [p[0] for p in router.get_candidate_chain("strata")]
    assert strata_strict_chain == ["strata"]

    # 2. Candidate chain for 'strata/custom-model' must ONLY contain strata
    strata_prefix_chain = [
        p[0] for p in router.get_candidate_chain("strata/custom-qwen")
    ]
    assert strata_prefix_chain == ["strata"]

    # 3. Chat completion with 'strata' must fail when Strata is offline, without calling fallback
    attempted_providers = []

    async def mock_execute(provider_cfg, payload, stream=False, client=None):
        p_name = provider_cfg.get("name")
        attempted_providers.append(p_name)
        return (
            503,
            {
                "error": {
                    "message": "Strata connection error",
                    "type": "connection_error",
                }
            },
            {},
        )

    monkeypatch.setattr("apps.free_llm_proxy.server.execute_completion", mock_execute)

    headers = {"Authorization": "Bearer sk-test-master-key"}
    resp = client.post(
        "/v1/chat/completions",
        headers=headers,
        json={"model": "strata", "messages": [{"role": "user", "content": "hello"}]},
    )
    assert resp.status_code == 502
    assert len(attempted_providers) == 1
    assert "Strata" in attempted_providers[0]


def test_strata_auto_chat_completion_with_fallback(client, monkeypatch):
    """Verify strata-auto attempts strata first, then cleanly fails over to auto on downtime."""
    attempted_providers = []

    async def mock_execute(provider_cfg, payload, stream=False, client=None):
        p_id = provider_cfg.get("name")
        attempted_providers.append(p_id)
        if "Strata" in p_id:
            # Simulate Strata being offline / connection failure
            return (
                503,
                {
                    "error": {
                        "message": "Connection refused",
                        "type": "connection_error",
                    }
                },
                {},
            )
        # Fallback provider succeeds
        return (
            200,
            {
                "id": "chatcmpl-fallback",
                "object": "chat.completion",
                "created": 1700000000,
                "model": payload.get("model"),
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "Handled by fallback provider!",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 5,
                    "completion_tokens": 5,
                    "total_tokens": 10,
                },
            },
            {},
        )

    monkeypatch.setattr("apps.free_llm_proxy.server.execute_completion", mock_execute)

    headers = {"Authorization": "Bearer sk-test-master-key"}
    resp = client.post(
        "/v1/chat/completions",
        headers=headers,
        json={
            "model": "strata-auto",
            "messages": [{"role": "user", "content": "ping"}],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["choices"][0]["message"]["content"] == "Handled by fallback provider!"
    assert len(attempted_providers) >= 2
    assert "Strata (Local)" in attempted_providers[0]


def test_strata_auto_bypasses_strata_when_cooling():
    """Verify that when Strata is in cooldown, strata-auto skips Strata immediately."""
    cb = CircuitBreaker(default_cooldown_seconds=60)
    router = Router(circuit_breaker=cb)

    # Initial state: Strata is healthy and at front of chain
    chain_healthy = [p[0] for p in router.get_candidate_chain("strata-auto")]
    assert chain_healthy[0] == "strata"

    # Trip Strata into cooldown
    cb.record_failure("strata", status_code=503)
    cb.record_failure("strata", status_code=503)
    assert not cb.is_healthy("strata")

    # While cooling, strata-auto must skip Strata and route directly to healthy auto providers
    chain_cooling = [p[0] for p in router.get_candidate_chain("strata-auto")]
    assert "strata" not in chain_cooling
    assert len(chain_cooling) > 0


@pytest.mark.asyncio
async def test_execute_completion_catches_connect_error(monkeypatch):
    """Verify execute_completion catches httpx.RequestError and returns HTTP 503 gracefully."""
    import httpx
    from apps.free_llm_proxy.client import execute_completion

    provider_cfg = {
        "name": "Strata (Local)",
        "base_url": "http://localhost:8080/v1",
        "api_key": None,
    }

    async def mock_post(*args, **kwargs):
        raise httpx.ConnectError("Connection refused to localhost:8080")

    mock_client = httpx.AsyncClient()
    monkeypatch.setattr(mock_client, "post", mock_post)

    status_code, body, headers = await execute_completion(
        provider_cfg=provider_cfg,
        payload={"model": "strata", "messages": [{"role": "user", "content": "hi"}]},
        stream=False,
        client=mock_client,
    )

    assert status_code == 503
    assert body["error"]["type"] == "connection_error"
    assert "Connection refused" in body["error"]["message"]
    await mock_client.aclose()


def test_strata_env_disable(monkeypatch):
    """Verify setting ENABLE_STRATA=false removes strata from active providers."""
    from apps.free_llm_proxy import config

    monkeypatch.setattr(config, "ENABLE_STRATA", False)
    cfg_data = config.load_providers_config()
    assert "strata" not in cfg_data["providers"]


def test_max_tokens_unclamped_for_strata_and_clamped_for_cloud(client, monkeypatch):
    """Verify max_tokens >= 128k is preserved for Strata but clamped to 16384 for cloud providers."""
    executed_payloads = []

    async def mock_execute(provider_cfg, payload, stream=False, client=None):
        executed_payloads.append((provider_cfg.get("name"), dict(payload)))
        return (
            200,
            {
                "id": "chatcmpl-tokens",
                "object": "chat.completion",
                "created": 1700000000,
                "model": payload.get("model"),
                "choices": [
                    {"index": 0, "message": {"role": "assistant", "content": "ok"}}
                ],
            },
            {},
        )

    monkeypatch.setattr("apps.free_llm_proxy.server.execute_completion", mock_execute)

    headers = {"Authorization": "Bearer sk-test-master-key"}

    # Request 1: Direct strata target with 131072 tokens and reasoning_budget_tokens
    resp = client.post(
        "/v1/chat/completions",
        headers=headers,
        json={
            "model": "strata",
            "messages": [{"role": "user", "content": "deep thinking task"}],
            "max_tokens": 131072,
            "reasoning_budget_tokens": 12288,
        },
    )
    assert resp.status_code == 200
    assert len(executed_payloads) == 1
    assert executed_payloads[0][1]["max_tokens"] == 131072
    assert executed_payloads[0][1]["reasoning_budget_tokens"] == 12288

    # Request 2: Cloud auto target with 131072 tokens -> must be clamped to 16384 and reasoning_budget_tokens stripped
    resp2 = client.post(
        "/v1/chat/completions",
        headers=headers,
        json={
            "model": "free-auto",
            "messages": [{"role": "user", "content": "cloud task"}],
            "max_tokens": 131072,
            "reasoning_budget_tokens": 12288,
        },
    )
    assert resp2.status_code == 200
    assert len(executed_payloads) == 2
    assert executed_payloads[1][1]["max_tokens"] == 16384
    assert "reasoning_budget_tokens" not in executed_payloads[1][1]


def test_unauthorized_call_is_logged_in_audit_db(client):
    """Verify that failed authentication attempts (401) are logged to audit_db."""
    from apps.free_llm_proxy.server import audit_db

    initial_metrics = audit_db.get_metrics()
    initial_unauth = initial_metrics.get("unauthorized_requests", 0)

    resp = client.post(
        "/v1/chat/completions",
        headers={
            "Authorization": "Bearer bad-token-attempt",
            "X-Forwarded-For": "203.0.113.195",
        },
        json={"model": "free-auto", "messages": [{"role": "user", "content": "probe"}]},
    )
    assert resp.status_code == 401

    updated_metrics = audit_db.get_metrics()
    assert updated_metrics["unauthorized_requests"] == initial_unauth + 1
    recent = updated_metrics["recent_calls"][0]
    assert recent["status_code"] == 401
    assert recent["client_ip"] == "203.0.113.195"
    assert recent["routed_provider"] == "none"


def test_gemini_pro_model_is_coerced_to_free_flash():
    """Verify that requesting a Gemini Pro or paid model coerces to free flash."""
    cb = CircuitBreaker()
    router = Router(circuit_breaker=cb)

    # Gemini catalog with both pro and flash
    available_models = [
        "models/gemini-1.5-pro",
        "models/gemini-3.8-flash",
        "models/gemini-2.5-flash-lite",
    ]

    # If client asks for gemini-1.5-pro, router must coerce to free flash
    resolved = router.resolve_model_for_provider(
        "gemini", "models/gemini-1.5-pro", available_models
    )
    assert "flash" in resolved.lower()
    assert "pro" not in resolved.lower()


def test_gemini_uses_gemini_api_key_free(monkeypatch):
    """Verify that Gemini provider uses GEMINI_API_KEY_FREE from providers.json."""
    from apps.free_llm_proxy import config

    providers_cfg = config.load_providers_config()
    assert providers_cfg["providers"]["gemini"]["env_key"] == "GEMINI_API_KEY_FREE"


def test_gemini_strictly_filters_out_legacy_models():
    """Verify that Gemini router strips obsolete 1.5, 2.0, and 2.5 models."""
    cb = CircuitBreaker()
    router = Router(circuit_breaker=cb)

    available_models = [
        "models/gemini-1.5-flash",
        "models/gemini-2.0-flash",
        "models/gemini-2.5-flash",
        "models/gemini-3.6-flash",
        "models/gemini-flash-latest",
    ]

    # Asking for free-auto or generic flash must select flash-latest or 3.x flash, never 1.5/2.0/2.5
    resolved = router.resolve_model_for_provider(
        "gemini", "free-auto", available_models
    )
    assert resolved in (
        "models/gemini-flash-latest",
        "gemini-flash-latest",
        "models/gemini-3.6-flash",
        "gemini-3.6-flash",
    )
    assert not any(v in resolved for v in ("1.5", "2.0", "2.5"))


def test_resolved_model_has_no_wildcards():
    """Verify that resolved models never contain raw asterisk wildcards even on empty catalogs."""
    cb = CircuitBreaker()
    router = Router(circuit_breaker=cb)

    resolved = router.resolve_model_for_provider("gemini", "free-auto", [])
    assert "*" not in resolved
    assert resolved in ("gemini-flash-latest", "gemini-3.8-flash")


def test_gemini_in_provider_cascade_on_503_spike(client, monkeypatch):
    """Verify that if the primary Gemini model encounters HTTP 503, the proxy tries alternative Flash models before leaving Google."""
    attempts = []

    async def mock_execute(provider_cfg, payload, stream=False):
        model = payload["model"]
        attempts.append((provider_cfg.get("name"), model))
        if model in (
            "gemini-flash-latest",
            "models/gemini-flash-latest",
            "gemini-3.8-flash",
        ):
            return 503, {"error": {"message": "High demand spike"}}, {}
        if model in ("gemini-3.6-flash", "models/gemini-3.6-flash"):
            return (
                200,
                {"choices": [{"message": {"content": "Cascade OK"}}], "usage": {}},
                {},
            )
        return 200, {"choices": [{"message": {"content": "OK"}}], "usage": {}}, {}

    monkeypatch.setattr("apps.free_llm_proxy.server.execute_completion", mock_execute)

    headers = {"Authorization": "Bearer sk-test-master-key"}
    resp = client.post(
        "/v1/chat/completions",
        headers=headers,
        json={
            "model": "gemini/gemini-flash-latest",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["choices"][0]["message"]["content"] == "Cascade OK"
    # Ensure it tried the alternative flash model
    assert any("gemini-3.6-flash" in att[1] for att in attempts)


@pytest.mark.asyncio
async def test_kilo_free_model_isolation_and_resolution():
    """Verify that Kilo catalog discovery strips paid models and resolves strictly to free models."""
    from apps.free_llm_proxy.discovery import ModelDiscovery

    discovery = ModelDiscovery()
    raw_kilo_catalog = [
        {"id": "nvidia/nemotron-3-super-120b-a12b"},  # Paid
        {"id": "anthropic/claude-3-opus"},  # Paid
        {"id": "kilo-auto/free"},  # Free
        {"id": "reflection/beam-free"},  # Free
        {"id": "nvidia/nemotron-3.5-super-vl:free"},  # Free
    ]

    class MockResp:
        status_code = 200

        def json(self):
            return {"data": raw_kilo_catalog}

    class MockClient:
        async def get(self, url, headers=None):
            return MockResp()

    filtered = await discovery.fetch_live_models(
        "kilo", "https://api.kilo.ai/api/gateway", {}, client=MockClient()
    )
    # Paid models must be completely excluded
    assert "nvidia/nemotron-3-super-120b-a12b" not in filtered
    assert "anthropic/claude-3-opus" not in filtered
    # Free models must be present
    assert "kilo-auto/free" in filtered
    assert "reflection/beam-free" in filtered
    assert "nvidia/nemotron-3.5-super-vl:free" in filtered

    # Verify router resolution for kilo prioritizes kilo-auto/free or free models
    cb = CircuitBreaker()
    router = Router(circuit_breaker=cb, discovery=discovery)
    resolved = router.resolve_model_for_provider("kilo", "free-auto", filtered)
    assert resolved in (
        "kilo-auto/free",
        "reflection/beam-free",
        "nvidia/nemotron-3.5-super-vl:free",
    )
    assert not any(p in resolved for p in ("super-120b", "claude-3-opus"))


def test_default_model_is_auto_strata_and_includes_strata_in_tier1():
    """Verify that ChatCompletionRequest and Router defaults to auto-strata with Strata in Tier 1."""
    from apps.free_llm_proxy.models import ChatCompletionRequest

    # Schema default
    req = ChatCompletionRequest(messages=[{"role": "user", "content": "hi"}])
    assert req.model == "auto-strata"

    # Router candidate chain for default/empty/auto
    cb = CircuitBreaker()
    router = Router(circuit_breaker=cb)

    for empty_val in ("", "auto", "default", "auto-strata"):
        chain = [p[0] for p in router.get_candidate_chain(empty_val)]
        assert "strata" in chain
        # Strata must be in the Tier 1 group (healthy candidates before Tier 2)
        assert chain.index("strata") < len(chain)


def test_openrouter_in_provider_cascade_on_503(client, monkeypatch):
    """Verify that an upstream 503 on an OpenRouter model cascades to openrouter/free before failing provider."""
    attempts = []

    async def mock_execute(provider_cfg, payload, stream=False):
        model = payload["model"]
        attempts.append((provider_cfg.get("name"), model))
        if provider_cfg.get("name") == "OpenRouter":
            if model == "recursive/flint-v1.0:free":
                return 503, {"error": {"message": "no upstreams available"}}, {}
            if model == "openrouter/free":
                return (
                    200,
                    {
                        "choices": [{"message": {"content": "OpenRouter Cascade OK"}}],
                        "usage": {},
                    },
                    {},
                )
        return 200, {"choices": [{"message": {"content": "OK"}}], "usage": {}}, {}

    monkeypatch.setattr("apps.free_llm_proxy.server.execute_completion", mock_execute)

    headers = {"Authorization": "Bearer sk-test-master-key"}
    resp = client.post(
        "/v1/chat/completions",
        headers=headers,
        json={
            "model": "openrouter/recursive/flint-v1.0:free",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["choices"][0]["message"]["content"] == "OpenRouter Cascade OK"
    assert any(att[1] == "openrouter/free" for att in attempts)


def test_nvidia_in_provider_cascade_on_404(client, monkeypatch):
    """Verify that a 404 (deprecated function) on NVIDIA NIM cascades to another model before failing provider."""
    attempts = []

    async def mock_execute(provider_cfg, payload, stream=False):
        model = payload["model"]
        attempts.append((provider_cfg.get("name"), model))
        if provider_cfg.get("name") == "NVIDIA NIM":
            if "super-120b-a12b" in model:
                return 404, {"status": 404, "title": "Not Found"}, {}
            if "minimax" in model or "super-vl" in model:
                return (
                    200,
                    {
                        "choices": [{"message": {"content": "NVIDIA Cascade OK"}}],
                        "usage": {},
                    },
                    {},
                )
        return 200, {"choices": [{"message": {"content": "OK"}}], "usage": {}}, {}

    monkeypatch.setattr("apps.free_llm_proxy.server.execute_completion", mock_execute)

    headers = {"Authorization": "Bearer sk-test-master-key"}
    resp = client.post(
        "/v1/chat/completions",
        headers=headers,
        json={
            "model": "nvidia/nvidia/nemotron-3-super-120b-a12b",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["choices"][0]["message"]["content"] == "NVIDIA Cascade OK"


def test_auto_go_includes_go_as_last_resort_and_excludes_strata(monkeypatch):
    """auto-go must include OpenCode Go only as the final fallback tier, never Strata."""
    monkeypatch.setenv("OPENCODE_GO_API_KEY", "go_test_key")
    router = Router()

    chain = [p[0] for p in router.get_candidate_chain("auto-go")]

    assert "opencode-go" in chain
    assert chain[-1] == "opencode-go"
    assert "strata" not in chain


def test_auto_strata_go_includes_strata_and_go_last(monkeypatch):
    """auto-strata-go must include Strata in Tier 1 and OpenCode Go as the last resort."""
    monkeypatch.setenv("OPENCODE_GO_API_KEY", "go_test_key")
    router = Router()

    chain = [p[0] for p in router.get_candidate_chain("auto-strata-go")]

    assert "strata" in chain
    assert "opencode-go" in chain
    assert chain[-1] == "opencode-go"
    assert chain.index("strata") < chain.index("opencode-go")


def test_strata_auto_go_uses_strata_first_and_go_last(monkeypatch):
    """strata-auto-go must put Strata first, then the free pool, then paid Go."""
    monkeypatch.setenv("OPENCODE_GO_API_KEY", "go_test_key")
    router = Router()

    chain = [p[0] for p in router.get_candidate_chain("strata-auto-go")]

    assert chain[0] == "strata"
    assert chain[-1] == "opencode-go"
    assert chain.count("strata") == 1
    assert chain.count("opencode-go") == 1
    assert len(chain) > 2


def test_strata_auto_go_end_to_end_fails_over_strata_then_free_then_go(
    client, monkeypatch
):
    """strata-auto-go must fail over from Strata through free providers to Go."""
    monkeypatch.setenv("OPENCODE_GO_API_KEY", "go_test_key")
    attempted: list[str] = []

    async def mock_fetch(provider_id, base_url, headers):
        return ["test-model"]

    async def mock_execute(provider_cfg, payload, stream=False):
        name = provider_cfg.get("name")
        attempted.append(name)
        if name == "OpenCode Go":
            return (
                200,
                {
                    "id": "chatcmpl-strata-auto-go",
                    "object": "chat.completion",
                    "created": 1700000000,
                    "model": payload.get("model"),
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": "Served by OpenCode Go",
                            },
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 3,
                        "completion_tokens": 4,
                        "total_tokens": 7,
                    },
                },
                {},
            )
        return 429, {"error": {"message": "rate limited"}}, {"retry-after": "1"}

    monkeypatch.setattr(
        "apps.free_llm_proxy.server.discovery.fetch_live_models", mock_fetch
    )
    monkeypatch.setattr("apps.free_llm_proxy.server.execute_completion", mock_execute)

    resp = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer sk-test-master-key"},
        json={
            "model": "strata-auto-go",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )

    assert resp.status_code == 200
    assert resp.json()["choices"][0]["message"]["content"] == "Served by OpenCode Go"
    assert attempted[0] == "Strata (Local)"
    assert attempted[-1] == "OpenCode Go"
    assert attempted.count("OpenCode Go") == 1


def test_free_aliases_never_include_opencode_go(monkeypatch):
    """Existing free aliases must remain strictly zero-cost even when a Go key is configured."""
    monkeypatch.setenv("OPENCODE_GO_API_KEY", "go_test_key")
    router = Router()

    for alias in (
        "free-auto",
        "free-fast",
        "free-reasoning",
        "auto-strata",
        "strata-auto",
        "auto",
        "default",
        "",
    ):
        chain = [p[0] for p in router.get_candidate_chain(alias)]
        assert "opencode-go" not in chain, f"{alias!r} leaked paid OpenCode Go route"


def test_opencode_go_absent_without_api_key(monkeypatch):
    """OpenCode Go must stay inactive when no API key is configured."""
    monkeypatch.delenv("OPENCODE_GO_API_KEY", raising=False)
    router = Router()

    assert "opencode-go" not in router.get_active_providers()
    assert "opencode-go" not in [p[0] for p in router.get_candidate_chain("auto-go")]


def test_opencode_go_resolves_alias_against_discovered_catalog(monkeypatch):
    """Alias and explicit model resolution must use the live OpenCode Go catalog."""
    monkeypatch.setenv("OPENCODE_GO_API_KEY", "go_test_key")
    router = Router()

    catalog = [
        "gemini-4-argon",
        "deepseek-v4.1-flash",
        "kimi-k3",
        "qwen3.8-max",
    ]

    assert (
        router.resolve_model_for_provider("opencode-go", "auto-go", catalog)
        == "deepseek-v4.1-flash"
    )
    assert (
        router.resolve_model_for_provider("opencode-go", "auto-strata-go", catalog)
        == "deepseek-v4.1-flash"
    )
    assert (
        router.resolve_model_for_provider("opencode-go", "strata-auto-go", catalog)
        == "deepseek-v4.1-flash"
    )
    assert (
        router.resolve_model_for_provider(
            "opencode-go", "opencode-go/qwen3.8-max", catalog
        )
        == "qwen3.8-max"
    )


def test_auto_go_end_to_end_falls_back_to_go(client, monkeypatch):
    """auto-go must exhaust free providers and only then call OpenCode Go."""
    monkeypatch.setenv("OPENCODE_GO_API_KEY", "go_test_key")
    attempted: list[str] = []
    captured_go_cfg: dict = {}

    async def mock_fetch(provider_id, base_url, headers):
        return ["test-model"]

    async def mock_execute(provider_cfg, payload, stream=False):
        name = provider_cfg.get("name")
        attempted.append(name)
        if name == "OpenCode Go":
            captured_go_cfg.update(provider_cfg)
            return (
                200,
                {
                    "id": "chatcmpl-go",
                    "object": "chat.completion",
                    "created": 1700000000,
                    "model": payload.get("model"),
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": "Served by OpenCode Go",
                            },
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 3,
                        "completion_tokens": 4,
                        "total_tokens": 7,
                    },
                },
                {},
            )
        return 429, {"error": {"message": "rate limited"}}, {"retry-after": "1"}

    monkeypatch.setattr(
        "apps.free_llm_proxy.server.discovery.fetch_live_models", mock_fetch
    )
    monkeypatch.setattr("apps.free_llm_proxy.server.execute_completion", mock_execute)

    headers = {"Authorization": "Bearer sk-test-master-key"}
    resp = client.post(
        "/v1/chat/completions",
        headers={**headers, "x-opencode-session": "ses_client_42"},
        json={"model": "auto-go", "messages": [{"role": "user", "content": "hi"}]},
    )

    assert resp.status_code == 200
    assert resp.json()["choices"][0]["message"]["content"] == "Served by OpenCode Go"
    assert attempted[-1] == "OpenCode Go"
    assert attempted.count("OpenCode Go") == 1
    assert captured_go_cfg["extra_headers"]["x-opencode-session"] == "ses_client_42"
    assert captured_go_cfg["extra_headers"]["User-Agent"] == (
        "free-llm-proxy/1.0 (llm.clvg.uk)"
    )


def test_auto_go_exhausts_cooling_free_pool_before_paid_provider(monkeypatch):
    """A rate-limit storm must never promote the paid provider ahead of cooling free ones."""
    monkeypatch.setenv("OPENCODE_GO_API_KEY", "go_test_key")
    router = Router()
    active = router.get_active_providers()
    free_ids = [
        p_id
        for p_id, cfg in active.items()
        if cfg.get("billing") != "paid" and p_id != "strata"
    ]
    assert free_ids

    for p_id in free_ids:
        router.circuit_breaker.record_failure(p_id, status_code=429, retry_after=60)

    chain = [p[0] for p in router.get_candidate_chain("auto-go")]

    assert chain[0] != "opencode-go"
    assert chain[-1] == "opencode-go"
    assert set(free_ids).issubset(chain)


def test_paid_provider_without_alias_allowlist_never_enters_auto(monkeypatch):
    """Paid routing must fail closed if its alias allowlist is missing or emptied."""
    monkeypatch.setenv("OPENCODE_GO_API_KEY", "go_test_key")
    router = Router()
    router.providers["opencode-go"].pop("auto_aliases", None)

    for alias in (
        "free-auto",
        "auto-go",
        "auto-strata-go",
        "strata-auto-go",
        "free-fast",
        "free-reasoning",
        "auto-strata",
        "auto",
        "default",
        "",
    ):
        chain = [p[0] for p in router.get_candidate_chain(alias)]
        assert "opencode-go" not in chain, f"{alias!r} leaked paid route"


def test_invalid_tier_value_does_not_crash_router(monkeypatch):
    """Hand-edited provider configs must degrade, not raise, on a malformed tier."""
    monkeypatch.setenv("OPENCODE_GO_API_KEY", "go_test_key")
    router = Router()
    router.providers["nvidia"]["tier"] = None

    chain = [p[0] for p in router.get_candidate_chain("free-auto")]

    assert "nvidia" in chain


def test_explicit_paid_model_not_dispatched_when_catalog_unavailable(
    client, monkeypatch
):
    """Fail closed on money: never send a paid request when its live catalog cannot be read."""
    monkeypatch.setenv("OPENCODE_GO_API_KEY", "go_test_key")
    attempted: list[str] = []

    async def mock_fetch(provider_id, base_url, headers):
        return []

    async def mock_execute(provider_cfg, payload, stream=False):
        attempted.append(provider_cfg.get("name"))
        return 429, {"error": {"message": "rate limited"}}, {"retry-after": "1"}

    monkeypatch.setattr(
        "apps.free_llm_proxy.server.discovery.fetch_live_models", mock_fetch
    )
    monkeypatch.setattr("apps.free_llm_proxy.server.execute_completion", mock_execute)

    resp = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer sk-test-master-key"},
        json={
            "model": "opencode-go/deepseek-v4.1-flash",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )

    assert resp.status_code == 502
    assert "OpenCode Go" not in attempted
