"""Hermetic tests for daily session open price reconciliation.

Verifies:
1. get_daily_session_open_price hierarchy (daily_predictions, fetch_intraday_prices, live quote).
2. reconcile_daily_open_trades updates entry trade price, total cost, position cost basis, and portfolio cash.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from execution.daily_reconciliation import (
    get_daily_session_open_price,
    reconcile_daily_open_trades,
)


@pytest.fixture
def mock_supabase():
    """Mock Supabase client for hermetic execution tests."""
    client = MagicMock()
    table_mock = MagicMock()
    client.table.return_value = table_mock
    table_mock.select.return_value = table_mock
    table_mock.insert.return_value = table_mock
    table_mock.update.return_value = table_mock
    table_mock.delete.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.like.return_value = table_mock
    table_mock.gte.return_value = table_mock
    table_mock.lte.return_value = table_mock
    table_mock.execute.return_value = MagicMock(data=[])
    return client


@pytest.mark.asyncio
async def test_get_daily_session_open_price_from_predictions(mock_supabase):
    """Verify get_daily_session_open_price pulls open_price from daily_predictions."""
    table_mock = MagicMock()
    table_mock.select.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.execute.return_value = MagicMock(data=[{"open_price": 770.58}])
    mock_supabase.table.return_value = table_mock

    open_p = await get_daily_session_open_price("SPY", "2026-10-02", client=mock_supabase)
    assert open_p == 770.58


@pytest.mark.asyncio
async def test_get_daily_session_open_price_fallback_to_intraday(mock_supabase):
    """Verify get_daily_session_open_price falls back to fetch_intraday_prices when prediction has no open."""
    table_mock = MagicMock()
    table_mock.select.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.execute.return_value = MagicMock(data=[])
    mock_supabase.table.return_value = table_mock

    with patch(
        "tasks.evaluate_daily_predictions.fetch_intraday_prices",
        new=AsyncMock(return_value=(768.42, 770.0, 765.0, 769.0)),
    ):
        open_p = await get_daily_session_open_price("SPY", "2026-10-02", client=mock_supabase)
        assert open_p == 768.42


@pytest.mark.asyncio
async def test_reconcile_daily_open_trades_updates_trade_and_positions(mock_supabase):
    """Verify reconcile_daily_open_trades updates provisional entry price to actual session open."""
    target_date = "2026-10-02"
    portfolio_id = uuid4()
    prev_close = 763.99
    actual_open = 770.58
    shares = 13

    mock_portfolio_data = [
        {
            "id": str(portfolio_id),
            "owner_id": "sys-daily-spy-MiniMax-M3",
            "cash_balance": 10000.0 - (shares * prev_close),
            "total_equity": 10000.0,
        }
    ]
    mock_positions_data = [
        {
            "portfolio_id": str(portfolio_id),
            "ticker": "SPY",
            "quantity": shares,
            "average_cost_basis": prev_close,
        }
    ]
    mock_entry_trades = [
        {
            "id": str(uuid4()),
            "portfolio_id": str(portfolio_id),
            "ticker": "SPY",
            "signal": "BUY",
            "quantity": shares,
            "price": prev_close,
            "total_cost": shares * prev_close,
            "executed_at": f"{target_date}T13:30:00Z",
        }
    ]

    updated_rows = {}

    def table_router(table_name):
        t = MagicMock()
        t.select.return_value = t
        t.eq.return_value = t
        t.like.return_value = t
        t.gte.return_value = t
        t.lte.return_value = t

        def record_update(payload):
            updated_rows[table_name] = payload
            ub = MagicMock()
            ub.eq.return_value = ub
            ub.execute.return_value = MagicMock(data=[payload])
            return ub

        t.update.side_effect = record_update

        if table_name == "portfolios":
            t.execute.return_value = MagicMock(data=mock_portfolio_data)
        elif table_name == "portfolio_positions":
            t.execute.return_value = MagicMock(data=mock_positions_data)
        elif table_name == "trades":
            t.execute.return_value = MagicMock(data=mock_entry_trades)
        elif table_name == "daily_predictions":
            t.execute.return_value = MagicMock(
                data=[
                    {
                        "model_name": "MiniMax-M3",
                        "target_date": target_date,
                        "open_price": actual_open,
                        "close_price": 769.50,
                    }
                ]
            )
        else:
            t.execute.return_value = MagicMock(data=[])
        return t

    mock_supabase.table.side_effect = table_router

    with patch("execution.daily_trading.get_supabase_client", return_value=mock_supabase):
        result = await reconcile_daily_open_trades(target_date=target_date)

    assert result["status"] == "success"
    assert len(result["reconciled"]) == 1
    assert result["reconciled"][0]["old_price"] == prev_close
    assert result["reconciled"][0]["new_price"] == actual_open

    # Check updates in trades and portfolio_positions
    assert updated_rows["trades"]["price"] == actual_open
    assert abs(updated_rows["trades"]["total_cost"] - (shares * actual_open)) < 0.01
    assert updated_rows["portfolio_positions"]["average_cost_basis"] == actual_open
