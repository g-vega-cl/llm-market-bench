"""Shared SQLite call log for every engine LLM lane.

The free-llm-proxy owns this table (``apps/free_llm_proxy/db.py``); the engine writes the
same columns so one query surface covers proxy-routed and direct OpenRouter traffic
instead of shipping usage telemetry to a third-party analytics project.

Telemetry is best-effort: a write failure is logged and swallowed. A prediction or a
trade must never fail because a row could not be written.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.config import logger

BUSY_TIMEOUT_MS = 5000
DEFAULT_PREVIEW_CHARS = 200

# Must stay identical to the proxy's effective schema after its migrations run.
# test_llm_call_log asserts column parity against the proxy's own AuditDB.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS call_logs (
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
    error_message TEXT,
    client_ip TEXT,
    user_agent TEXT,
    purpose TEXT,
    prompt_preview TEXT,
    is_stream INTEGER DEFAULT 0,
    usage_available INTEGER DEFAULT 0,
    ttft_ms REAL DEFAULT 0,
    duration_ms REAL DEFAULT 0,
    stream_completed INTEGER DEFAULT 0,
    billing TEXT DEFAULT 'free'
)
"""

_INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_call_logs_timestamp ON call_logs(timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_call_logs_status ON call_logs(status_code)",
    "CREATE INDEX IF NOT EXISTS idx_call_logs_client_ip ON call_logs(client_ip)",
)

_INSERT = """
INSERT INTO call_logs (
    id, timestamp, requested_model, routed_provider, routed_model,
    prompt_tokens, completion_tokens, total_tokens, latency_ms,
    status_code, failover_chain, error_message,
    client_ip, user_agent, purpose, prompt_preview,
    is_stream, usage_available, ttft_ms, duration_ms, stream_completed, billing
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

_initialized: set[str] = set()


def resolved_db_path() -> Path:
    """The proxy's database file: explicit env override first, then the repo default."""
    override = os.environ.get("SQLITE_DB_PATH", "").strip()
    if override:
        return Path(override)
    repo_root = Path(__file__).resolve().parents[4]
    return repo_root / "apps" / "free_llm_proxy" / "data" / "free_llm_proxy.db"


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open the shared file so three writers wait for a lock instead of failing.

    WAL is persistent per database file, so the proxy's connections inherit it too.
    """
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=BUSY_TIMEOUT_MS / 1000, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def preview(text: str | None, limit: int = DEFAULT_PREVIEW_CHARS) -> str | None:
    """Trim a prompt/context snippet for the log row."""
    if not text:
        return None
    collapsed = " ".join(str(text).split())
    return collapsed[:limit] or None


def _ensure_schema(conn: sqlite3.Connection, key: str) -> None:
    if key in _initialized:
        return
    conn.execute(_SCHEMA)
    for statement in _INDEXES:
        conn.execute(statement)
    conn.commit()
    _initialized.add(key)


def log_call(
    *,
    requested_model: str,
    routed_provider: str,
    routed_model: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    latency_ms: float = 0.0,
    status_code: int = 200,
    failover_chain: list[str] | None = None,
    error_message: str | None = None,
    client_ip: str | None = None,
    user_agent: str | None = None,
    purpose: str | None = None,
    prompt_preview: str | None = None,
    is_stream: bool = False,
    usage_available: bool = False,
    ttft_ms: float = 0.0,
    duration_ms: float | None = None,
    stream_completed: bool = False,
    billing: str = "free",
    db_path: str | Path | None = None,
) -> str | None:
    """Record one call. Returns the call id, or ``None`` when the write failed."""
    try:
        path = Path(db_path) if db_path is not None else resolved_db_path()
        call_id = f"call_{uuid.uuid4().hex[:12]}"
        row: tuple[Any, ...] = (
            call_id,
            datetime.now(UTC).isoformat(),
            requested_model,
            routed_provider,
            routed_model,
            prompt_tokens,
            completion_tokens,
            total_tokens,
            latency_ms,
            status_code,
            json.dumps(failover_chain or []),
            error_message,
            client_ip,
            user_agent,
            purpose,
            prompt_preview,
            int(is_stream),
            int(usage_available),
            ttft_ms,
            latency_ms if duration_ms is None else duration_ms,
            int(stream_completed),
            billing,
        )
        conn = connect(path)
        try:
            _ensure_schema(conn, str(path))
            conn.execute(_INSERT, row)
            conn.commit()
        finally:
            conn.close()
        return call_id
    except Exception as exc:  # noqa: BLE001 - telemetry must never break a caller
        logger.warning("LLM call log write failed (%s): %s", purpose or "unscoped", exc)
        return None
