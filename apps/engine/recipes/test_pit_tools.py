"""Hermetic TDD tests for strict point-in-time (PIT) tool isolation in backtests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _mock_sb_tables(table_rows: dict[str, list[dict]]) -> MagicMock:
    sb = MagicMock()

    def _table(name: str) -> MagicMock:
        t = MagicMock()
        rows = table_rows.get(name, [])
        t.execute.return_value = MagicMock(data=rows)
        for m in ("select", "eq", "gte", "lt", "lte", "in_", "contains", "ilike", "order", "limit"):
            getattr(t, m).return_value = t
        return t

    sb.table.side_effect = _table
    return sb


@pytest.mark.asyncio
async def test_execute_tool_blocks_live_only_tools_in_backtest_mode():
    from core.llm.handlers.base import execute_tool

    with patch("core.llm.tools.execute_web_search_tool", new=AsyncMock()) as mock_web:
        result = await execute_tool(
            "web_search",
            {"query": "NVDA today"},
            model_name="strata",
            cutoff_date="2026-03-02",
            as_of_utc="2026-03-02T14:30:00+00:00",
        )

    mock_web.assert_not_called()
    assert "disabled in point-in-time backtests" in result


@pytest.mark.asyncio
async def test_pit_stock_quote_uses_historical_bar_never_live_manager():
    from core.llm.handlers.base import execute_tool

    sb = _mock_sb_tables(
        {
            "recipe_intraday_bars": [
                {"ticker": "NVDA", "bar_time_utc": "2026-03-02T14:30:00+00:00", "open": 122.5, "close": 124.0}
            ]
        }
    )
    with (
        patch("recipes.pit_tools.get_supabase_client", return_value=sb),
        patch("core.llm.tools.execute_stock_tool", new=AsyncMock()) as mock_live_quote,
    ):
        result = await execute_tool(
            "get_stock_quote",
            {"ticker": "NVDA"},
            model_name="strata",
            cutoff_date="2026-03-02",
            as_of_utc="2026-03-02T14:30:00+00:00",
        )

    mock_live_quote.assert_not_called()
    assert "$122.50" in result
    assert "2026-03-02" in result


@pytest.mark.asyncio
async def test_pit_news_and_memories_never_leak_post_cutoff_records():
    from core.llm.handlers.base import execute_tool

    sb = _mock_sb_tables(
        {
            "recipe_news_corpus": [
                {
                    "article_id": "n1",
                    "title": "Old Chip Catalyst",
                    "date_published": "2026-03-02T13:00:00+00:00",
                    "tickers": ["NVDA"],
                    "full_text": "Historical article",
                }
            ],
            "memories": [
                {
                    "id": "m1",
                    "memory_type": "MARKET_EVENT",
                    "importance_score": 8,
                    "created_at": "2026-03-01T10:00:00+00:00",
                    "content": "Historical tariff memory",
                }
            ],
        }
    )

    with (
        patch("recipes.pit_tools.get_supabase_client", return_value=sb),
        patch("core.llm.tools.execute_get_ticker_news_tool", new=AsyncMock()) as mock_live_news,
        patch("core.llm.tools.execute_search_past_memories_tool", new=AsyncMock()) as mock_live_mem,
    ):
        news_out = await execute_tool(
            "get_ticker_news",
            {"ticker": "NVDA", "limit": 5},
            model_name="strata",
            cutoff_date="2026-03-02",
            as_of_utc="2026-03-02T14:30:00+00:00",
        )
        mem_out = await execute_tool(
            "search_past_memories",
            {"query": "tariff", "limit": 5},
            model_name="strata",
            cutoff_date="2026-03-02",
            as_of_utc="2026-03-02T14:30:00+00:00",
        )

    mock_live_news.assert_not_called()
    mock_live_mem.assert_not_called()
    assert "Old Chip Catalyst" in news_out
    assert "Historical tariff memory" in mem_out


@pytest.mark.asyncio
async def test_pit_earnings_and_key_metrics_strip_future_dates():
    from core.llm.handlers.base import execute_tool

    future_earn = [
        {"date": "2026-05-20", "epsActual": 2.0, "epsEstimated": 1.5, "isUpcoming": False},
        {"date": "2026-02-20", "epsActual": 1.2, "epsEstimated": 1.1, "isUpcoming": False},
    ]
    future_km = [
        {"date": "2026-06-30", "peRatio": 99.0},
        {"date": "2025-12-31", "peRatio": 35.0},
    ]
    mock_mgr = MagicMock()
    mock_mgr.get_earnings_history = AsyncMock(return_value=future_earn)
    mock_mgr.get_key_metrics = AsyncMock(return_value=future_km)

    with patch("recipes.pit_tools.MarketDataManager", return_value=mock_mgr):
        earn_out = await execute_tool(
            "get_earnings_history",
            {"ticker": "NVDA", "limit": 5},
            model_name="strata",
            cutoff_date="2026-03-02",
            as_of_utc="2026-03-02T14:30:00+00:00",
        )
        km_out = await execute_tool(
            "get_key_metrics",
            {"ticker": "NVDA", "period": "annual", "limit": 2},
            model_name="strata",
            cutoff_date="2026-03-02",
            as_of_utc="2026-03-02T14:30:00+00:00",
        )

    assert "2026-02-20" in earn_out
    assert "2026-05-20" not in earn_out
    assert "2025-12-31" in km_out
    assert "2026-06-30" not in km_out


@pytest.mark.asyncio
async def test_execute_tool_plain_cutoff_date_does_not_hijack_pit_router():
    from core.llm.handlers.base import execute_tool

    with (
        patch("core.llm.tools.execute_stock_tool", new=AsyncMock(return_value="LIVE_OK")) as mock_live_quote,
        patch("recipes.pit_tools.execute_pit_tool", new=AsyncMock()) as mock_pit,
    ):
        result = await execute_tool(
            "get_stock_quote",
            {"ticker": "NVDA"},
            model_name="strata",
            cutoff_date="2026-03-02",
        )

    assert result == "LIVE_OK"
    mock_live_quote.assert_awaited_once()
    mock_pit.assert_not_called()


@pytest.mark.asyncio
async def test_pit_fetch_newsletter_falls_back_to_news_corpus_and_enforces_cutoff():
    from core.llm.handlers.base import execute_tool

    sb = _mock_sb_tables(
        {
            "macro_news": [],
            "recipe_news_corpus": [
                {
                    "article_id": "art-42",
                    "title": "Chip Demand Surge",
                    "date_published": "2026-03-02T12:00:00+00:00",
                    "tickers": ["NVDA"],
                    "full_text": "Full corpus body text for PIT backtest.",
                }
            ],
        }
    )
    with patch("recipes.pit_tools.get_supabase_client", return_value=sb):
        out = await execute_tool(
            "fetch_newsletter_content",
            {"source_ids": ["art-42"]},
            model_name="strata",
            cutoff_date="2026-03-02",
            as_of_utc="2026-03-02T14:30:00+00:00",
        )

    assert "Chip Demand Surge" in out
    assert "Full corpus body text for PIT backtest." in out


@pytest.mark.asyncio
async def test_pit_technicals_fails_closed_without_live_fallback():
    from core.llm.handlers.base import execute_tool

    empty_sb = _mock_sb_tables({"price_history": []})
    mock_mgr = MagicMock()
    mock_mgr.get_history = AsyncMock()
    with (
        patch("core.db.get_supabase_client", return_value=empty_sb),
        patch("tools.technicals.MarketDataManager", return_value=mock_mgr),
    ):
        out = await execute_tool(
            "get_technical_indicators",
            {"ticker": "NVDA", "indicators": ["rsi"]},
            model_name="strata",
            cutoff_date="2026-03-02",
            as_of_utc="2026-03-02T14:30:00+00:00",
        )

    mock_mgr.get_history.assert_not_called()
    assert "no price history available" in out.lower()


@pytest.mark.asyncio
async def test_pit_price_history_uses_strict_prior_day_lt_filter():
    from core.llm.handlers.base import execute_tool

    snap_tbl = MagicMock()
    snap_tbl.execute.return_value = MagicMock(
        data=[{"fetched_at": "2026-03-01T21:00:00+00:00", "close": 120.0, "price": 120.0, "volume": 1000}]
    )
    for m in ("select", "eq", "gte", "lt", "lte", "in_", "contains", "ilike", "order", "limit"):
        getattr(snap_tbl, m).return_value = snap_tbl

    sb = MagicMock()
    sb.table.return_value = snap_tbl
    with patch("recipes.pit_tools.get_supabase_client", return_value=sb):
        out = await execute_tool(
            "get_price_history",
            {"ticker": "NVDA", "days": 5},
            model_name="strata",
            cutoff_date="2026-03-02",
            as_of_utc="2026-03-02T14:30:00+00:00",
        )

    snap_tbl.lt.assert_called_with("fetched_at", "2026-03-02T00:00:00+00:00")
    assert "$120.00" in out


@pytest.mark.asyncio
async def test_pit_market_feeling_queries_existing_columns():
    from core.llm.handlers.base import execute_tool

    mf_tbl = MagicMock()
    mf_tbl.execute.return_value = MagicMock(
        data=[
            {
                "sentiment_label": "Cautious",
                "market_direction": "BEARISH",
                "confidence_score": 72,
                "why_explanation": "Tariff headlines weighed on semiconductors.",
                "primary_concern": "Trade policy",
                "secondary_concern": "Yields",
                "created_at": "2026-06-05T14:00:00+00:00",
            }
        ]
    )
    for m in ("select", "eq", "gte", "lt", "lte", "in_", "contains", "ilike", "order", "limit"):
        getattr(mf_tbl, m).return_value = mf_tbl

    sb = MagicMock()
    sb.table.return_value = mf_tbl
    with patch("recipes.pit_tools.get_supabase_client", return_value=sb):
        out = await execute_tool(
            "get_market_feeling",
            {},
            model_name="strata",
            cutoff_date="2026-06-05",
            as_of_utc="2026-06-05T16:30:00+00:00",
        )

    selected_cols = mf_tbl.select.call_args[0][0]
    assert "feeling_text" not in selected_cols
    assert "Cautious" in out
    assert "Tariff headlines weighed on semiconductors." in out
