"""Unit tests for the call_warren_buffett tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.llm.tools import execute_call_warren_buffett_tool
from execution.providers.base import TickerData


@pytest.mark.asyncio
async def test_execute_call_warren_buffett_macro_mode():
    """Verify that calling Warren Buffett without a ticker returns a macro valuation audit."""
    mock_db_res = MagicMock()
    mock_db_res.data = [
        {
            "date": "2026-09-21",
            "pe_ratio": 26.5,
            "forward_pe": 22.0,
            "pb_ratio": 4.8,
            "ps_ratio": 2.9,
            "pfcf_ratio": 24.0,
        }
    ]

    mock_fred_data = {"latest_value": 4.25, "observations": [{"value": 4.25}]}

    with (
        patch("core.db.get_supabase_client") as mock_db,
        patch("core.fred.fetch_fred_series_observations", new_callable=AsyncMock, return_value=mock_fred_data),
    ):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = mock_db_res
        mock_db.return_value = mock_client

        report = await execute_call_warren_buffett_tool()

    assert "THE ORACLE OF OMAHA" in report
    assert "MACRO VALUATION & CAPITAL ALLOCATION BRIEFING" in report
    assert "Forward P/E: 22.00" in report
    assert "Equity Risk Premium (ERP)" in report
    assert "Be fearful when others are greedy" in report


@pytest.mark.asyncio
async def test_execute_call_warren_buffett_ticker_quality_company():
    """Verify that a high-quality, profitable company receives moat praise and fair valuation analysis."""
    mock_quote = TickerData(
        ticker="BRK.B",
        price=450.0,
        market_cap=950000000000.0,
        exists=True,
        currency="USD",
        exchange="NYSE",
    )

    mock_metrics = [
        {
            "symbol": "BRK.B",
            "date": "2025-12-31",
            "peRatio": 18.5,
            "pbRatio": 1.45,
            "debtToEquity": 0.25,
            "netDebt": -50000000000.0,  # Net cash
            "roe": 0.16,
            "freeCashFlowYield": 0.055,
            "currentRatio": 1.8,
        }
    ]

    mock_fred_data = {"latest_value": 4.25}

    with (
        patch("execution.market_data.MarketDataManager.get_quote", new_callable=AsyncMock, return_value=mock_quote),
        patch(
            "execution.market_data.MarketDataManager.get_key_metrics", new_callable=AsyncMock, return_value=mock_metrics
        ),
        patch("core.fred.fetch_fred_series_observations", new_callable=AsyncMock, return_value=mock_fred_data),
    ):
        report = await execute_call_warren_buffett_tool(
            ticker="BRK.B",
            action="BUY",
            proposed_thesis="Strong insurance float and fortress balance sheet with earnings resilience.",
        )

    assert "Ticker: BRK.B" in report
    assert "MOAT & CAPITAL EFFICIENCY" in report
    assert "BALANCE SHEET SANITY" in report
    assert "Conservative fortress balance sheet" in report
    assert "MUNGER INVERSION" in report
    assert "ORACLE VERDICT" in report


@pytest.mark.asyncio
async def test_execute_call_warren_buffett_ticker_swimming_naked():
    """Verify that excessive leverage triggers a swimming naked balance sheet warning."""
    mock_quote = TickerData(
        ticker="RISKY",
        price=25.0,
        market_cap=500000000.0,
        exists=True,
        currency="USD",
        exchange="NYSE",
    )

    mock_metrics = [
        {
            "symbol": "RISKY",
            "date": "2025-12-31",
            "peRatio": 42.0,
            "pbRatio": 6.2,
            "debtToEquity": 3.8,  # Heavily levered
            "netDebt": 1200000000.0,  # 1.2B net debt on 500M market cap
            "roe": -0.05,
            "freeCashFlowYield": -0.02,
            "currentRatio": 0.75,
        }
    ]

    mock_fred_data = {"latest_value": 4.25}

    with (
        patch("execution.market_data.MarketDataManager.get_quote", new_callable=AsyncMock, return_value=mock_quote),
        patch(
            "execution.market_data.MarketDataManager.get_key_metrics", new_callable=AsyncMock, return_value=mock_metrics
        ),
        patch("core.fred.fetch_fred_series_observations", new_callable=AsyncMock, return_value=mock_fred_data),
    ):
        report = await execute_call_warren_buffett_tool(
            ticker="RISKY",
            action="BUY",
            proposed_thesis="Turnaround candidate after short squeeze.",
        )

    assert "SWIMMING NAKED WARNING" in report
    assert "Never lose money" in report
    assert "REJECTED" in report or "CAUTION" in report


@pytest.mark.asyncio
async def test_execute_call_warren_buffett_ticker_not_found():
    """Verify that an invalid or unquoted ticker returns a helpful error string."""
    with patch("execution.market_data.MarketDataManager.get_quote", new_callable=AsyncMock, return_value=None):
        report = await execute_call_warren_buffett_tool(ticker="INVALID123")

    assert "Error:" in report
    assert "INVALID123" in report


@pytest.mark.asyncio
async def test_execute_tool_dispatch_call_warren_buffett():
    """Verify that execute_tool properly routes call_warren_buffett to execute_call_warren_buffett_tool."""
    from core.llm.handlers.base import execute_tool

    with patch(
        "core.llm.tools.execute_call_warren_buffett_tool",
        new_callable=AsyncMock,
        return_value="Dispatched Oracle Report",
    ) as mock_exec:
        result = await execute_tool(
            "call_warren_buffett",
            {"ticker": "AAPL", "action": "BUY", "proposed_thesis": "Moat thesis"},
            model_name="test_agent",
        )

    mock_exec.assert_awaited_once_with(
        ticker="AAPL",
        action="BUY",
        proposed_thesis="Moat thesis",
    )
    assert result == "Dispatched Oracle Report"
