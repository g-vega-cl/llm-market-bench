import os
import sys
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

# Ensure apps/engine is on path
sys.path.append(os.path.join(os.getcwd(), "apps", "engine"))

from execution.daily_trading import (
    DEFAULT_DAILY_CLOSE_SLIPPAGE_BPS,
    SYS_DAILY_SPY_CLOSE_OWNER_PREFIX,
    SYS_DAILY_SPY_OWNER_PREFIX,
    compute_daily_trade_execution,
    execute_system_daily_close_trade,
    execute_system_daily_trade,
)


def test_constants():
    assert SYS_DAILY_SPY_OWNER_PREFIX == "sys-daily-spy-"
    assert SYS_DAILY_SPY_CLOSE_OWNER_PREFIX == "sys-daily-spy-close-"
    assert DEFAULT_DAILY_CLOSE_SLIPPAGE_BPS == 2.0  # 0.02% slippage for highly liquid SPY


def test_compute_daily_trade_execution_close_exit_up_ignores_target():
    """UP prediction where intraday high hits target, but close price drops.

    With exit_on_target=False, the trade must NOT exit at target price.
    It must hold until close and exit at close_p * (1 - slippage).
    """
    pred = {
        "predicted_direction": "UP",
        "expected_return_pct": 0.50,
        "confidence": 70.0,
    }
    intraday = {
        "open_price": 500.0,
        "high_price": 505.0,  # Max +1.0%, hits +0.50% target
        "low_price": 495.0,
        "close_price": 496.0,  # Dropped -0.80% at close
        "intraday_hit": True,
    }
    capital = 10000.0
    slippage_bps = 2.0  # 0.02% = 0.0002

    res = compute_daily_trade_execution(
        pred, intraday, capital=capital, slippage_bps=slippage_bps, exit_on_target=False
    )

    assert res["direction"] == "UP"
    # Entry: 500 * (1 + 0.0002) = 500.10
    assert res["entry_price"] == pytest.approx(500.10)
    # Target price: 500 * (1 + 0.005) = 502.50
    assert res["target_price"] == pytest.approx(502.50)
    # Exit price MUST be close price with exit slippage: 496.0 * (1 - 0.0002) = 495.9008
    assert res["exit_price"] == pytest.approx(496.0 * (1.0 - 0.0002))
    # Shares: int(10000 / 500.10) = 19
    assert res["shares"] == 19
    # Realized PnL is negative because position was held until close
    expected_pnl = (res["exit_price"] - res["entry_price"]) * 19
    assert res["realized_pnl"] == pytest.approx(expected_pnl)
    assert res["realized_pnl"] < 0


def test_compute_daily_trade_execution_close_exit_down_ignores_target():
    """DOWN prediction where intraday low hits target, but close price rallies.

    With exit_on_target=False, the trade must NOT exit at target price.
    It must hold until close and exit at close_p * (1 + slippage).
    """
    pred = {
        "predicted_direction": "DOWN",
        "expected_return_pct": -0.60,
        "confidence": 75.0,
    }
    intraday = {
        "open_price": 500.0,
        "high_price": 505.0,
        "low_price": 495.0,  # Low -1.0%, hits -0.60% target
        "close_price": 504.0,  # Rallied to +0.80% at close
        "intraday_hit": True,
    }
    capital = 10000.0
    slippage_bps = 2.0  # 0.02% = 0.0002

    res = compute_daily_trade_execution(
        pred, intraday, capital=capital, slippage_bps=slippage_bps, exit_on_target=False
    )

    assert res["direction"] == "DOWN"
    # Entry: 500 * (1 - 0.0002) = 499.90
    assert res["entry_price"] == pytest.approx(499.90)
    # Target price: 500 * (1 - 0.006) = 497.00
    assert res["target_price"] == pytest.approx(497.00)
    # Exit price MUST be close price with cover slippage: 504.0 * (1 + 0.0002) = 504.1008
    assert res["exit_price"] == pytest.approx(504.0 * (1.0 + 0.0002))
    # Shares: int(10000 / 499.90) = 20
    assert res["shares"] == 20
    # Realized PnL is negative (short loss)
    expected_pnl = (res["entry_price"] - res["exit_price"]) * 20
    assert res["realized_pnl"] == pytest.approx(expected_pnl)
    assert res["realized_pnl"] < 0


def test_compute_daily_trade_execution_default_backward_compatible():
    """Verify that omitting exit_on_target defaults to True (original behavior)."""
    pred = {
        "predicted_direction": "UP",
        "expected_return_pct": 0.50,
    }
    intraday = {
        "open_price": 500.0,
        "high_price": 505.0,
        "low_price": 498.0,
        "close_price": 496.0,
        "intraday_hit": True,
    }
    res = compute_daily_trade_execution(pred, intraday, capital=10000.0, slippage_bps=5.0)
    assert res["target_hit"] is True
    assert res["exit_price"] == pytest.approx(502.50)  # Exited at target price
    assert res["realized_pnl"] > 0


@pytest.mark.asyncio
async def test_execute_system_daily_close_trade_flow():
    """Verify execute_system_daily_close_trade creates sys-daily-spy-close-* portfolio."""
    pred = {
        "id": str(uuid4()),
        "model_name": "deepseek-v4-flash",
        "target_date": "2026-09-18",
        "ticker": "SPY",
        "predicted_direction": "DOWN",
        "expected_return_pct": -0.40,
    }
    intraday = {
        "open_price": 761.31,
        "high_price": 763.50,
        "low_price": 759.00,  # Touched -0.40% target
        "close_price": 761.62,
        "intraday_hit": True,
    }

    inserted_trades = []
    portfolio_updates = []
    performance_upserts = []
    test_pid = str(uuid4())

    mock_supabase = MagicMock()

    def mock_table(name: str):
        table_mock = MagicMock()
        if name == "portfolios":
            table_mock.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[
                    {
                        "id": test_pid,
                        "owner_id": "sys-daily-spy-close-deepseek-v4-flash",
                        "cash_balance": 10000.0,
                        "total_equity": 10000.0,
                    }
                ]
            )
            table_mock.update.side_effect = lambda data: MagicMock(
                eq=lambda col, val: MagicMock(execute=lambda: portfolio_updates.append(data) or MagicMock(data=[data]))
            )
        elif name == "portfolio_positions":
            table_mock.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        elif name == "trades":
            table_mock.select.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value = (
                MagicMock(data=[])
            )
            table_mock.insert.side_effect = lambda data: MagicMock(
                execute=lambda: inserted_trades.append(data) or MagicMock(data=[data])
            )
        elif name == "portfolio_performance":
            table_mock.upsert.side_effect = lambda data, on_conflict: MagicMock(
                execute=lambda: performance_upserts.append(data) or MagicMock(data=[data])
            )
        return table_mock

    mock_supabase.table.side_effect = mock_table

    with (
        patch("execution.daily_trading.get_supabase_client", return_value=mock_supabase),
        patch("execution.portfolio.get_supabase_client", return_value=mock_supabase),
    ):
        res = await execute_system_daily_close_trade(
            prediction=pred,
            intraday_data=intraday,
            slippage_bps=2.0,
        )

    assert res["status"] == "success"
    assert res["owner_id"] == "sys-daily-spy-close-deepseek-v4-flash"
    assert len(inserted_trades) == 2
    entry_trade, exit_trade = inserted_trades[0], inserted_trades[1]

    assert entry_trade["signal"] == "SHORT"
    assert entry_trade["executed_at"] == "2026-09-18T13:30:00Z"
    # Entry price with 2 bps slippage: 761.31 * (1 - 0.0002) = 761.157738
    assert entry_trade["price"] == pytest.approx(761.31 * 0.9998)

    assert exit_trade["signal"] == "COVER"
    assert exit_trade["executed_at"] == "2026-09-18T20:00:00Z"
    # Exit price with 2 bps slippage: 761.62 * (1 + 0.0002) = 761.772324
    assert exit_trade["price"] == pytest.approx(761.62 * 1.0002)

    # In DOWN, close 761.62 > open 761.31 -> loss
    assert exit_trade["realized_pnl"] < 0


@pytest.mark.asyncio
async def test_execute_system_daily_close_trade_idempotency():
    """Verify that re-running execute_system_daily_close_trade cleans up existing trades and reverts PnL."""
    pred = {
        "id": str(uuid4()),
        "model_name": "MiniMax-M3",
        "target_date": "2026-09-18",
        "ticker": "SPY",
        "predicted_direction": "UP",
        "expected_return_pct": 0.50,
    }
    intraday = {
        "open_price": 760.00,
        "high_price": 765.00,
        "low_price": 758.00,
        "close_price": 762.00,
        "intraday_hit": True,
    }

    deleted_trade_ids = []
    mock_port = MagicMock()
    mock_port.id = uuid4()
    mock_port.cash_balance = 10050.0  # Had previous +$50 trade

    mock_client = MagicMock()
    chain = MagicMock()

    def mock_table(table_name):
        if table_name == "trades":
            chain.select.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value = (
                MagicMock(data=[{"id": "prev-trade-1", "realized_pnl": 50.0}])
            )
            mock_delete = MagicMock()
            mock_delete.return_value.eq.return_value.execute.side_effect = lambda: deleted_trade_ids.append(
                "prev-trade-1"
            )
            chain.delete = mock_delete
        elif table_name in ("portfolios", "portfolio_performance"):
            chain.execute.return_value = MagicMock(data=[])
        return chain

    mock_client.table.side_effect = mock_table

    with (
        patch("execution.daily_trading.get_supabase_client", return_value=mock_client),
        patch("execution.daily_trading.get_or_create_system_portfolio", return_value=mock_port),
    ):
        res = await execute_system_daily_close_trade(pred, intraday, slippage_bps=2.0)

    assert res["status"] == "success"
    assert "prev-trade-1" in deleted_trade_ids
    # Cash was 10050.0 - 50.0 reverted = 10000.0 before new trade
    # New trade: UP 760.0 -> 762.0, shares = int(10000 / 760.152) = 13
    assert res["new_equity"] > 10000.0


@pytest.mark.asyncio
async def test_execute_system_daily_trade_target_flow():
    """Verify execute_system_daily_trade routes to sys-daily-spy-* and exits on target."""
    pred = {
        "id": str(uuid4()),
        "model_name": "MiniMax-M3",
        "target_date": "2026-09-18",
        "ticker": "SPY",
        "predicted_direction": "UP",
        "expected_return_pct": 0.40,
    }
    intraday = {
        "open_price": 760.00,
        "high_price": 765.00,  # Touched target
        "low_price": 758.00,
        "close_price": 759.00,  # Dropped below open
        "intraday_hit": True,
    }

    mock_port = MagicMock()
    mock_port.id = uuid4()
    mock_port.cash_balance = 10000.0

    mock_client = MagicMock()
    chain = MagicMock()
    inserted_trades = []

    def mock_table(table_name):
        if table_name == "trades":
            chain.select.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value = (
                MagicMock(data=[])
            )
            chain.insert.side_effect = lambda data: MagicMock(
                execute=lambda: inserted_trades.append(data) or MagicMock(data=[data])
            )
        elif table_name in ("portfolios", "portfolio_performance"):
            chain.execute.return_value = MagicMock(data=[])
        return chain

    mock_client.table.side_effect = mock_table

    with (
        patch("execution.daily_trading.get_supabase_client", return_value=mock_client),
        patch("execution.daily_trading.get_or_create_system_portfolio", return_value=mock_port),
    ):
        res = await execute_system_daily_trade(pred, intraday)

    assert res["status"] == "success"
    assert res["owner_id"] == "sys-daily-spy-MiniMax-M3"
    assert res["execution"]["target_hit"] is True
    # Profit target exit: exit price = 760 * (1 + 0.004) = 763.04
    assert res["execution"]["exit_price"] == pytest.approx(763.04)
    assert res["execution"]["realized_pnl"] > 0
