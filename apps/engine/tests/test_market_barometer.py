"""Unit tests for S&P 500 Market Health Barometer aggregator."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts.update_market_barometer import calculate_barometer


@pytest.mark.asyncio
async def test_calculate_barometer():
    # Mock data for two constituents
    # AAPL: Market Cap = 2000B, Price = 100, PE = 20.0, PS = 5.0, PB = 10.0, next_eps_est = 6.0, beat = True, company_name = Apple Inc.
    # MSFT: Market Cap = 1000B, Price = 200, PE = 30.0, PS = 10.0, PB = 5.0, next_eps_est = 8.0, beat = False, company_name = Microsoft Corp
    mock_constituents = ["AAPL", "MSFT"]

    mock_fetch_data = AsyncMock()
    mock_fetch_data.side_effect = [
        # AAPL
        {
            "symbol": "AAPL",
            "company_name": "Apple Inc.",
            "market_cap": 2000_000_000_000.0,
            "price": 100.0,
            "pe": 20.0,
            "pb": 10.0,
            "ps": 5.0,
            "next_eps_est": 6.0,
            "beat": True,
        },
        # MSFT
        {
            "symbol": "MSFT",
            "company_name": "Microsoft Corp",
            "market_cap": 1000_000_000_000.0,
            "price": 200.0,
            "pe": 30.0,
            "pb": 5.0,
            "ps": 10.0,
            "next_eps_est": 8.0,
            "beat": False,
        },
    ]

    mock_db = MagicMock()
    mock_table = MagicMock()
    mock_upsert = MagicMock()

    mock_db.table.return_value = mock_table
    mock_table.upsert.return_value = mock_upsert
    mock_upsert.execute = MagicMock()

    with patch(
        "scripts.update_market_barometer.FMPProvider.get_sp500_constituents", new_callable=AsyncMock
    ) as mock_get_const:
        mock_get_const.return_value = mock_constituents

        with patch("scripts.update_market_barometer.fetch_constituent_data", mock_fetch_data):
            with patch("scripts.update_market_barometer.get_supabase_client", return_value=mock_db):
                with patch("scripts.update_market_barometer.FMP_API_KEY", "dummy_key"):
                    await calculate_barometer()

    # Assert supabase was called with correct arguments
    mock_db.table.assert_called_once_with("market_barometer_history")

    args, kwargs = mock_table.upsert.call_args
    payload = args[0]

    assert payload["date"] == datetime.now().strftime("%Y-%m-%d")
    assert pytest.approx(payload["pe_ratio"], 0.01) == 22.5
    assert pytest.approx(payload["ps_ratio"], 0.01) == 6.0
    assert pytest.approx(payload["pb_ratio"], 0.01) == 7.5
    assert pytest.approx(payload["forward_pe"], 0.01) == 18.75
    assert pytest.approx(payload["earnings_surprise_momentum"], 0.01) == 50.0
    
    assert len(payload["constituents_data"]) == 2
    assert payload["constituents_data"][0]["symbol"] == "AAPL"
    assert payload["constituents_data"][0]["company_name"] == "Apple Inc."
    assert payload["constituents_data"][0]["pe"] == 20.0
    assert payload["constituents_data"][1]["symbol"] == "MSFT"
    assert payload["constituents_data"][1]["company_name"] == "Microsoft Corp"
    assert payload["constituents_data"][1]["pe"] == 30.0
