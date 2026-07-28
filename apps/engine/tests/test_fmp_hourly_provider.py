from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from execution.providers.fmp import FMPProvider


@pytest.mark.asyncio
async def test_get_hourly_history_api_call():
    """Test that FMPProvider.get_hourly_history makes correct FMP API calls."""
    provider = FMPProvider()
    provider.api_key = "mock_key"

    ticker = "AAPL"
    from_date = "2026-04-27"
    to_date = "2026-05-01"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {"date": "2026-04-27 11:00:00", "open": 170.0, "high": 171.0, "low": 169.5, "close": 170.5, "volume": 50000},
        {"date": "2026-04-27 14:00:00", "open": 171.0, "high": 172.0, "low": 170.8, "close": 171.5, "volume": 60000},
    ]
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp

        # We temporarily bypass/mock the cache to test the pure API call
        with (
            patch.object(provider, "_get_cached_hourly_bars", return_value=[]),
            patch.object(provider, "_cache_hourly_bars", return_value=None),
        ):
            bars = await provider.get_hourly_history(ticker, from_date, to_date)

            assert len(bars) == 2
            assert bars[0]["open"] == 170.0
            assert bars[1]["close"] == 171.5

            mock_get.assert_called_once()
            _, kwargs = mock_get.call_args
            params = kwargs.get("params")
            assert params["symbol"] == ticker
            assert params["from"] == from_date
            assert params["to"] == to_date
            assert params["apikey"] == "mock_key"


@pytest.mark.asyncio
async def test_get_hourly_history_caching():
    """Test that FMPProvider.get_hourly_history returns cached data instead of hit API."""
    provider = FMPProvider()
    provider.api_key = "mock_key"

    ticker = "AAPL"
    from_date = "2026-04-27"
    to_date = "2026-05-01"

    cached_bars = [
        {"date": "2026-04-27 11:00:00", "open": 170.0, "high": 171.0, "low": 169.5, "close": 170.5, "volume": 50000}
    ]

    with (
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
        patch.object(provider, "_get_cached_hourly_bars", return_value=cached_bars) as mock_read_cache,
        patch.object(provider, "_cache_hourly_bars") as mock_write_cache,
    ):
        bars = await provider.get_hourly_history(ticker, from_date, to_date)

        assert len(bars) == 1
        assert bars[0]["open"] == 170.0

        # Verify cache was checked and API was NOT called
        mock_read_cache.assert_called_once_with(ticker, from_date, to_date)
        mock_get.assert_not_called()
        mock_write_cache.assert_not_called()
