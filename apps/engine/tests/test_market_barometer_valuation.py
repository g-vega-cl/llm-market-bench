"""Unit tests for Market Health Barometer historical valuation percentiles and Equity Risk Premium (ERP)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.llm.tools import execute_market_health_barometer_tool


@pytest.mark.asyncio
async def test_execute_market_health_barometer_tool_with_erp_and_percentiles():
    mock_db = MagicMock()
    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_order = MagicMock()
    mock_limit = MagicMock()

    mock_db.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.order.return_value = mock_order
    mock_order.limit.return_value = mock_limit

    # Provide 5 historical snapshots with varying P/E ratios
    # Latest (index 0): PE = 25.0, Forward PE = 20.0, Beat Rate = 80.0
    mock_limit.execute.return_value = MagicMock(
        data=[
            {
                "date": "2026-09-02",
                "pe_ratio": 25.0,
                "forward_pe": 20.0,
                "pb_ratio": 4.5,
                "ps_ratio": 3.0,
                "pfcf_ratio": 22.0,
                "earnings_surprise_momentum": 80.0,
            },
            {
                "date": "2026-09-01",
                "pe_ratio": 24.0,
                "forward_pe": 19.5,
                "pb_ratio": 4.4,
                "ps_ratio": 2.9,
                "pfcf_ratio": 21.5,
                "earnings_surprise_momentum": 79.0,
            },
            {
                "date": "2026-08-31",
                "pe_ratio": 26.0,
                "forward_pe": 21.0,
                "pb_ratio": 4.6,
                "ps_ratio": 3.1,
                "pfcf_ratio": 23.0,
                "earnings_surprise_momentum": 81.0,
            },
            {
                "date": "2026-08-28",
                "pe_ratio": 23.0,
                "forward_pe": 18.5,
                "pb_ratio": 4.2,
                "ps_ratio": 2.8,
                "pfcf_ratio": 20.0,
                "earnings_surprise_momentum": 78.0,
            },
        ]
    )

    # Mock FRED 10Y yield = 4.25%
    # Forward PE = 20.0 -> Earnings Yield = 100 / 20.0 = 5.00%
    # ERP = 5.00% - 4.25% = +0.75%
    mock_fred_series = AsyncMock(
        return_value={
            "series_id": "DGS10",
            "title": "10-Year Treasury Constant Maturity Rate",
            "latest_value": 4.25,
            "observations": [{"date": "2026-09-01", "value": 4.25}],
        }
    )

    with patch("core.db.get_supabase_client", return_value=mock_db):
        with patch("core.fred.fetch_fred_series_observations", mock_fred_series):
            result = await execute_market_health_barometer_tool(limit=5)

    assert "S&P 500 Aggregate Market Health Barometer" in result
    assert "Aggregate Trailing P/E: 25.00" in result
    assert "Aggregate Forward P/E:  20.00" in result
    assert "Earnings Beat Rate:     80.0%" in result
    # Check Equity Risk Premium and Forward Earnings Yield
    assert "Equity Risk Premium (ERP):" in result
    assert "+0.75%" in result or "0.75%" in result
    assert "5.00%" in result
    # Check historical variation context
    assert "Historical Valuation Context" in result or "Range" in result or "percentile" in result.lower()


@pytest.mark.asyncio
async def test_execute_market_health_barometer_tool_fred_fallback():
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
                "pe_ratio": 25.0,
                "forward_pe": 20.0,
                "pb_ratio": 4.5,
                "ps_ratio": 3.0,
                "pfcf_ratio": 22.0,
                "earnings_surprise_momentum": 80.0,
            }
        ]
    )

    # FRED raises error or returns empty
    mock_fred_series = AsyncMock(side_effect=Exception("FRED API Offline"))

    with patch("core.db.get_supabase_client", return_value=mock_db):
        with patch("core.fred.fetch_fred_series_observations", mock_fred_series):
            result = await execute_market_health_barometer_tool(limit=5)

    assert "S&P 500 Aggregate Market Health Barometer" in result
    assert "Aggregate Forward P/E:  20.00" in result
    # Should not crash on FRED exception
    assert "Error retrieving barometer data" not in result
