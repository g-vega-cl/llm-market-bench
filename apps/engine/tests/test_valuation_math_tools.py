"""Unit tests for the execute_financial_valuation_tool and provider factory check."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.llm.tools import execute_financial_valuation_tool
from execution.market_data import TickerData
from execution.providers.factory import get_financial_provider


@pytest.mark.asyncio
async def test_execute_financial_valuation_tool_success():
    """Verify that execute_financial_valuation_tool calculates DCF valuation and compares comps correctly."""
    mock_quote = TickerData(
        ticker="AAPL",
        price=150.0,
        market_cap=2400000000.0,  # 2.4B
        exists=True,
        currency="USD",
        exchange="NASDAQ",
    )

    mock_metrics = [
        {
            "symbol": "AAPL",
            "date": "2024-09-28",
            "calendarYear": "2024",
            "period": "FY",
            "netDebt": 100000000.0,  # 100M
            "peRatio": 30.0,
            "priceToFreeCashFlowsRatio": 25.0,
            "enterpriseValueOverEBITDA": 22.0,
            "freeCashFlowYield": 0.04,
        }
    ]

    mock_profile = [
        {
            "symbol": "AAPL",
            "companyName": "Apple Inc.",
            "beta": 1.2,
        }
    ]

    mock_estimates = [
        {"estimatedRevenueAvg": 400000000000.0},
        {"estimatedRevenueAvg": 440000000000.0},  # YoY +10%
    ]

    mock_growth = [{"revenueGrowth": 0.09}]

    # Mock DB barometer return
    mock_db_res = MagicMock()
    mock_db_res.data = [{"pe_ratio": 22.0, "price_to_fcf_ratio": 20.0}]

    with (
        patch("execution.market_data.MarketDataManager.get_quote", new_callable=AsyncMock, return_value=mock_quote),
        patch(
            "execution.market_data.MarketDataManager.get_key_metrics", new_callable=AsyncMock, return_value=mock_metrics
        ),
        patch(
            "execution.market_data.MarketDataManager.get_company_profile",
            new_callable=AsyncMock,
            return_value=mock_profile,
        ),
        patch(
            "execution.market_data.MarketDataManager.get_analyst_estimates",
            new_callable=AsyncMock,
            return_value=mock_estimates,
        ),
        patch(
            "execution.market_data.MarketDataManager.get_financial_growth",
            new_callable=AsyncMock,
            return_value=mock_growth,
        ),
        patch("core.db.get_supabase_client") as mock_db,
    ):
        mock_db.return_value.table.return_value.select.return_value.order.return_value.limit.return_value.execute = (
            MagicMock(return_value=mock_db_res)
        )

        # Run with default inputs (which should fetch forward consensus growth = 10%)
        result = await execute_financial_valuation_tool("AAPL")

        assert "Audit Report: AAPL" in result
        assert "Apple Inc." in result
        assert "WACC" in result
        assert "Forecast Growth Rate" in result
        assert "10.0%" in result
        assert "Valuation Status" in result
        assert "DCF Bridge" in result or "Explicit Cash Flows" in result
        assert "P/E Ratio" in result


def test_yfinance_provider_raises_value_error():
    """Verify that requesting yfinance from provider factory raises a ValueError."""
    with pytest.raises(ValueError) as exc_info:
        get_financial_provider("yfinance")
    assert "yfinance provider is deprecated and removed" in str(exc_info.value)
