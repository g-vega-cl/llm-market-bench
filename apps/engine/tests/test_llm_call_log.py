"""Contract tests for the shared SQLite call log used by every engine LLM lane.

The engine writes into the same ``call_logs`` table the free-llm-proxy owns, so the
two schemas must not drift apart. The parity test loads the proxy's ``db.py`` by file
path (the engine never imports the proxy package) and diffs the columns both writers
produce.
"""

from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path

import pytest

from core.llm import call_log

REPO_ROOT = Path(__file__).resolve().parents[3]
PROXY_DB_PATH = REPO_ROOT / "apps" / "free_llm_proxy" / "db.py"


def _load_proxy_audit_db():
    """Import the proxy's AuditDB from its file so no package path juggling is needed."""
    spec = importlib.util.spec_from_file_location("_proxy_db_probe", PROXY_DB_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.AuditDB


def _columns(db_file: Path) -> dict[str, tuple[str, str | None]]:
    conn = sqlite3.connect(db_file)
    try:
        rows = conn.execute("PRAGMA table_info(call_logs)").fetchall()
    finally:
        conn.close()
    return {row[1]: (row[2], row[4]) for row in rows}


def test_engine_schema_matches_proxy_schema(tmp_path):
    """A column added to one writer must be added to the other, or rows silently diverge."""
    proxy_db = tmp_path / "proxy.db"
    engine_db = tmp_path / "engine.db"

    _load_proxy_audit_db()(db_path=str(proxy_db))
    call_log.log_call(
        requested_model="probe/model",
        routed_provider="openrouter",
        routed_model="probe/model",
        purpose="schema_parity",
        db_path=str(engine_db),
    )

    assert _columns(engine_db) == _columns(proxy_db)


def test_log_call_persists_every_field(tmp_path):
    db_file = tmp_path / "calls.db"

    call_id = call_log.log_call(
        requested_model="requested/model",
        routed_provider="openrouter",
        routed_model="served/model",
        prompt_tokens=11,
        completion_tokens=7,
        total_tokens=18,
        latency_ms=42.5,
        status_code=200,
        failover_chain=["strata", "openrouter"],
        error_message=None,
        purpose="engine:jev_decisions:daily_predictor",
        prompt_preview="SPY risk-on, VIX 14",
        usage_available=True,
        billing="paid",
        db_path=str(db_file),
    )

    assert call_id.startswith("call_")

    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    try:
        row = dict(conn.execute("SELECT * FROM call_logs").fetchone())
    finally:
        conn.close()

    assert row["requested_model"] == "requested/model"
    assert row["routed_provider"] == "openrouter"
    assert row["routed_model"] == "served/model"
    assert row["prompt_tokens"] == 11
    assert row["completion_tokens"] == 7
    assert row["total_tokens"] == 18
    assert row["latency_ms"] == pytest.approx(42.5)
    assert row["status_code"] == 200
    assert row["purpose"] == "engine:jev_decisions:daily_predictor"
    assert row["prompt_preview"] == "SPY risk-on, VIX 14"
    assert row["usage_available"] == 1
    assert row["billing"] == "paid"
    assert row["client_ip"] is None
    assert "timestamp" in row and row["timestamp"]


def test_log_call_never_raises_when_db_is_unwritable(tmp_path):
    """Telemetry must never take down a predictor turn or a trade."""
    blocker = tmp_path / "not-a-dir"
    blocker.write_text("occupied")

    result = call_log.log_call(
        requested_model="m",
        routed_provider="openrouter",
        routed_model="m",
        db_path=str(blocker / "calls.db"),
    )

    assert result is None


def test_connection_sets_busy_timeout_and_wal(tmp_path):
    """Three containers share this file; a lock must wait, not raise, and readers must not block."""
    db_file = tmp_path / "pragmas.db"
    conn = call_log.connect(db_file)
    try:
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == call_log.BUSY_TIMEOUT_MS
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    finally:
        conn.close()


def test_default_db_path_honours_env_override(tmp_path, monkeypatch):
    target = tmp_path / "custom.db"
    monkeypatch.setenv("SQLITE_DB_PATH", str(target))

    assert call_log.resolved_db_path() == target


def test_default_db_path_falls_back_to_proxy_data_dir(monkeypatch):
    monkeypatch.delenv("SQLITE_DB_PATH", raising=False)

    path = call_log.resolved_db_path()

    assert path == REPO_ROOT / "apps" / "free_llm_proxy" / "data" / "free_llm_proxy.db"
