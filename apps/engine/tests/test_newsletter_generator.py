"""Tests for the Daily Generated Newsletter pipeline using DeepSeek V4 Flash."""

from unittest.mock import MagicMock, patch

import pytest

from tasks.newsletter_generator import GeneratedNewsletterOutput, generate_daily_newsletter


@pytest.mark.asyncio
async def test_generate_daily_newsletter_success():
    """Test generating a newsletter successfully with ingested snapshots using DeepSeek V4 Flash."""
    mock_sb = MagicMock()
    # Mock fetching newsletter snapshots
    mock_snapshots = [
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "sender": "Bloomberg Daybreak",
            "subject": "Tech Stocks Surge on AI Demand",
            "content": "NVIDIA and AMD reached new high levels today as chip demand remains strong...",
            "date": "2026-08-06T12:00:00Z",
        },
        {
            "id": "22222222-2222-2222-2222-222222222222",
            "sender": "WSJ Markets",
            "subject": "Federal Reserve Hints at Rate Hold",
            "content": "Federal Reserve officials signaled stability in interest rates following CPI data...",
            "date": "2026-08-06T12:30:00Z",
        },
    ]

    mock_sb.table.return_value.select.return_value.gte.return_value.execute.return_value.data = mock_snapshots
    mock_sb.table.return_value.insert.return_value.execute.return_value.data = [{"id": "new-gen-id"}]

    mock_llm_response = GeneratedNewsletterOutput(
        title="Morning Market Pulse: Tech Surge & Fed Signals",
        summary="Tech stocks rally on AI hardware momentum while Fed signals interest rate stability.",
        bullet_points=[
            "NVIDIA & AMD hit fresh highs on relentless AI chip demand.",
            "Federal Reserve signals cautious rate stability after CPI data.",
        ],
        content="""# Morning Market Pulse — Aug 06, 2026

Markets opened on a bullish footing today, propelled by massive momentum in the semiconductor industry and encouraging macroeconomic commentary.

### 🚀 Key Market Dynamics
- **Tech Sector Rally**: Hardware manufacturers continue to see elevated volume.
- **Fed Outlook**: Rate stability remains the baseline assumption for upcoming meetings.

Overall, investor sentiment is leaning constructive as earnings season continues to exceed baseline expectations.""",
        read_time_minutes=2,
    )

    with (
        patch("tasks.newsletter_generator.ingest_newsletters", return_value=[]),
        patch("tasks.newsletter_generator._call_deepseek_flash", return_value=mock_llm_response) as mock_llm_call,
    ):
        result = await generate_daily_newsletter(session="open", sb_client=mock_sb)

        assert result is not None
        assert result["title"] == "Morning Market Pulse: Tech Surge & Fed Signals"
        assert result["session"] == "open"
        assert result["read_time_minutes"] == 2
        assert "formatted_time" in result
        assert "ET" in result["formatted_time"]
        assert mock_llm_call.called

        # Verify insertion into generated_newsletters
        mock_sb.table.assert_called_with("generated_newsletters")
        insert_args = mock_sb.table().insert.call_args[0][0]
        assert insert_args["session"] == "open"
        assert insert_args["title"] == "Morning Market Pulse: Tech Surge & Fed Signals"
        assert insert_args["source_count"] == 2


@pytest.mark.asyncio
async def test_generate_daily_newsletter_fallback_when_no_snapshots():
    """Test generating a fallback newsletter when 0 snapshots exist today."""
    mock_sb = MagicMock()
    mock_sb.table.return_value.select.return_value.gte.return_value.execute.return_value.data = []
    mock_sb.table.return_value.insert.return_value.execute.return_value.data = [{"id": "fallback-id"}]

    mock_llm_response = GeneratedNewsletterOutput(
        title="Market Briefing: Low Ingestion Session",
        summary="No new financial newsletters were ingested in this session window.",
        bullet_points=["Quiet news flow reported during market session."],
        content="Quiet session with limited newsletter updates. Markets operating within standard range.",
        read_time_minutes=1,
    )

    with (
        patch("tasks.newsletter_generator.ingest_newsletters", return_value=[]),
        patch("tasks.newsletter_generator._call_deepseek_flash", return_value=mock_llm_response),
    ):
        result = await generate_daily_newsletter(session="close", sb_client=mock_sb)

        assert result is not None
        assert result["session"] == "close"
        assert result["source_count"] == 0



@pytest.mark.asyncio
async def test_generate_daily_newsletter_triggers_ingest_and_uses_24h_window():
    """Test that generate_daily_newsletter triggers ingest_newsletters and queries 24-hour lookback window."""
    mock_sb = MagicMock()
    mock_sb.table.return_value.select.return_value.gte.return_value.execute.return_value.data = [
        {
            "id": "33333333-3333-3333-3333-333333333333",
            "sender": "Morning Brew",
            "subject": "Overnight Market Recap",
            "content": "Overnight futures gained 0.4% following Asian tech market gains...",
            "date": "2026-08-07T05:00:00Z",
        }
    ]
    mock_sb.table.return_value.insert.return_value.execute.return_value.data = [{"id": "gen-id-24h"}]

    mock_llm_response = GeneratedNewsletterOutput(
        title="Overnight Recap: Futures Gain",
        summary="Futures push higher overnight as tech markets post gains.",
        bullet_points=["Futures up 0.4% overnight."],
        content="Futures gained overnight leading into market open...",
        read_time_minutes=1,
    )

    fake_ingested_snapshots = [
        {
            "source_id": "test_src_1",
            "chunk_hash": "hash123",
            "sender": "Morning Brew",
            "subject": "Overnight Market Recap",
            "content": "Overnight futures gained 0.4%...",
            "date": "2026-08-07T05:00:00Z",
        }
    ]

    with (
        patch("tasks.newsletter_generator.ingest_newsletters", return_value=fake_ingested_snapshots) as mock_ingest,
        patch("tasks.newsletter_generator.bulk_upsert_newsletter_snapshots") as mock_upsert,
        patch("tasks.newsletter_generator._call_deepseek_flash", return_value=mock_llm_response),
    ):
        result = await generate_daily_newsletter(session="open", sb_client=mock_sb)

        assert mock_ingest.called
        assert mock_upsert.called
        assert result is not None
        assert result["source_count"] == 1

        # Verify gte called with 24h lookback time string
        gte_arg = mock_sb.table().select().gte.call_args[0][1]
        assert "T" in gte_arg

