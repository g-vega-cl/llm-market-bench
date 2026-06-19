"""Unit tests for the new FMPProvider endpoints: profile, estimates, growth."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from execution.providers.fmp import FMPProvider


@pytest.mark.asyncio
async def test_fmp_provider_get_company_profile():
    """Test get_company_profile fetches and returns profile list."""
    provider = FMPProvider()
    provider.api_key = "test_api_key"

    mock_response = [
        {
            "symbol": "AAPL",
            "companyName": "Apple Inc.",
            "beta": 1.25,
            "mktCap": 3000000000000.0,
        }
    ]

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_response
        mock_get.return_value = mock_resp

        profile = await provider.get_company_profile("AAPL")

        assert len(profile) == 1
        assert profile[0]["companyName"] == "Apple Inc."
        assert profile[0]["beta"] == 1.25
        mock_get.assert_called_once_with(
            "https://financialmodelingprep.com/stable/profile", params={"symbol": "AAPL", "apikey": "test_api_key"}
        )


@pytest.mark.asyncio
async def test_fmp_provider_get_analyst_estimates():
    """Test get_analyst_estimates fetches and returns consensus estimates."""
    provider = FMPProvider()
    provider.api_key = "test_api_key"

    mock_response = [
        {
            "symbol": "AAPL",
            "date": "2025-12-31",
            "estimatedRevenueAvg": 450000000000.0,
        }
    ]

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_response
        mock_get.return_value = mock_resp

        estimates = await provider.get_analyst_estimates("AAPL", period="annual", limit=1)

        assert len(estimates) == 1
        assert estimates[0]["estimatedRevenueAvg"] == 450000000000.0
        mock_get.assert_called_once_with(
            "https://financialmodelingprep.com/stable/analyst-estimates",
            params={"symbol": "AAPL", "period": "annual", "limit": 1, "apikey": "test_api_key"},
        )


@pytest.mark.asyncio
async def test_fmp_provider_get_financial_growth():
    """Test get_financial_growth fetches and returns growth ratios."""
    provider = FMPProvider()
    provider.api_key = "test_api_key"

    mock_response = [
        {
            "symbol": "AAPL",
            "date": "2024-12-31",
            "revenueGrowth": 0.085,
        }
    ]

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_response
        mock_get.return_value = mock_resp

        growth = await provider.get_financial_growth("AAPL", period="annual", limit=1)

        assert len(growth) == 1
        assert growth[0]["revenueGrowth"] == 0.085
        mock_get.assert_called_once_with(
            "https://financialmodelingprep.com/stable/financial-growth",
            params={"symbol": "AAPL", "period": "annual", "limit": 1, "apikey": "test_api_key"},
        )
