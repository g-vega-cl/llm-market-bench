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


@pytest.mark.asyncio
async def test_execute_tool_triggers_audit_for_macro_options_sentiment():
    """Reproduction test: Verify execute_tool dispatches get_macro_options_sentiment and audits it."""
    from unittest.mock import MagicMock

    from core.llm.handlers.base import execute_tool

    mock_record = MagicMock()

    with (
        patch("core.llm.handlers.base.async_record_tool_audit", mock_record),
        patch(
            "core.llm.tools.execute_get_macro_options_sentiment_tool",
            AsyncMock(return_value="Macro options output"),
        ) as mock_macro_tool,
    ):
        result = await execute_tool(
            name="get_macro_options_sentiment",
            args={"primary_ticker": "SPY"},
            model_name="daily_predictor",
        )

    assert result == "Macro options output"
    assert mock_macro_tool.called
    assert mock_record.call_count == 1
    _, kwargs = mock_record.call_args
    assert kwargs["tool_name"] == "get_macro_options_sentiment"
    assert kwargs["tool_args"] == {"primary_ticker": "SPY"}
    assert kwargs["tool_result"] == "Macro options output"
    assert kwargs["model_name"] == "daily_predictor"
    assert kwargs["status"] == "success"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_name,tool_args,mock_target",
    [
        (
            "audit_financial_valuation",
            {"ticker": "NVDA", "growth_rate": 0.15},
            "core.llm.tools.execute_financial_valuation_tool",
        ),
        (
            "get_sector_alternatives",
            {"ticker": "XOM"},
            "core.llm.tools.execute_sector_alternatives_tool",
        ),
        (
            "find_uncorrelated_assets",
            {"max_correlation": 0.25},
            "core.llm.tools.execute_find_uncorrelated_assets_tool",
        ),
        (
            "run_stock_screener",
            {"market_cap_min": 1000000000},
            "core.llm.tools.execute_stock_screener_tool",
        ),
    ],
)
async def test_execute_tool_triggers_audit_for_phase2_tools(tool_name, tool_args, mock_target):
    """Verify Phase 2 valuation & screening tools invoke audit logging via execute_tool."""
    from unittest.mock import MagicMock

    from core.llm.handlers.base import execute_tool

    mock_record = MagicMock()
    with (
        patch("core.llm.handlers.base.async_record_tool_audit", mock_record),
        patch(mock_target, AsyncMock(return_value="Phase 2 Tool Result")),
    ):
        result = await execute_tool(
            name=tool_name,
            args=tool_args,
            model_name="claude-3-5-sonnet",
        )

    assert result == "Phase 2 Tool Result"
    assert mock_record.call_count == 1
    _, kwargs = mock_record.call_args
    assert kwargs["tool_name"] == tool_name
    assert kwargs["tool_args"] == tool_args
    assert kwargs["tool_result"] == "Phase 2 Tool Result"
    assert kwargs["model_name"] == "claude-3-5-sonnet"
    assert kwargs["status"] == "success"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_name,tool_args,mock_target",
    [
        (
            "web_search",
            {"query": "Fed interest rate decision October 2026"},
            "core.llm.tools.execute_web_search_tool",
        ),
        (
            "get_ticker_news",
            {"ticker": "AAPL", "limit": 3},
            "core.llm.tools.execute_get_ticker_news_tool",
        ),
        (
            "search_prediction_markets",
            {"query": "recession 2026", "platform": "polymarket"},
            "core.llm.tools.execute_search_prediction_markets_tool",
        ),
        (
            "get_prediction_market_odds",
            {"market_id": "poly-123", "platform": "polymarket"},
            "core.llm.tools.execute_get_prediction_market_odds_tool",
        ),
    ],
)
async def test_execute_tool_triggers_audit_for_phase3_tools(tool_name, tool_args, mock_target):
    """Verify Phase 3 research & grounding tools invoke audit logging via execute_tool."""
    from unittest.mock import MagicMock

    from core.llm.handlers.base import execute_tool

    mock_record = MagicMock()
    with (
        patch("core.llm.handlers.base.async_record_tool_audit", mock_record),
        patch(mock_target, AsyncMock(return_value="Phase 3 Tool Result")),
    ):
        result = await execute_tool(
            name=tool_name,
            args=tool_args,
            model_name="deepseek-chat",
        )

    assert result == "Phase 3 Tool Result"
    assert mock_record.call_count == 1
    _, kwargs = mock_record.call_args
    assert kwargs["tool_name"] == tool_name
    assert kwargs["tool_args"] == tool_args
    assert kwargs["tool_result"] == "Phase 3 Tool Result"
    assert kwargs["model_name"] == "deepseek-chat"
    assert kwargs["status"] == "success"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_name,tool_args,mock_target",
    [
        (
            "get_calendar_scenario_analysis",
            {"timeframe": "next_week", "ticker": "SPY"},
            "core.llm.tools.execute_get_calendar_scenario_analysis_tool",
        ),
        (
            "get_today_economic_releases",
            {"target_date": "2026-10-03", "country": "US"},
            "core.llm.tools.execute_get_today_economic_releases_tool",
        ),
        (
            "get_global_macro_context",
            {},
            "core.llm.tools.execute_get_global_macro_context_tool",
        ),
        (
            "get_volatility_index_details",
            {"lookback_days": 90},
            "core.llm.tools.execute_get_volatility_index_details_tool",
        ),
    ],
)
async def test_execute_tool_triggers_audit_for_phase4_macro_suite(tool_name, tool_args, mock_target):
    """Verify Phase 4 macro suite tools invoke audit logging via execute_tool."""
    from unittest.mock import MagicMock

    from core.llm.handlers.base import execute_tool

    mock_record = MagicMock()
    with (
        patch("core.llm.handlers.base.async_record_tool_audit", mock_record),
        patch(mock_target, AsyncMock(return_value="Phase 4 Tool Result")),
    ):
        result = await execute_tool(
            name=tool_name,
            args=tool_args,
            model_name="daily_predictor",
        )

    assert result == "Phase 4 Tool Result"
    assert mock_record.call_count == 1
    _, kwargs = mock_record.call_args
    assert kwargs["tool_name"] == tool_name
    assert kwargs["tool_args"] == tool_args
    assert kwargs["tool_result"] == "Phase 4 Tool Result"
    assert kwargs["model_name"] == "daily_predictor"
    assert kwargs["status"] == "success"


@pytest.mark.asyncio
async def test_daily_predictor_get_daily_market_context_triggers_audit():
    """Verify that get_daily_market_context routes macro tool calls through execute_tool and audits them."""
    from unittest.mock import MagicMock

    from tasks.daily_predictor import get_daily_market_context

    mock_record = MagicMock()
    mock_mdm = MagicMock()
    mock_mdm.is_premarket = AsyncMock(return_value=False)
    mock_mdm.get_history = AsyncMock(return_value=[])
    mock_mdm.get_premarket_quote = AsyncMock(return_value=None)

    with (
        patch("core.llm.handlers.base.async_record_tool_audit", mock_record),
        patch("execution.market_data.MarketDataManager", return_value=mock_mdm),
        patch("core.llm.tools.execute_fetch_daily_newsletter_tool", new_callable=AsyncMock, return_value=""),
        patch(
            "core.llm.tools.execute_get_macro_options_sentiment_tool",
            new_callable=AsyncMock,
            return_value="Macro Options Data",
        ),
        patch(
            "core.llm.tools.execute_get_global_macro_context_tool",
            new_callable=AsyncMock,
            return_value="Global Macro Data",
        ),
        patch(
            "core.llm.tools.execute_get_volatility_index_details_tool",
            new_callable=AsyncMock,
            return_value="VIX Data",
        ),
        patch(
            "core.llm.tools.execute_market_health_barometer_tool",
            new_callable=AsyncMock,
            return_value="Barometer Data",
        ),
        patch(
            "core.llm.tools.execute_get_market_feeling_tool",
            new_callable=AsyncMock,
            return_value="Market Feeling Data",
        ),
        patch(
            "core.llm.tools.execute_get_calendar_scenario_analysis_tool",
            new_callable=AsyncMock,
            return_value="Calendar Scenarios",
        ),
        patch(
            "core.llm.tools.execute_get_today_economic_releases_tool",
            new_callable=AsyncMock,
            return_value="Economic Releases",
        ),
    ):
        ctx = await get_daily_market_context(ticker="SPY")
        assert "Macro Options Data" in ctx
        assert "Global Macro Data" in ctx
        assert "VIX Data" in ctx

        # Check recorded audits
        assert mock_record.call_count >= 5
        audited_tools = [call.kwargs["tool_name"] for call in mock_record.call_args_list]
        assert "get_macro_options_sentiment" in audited_tools
        assert "get_global_macro_context" in audited_tools
        assert "get_volatility_index_details" in audited_tools

        for call in mock_record.call_args_list:
            assert call.kwargs["model_name"] == "daily_predictor"
            assert call.kwargs["status"] == "success"
