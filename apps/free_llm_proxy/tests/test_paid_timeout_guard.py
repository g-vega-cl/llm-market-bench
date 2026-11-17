"""TDD suite: timeouts surface as 504 `timeout_error`, and never buy paid tokens.

The guard can only work if a timed-out attempt is recognisable: `execute_completion`
must map `httpx.TimeoutException` to `504 timeout_error` (a socket read timeout used
to surface as `503 connection_error`, which the guard never saw), and the httpx read
window must come from `CLOUD_REQUEST_TIMEOUT_SECONDS` instead of a hardcoded 60s.
"""

import httpx
import pytest
from fastapi.testclient import TestClient

from apps.free_llm_proxy import config
from apps.free_llm_proxy.client import build_timeout, execute_completion
from apps.free_llm_proxy.server import app
from apps.free_llm_proxy.tests.limit_helpers import (
    capture,
    install_catalog,
    install_chain,
    post,
    provider_cfg,
)

CHAIN = [("kilo", "kilo"), ("opencode-go", "opencode-go")]
CATALOG = {"kilo": ["kilo-auto/free"], "opencode-go": ["kimi-k3-flash"]}
TIMEOUT_BODY = {
    "error": {
        "message": "Provider https://kilo.test timed out",
        "type": "timeout_error",
    }
}


@pytest.fixture
def client():
    return TestClient(app)


def _install(monkeypatch) -> None:
    install_chain(monkeypatch, [(name, provider_cfg(p_id)) for name, p_id in CHAIN])
    install_catalog(monkeypatch, CATALOG)


async def _timeout_free(provider_cfg_):
    """Free providers blow the wall clock; a paid dispatch would succeed."""
    if provider_cfg_.get("billing") == "paid":
        return None
    return 504, TIMEOUT_BODY, {}


# --------------------------------------------------------------------------- #
# Transport: the effective timeout and the timeout/connection distinction
# --------------------------------------------------------------------------- #


def test_read_timeout_window_follows_config(monkeypatch):
    """No hidden 60s read cap: the httpx window is the configured wall clock."""
    monkeypatch.setattr(config, "CLOUD_REQUEST_TIMEOUT_SECONDS", 42.0, raising=False)

    timeout = build_timeout()

    assert timeout.read == 42.0
    assert timeout.connect == 3.0


class _RaisingClient:
    def __init__(self, exc):
        self._exc = exc

    async def post(self, *args, **kwargs):
        raise self._exc

    async def aclose(self):
        return None


@pytest.mark.asyncio
async def test_read_timeout_maps_to_504_timeout_error():
    """A socket read timeout is a timeout, not a connection error."""
    status, body, _headers = await execute_completion(
        provider_cfg={"base_url": "https://kilo.test/v1"},
        payload={"model": "x"},
        client=_RaisingClient(httpx.ReadTimeout("read timed out")),  # type: ignore[arg-type]
    )

    assert status == 504
    assert body["error"]["type"] == "timeout_error"


@pytest.mark.asyncio
async def test_connect_error_still_maps_to_503_connection_error():
    """A refused connection stays a connection error so it is not mislabelled."""
    status, body, _headers = await execute_completion(
        provider_cfg={"base_url": "https://kilo.test/v1"},
        payload={"model": "x"},
        client=_RaisingClient(httpx.ConnectError("refused")),
    )

    assert status == 503
    assert body["error"]["type"] == "connection_error"


# --------------------------------------------------------------------------- #
# Money guard: a free-provider timeout must not reach the paid tier
# --------------------------------------------------------------------------- #


def test_timeout_skips_paid_tier(client, monkeypatch):
    """auto-go: kilo timing out must produce an error, not an OpenCode Go charge."""
    _install(monkeypatch)
    monkeypatch.setattr(config, "PAID_TIMEOUT_GUARD", True, raising=False)
    dispatched = capture(monkeypatch, behaviour=_timeout_free)

    resp = post(client, "auto-go")

    assert [name for name, _ in dispatched] == ["Kilo Code"]
    assert resp.status_code == 502
    assert "paid guard" in resp.text
    # The terminal error still reports the real cause, not the guard's note.
    assert "timed out" in resp.text


def test_timeout_does_not_trigger_in_provider_cascade(client, monkeypatch):
    """A 504 must not be retried inside the same provider (429/503 still are)."""
    _install(monkeypatch)
    dispatched = capture(monkeypatch, behaviour=_timeout_free)

    post(client, "auto-go")

    assert [name for name, _ in dispatched].count("Kilo Code") == 1


def test_timeout_still_dispatches_when_guard_disabled(client, monkeypatch):
    """With the guard off, paid failover behaves as before (explicit opt-out)."""
    _install(monkeypatch)
    monkeypatch.setattr(config, "PAID_TIMEOUT_GUARD", False, raising=False)
    dispatched = capture(monkeypatch, behaviour=_timeout_free)

    resp = post(client, "auto-go")

    assert [name for name, _ in dispatched] == ["Kilo Code", "OpenCode Go"]
    assert resp.status_code == 200


def test_explicit_paid_target_survives_free_timeout(client, monkeypatch):
    """An explicit opencode-go request is a deliberate charge and is not blocked."""
    _install(monkeypatch)
    dispatched = capture(monkeypatch, behaviour=_timeout_free)

    resp = post(client, "opencode-go/kimi-k3-flash")

    assert resp.status_code == 200
    assert [name for name, _ in dispatched] == ["Kilo Code", "OpenCode Go"]


def test_timeout_guard_is_per_request(client, monkeypatch):
    """A timeout in one request must not poison the next request's paid fallback."""
    _install(monkeypatch)
    capture(monkeypatch, behaviour=_timeout_free)
    post(client, "auto-go")

    async def success(provider_cfg_):
        return None

    dispatched_ok = capture(monkeypatch, behaviour=success)

    resp = post(client, "auto-go")

    assert resp.status_code == 200
    assert [name for name, _ in dispatched_ok] == ["Kilo Code"]


def test_429_still_reaches_paid_tier(client, monkeypatch):
    """Only timeouts are guarded; a genuine rate limit may still use the paid tier."""
    _install(monkeypatch)

    async def rate_limited(provider_cfg_):
        if provider_cfg_.get("billing") == "paid":
            return None
        return 429, {"error": {"message": "rate limited"}}, {"retry-after": "1"}

    dispatched = capture(monkeypatch, behaviour=rate_limited)

    resp = post(client, "auto-go")

    # Kilo's in-provider 429 cascade retries its own free fallbacks first, so the
    # only assertion that matters is that the paid tier is still reachable.
    assert [name for name, _ in dispatched][-1] == "OpenCode Go"
    assert resp.status_code == 200
