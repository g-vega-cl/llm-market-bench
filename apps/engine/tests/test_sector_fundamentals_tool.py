"""Unit tests for get_sector_fundamentals tool."""

from unittest.mock import MagicMock, patch

import pytest

from core.llm.handlers.base import execute_tool
from core.llm.tools import execute_sector_fundamentals_tool


@pytest.mark.asyncio
async def test_execute_sector_fundamentals_tool_with_constituents():
    mock_db = MagicMock()
    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_order = MagicMock()
    mock_limit = MagicMock()

    mock_db.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.order.return_value = mock_order
    mock_order.limit.return_value = mock_limit

    # Mock constituents with sector mappings and earnings info
    mock_constituents = [
        # Tech (XLK)
        {
            "symbol": "AAPL",
            "company_name": "Apple Inc.",
            "sector": "Technology",
            "market_cap": 2000_000_000_000.0,
            "price": 100.0,
            "pe": 20.0,
            "next_eps_est": 6.0,  # fwd income = (2000B / 100) * 6 = 120B -> fwd PE = 2000 / 120 = 16.67
            "beat": True,
        },
        {
            "symbol": "NVDA",
            "company_name": "NVIDIA Corp",
            "sector": "Technology",
            "market_cap": 1000_000_000_000.0,
            "price": 100.0,
            "pe": 40.0,
            "next_eps_est": 4.0,  # fwd income = (1000B / 100) * 4 = 40B -> fwd PE = 1000 / 40 = 25.0
            "beat": True,
        },
        # Financials (XLF)
        {
            "symbol": "JPM",
            "company_name": "JPMorgan Chase & Co.",
            "sector": "Financial Services",
            "market_cap": 500_000_000_000.0,
            "price": 100.0,
            "pe": 12.0,
            "next_eps_est": 10.0,
            "beat": False,
        },
        # Energy (XLE)
        {
            "symbol": "XOM",
            "company_name": "Exxon Mobil Corp",
            "sector": "Energy",
            "market_cap": 400_000_000_000.0,
            "price": 100.0,
            "pe": 10.0,
            "next_eps_est": 11.0,
            "beat": True,
        },
    ]

    mock_limit.execute.return_value = MagicMock(
        data=[
            {
                "date": "2026-09-02",
                "pe_ratio": 24.5,
                "forward_pe": 20.2,
                "constituents_data": mock_constituents,
            }
        ]
    )

    with patch("core.db.get_supabase_client", return_value=mock_db):
        result = await execute_sector_fundamentals_tool()

    assert "S&P 500 Sector Fundamentals & Earnings Breakdown" in result
    # XLK Tech: Total mcap 3000B, sum_income = 2000/20 + 1000/40 = 100 + 25 = 125B -> PE = 3000 / 125 = 24.00
    # XLK beat rate: 2/2 = 100.0%
    assert "XLK" in result
    assert "24.00" in result or "24.0" in result
    assert "100.0%" in result

    # XLF Financials: beat rate 0/1 = 0.0%
    assert "XLF" in result
    assert "0.0%" in result

    # XLE Energy: beat rate 1/1 = 100.0%
    assert "XLE" in result


@pytest.mark.asyncio
async def test_tool_dispatch_get_sector_fundamentals():
    mock_db = MagicMock()
    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_order = MagicMock()
    mock_limit = MagicMock()

    mock_db.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.order.return_value = mock_order
    mock_order.limit.return_value = mock_limit

    mock_limit.execute.return_value = MagicMock(
        data=[
            {
                "date": "2026-09-02",
                "constituents_data": [
                    {
                        "symbol": "AAPL",
                        "sector": "Technology",
                        "market_cap": 2000_000_000_000.0,
                        "price": 100.0,
                        "pe": 20.0,
                        "next_eps_est": 6.0,
                        "beat": True,
                    }
                ],
            }
        ]
    )

    with patch("core.db.get_supabase_client", return_value=mock_db):
        output = await execute_tool("get_sector_fundamentals", {}, "deepseek-v4-flash")

    assert "S&P 500 Sector Fundamentals" in output
    assert "XLK" in output


@pytest.mark.asyncio
async def test_execute_sector_fundamentals_tool_no_data():
    mock_db = MagicMock()
    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_order = MagicMock()
    mock_limit = MagicMock()

    mock_db.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.order.return_value = mock_order
    mock_order.limit.return_value = mock_limit

    # Empty table
    mock_limit.execute.return_value = MagicMock(data=[])

    with patch("core.db.get_supabase_client", return_value=mock_db):
        result = await execute_sector_fundamentals_tool()

    assert "No S&P 500 Market Health Barometer data found" in result or "No constituent data" in result
