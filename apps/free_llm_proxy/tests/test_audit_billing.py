"""Billing provenance on proxy call logs (paid last-resort visibility)."""

from __future__ import annotations

from apps.free_llm_proxy.db import AuditDB


def test_log_call_persists_billing_and_counts_paid_usage():
    db = AuditDB(":memory:")

    db.log_call(
        requested_model="auto-go",
        routed_provider="groq",
        routed_model="gpt-oss-120b",
        status_code=200,
        billing="free",
    )
    db.log_call(
        requested_model="auto-go",
        routed_provider="openrouter",
        routed_model="paid/last-resort",
        status_code=200,
        billing="paid",
        total_tokens=1234,
    )

    metrics = db.get_metrics()

    assert metrics["paid_calls_total"] == 1
    assert metrics["paid_calls_24h"] == 1
    assert metrics["paid_tokens_24h"] == 1234


def test_log_call_defaults_to_free_billing():
    db = AuditDB(":memory:")

    db.log_call(
        requested_model="auto-go", routed_provider="gemini", routed_model="flash"
    )

    assert db.get_metrics()["paid_calls_total"] == 0


def test_paid_window_excludes_rows_older_than_24h():
    """A 40-hour-old paid call must not be counted in the 24h window (ISO 'T' vs SQL ' ')."""
    from datetime import UTC, datetime, timedelta

    db = AuditDB(":memory:")
    db.log_call(
        requested_model="auto-go",
        routed_provider="opencode-go",
        routed_model="paid/last-resort",
        status_code=200,
        billing="paid",
        total_tokens=10,
    )
    old = (datetime.now(UTC) - timedelta(hours=40)).isoformat()
    conn = db._get_connection()
    conn.execute("UPDATE call_logs SET timestamp = ?", (old,))
    conn.commit()

    metrics = db.get_metrics()

    assert metrics["paid_calls_total"] == 1
    assert metrics["paid_calls_24h"] == 0
