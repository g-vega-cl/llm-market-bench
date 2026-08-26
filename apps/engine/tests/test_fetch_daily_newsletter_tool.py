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
                }
            ]
        )
    )

    with patch("core.db.get_async_supabase_client", new=AsyncMock(return_value=mock_sb)):
        res = await query_past_newsletters(limit=1, session="open")
        assert "Briefing 1" in res
        assert "Summary 1" in res


@pytest.mark.asyncio
async def test_get_daily_market_context_includes_newsletter():
    mock_newsletter_str = (
        "=== MORNING NEWSLETTER BRIEFING ===\n"
        "Title: Morning Market Briefing\n"
        "Summary: Test summary\n"
        "Full Briefing Content:\nTest full content"
    )

    with (
        patch("core.llm.tools.execute_fetch_daily_newsletter_tool", new=AsyncMock(return_value=mock_newsletter_str)),
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
        assert "Morning Newsletter Briefing:" in context
        assert "Morning Market Briefing" in context
        assert "Test full content" in context
