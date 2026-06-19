"""Unit tests for S&P 500 Market Health Barometer aggregator."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts.update_market_barometer import calculate_barometer


@pytest.mark.asyncio
async def test_calculate_barometer():
    # Mock data for three constituents
    # AAPL: Market Cap = 2000B, Price = 100, PE = 20.0, PS = 5.0, PB = 10.0, pfcf = 25.0, next_eps_est = 6.0, beat = True, company_name = Apple Inc.
    # MSFT: Market Cap = 1000B, Price = 200, PE = 30.0, PS = 10.0, PB = 5.0, pfcf = 15.0, next_eps_est = 8.0, beat = False, company_name = Microsoft Corp
    # TSLA: Market Cap = 500B, Price = 150, PE = 50.0, PS = 8.0, PB = 12.0, pfcf = -10.0, next_eps_est = 3.0, beat = True, company_name = Tesla Inc (Negative FCF, should be excluded from aggregate P/FCF)
    mock_constituents = ["AAPL", "MSFT", "TSLA"]

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
            "pfcf": 25.0,
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
            "pfcf": 15.0,
            "next_eps_est": 8.0,
            "beat": False,
        },
        # TSLA
        {
            "symbol": "TSLA",
            "company_name": "Tesla Inc",
            "market_cap": 500_000_000_000.0,
            "price": 150.0,
            "pe": 50.0,
            "pb": 12.0,
            "ps": 8.0,
            "pfcf": -10.0,
            "next_eps_est": 3.0,
            "beat": True,
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
    # PE weights: AAPL (2000B PE 20 -> 100B income), MSFT (1000B PE 30 -> 33.33B income), TSLA (500B PE 50 -> 10B income)
    # Total Cap = 3500B, Total Income = 143.33B -> 3500 / 143.33333333333334 = 24.418
    assert pytest.approx(payload["pe_ratio"], 0.01) == 24.418
    # PS weights: AAPL (2000B PS 5 -> 400B revenue), MSFT (1000B PS 10 -> 100B revenue), TSLA (500B PS 8 -> 62.5B revenue)
    # Total Cap = 3500B, Total Revenue = 562.5B -> 3500 / 562.5 = 6.222
    assert pytest.approx(payload["ps_ratio"], 0.01) == 6.222
    # PB weights: AAPL (2000B PB 10 -> 200B book), MSFT (1000B PB 5 -> 200B book), TSLA (500B PB 12 -> 41.67B book)
    # Total Cap = 3500B, Total Book = 441.67B -> 3500 / 441.6666666666667 = 7.925
    assert pytest.approx(payload["pb_ratio"], 0.01) == 7.925
    # Forward PE weights: 
    # AAPL: next_eps = 6.0, price = 100 -> shares = 20B -> fwd_income = 120B
    # MSFT: next_eps = 8.0, price = 200 -> shares = 5B -> fwd_income = 40B
    # TSLA: next_eps = 3.0, price = 150 -> shares = 3.33B -> fwd_income = 10B
    # Total Cap = 3500B, Total Fwd Income = 170B -> 3500 / 170 = 20.588
    assert pytest.approx(payload["forward_pe"], 0.01) == 20.588
    # PFCF weights (excluding TSLA with negative pfcf):
    # AAPL (2000B pfcf 25 -> 80B FCF), MSFT (1000B pfcf 15 -> 66.67B FCF)
    # Total Cap (for positive FCF) = 3000B, Total FCF = 146.67B -> 3000 / 146.66666666666666 = 20.455
    assert pytest.approx(payload["pfcf_ratio"], 0.01) == 20.455
    # Earnings surprise momentum (beat rate): 2 of 3 beat -> 66.67%
    assert pytest.approx(payload["earnings_surprise_momentum"], 0.01) == 66.667

    assert len(payload["constituents_data"]) == 3
    assert payload["constituents_data"][0]["symbol"] == "AAPL"
    assert payload["constituents_data"][0]["company_name"] == "Apple Inc."
    assert payload["constituents_data"][0]["pe"] == 20.0
    assert payload["constituents_data"][0]["pfcf"] == 25.0
    assert payload["constituents_data"][1]["symbol"] == "MSFT"
    assert payload["constituents_data"][1]["company_name"] == "Microsoft Corp"
    assert payload["constituents_data"][1]["pe"] == 30.0
    assert payload["constituents_data"][1]["pfcf"] == 15.0
    assert payload["constituents_data"][2]["symbol"] == "TSLA"
    assert payload["constituents_data"][2]["company_name"] == "Tesla Inc"
    assert payload["constituents_data"][2]["pe"] == 50.0
    assert payload["constituents_data"][2]["pfcf"] == -10.0
