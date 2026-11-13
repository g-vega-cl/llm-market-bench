"""Tests for audit DB telemetry columns, indexes, and token coverage."""

from __future__ import annotations

import sqlite3

from apps.free_llm_proxy.db import AuditDB


def test_metrics_token_coverage():
    """Token coverage exposes the streaming usage gap explicitly."""
    db = AuditDB(db_path=":memory:")
    db.log_call(
        requested_model="free-auto",
        routed_provider="groq",
        routed_model="test",
        total_tokens=10,
        latency_ms=100.0,
        status_code=200,
        is_stream=True,
        usage_available=True,
        duration_ms=250.0,
        stream_completed=True,
    )
    db.log_call(
        requested_model="free-auto",
        routed_provider="groq",
        routed_model="test",
        total_tokens=0,
        latency_ms=120.0,
        status_code=200,
        is_stream=True,
        usage_available=False,
        duration_ms=350.0,
        stream_completed=True,
    )
    db.log_call(
        requested_model="free-auto",
        routed_provider="groq",
        routed_model="test",
        total_tokens=0,
        latency_ms=150.0,
        status_code=200,
        is_stream=True,
        usage_available=False,
        duration_ms=1000.0,
        stream_completed=False,
    )

    metrics = db.get_metrics()
    assert metrics["streaming_requests"] == 3
    assert metrics["usage_available_requests"] == 1
    assert metrics["token_coverage_pct"] == 33.3
    assert metrics["incomplete_streams"] == 1
    assert metrics["avg_stream_duration_ms"] == 300.0


def test_schema_has_telemetry_columns_and_indexes():
    db = AuditDB(db_path=":memory:")
    connection = db._get_connection()
    columns = {row[1] for row in connection.execute("PRAGMA table_info(call_logs)")}
    indexes = {row[1] for row in connection.execute("PRAGMA index_list(call_logs)")}

    assert {
        "is_stream",
        "usage_available",
        "ttft_ms",
        "duration_ms",
        "stream_completed",
    } <= columns
    assert {
        "idx_call_logs_timestamp",
        "idx_call_logs_status",
        "idx_call_logs_client_ip",
    } <= indexes


def test_legacy_rows_backfill_usage_available(tmp_path):
    """Existing databases gain the new columns without losing old rows."""
    db_file = tmp_path / "legacy.db"
    connection = sqlite3.connect(db_file)
    connection.execute(
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
            error_message TEXT,
            client_ip TEXT,
            user_agent TEXT,
            purpose TEXT,
            prompt_preview TEXT
        )
        """
    )
    connection.execute(
        """
        INSERT INTO call_logs (
            id, timestamp, requested_model, routed_provider, routed_model,
            prompt_tokens, completion_tokens, total_tokens, latency_ms,
            status_code, failover_chain
        ) VALUES (
            'legacy', '2026-11-01T00:00:00+00:00', 'free-auto', 'groq', 'test',
            5, 5, 10, 42.0, 200, '[]'
        )
        """
    )
    connection.commit()
    connection.close()

    migrated = AuditDB(db_path=str(db_file))
    call = migrated.get_metrics()["recent_calls"][0]

    assert call["usage_available"] == 1
    assert call["is_stream"] == 0
    assert call["duration_ms"] == 42.0
    assert call["total_tokens"] == 10
