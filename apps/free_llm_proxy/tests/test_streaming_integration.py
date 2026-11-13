"""End-to-end streaming telemetry tests through the FastAPI app."""

from __future__ import annotations

from apps.free_llm_proxy import server
from apps.free_llm_proxy.db import AuditDB

AUTH = {"Authorization": "Bearer sk-test-master-key"}


def test_stream_usage_logged_without_changing_api(client, monkeypatch):
    """End-to-end: streaming usage reaches the audit DB after the stream ends."""
    db = AuditDB(db_path=":memory:")
    monkeypatch.setattr(server, "audit_db", db)

    async def mock_fetch(_provider_id, _base_url, _headers):
        return ["test-model"]

    async def mock_execute(provider_cfg, payload, stream=False):
        async def chunks():
            yield b'data: {"choices": [{"delta": {"content": "Hello"}}]}\n\n'
            yield b'data: {"choices": [], "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18}}\n\n'
            yield b"data: [DONE]\n\n"

        return 200, chunks(), {}

    monkeypatch.setattr(server.discovery, "fetch_live_models", mock_fetch)
    monkeypatch.setattr(server, "execute_completion", mock_execute)

    response = client.post(
        "/v1/chat/completions",
        headers=AUTH,
        json={
            "model": "free-auto",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": True,
        },
    )

    assert response.status_code == 200
    assert "Hello" in response.text
    assert "[DONE]" in response.text

    metrics = db.get_metrics()
    assert metrics["streaming_requests"] == 1
    assert metrics["usage_available_requests"] == 1
    assert metrics["token_coverage_pct"] == 100.0
    assert metrics["total_tokens"] == 18

    call = metrics["recent_calls"][0]
    assert call["is_stream"] == 1
    assert call["usage_available"] == 1
    assert call["stream_completed"] == 1
    assert call["prompt_tokens"] == 11
    assert call["completion_tokens"] == 7
    assert call["total_tokens"] == 18
    assert call["duration_ms"] >= 0


def test_stream_without_usage_marks_usage_unavailable(client, monkeypatch):
    """Providers that omit usage still stream normally and are marked unavailable."""
    db = AuditDB(db_path=":memory:")
    monkeypatch.setattr(server, "audit_db", db)

    async def mock_fetch(_provider_id, _base_url, _headers):
        return ["test-model"]

    async def mock_execute(provider_cfg, payload, stream=False):
        async def chunks():
            yield b'data: {"choices": [{"delta": {"content": "Hello"}}]}\n\n'
            yield b"data: [DONE]\n\n"

        return 200, chunks(), {}

    monkeypatch.setattr(server.discovery, "fetch_live_models", mock_fetch)
    monkeypatch.setattr(server, "execute_completion", mock_execute)

    response = client.post(
        "/v1/chat/completions",
        headers=AUTH,
        json={
            "model": "free-auto",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": True,
        },
    )

    assert response.status_code == 200
    assert "Hello" in response.text

    metrics = db.get_metrics()
    assert metrics["streaming_requests"] == 1
    assert metrics["usage_available_requests"] == 0
    assert metrics["token_coverage_pct"] == 0.0
    call = metrics["recent_calls"][0]
    assert call["is_stream"] == 1
    assert call["usage_available"] == 0
    assert call["total_tokens"] == 0


def test_strata_stream_payload_is_not_modified(client, monkeypatch):
    """Strata streaming keeps its exact payload: no stream_options, no clamping."""
    captured: dict = {}

    async def mock_fetch(_provider_id, _base_url, _headers):
        return ["qwen-local"]

    async def mock_execute(provider_cfg, payload, stream=False):
        captured.update(payload)

        async def chunks():
            yield b'data: {"choices": [], "usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3}}\n\n'
            yield b"data: [DONE]\n\n"

        return 200, chunks(), {}

    monkeypatch.setattr(server.discovery, "fetch_live_models", mock_fetch)
    monkeypatch.setattr(server, "execute_completion", mock_execute)

    response = client.post(
        "/v1/chat/completions",
        headers=AUTH,
        json={
            "model": "strata",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": True,
            "max_tokens": 131072,
            "reasoning_budget_tokens": 12288,
        },
    )

    assert response.status_code == 200
    assert "stream_options" not in captured
    assert captured["model"] == "qwen-local"
    assert captured["max_tokens"] == 131072
    assert captured["reasoning_budget_tokens"] == 12288


def test_health_and_metrics_include_connector_scope(client, monkeypatch):
    """Both health and metrics identify the connector they describe."""
    monkeypatch.setattr(server.config, "CONNECTOR_ID", "test-connector")

    health = client.get("/health").json()
    assert health["connector_id"] == "test-connector"

    metrics = client.get("/v1/metrics", headers=AUTH).json()
    assert metrics["connector_id"] == "test-connector"
    assert metrics["scope"] == "connector"
    assert "streaming_requests" in metrics
    assert "token_coverage_pct" in metrics
