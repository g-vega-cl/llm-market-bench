"""Tests for the /v1/logs endpoint and AuditDB.get_logs query filters."""

from __future__ import annotations

from apps.free_llm_proxy import server
from apps.free_llm_proxy.db import AuditDB


def test_logs_endpoint_requires_master_key(client):
    response = client.get("/v1/logs")
    assert response.status_code == 401


def test_logs_endpoint_returns_filtered_and_paginated_logs(client, monkeypatch):
    db = AuditDB(":memory:")
    monkeypatch.setattr(server, "audit_db", db)

    db.log_call(
        requested_model="auto-go",
        routed_provider="groq",
        routed_model="llama-3.3-70b",
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        latency_ms=210.5,
        status_code=200,
        failover_chain=["cerebras (HTTP 429)"],
        purpose="recipe-builder",
        prompt_preview="Build a momentum bot",
        billing="free",
    )
    db.log_call(
        requested_model="auto-go",
        routed_provider="openrouter",
        routed_model="paid/last-resort",
        prompt_tokens=200,
        completion_tokens=80,
        total_tokens=280,
        latency_ms=420.0,
        status_code=200,
        failover_chain=[],
        purpose="auto-wiki",
        prompt_preview="Summarize git diff",
        billing="paid",
    )
    db.log_call(
        requested_model="auto-go",
        routed_provider="none",
        routed_model="none",
        latency_ms=55.0,
        status_code=429,
        error_message="All providers rate limited",
        purpose="intraday",
        billing="free",
    )

    headers = {"Authorization": "Bearer sk-test-master-key"}

    res_all = client.get("/v1/logs?limit=10", headers=headers)
    assert res_all.status_code == 200
    body = res_all.json()
    assert body["total"] == 3
    assert len(body["logs"]) == 3
    # Ordered newest first
    assert body["logs"][0]["status_code"] == 429
    assert body["logs"][2]["routed_provider"] == "groq"
    assert body["logs"][2]["failover_chain"] == ["cerebras (HTTP 429)"]

    # Filter by provider
    res_groq = client.get("/v1/logs?provider=groq", headers=headers)
    assert res_groq.status_code == 200
    assert res_groq.json()["total"] == 1
    assert res_groq.json()["logs"][0]["routed_provider"] == "groq"

    # Filter by status_code
    res_429 = client.get("/v1/logs?status_code=429", headers=headers)
    assert res_429.status_code == 200
    assert res_429.json()["total"] == 1
    assert res_429.json()["logs"][0]["error_message"] == "All providers rate limited"

    # Filter by billing
    res_paid = client.get("/v1/logs?billing=paid", headers=headers)
    assert res_paid.status_code == 200
    assert res_paid.json()["total"] == 1
    assert res_paid.json()["logs"][0]["billing"] == "paid"

    # Pagination
    res_page = client.get("/v1/logs?limit=1&offset=1", headers=headers)
    assert res_page.status_code == 200
    assert res_page.json()["total"] == 3
    assert len(res_page.json()["logs"]) == 1
    assert res_page.json()["logs"][0]["routed_provider"] == "openrouter"
