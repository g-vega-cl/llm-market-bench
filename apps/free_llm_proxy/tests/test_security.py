"""Tests for log-only unauthorized-request spike detection."""

from __future__ import annotations

import logging

from apps.free_llm_proxy import server
from apps.free_llm_proxy.security import UnauthorizedMonitor


def test_monitor_alerts_once_per_window():
    now = [100.0]
    monitor = UnauthorizedMonitor(
        threshold=3,
        window_seconds=60,
        connector_id="test-connector",
        clock=lambda: now[0],
    )

    assert monitor.record("1.1.1.1") is None
    assert monitor.record("1.1.1.1") is None
    spike = monitor.record("2.2.2.2")

    assert spike is not None
    assert spike.count == 3
    assert spike.top_ips[0] == ("1.1.1.1", 2)
    assert monitor.alert_active is True

    # Do not alert again while the same window is over threshold.
    assert monitor.record("3.3.3.3") is None

    # Window expires, counter clears, a fresh burst can alert again.
    now[0] = 200.0
    assert monitor.count() == 0
    assert monitor.alert_active is False
    assert monitor.record("4.4.4.4") is None
    assert monitor.record("4.4.4.4") is None
    assert monitor.record("4.4.4.4") is not None


def test_monitor_threshold_zero_disables_alerts():
    monitor = UnauthorizedMonitor(threshold=0, window_seconds=60, clock=lambda: 0.0)
    assert monitor.record("1.1.1.1") is None
    assert monitor.count() == 0
    assert monitor.alert_active is False


def test_401_spike_is_logged_without_external_calls(client, monkeypatch, caplog):
    """Two configured 401s emit one structured warning and nothing else."""
    monitor = UnauthorizedMonitor(
        threshold=2,
        window_seconds=60,
        connector_id="test-connector",
        clock=lambda: 100.0,
    )
    monkeypatch.setattr(server, "unauthorized_monitor", monitor)

    with caplog.at_level(logging.WARNING, logger="free_llm_proxy.security"):
        for _ in range(2):
            response = client.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer wrong-key"},
                json={
                    "model": "free-auto",
                    "messages": [{"role": "user", "content": "probe"}],
                },
            )
            assert response.status_code == 401

    messages = [record.getMessage() for record in caplog.records]
    assert sum("security.401_spike" in message for message in messages) == 1
    assert any("connector=test-connector" in message for message in messages)


def test_metrics_expose_security_counter(client, monkeypatch):
    monitor = UnauthorizedMonitor(
        threshold=10,
        window_seconds=60,
        connector_id="test-connector",
        clock=lambda: 100.0,
    )
    monkeypatch.setattr(server, "unauthorized_monitor", monitor)

    for _ in range(2):
        client.post(
            "/v1/chat/completions",
            headers={"Authorization": "Bearer wrong-key"},
            json={"model": "free-auto", "messages": [{"role": "user", "content": "x"}]},
        )

    metrics = client.get(
        "/v1/metrics", headers={"Authorization": "Bearer sk-test-master-key"}
    ).json()
    assert metrics["unauthorized_last_5m"] == 2
    assert metrics["security_alert_active"] is False
