from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from execution.providers.fmp import FMPProvider


@pytest.mark.asyncio
async def test_fmp_provider_get_history_date_parameters():
    """Test that FMPProvider.get_history uses correct date parameters."""
    provider = FMPProvider()
    provider.api_key = "test_api_key"

    ticker = "AAPL"
    days = 90

    # Calculate expected dates
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    expected_from = start_date.strftime("%Y-%m-%d")
    expected_to = end_date.strftime("%Y-%m-%d")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"historical": [
        {"date": "2026-04-10", "close": 150.0, "volume": 1000},
        {"date": "2026-04-11", "close": 155.0, "volume": 1100}
    ]}
    mock_resp.raise_for_status = MagicMock()

    # Mock the AsyncClient.get method
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        history = await provider.get_history(ticker, days=days)

        assert len(history) == 2
        assert history[0]["price"] == 150.0
        assert history[1]["price"] == 155.0

        # Verify API call parameters
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        params = kwargs.get("params")

        assert params["symbol"] == ticker
        assert params["from"] == expected_from
        assert params["to"] == expected_to
        assert params["apikey"] == "test_api_key"
        assert "timeseries" not in params

@pytest.mark.asyncio
async def test_fmp_provider_get_history_empty_response():
    """Test FMPProvider.get_history with empty response."""
    provider = FMPProvider()
    provider.api_key = "test_api_key"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"historical": []}
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        history = await provider.get_history("AAPL", days=30)
        assert history == []

@pytest.mark.asyncio
async def test_fmp_provider_get_history_http_error():
    """Test FMPProvider.get_history with HTTP error."""
    provider = FMPProvider()
    provider.api_key = "test_api_key"

    with patch("httpx.AsyncClient.get", side_effect=httpx.HTTPError("API Down")):
        history = await provider.get_history("AAPL", days=30)
        assert history == []
