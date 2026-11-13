"""Hermetic pytest fixtures for Free LLM Proxy tests."""

import os
import pytest
from fastapi.testclient import TestClient

# Enforce test environment variables before importing the server module.
os.environ["FREE_PROXY_MASTER_KEY"] = "sk-test-master-key"
os.environ["PORT"] = "8086"
os.environ["SQLITE_DB_PATH"] = ":memory:"
os.environ["CONNECTOR_ID"] = "test-connector"
os.environ["GROQ_API_KEY"] = "gsk_test_key"
os.environ["GEMINI_API_KEY_FREE"] = "gemini_test_key"
os.environ["OPENROUTER_API_KEY"] = "or_test_key"

from apps.free_llm_proxy.server import app  # noqa: E402


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_shared_circuit_breaker():
    """Keep provider cooldowns isolated between tests, including on assertion failure."""
    from apps.free_llm_proxy.server import circuit_breaker, unauthorized_monitor

    stores = (
        circuit_breaker._cooldowns,
        circuit_breaker._failures,
        circuit_breaker._rate_limit_hits,
    )
    for store in stores:
        store.clear()
    unauthorized_monitor.reset()
    yield
    for store in stores:
        store.clear()
    unauthorized_monitor.reset()


@pytest.fixture(autouse=True)
def guard_no_external_network(monkeypatch):
    """Enforce hermetic testing: throw RuntimeError if real socket connect is attempted."""
    import socket

    orig_connect = socket.socket.connect

    def guarded_connect(self, address):
        host = address[0]
        # Allow internal localhost / testclient loopback
        if str(host) in {"127.0.0.1", "localhost", "::1"}:
            return orig_connect(self, address)
        raise RuntimeError(
            f"Hermetic violation: Attempted outbound network connection to {address}"
        )

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
