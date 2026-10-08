"""Unit tests for intraday market news ingestion, Jev relevance sieve, and tool execution."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def test_generate_source_id_hash():
    """Verify deterministic hash generation for deduplication."""
    from analysis.intraday_news import generate_source_id_hash

    h1 = generate_source_id_hash("ISM Services PMI Jumps", "Macro Wire", "2026-10-05T10:00:00Z")
    h2 = generate_source_id_hash("ISM Services PMI Jumps", "Macro Wire", "2026-10-05T10:00:00Z")
    h3 = generate_source_id_hash("Different Headline", "Macro Wire", "2026-10-05T10:00:00Z")

    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64


@pytest.mark.asyncio
async def test_evaluate_news_with_jev_market_moving():
    """Verify Jev marks genuine macro surprise as MARKET_MOVING."""
    from analysis.intraday_news import evaluate_news_with_jev

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "answers": {
            "market_relevance": {
                "choice": "MARKET_MOVING",
                "confidence": 0.92,
                "probabilities": {"MARKET_MOVING": 0.92, "NOISE": 0.08},
            }
        }
    }

    event = {
        "headline": "ISM Services PMI jumps to 54.9 in September vs 51.7 expected",
        "source": "Benzinga Wire",
        "tickers": ["SPY", "QQQ"],
        "context": "Strongest reading since Feb 2023",
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        res = await evaluate_news_with_jev(event, api_key="dummy_key")

    assert res["choice"] == "MARKET_MOVING"
    assert res["confidence"] == 92.0
    assert res["is_market_moving"] is True


@pytest.mark.asyncio
async def test_evaluate_news_with_jev_noise():
    """Verify Jev marks promotional/legal press releases as NOISE."""
    from analysis.intraday_news import evaluate_news_with_jev

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "answers": {
            "market_relevance": {
                "choice": "NOISE",
                "confidence": 0.98,
                "probabilities": {"MARKET_MOVING": 0.02, "NOISE": 0.98},
            }
        }
    }

    event = {
        "headline": "Law Firm Urges Micro-Cap Investors to Join Class Action Lawsuit",
        "source": "PR Wire",
        "tickers": ["XYZ"],
        "context": "Securities litigation notice",
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        res = await evaluate_news_with_jev(event, api_key="dummy_key")

    assert res["choice"] == "NOISE"
    assert res["confidence"] == 98.0
    assert res["is_market_moving"] is False


@pytest.mark.asyncio
async def test_evaluate_news_with_jev_missing_key():
    """Verify evaluate_news_with_jev defaults to NOISE when API key is missing."""
    from analysis.intraday_news import evaluate_news_with_jev

    with patch("analysis.intraday_news.OPENROUTER_API_KEY", None):
        res = await evaluate_news_with_jev({"headline": "Any News"}, api_key=None)

    assert res["choice"] == "NOISE"
    assert res["confidence"] == 0.0
    assert res["is_market_moving"] is False


@pytest.mark.asyncio
async def test_fetch_raw_intraday_events():
    """Verify raw events are extracted from economic calendar, Polygon, and Alpaca."""
    from analysis.intraday_news import fetch_raw_intraday_events
    from core.economic_releases import EconomicEvent

    mock_econ_event = EconomicEvent(
        date="2026-10-05 10:00:00",
        time_et="10:00 ET",
        country="US",
        event="ISM Services PMI",
        impact="High",
        actual=54.9,
        estimate=51.7,
        previous=51.5,
        change=3.4,
        status="RELEASED",
        surprise=3.2,
    )

    with (
        patch(
            "analysis.intraday_news.fetch_economic_calendar_events",
            new_callable=AsyncMock,
            return_value=[mock_econ_event],
        ),
        patch(
            "analysis.intraday_news._fetch_polygon_news_events",
            new_callable=AsyncMock,
            return_value=[
                {
                    "headline": "Fed Governor Signals Patient Approach to Future Cuts",
                    "source": "Polygon Wire",
                    "url": "https://example.com/fed",
                    "tickers": ["SPY", "TLT"],
                    "event_timestamp": "2026-10-05T14:30:00Z",
                    "context": "Central bank policy remarks",
                }
            ],
        ),
        patch(
            "analysis.intraday_news._fetch_alpaca_news_events",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        events = await fetch_raw_intraday_events()

    assert len(events) >= 2
    ism_event = next(e for e in events if "ISM Services PMI" in e["headline"])
    assert ism_event["event_timestamp"] == "2026-10-05T10:00:00+00:00"
    assert any("Fed Governor" in e["headline"] for e in events)


@pytest.mark.asyncio
async def test_sync_intraday_market_news_upsert():
    """Verify sync_intraday_market_news filters with Jev and stores records in Supabase."""
    from analysis.intraday_news import sync_intraday_market_news

    mock_sb = MagicMock()
    # Mock existing records check -> empty
    mock_sb.table().select().gte().order().execute.return_value.data = []
    # Mock existing hashes check -> empty
    mock_sb.table().select().in_().execute.return_value.data = []

    mock_raw_events = [
        {
            "headline": "Jobs Report Beats Expectations",
            "source": "Macro Wire",
            "url": "https://example.com/jobs",
            "tickers": ["SPY"],
            "event_timestamp": "2026-10-05T12:30:00Z",
            "source_id_hash": "hash_jobs_123",
            "context": "Surprise nonfarm payrolls",
        },
        {
            "headline": "Penny Stock Company Announces New Office Lease",
            "source": "PR Wire",
            "url": "https://example.com/pr",
            "tickers": ["PENNY"],
            "event_timestamp": "2026-10-05T12:35:00Z",
            "source_id_hash": "hash_penny_456",
            "context": "Routine corporate announcement",
        },
    ]

    async def mock_jev(event, **kwargs):
        if "Jobs Report" in event["headline"]:
            return {"choice": "MARKET_MOVING", "confidence": 94.0, "is_market_moving": True}
        return {"choice": "NOISE", "confidence": 99.0, "is_market_moving": False}

    with (
        patch("analysis.intraday_news.fetch_raw_intraday_events", new_callable=AsyncMock, return_value=mock_raw_events),
        patch("analysis.intraday_news.evaluate_news_with_jev", side_effect=mock_jev),
        patch(
            "analysis.intraday_news.get_recent_vetted_news",
            new_callable=AsyncMock,
            return_value=[{"headline": "Jobs Report Beats Expectations", "jev_choice": "MARKET_MOVING"}],
        ),
    ):
        saved = await sync_intraday_market_news(force=True, sb_client=mock_sb)

    assert len(saved) == 1
    assert saved[0]["headline"] == "Jobs Report Beats Expectations"
    assert saved[0]["jev_choice"] == "MARKET_MOVING"
    mock_sb.table().upsert.assert_called_once()


@pytest.mark.asyncio
async def test_execute_get_market_moving_news_tool_markdown():
    """Verify execute_get_market_moving_news_tool formats records into clean markdown briefing."""
    from analysis.intraday_news import execute_get_market_moving_news_tool

    mock_records = [
        {
            "headline": "ISM Services PMI Surges to 54.9 vs 51.7 Consensus",
            "summary": "Inflationary pressure in services; 10Y Treasury yield touches 4.28%.",
            "source": "FMP Macro Calendar",
            "tickers": ["SPY", "QQQ", "US10Y"],
            "event_timestamp": "2026-10-05T14:00:00Z",
            "jev_choice": "MARKET_MOVING",
            "jev_confidence": 92.0,
            "url": "https://example.com/ism",
        }
    ]

    with (
        patch("analysis.intraday_news.get_recent_vetted_news", new_callable=AsyncMock, return_value=mock_records),
        patch("analysis.intraday_news.sync_intraday_market_news", new_callable=AsyncMock, return_value=mock_records),
    ):
        result = await execute_get_market_moving_news_tool(limit=5)

    assert "INTRADAY MARKET-MOVING EVENTS" in result
    assert "ISM Services PMI Surges" in result
    assert "MARKET_MOVING" in result
    assert "92%" in result
    assert "SPY" in result


@pytest.mark.asyncio
async def test_execute_get_market_moving_news_tool_empty():
    """Verify tool returns clean standby message when no news is available."""
    from analysis.intraday_news import execute_get_market_moving_news_tool

    with (
        patch("analysis.intraday_news.get_recent_vetted_news", new_callable=AsyncMock, return_value=[]),
        patch("analysis.intraday_news.sync_intraday_market_news", new_callable=AsyncMock, return_value=[]),
    ):
        result = await execute_get_market_moving_news_tool()

    assert "No high-impact market-moving events or macro surprises detected today so far." in result
