"""TDD Tests for Systematic Daily Bond Trading (TLT Close-Exit)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from execution.daily_bond_trading import (
    DEFAULT_BOND_CLOSE_SLIPPAGE_BPS,
    SYS_DAILY_TLT_CLOSE_OWNER_PREFIX,
    execute_daily_bond_moo_entries,
    execute_system_daily_bond_close_trade,
)


def test_bond_trading_constants():
    """Verify owner prefix and slippage constants."""
    assert SYS_DAILY_TLT_CLOSE_OWNER_PREFIX == "sys-daily-tlt-close-"
    assert DEFAULT_BOND_CLOSE_SLIPPAGE_BPS == 2.0


@pytest.mark.asyncio
async def test_execute_daily_bond_moo_entries():
    """Verify MOO entries place BUY for UP and SHORT for DOWN in sys-daily-tlt-close-* portfolios."""
    mock_supabase = MagicMock()
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table

    mock_pred_data = [
        {"model_name": "gpt-5.6-luna", "predicted_direction": "UP", "ticker": "TLT"},
        {"model_name": "deepseek-v4-flash", "predicted_direction": "DOWN", "ticker": "TLT"},
    ]

    # Mock daily_predictions table
    mock_daily_pred_table = MagicMock()
    mock_daily_pred_select = MagicMock()
    mock_daily_pred_select.eq.return_value = mock_daily_pred_select
    mock_daily_pred_select.execute.return_value = MagicMock(data=mock_pred_data)
    mock_daily_pred_table.select.return_value = mock_daily_pred_select

    # Mock trades table
    mock_trades_table = MagicMock()
    mock_trades_select = MagicMock()
    mock_trades_select.eq.return_value = mock_trades_select
    mock_trades_select.gte.return_value = mock_trades_select
    mock_trades_select.lte.return_value = mock_trades_select
    mock_trades_select.execute.return_value = MagicMock(data=[])
    mock_trades_table.select.return_value = mock_trades_select
    mock_trades_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "trade-1"}])

    def table_router(table_name):
        if table_name == "daily_predictions":
            return mock_daily_pred_table
        return mock_trades_table

    mock_supabase.table.side_effect = table_router

    mock_portfolio = MagicMock()
    mock_portfolio.id = "port-uuid-1"
    mock_portfolio.cash_balance = 10000.0

    with (
        patch("execution.daily_bond_trading.get_supabase_client", return_value=mock_supabase),
        patch(
            "execution.daily_bond_trading.get_or_create_system_portfolio",
            new_callable=AsyncMock,
            return_value=mock_portfolio,
        ),
        patch("execution.daily_bond_trading.get_daily_session_open_price", new_callable=AsyncMock, return_value=92.50),
    ):
        result = await execute_daily_bond_moo_entries(target_date="2026-10-07")
        assert result["status"] == "success"
        assert len(result["entries"]) == 2
        # Check first entry: UP -> BUY
        assert result["entries"][0]["signal"] == "BUY"
        assert result["entries"][0]["owner_id"] == "sys-daily-tlt-close-gpt-5.6-luna"
        # Check second entry: DOWN -> SHORT
        assert result["entries"][1]["signal"] == "SHORT"
        assert result["entries"][1]["owner_id"] == "sys-daily-tlt-close-deepseek-v4-flash"


@pytest.mark.asyncio
async def test_execute_system_daily_bond_close_trade():
    """Verify close-exit trade computation and database recording for TLT."""
    mock_supabase = MagicMock()
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table

    mock_select = MagicMock()
    mock_select.eq.return_value = mock_select
    mock_select.gte.return_value = mock_select
    mock_select.lte.return_value = mock_select
    mock_select.execute.return_value = MagicMock(data=[])
    mock_table.select.return_value = mock_select

    mock_insert = MagicMock()
    mock_insert.execute.return_value = MagicMock(data=[{"id": "trade-2"}])
    mock_table.insert.return_value = mock_insert

    mock_update = MagicMock()
    mock_update.eq.return_value = mock_update
    mock_update.execute.return_value = MagicMock(data=[{}])
    mock_table.update.return_value = mock_update

    mock_upsert = MagicMock()
    mock_upsert.execute.return_value = MagicMock(data=[{}])
    mock_table.upsert.return_value = mock_upsert

    mock_portfolio = MagicMock()
    mock_portfolio.id = "port-uuid-1"
    mock_portfolio.cash_balance = 10000.0

    pred = {
        "model_name": "deepseek-v4-flash",
        "predicted_direction": "UP",
        "ticker": "TLT",
        "target_date": "2026-10-07",
    }
    intraday = {
        "open_price": 92.00,
        "high_price": 93.00,
        "low_price": 91.80,
        "close_price": 92.80,
    }

    with (
        patch("execution.daily_bond_trading.get_supabase_client", return_value=mock_supabase),
        patch(
            "execution.daily_bond_trading.get_or_create_system_portfolio",
            new_callable=AsyncMock,
            return_value=mock_portfolio,
        ),
    ):
        res = await execute_system_daily_bond_close_trade(prediction=pred, intraday_data=intraday)
        assert res["status"] == "success"
        assert res["owner_id"] == "sys-daily-tlt-close-deepseek-v4-flash"
        # 92.80 vs 92.00 open on 100 shares -> positive PnL
        assert res["execution"]["realized_pnl"] > 0
        assert res["new_equity"] > 10000.0
