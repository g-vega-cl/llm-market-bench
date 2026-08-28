from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autoresearch.tools import query_past_newsletters
from core.llm.tools import (
    CANONICAL_TOOLS_REGISTRY,
    FETCH_DAILY_NEWSLETTER_TOOL,
    execute_fetch_daily_newsletter_tool,
    to_anthropic,
    to_gemini,
)
from tasks.daily_predictor import get_daily_market_context


@pytest.fixture
def mock_supabase_newsletters():
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_sb.table.return_value = mock_table
    return mock_sb, mock_table


@pytest.mark.asyncio
async def test_execute_fetch_daily_newsletter_tool_success(mock_supabase_newsletters):
    mock_sb, mock_table = mock_supabase_newsletters

    mock_record = {
        "title": "Morning Market Briefing — August 26, 2026",
        "summary": "Markets open higher following strong tech earnings.",
        "content": "# Morning Briefing\n\nFull newsletter content detailing macro narrative and trade ideas.",
        "bullet_points": ["Tech leads rally", "Yields fall 4bps"],
        "session": "open",
        "read_time_minutes": 6,
        "source_count": 5,
        "formatted_time": "09:15 ET",
        "created_at": "2026-08-26T09:15:00Z",
    }

    mock_query = MagicMock()
    mock_table.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.gte.return_value = mock_query
    mock_query.lte.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=[mock_record])

    with patch("core.llm.tools.get_supabase_client", return_value=mock_sb):
        res = await execute_fetch_daily_newsletter_tool(session="open", include_full_content=True)

        assert "Morning Market Briefing — August 26, 2026" in res
        assert "Markets open higher following strong tech earnings." in res
        assert "Full newsletter content detailing macro narrative and trade ideas." in res
        assert "Tech leads rally" in res


@pytest.mark.asyncio
async def test_execute_fetch_daily_newsletter_tool_fallback(mock_supabase_newsletters):
    mock_sb, mock_table = mock_supabase_newsletters

    fallback_record = {
        "title": "Evening Market Close Briefing — August 25, 2026",
        "summary": "Markets close mixed.",
        "content": "Previous day close analysis content.",
        "bullet_points": ["Defensive rotation"],
        "session": "close",
        "read_time_minutes": 6,
        "source_count": 3,
        "formatted_time": "17:00 ET",
        "created_at": "2026-08-25T17:00:00Z",
    }

    mock_first_query = MagicMock()
    mock_fallback_query = MagicMock()

    mock_table.select.side_effect = [mock_first_query, mock_fallback_query]

    mock_first_query.eq.return_value = mock_first_query
    mock_first_query.gte.return_value = mock_first_query
    mock_first_query.lte.return_value = mock_first_query
    mock_first_query.order.return_value = mock_first_query
    mock_first_query.limit.return_value = mock_first_query
    mock_first_query.execute.return_value = MagicMock(data=[])

    mock_fallback_query.eq.return_value = mock_fallback_query
    mock_fallback_query.order.return_value = mock_fallback_query
    mock_fallback_query.limit.return_value = mock_fallback_query
    mock_fallback_query.execute.return_value = MagicMock(data=[fallback_record])

    with patch("core.llm.tools.get_supabase_client", return_value=mock_sb):
        res = await execute_fetch_daily_newsletter_tool(session="open", target_date="2026-08-26")

        assert "Evening Market Close Briefing" in res
        assert "Previous day close analysis content." in res


@pytest.mark.asyncio
async def test_execute_fetch_daily_newsletter_tool_no_data(mock_supabase_newsletters):
    mock_sb, mock_table = mock_supabase_newsletters
    mock_query = MagicMock()
    mock_table.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=[])

    with patch("core.llm.tools.get_supabase_client", return_value=mock_sb):
        res = await execute_fetch_daily_newsletter_tool(session="open")
        assert "No generated daily newsletters found" in res


def test_fetch_daily_newsletter_tool_schema():
    tool = FETCH_DAILY_NEWSLETTER_TOOL
    assert tool is not None
    assert "parameters" in tool["function"]
    assert "fetch_daily_newsletter" in CANONICAL_TOOLS_REGISTRY

    anthropic_tool = to_anthropic(tool)
    assert anthropic_tool["name"] == "fetch_daily_newsletter"
    assert "input_schema" in anthropic_tool

    gemini_tool = to_gemini(tool)
    assert gemini_tool["name"] == "fetch_daily_newsletter"


@pytest.mark.asyncio
async def test_query_past_newsletters():
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_sb.table.return_value = mock_table
    mock_query = MagicMock()
    mock_table.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.execute = AsyncMock(
        return_value=MagicMock(
            data=[
                {
                    "title": "Briefing 1",
                    "summary": "Summary 1",
                    "bullet_points": ["Bullet 1"],
                    "session": "open",
                    "formatted_time": "09:15 ET",
                    "created_at": "2026-08-26T09:15:00Z",
                    "content": "Full detailed article body for briefing 1.",
                }
            ]
        )
    )

    with patch("core.db.get_async_supabase_client", new=AsyncMock(return_value=mock_sb)):
        res_summary = await query_past_newsletters(limit=1, session="open", include_full_content=False)
        assert "Briefing 1" in res_summary
        assert "Summary 1" in res_summary
        assert "Full detailed article body" not in res_summary

        res_full = await query_past_newsletters(limit=1, session="open", include_full_content=True)
        assert "Briefing 1" in res_full
        assert "Summary 1" in res_full
        assert "Full detailed article body for briefing 1." in res_full


@pytest.mark.asyncio
async def test_get_daily_market_context_dual_newsletters_default():
    async def mock_fetch_newsletter(session="latest", target_date=None, include_full_content=True):
        if session == "close":
            return (
                "=== PREVIOUS SESSION CLOSE BRIEFING ===\n"
                "Title: Evening Market Close Briefing\n"
                "Summary: Tech led rally into close\n"
                "Key Takeaways:\n- Tech +1.4%"
            )
        return (
            "=== TODAY'S PRE-MARKET OPEN BRIEFING ===\n"
            "Title: Morning Market Open Briefing\n"
            "Summary: Futures steady\n"
            "Full Briefing Content:\nFull morning article details"
        )

    with (
        patch("core.llm.tools.execute_fetch_daily_newsletter_tool", side_effect=mock_fetch_newsletter) as mock_fetch,
        patch("execution.market_data.MarketDataManager") as mock_mdm_cls,
        patch("core.llm.tools.execute_get_global_macro_context_tool", new=AsyncMock(return_value="Macro test")),
        patch("core.llm.tools.execute_get_volatility_index_details_tool", new=AsyncMock(return_value="Vol test")),
        patch("core.llm.tools.execute_market_health_barometer_tool", new=AsyncMock(return_value="Barometer test")),
        patch("core.llm.tools.execute_get_market_feeling_tool", new=AsyncMock(return_value="Feeling test")),
    ):
        mock_mdm = AsyncMock()
        mock_mdm.is_premarket.return_value = False
        mock_mdm.get_premarket_quote.return_value = None
        mock_mdm.get_history.return_value = []
        mock_mdm_cls.return_value = mock_mdm

        context = await get_daily_market_context(ticker="SPY")
        assert "Evening Market Close Briefing" in context
        assert "Morning Market Open Briefing" in context
        assert "Full morning article details" in context

        # Verify calls to execute_fetch_daily_newsletter_tool:
        # First call for close (summary only: include_full_content=False)
        # Second call for open (full content: include_full_content=True)
        assert mock_fetch.call_count == 2
        calls = mock_fetch.call_args_list
        assert calls[0].kwargs.get("session") == "close"
        assert calls[0].kwargs.get("include_full_content") is False
        assert calls[1].kwargs.get("session") == "open"
        assert calls[1].kwargs.get("include_full_content") is True


@pytest.mark.asyncio
async def test_get_daily_market_context_dual_newsletters_option_b():
    async def mock_fetch_newsletter(session="latest", target_date=None, include_full_content=True):
        if session == "close":
            return "Evening Close Content"
        return "Morning Open Content"

    with (
        patch("core.llm.tools.execute_fetch_daily_newsletter_tool", side_effect=mock_fetch_newsletter) as mock_fetch,
        patch("execution.market_data.MarketDataManager") as mock_mdm_cls,
        patch("core.llm.tools.execute_get_global_macro_context_tool", new=AsyncMock(return_value="")),
        patch("core.llm.tools.execute_get_volatility_index_details_tool", new=AsyncMock(return_value="")),
        patch("core.llm.tools.execute_market_health_barometer_tool", new=AsyncMock(return_value="")),
        patch("core.llm.tools.execute_get_market_feeling_tool", new=AsyncMock(return_value="")),
    ):
        mock_mdm = AsyncMock()
        mock_mdm.is_premarket.return_value = False
        mock_mdm.get_premarket_quote.return_value = None
        mock_mdm.get_history.return_value = []
        mock_mdm_cls.return_value = mock_mdm

        context = await get_daily_market_context(ticker="SPY", include_full_prior_close=True)
        assert "Evening Close Content" in context
        assert "Morning Open Content" in context

        assert mock_fetch.call_count == 2
        calls = mock_fetch.call_args_list
        assert calls[0].kwargs.get("session") == "close"
        assert calls[0].kwargs.get("include_full_content") is True
        assert calls[1].kwargs.get("session") == "open"
        assert calls[1].kwargs.get("include_full_content") is True
