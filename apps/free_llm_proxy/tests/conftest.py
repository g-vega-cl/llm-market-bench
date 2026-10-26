"""Hermetic pytest fixtures for Free LLM Proxy tests."""

import os
import pytest

# Enforce test environment variables
os.environ["FREE_PROXY_MASTER_KEY"] = "sk-test-master-key"
os.environ["PORT"] = "8086"
os.environ["SQLITE_DB_PATH"] = ":memory:"
os.environ["GROQ_API_KEY"] = "gsk_test_key"
os.environ["GEMINI_API_KEY"] = "gemini_test_key"
os.environ["OPENROUTER_API_KEY"] = "or_test_key"


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
