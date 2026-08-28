"""Tests for macro live returns calculation and market_data_cache today_pct_change updates."""

from unittest.mock import MagicMock, patch

import pytest

from execution.market_data import MarketDataManager
from execution.providers.base import TickerData
from scripts.update_prices import compute_ticker_macro_metrics


def test_save_batch_to_cache_includes_today_pct_change():
    """Verify _save_batch_to_cache includes today_pct_change in upsert payload."""
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    mock_table.upsert.return_value.execute.return_value = MagicMock()

    with patch("execution.market_data.get_supabase_client", return_value=mock_client):
        mdm = MarketDataManager()

    ticker_data = TickerData(
        ticker="SPY",
        price=771.1,
        market_cap=821405196069.0,
        change_pct=0.65528,
        previous_close=766.08,
    )

    mdm._save_batch_to_cache([ticker_data])

    mock_client.table.assert_called_with("market_data_cache")
    upsert_args = mock_table.upsert.call_args[0][0]
    assert len(upsert_args) == 1
    assert upsert_args[0]["ticker"] == "SPY"
    assert upsert_args[0]["price"] == 771.1
    assert upsert_args[0]["today_pct_change"] == pytest.approx(0.65528, abs=1e-4)


def test_compute_ticker_macro_metrics_with_intraday_eod_lag():
    """When history[0] is yesterday's date, compute_ticker_macro_metrics should use live price vs history[0]."""
    # Realistic history prices with ~0.8% volatility
    base_prices = [
        766.08,
        765.91,
        763.47,
        765.72,
        762.60,
        769.06,
        767.45,
        772.67,
        776.34,
        770.00,
        765.00,
        768.00,
        762.00,
        764.00,
        760.00,
        758.00,
        762.00,
        766.00,
        769.00,
        765.00,
        763.00,
        760.00,
        755.00,
        758.00,
        762.00,
        764.00,
        761.00,
        759.00,
        757.00,
        755.00,
        752.00,
        750.00,
    ]
    history = [
        {"price": p, "fetched_at": f"2026-08-{30 - i:02d}T00:00:00+00:00" if i > 0 else "2026-08-26T00:00:00+00:00"}
        for i, p in enumerate(base_prices)
    ]

    live_ticker_data = TickerData(
        ticker="SPY",
        price=771.1,
        market_cap=821405196069.0,
        previous_close=766.08,
        change_pct=0.65528,
    )

    metrics = compute_ticker_macro_metrics(
        ticker="SPY",
        history=history,
        live_ticker_data=live_ticker_data,
        today_date_str="2026-08-27",
    )

    assert metrics is not None
    assert metrics["price"] == 771.1
    assert metrics["today_pct_change"] == pytest.approx(0.65528, abs=1e-3)
    assert metrics["regime_flag"] == "Normal"
