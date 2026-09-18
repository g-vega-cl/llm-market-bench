"""Tests for core.economic_releases module and economic calendar integration."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from analysis.calendar_scenarios import calculate_target_window


def test_calculate_target_window_today():
    """Verify that calculate_target_window recognizes 'today'."""
    ref_date = date(2026, 9, 11)
    start, end, label = calculate_target_window("today", ref_date=ref_date)
    assert start == ref_date
    assert end == ref_date
    assert "Today" in label


@pytest.mark.asyncio
async def test_fetch_economic_calendar_events_parsing():
    """Verify parsing of FMP economic calendar releases with released and pending items."""
    from core.economic_releases import (
        EconomicEvent,
        fetch_economic_calendar_events,
        get_today_economic_releases_summary,
    )

    mock_fmp_data = [
        {
            "date": "2026-09-11 12:30:00",
            "country": "US",
            "event": "CPI s.a (Aug)",
            "currency": "USD",
            "previous": 332.81,
            "estimate": 334.14,
            "actual": 334.131,
            "change": 1.321,
            "impact": "High",
            "changePercentage": 0.4,
        },
        {
            "date": "2026-09-11 12:30:00",
            "country": "US",
            "event": "CPI n.s.a MoM (Aug)",
            "currency": "USD",
            "previous": -0.01,
            "estimate": None,
            "actual": 0.32,
            "change": 0.33,
            "impact": "Low",
            "changePercentage": 3300.0,
        },
        {
            "date": "2026-09-11 14:00:00",
            "country": "US",
            "event": "Michigan Consumer Sentiment (Prelim)",
            "currency": "USD",
            "previous": 67.9,
            "estimate": 68.5,
            "actual": None,
            "change": None,
            "impact": "Medium",
            "changePercentage": None,
        },
    ]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_fmp_data

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        events = await fetch_economic_calendar_events(
            from_date="2026-09-11",
            to_date="2026-09-11",
            force_refresh=True,
        )

        assert len(events) == 3

        cpi_event = events[0]
        assert isinstance(cpi_event, EconomicEvent)
        assert cpi_event.event == "CPI s.a (Aug)"
        assert cpi_event.actual == 334.131
        assert cpi_event.estimate == 334.14
        assert cpi_event.previous == 332.81
        assert cpi_event.status == "RELEASED"
        assert cpi_event.surprise == pytest.approx(-0.009, abs=1e-4)
        assert cpi_event.impact == "High"

        # Pending event check
        pending_event = events[2]
        assert pending_event.event == "Michigan Consumer Sentiment (Prelim)"
        assert pending_event.actual is None
        assert pending_event.status == "PENDING"
        assert pending_event.surprise is None

        # Summary formatting check
        summary = await get_today_economic_releases_summary(
            target_date="2026-09-11",
            force_refresh=True,
        )
        assert "TODAY'S ECONOMIC RELEASES" in summary
        assert "CPI s.a (Aug)" in summary
        assert "334.13" in summary
        assert "RELEASED" in summary
        assert "PENDING" in summary


@pytest.mark.asyncio
async def test_economic_releases_caching_ttl():
    """Verify that economic calendar results are cached for 30 minutes."""
    from core.economic_releases import (
        fetch_economic_calendar_events,
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {
            "date": "2026-09-11 12:30:00",
            "country": "US",
            "event": "CPI s.a (Aug)",
            "previous": 332.81,
            "estimate": 334.14,
            "actual": 334.131,
            "impact": "High",
        }
    ]

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp) as mock_get:
        # First call fetches from API
        events1 = await fetch_economic_calendar_events(from_date="2026-09-11", to_date="2026-09-11", force_refresh=True)
        assert mock_get.call_count == 1
        assert len(events1) == 1

        # Second call within TTL should hit cache
        events2 = await fetch_economic_calendar_events(
            from_date="2026-09-11", to_date="2026-09-11", force_refresh=False
        )
        assert mock_get.call_count == 1
        assert len(events2) == 1


@pytest.mark.asyncio
async def test_economic_releases_missing_api_key_or_error():
    """Verify graceful handling when FMP_API_KEY is missing or API returns non-200."""
    from core.economic_releases import (
        fetch_economic_calendar_events,
        get_today_economic_releases_summary,
    )

    with patch("core.economic_releases.FMP_API_KEY", ""):
        events = await fetch_economic_calendar_events(from_date="2026-09-11", to_date="2026-09-11", force_refresh=True)
        assert events == []
        summary = await get_today_economic_releases_summary(target_date="2026-09-11", force_refresh=True)
        assert summary == ""

    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        events = await fetch_economic_calendar_events(from_date="2026-09-11", to_date="2026-09-11", force_refresh=True)
        assert events == []


@pytest.mark.asyncio
async def test_get_daily_market_context_includes_economic_releases():
    """Verify that get_daily_market_context injects today's economic releases."""
    from tasks.daily_predictor import get_daily_market_context

    mock_econ_summary = (
        "=== TODAY'S ECONOMIC RELEASES & MACRO PRINTS (Live Actual vs Consensus) ===\n"
        "- [08:30 ET] US CPI s.a (Aug): Actual 334.13 vs Est 334.14 [Impact: HIGH | Status: RELEASED]"
    )

    with (
        patch(
            "core.economic_releases.get_today_economic_releases_summary",
            new_callable=AsyncMock,
            return_value=mock_econ_summary,
        ),
        patch("core.llm.tools.execute_fetch_daily_newsletter_tool", new_callable=AsyncMock, return_value=""),
        patch("core.llm.tools.execute_get_calendar_scenario_analysis_tool", new_callable=AsyncMock, return_value=""),
        patch("core.llm.tools.execute_get_options_sentiment_tool", new_callable=AsyncMock, return_value=""),
        patch("core.llm.tools.execute_get_global_macro_context_tool", new_callable=AsyncMock, return_value=""),
        patch("core.llm.tools.execute_get_volatility_index_details_tool", new_callable=AsyncMock, return_value=""),
        patch("core.llm.tools.execute_market_health_barometer_tool", new_callable=AsyncMock, return_value=""),
        patch("core.llm.tools.execute_get_market_feeling_tool", new_callable=AsyncMock, return_value=""),
        patch("execution.market_data.MarketDataManager.is_premarket", new_callable=AsyncMock, return_value=False),
        patch("execution.market_data.MarketDataManager.get_premarket_quote", new_callable=AsyncMock, return_value=None),
        patch("execution.market_data.MarketDataManager.get_history", new_callable=AsyncMock, return_value=[]),
    ):
        ctx = await get_daily_market_context(ticker="SPY")
        assert "TODAY'S ECONOMIC RELEASES" in ctx
        assert "CPI s.a (Aug)" in ctx


@pytest.mark.asyncio
async def test_execute_get_today_economic_releases_tool():
    """Verify tool execution helper and base handler dispatch."""
    from core.llm.handlers.base import execute_tool
    from core.llm.tools import execute_get_today_economic_releases_tool

    mock_summary = "=== TODAY'S ECONOMIC RELEASES ===\n- [08:30 ET] US CPI: Actual 334.13"

    with patch(
        "core.economic_releases.get_today_economic_releases_summary",
        new_callable=AsyncMock,
        return_value=mock_summary,
    ):
        res1 = await execute_get_today_economic_releases_tool(target_date="2026-09-11")
        assert "TODAY'S ECONOMIC RELEASES" in res1
        assert "334.13" in res1

        res2 = await execute_tool("get_today_economic_releases", {"target_date": "2026-09-11"}, model_name="deepseek")
        assert "TODAY'S ECONOMIC RELEASES" in res2


@pytest.mark.asyncio
async def test_generate_daily_newsletter_passes_economic_releases_context():
    """Verify that generate_daily_newsletter fetches and forwards economic releases context."""
    from tasks.newsletter_generator import GeneratedNewsletterOutput, generate_daily_newsletter

    mock_sb = MagicMock()
    mock_sb.table.return_value.select.return_value.gte.return_value.execute.return_value.data = []
    mock_sb.table.return_value.insert.return_value.execute.return_value.data = [{"id": "gen-news-123"}]

    mock_llm_out = GeneratedNewsletterOutput(
        title="CPI Release Digest",
        summary="CPI reported in line with expectations.",
        bullet_points=["CPI at 334.13"],
        content="Briefing content",
        read_time_minutes=6,
    )

    with (
        patch("tasks.newsletter_generator.ingest_newsletters", return_value=[]),
        patch("tasks.newsletter_generator.get_curated_macro_dashboard", new_callable=AsyncMock, return_value=""),
        patch("tasks.newsletter_generator.get_newsletter_options_context", new_callable=AsyncMock, return_value=""),
        patch(
            "core.economic_releases.get_today_economic_releases_summary",
            new_callable=AsyncMock,
            return_value="=== TODAY'S ECONOMIC RELEASES ===\n- CPI s.a: Actual 334.13",
        ),
        patch("tasks.newsletter_generator._call_deepseek_flash", return_value=mock_llm_out) as mock_flash,
    ):
        res = await generate_daily_newsletter(session="open", sb_client=mock_sb)
        assert res is not None
        mock_flash.assert_called_once()
        assert "economic_releases_context" in mock_flash.call_args.kwargs
        assert "CPI s.a: Actual 334.13" in mock_flash.call_args.kwargs["economic_releases_context"]
