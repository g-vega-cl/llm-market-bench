"""The OpenRouter decisions wrapper must log every call, success or not, and never
change the caller's error policy: it returns the response as-is and re-raises
transport errors after recording them.
"""

from __future__ import annotations

import sqlite3

import httpx
import pytest

from core.llm import openrouter_calls

DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"


class _StubResponse:
    def __init__(self, status_code: int, payload: dict, text: str | None = None) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text if text is not None else str(payload)

    def json(self) -> dict:
        return self._payload


class _StubClient:
    def __init__(self, response: _StubResponse | None = None, exc: Exception | None = None) -> None:
        self._response = response
        self._exc = exc
        self.calls: list[dict] = []

    async def post(self, url, headers=None, json=None):  # noqa: A002 - mirrors httpx signature
        self.calls.append({"url": url, "headers": headers, "json": json})
        if self._exc is not None:
            raise self._exc
        assert self._response is not None
        return self._response


def _rows(db_file) -> list[dict]:
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM call_logs ORDER BY rowid").fetchall()]
    finally:
        conn.close()


@pytest.mark.asyncio
async def test_successful_decisions_call_is_logged_with_usage(tmp_path, monkeypatch):
    db_file = tmp_path / "calls.db"
    monkeypatch.setenv("SQLITE_DB_PATH", str(db_file))
    client = _StubClient(
        response=_StubResponse(
            200,
            {
                "answers": {"dir": {"choice": "UP"}},
                "usage": {"prompt_tokens": 500, "completion_tokens": 20, "total_tokens": 520},
            },
        )
    )

    resp = await openrouter_calls.post_decisions(
        client,
        url=DECISIONS_URL,
        headers={"Authorization": "Bearer test"},
        payload={"model": "jev/model"},
        model="jev/model",
        purpose="engine:jev_decisions:daily_predictor",
        preview="SPY",
    )

    assert resp.status_code == 200
    assert client.calls and client.calls[0]["url"] == DECISIONS_URL

    (row,) = _rows(db_file)
    assert row["status_code"] == 200
    assert row["routed_provider"] == "openrouter"
    assert row["routed_model"] == "jev/model"
    assert row["prompt_tokens"] == 500
    assert row["completion_tokens"] == 20
    assert row["total_tokens"] == 520
    assert row["usage_available"] == 1
    assert row["purpose"] == "engine:jev_decisions:daily_predictor"
    assert row["prompt_preview"] == "SPY"
    assert row["latency_ms"] >= 0
    assert row["billing"] == "paid"


@pytest.mark.asyncio
async def test_error_response_is_logged_and_returned_untouched(tmp_path, monkeypatch):
    """Sites disagree on 4xx policy (degrade vs raise); the wrapper must not decide for them."""
    db_file = tmp_path / "calls.db"
    monkeypatch.setenv("SQLITE_DB_PATH", str(db_file))
    client = _StubClient(response=_StubResponse(429, {"error": "rate limited"}, text="rate limited"))

    resp = await openrouter_calls.post_decisions(
        client,
        url=DECISIONS_URL,
        headers={},
        payload={},
        model="jev/model",
        purpose="engine:jev_decisions:pead",
    )

    assert resp.status_code == 429
    (row,) = _rows(db_file)
    assert row["status_code"] == 429
    assert "rate limited" in (row["error_message"] or "")
    assert row["usage_available"] == 0


@pytest.mark.asyncio
async def test_transport_error_is_logged_then_reraised(tmp_path, monkeypatch):
    db_file = tmp_path / "calls.db"
    monkeypatch.setenv("SQLITE_DB_PATH", str(db_file))
    client = _StubClient(exc=httpx.ConnectTimeout("upstream timed out"))

    with pytest.raises(httpx.ConnectTimeout):
        await openrouter_calls.post_decisions(
            client,
            url=DECISIONS_URL,
            headers={},
            payload={},
            model="jev/model",
            purpose="engine:jev_decisions:intraday_news",
        )

    (row,) = _rows(db_file)
    assert row["status_code"] == 0
    assert "timed out" in (row["error_message"] or "")


@pytest.mark.asyncio
async def test_missing_usage_is_recorded_as_unavailable(tmp_path, monkeypatch):
    db_file = tmp_path / "calls.db"
    monkeypatch.setenv("SQLITE_DB_PATH", str(db_file))
    client = _StubClient(response=_StubResponse(200, {"answers": {}}))

    await openrouter_calls.post_decisions(
        client,
        url=DECISIONS_URL,
        headers={},
        payload={},
        model="jev/model",
        purpose="engine:jev_decisions:max_pain",
    )

    (row,) = _rows(db_file)
    assert row["usage_available"] == 0
    assert row["total_tokens"] == 0


class _StubRequestsResponse:
    def __init__(self, ok: bool, status_code: int, payload: dict | None = None, text: str = "") -> None:
        self.ok = ok
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self) -> dict:
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


def test_requests_completion_is_logged_with_tokens(tmp_path, monkeypatch):
    db_file = tmp_path / "calls.db"
    monkeypatch.setenv("SQLITE_DB_PATH", str(db_file))
    response = _StubRequestsResponse(
        ok=True,
        status_code=200,
        payload={"choices": [], "usage": {"prompt_tokens": 900, "completion_tokens": 100, "total_tokens": 1000}},
    )

    openrouter_calls.log_requests_call(
        purpose="engine:auto_wiki",
        model="deepseek/flash",
        preview="add a wiki page for the call log",
        response=response,
        latency_ms=1234.0,
    )

    (row,) = _rows(db_file)
    assert row["status_code"] == 200
    assert row["total_tokens"] == 1000
    assert row["usage_available"] == 1
    assert row["purpose"] == "engine:auto_wiki"
    assert row["latency_ms"] == pytest.approx(1234.0)


def test_requests_completion_failure_records_upstream_error(tmp_path, monkeypatch):
    db_file = tmp_path / "calls.db"
    monkeypatch.setenv("SQLITE_DB_PATH", str(db_file))
    response = _StubRequestsResponse(ok=False, status_code=402, text="insufficient credits")

    openrouter_calls.log_requests_call(
        purpose="engine:wiki_lint_llm",
        model="deepseek/flash",
        preview=None,
        response=response,
        latency_ms=88.0,
    )

    (row,) = _rows(db_file)
    assert row["status_code"] == 402
    assert "insufficient credits" in (row["error_message"] or "")
    assert row["usage_available"] == 0
