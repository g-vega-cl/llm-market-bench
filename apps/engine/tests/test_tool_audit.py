"""Unit and hermetic integration tests for tool execution audit logging."""

import os
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from core.tool_audit import (
    MAX_PAYLOAD_BYTES,
    get_archive_db_url,
    record_tool_audit,
)


@pytest.mark.asyncio
async def test_get_archive_db_url_env_override():
    """Verify explicit ARCHIVE_DB_URL takes precedence."""
    with patch.dict(os.environ, {"ARCHIVE_DB_URL": "https://custom-archive.example.com"}):
        assert get_archive_db_url() == "https://custom-archive.example.com"


@pytest.mark.asyncio
async def test_get_archive_db_url_github_actions_fallback():
    """Verify fallback to Cloudflare Tunnel URL when running in GitHub Actions."""
    env = {"GITHUB_ACTIONS": "true"}
    with patch.dict(os.environ, env, clear=False):
        if "ARCHIVE_DB_URL" in os.environ:
            del os.environ["ARCHIVE_DB_URL"]
        assert get_archive_db_url() == "https://benchify-archive-db.clvg.uk"


@pytest.mark.asyncio
async def test_get_archive_db_url_local_fallback():
    """Verify fallback to localhost:3001 when running locally outside CI."""
    env = {"GITHUB_ACTIONS": ""}
    with patch.dict(os.environ, env, clear=False):
        if "ARCHIVE_DB_URL" in os.environ:
            del os.environ["ARCHIVE_DB_URL"]
        if "GITHUB_ACTIONS" in os.environ:
            del os.environ["GITHUB_ACTIONS"]
        assert get_archive_db_url() == "http://127.0.0.1:3001"


@pytest.mark.asyncio
async def test_record_tool_audit_posts_expected_payload():
    """Verify record_tool_audit posts the structured JSON payload to PostgREST."""
    mock_post = AsyncMock(return_value=httpx.Response(201))

    with patch("httpx.AsyncClient.post", mock_post):
        success = await record_tool_audit(
            tool_name="get_volatility_metrics",
            tool_args={"ticker": "NVDA", "days": 14},
            tool_result="Current Price: $120.00\nStd Dev: $4.50",
            duration_ms=45,
            model_name="claude-3-5-sonnet",
        )

    assert success is True
    assert mock_post.call_count == 1
    call_args, call_kwargs = mock_post.call_args
    assert "/tool_execution_logs" in call_args[0]
    payload = call_kwargs["json"]
    assert payload["tool_name"] == "get_volatility_metrics"
    assert payload["tool_args"] == {"ticker": "NVDA", "days": 14}
    assert payload["tool_result"] == "Current Price: $120.00\nStd Dev: $4.50"
    assert payload["duration_ms"] == 45
    assert payload["model_name"] == "claude-3-5-sonnet"
    assert payload["status"] == "success"
    assert "created_at" in payload


@pytest.mark.asyncio
async def test_record_tool_audit_truncation_on_large_payload():
    """Verify payloads exceeding 1MB are capped and flagged in metadata."""
    huge_result = "X" * (MAX_PAYLOAD_BYTES + 5000)
    mock_post = AsyncMock(return_value=httpx.Response(201))

    with patch("httpx.AsyncClient.post", mock_post):
        await record_tool_audit(
            tool_name="get_volatility_metrics",
            tool_args={"ticker": "AAPL"},
            tool_result=huge_result,
            duration_ms=100,
        )

    call_args, call_kwargs = mock_post.call_args
    payload = call_kwargs["json"]
    assert len(payload["tool_result"]) == MAX_PAYLOAD_BYTES
    assert payload["metadata"]["truncated"] is True
    assert payload["metadata"]["original_bytes"] == len(huge_result)


@pytest.mark.asyncio
async def test_record_tool_audit_resilience_on_network_failure():
    """Verify that network drops or timeouts do not raise exceptions."""
    with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("Connection refused")):
        success = await record_tool_audit(
            tool_name="get_volatility_metrics",
            tool_args={"ticker": "NVDA"},
            tool_result="Metrics",
            duration_ms=20,
        )

    assert success is False


@pytest.mark.asyncio
async def test_execute_tool_triggers_audit_for_volatility_metrics():
    """Verify execute_tool invokes record_tool_audit in the background."""
    from unittest.mock import MagicMock

    from core.llm.handlers.base import execute_tool

    mock_record = MagicMock()

    with (
        patch("core.llm.handlers.base.async_record_tool_audit", mock_record),
        patch("core.llm.tools.execute_volatility_metrics_tool", AsyncMock(return_value="Vol output")),
    ):
        result = await execute_tool(
            name="get_volatility_metrics",
            args={"ticker": "NVDA", "days": 14},
            model_name="deepseek-chat",
        )

    assert result == "Vol output"
    assert mock_record.call_count == 1
    _, kwargs = mock_record.call_args
    assert kwargs["tool_name"] == "get_volatility_metrics"
    assert kwargs["tool_args"] == {"ticker": "NVDA", "days": 14}
    assert kwargs["tool_result"] == "Vol output"
    assert kwargs["model_name"] == "deepseek-chat"
    assert kwargs["duration_ms"] >= 0
