"""Unit tests for intraday portfolio sizing, execution, and persistence."""

from unittest.mock import MagicMock

import pytest

from trading.intraday_portfolio import (
    LIVE_TRADER_OWNER_ID,
    compute_intraday_trade_sizing,
    execute_intraday_portfolio_turn,
)


def test_compute_trade_sizing_empty_portfolio_buy():
    """Empty portfolio with $10,000 cash buys up to 20% target equity ($2,000)."""
    # 20% of 10,000 is 2,000. Price is 500.0 -> 4 shares.
    result = compute_intraday_trade_sizing(
        cash_balance=10000.0,
        current_shares=0,
        current_price=500.0,
        action="BUY",
        target_pct=0.20,
    )
    assert result["signal"] == "BUY"
    assert result["shares"] == 4
    assert result["target_allocation_dollars"] == 2000.0


def test_compute_trade_sizing_already_at_target_buy():
    """Portfolio already holding 20% in SPY does not buy more."""
    # 4 shares @ 500 = $2,000. Cash = $8,000. Total equity = $10,000.
    result = compute_intraday_trade_sizing(
        cash_balance=8000.0,
        current_shares=4,
        current_price=500.0,
        action="BUY",
        target_pct=0.20,
    )
    assert result["signal"] == "HOLD"
    assert result["shares"] == 0
    assert "already at or above" in result["reason"]


def test_compute_trade_sizing_partial_fill_buy():
    """Portfolio holding 10% buys additional shares to reach 20%."""
    # 2 shares @ 500 = $1,000. Cash = $9,000. Total equity = $10,000.
    # Target = 20% ($2,000). Gap = $1,000 -> 2 shares.
    result = compute_intraday_trade_sizing(
        cash_balance=9000.0,
        current_shares=2,
        current_price=500.0,
        action="BUY",
        target_pct=0.20,
    )
    assert result["signal"] == "BUY"
    assert result["shares"] == 2


def test_compute_trade_sizing_sell_liquidates_all():
    """SELL signal liquidates 100% of current shares."""
    result = compute_intraday_trade_sizing(
        cash_balance=8000.0,
        current_shares=4,
        current_price=505.0,
        action="SELL",
        target_pct=0.20,
    )
    assert result["signal"] == "SELL"
    assert result["shares"] == 4


def test_compute_trade_sizing_sell_with_zero_shares():
    """SELL signal with 0 shares is a no-op HOLD."""
    result = compute_intraday_trade_sizing(
        cash_balance=10000.0,
        current_shares=0,
        current_price=505.0,
        action="SELL",
        target_pct=0.20,
    )
    assert result["signal"] == "HOLD"
    assert result["shares"] == 0


def test_compute_trade_sizing_hold_signal():
    """HOLD signal never buys or sells."""
    result = compute_intraday_trade_sizing(
        cash_balance=8000.0,
        current_shares=4,
        current_price=500.0,
        action="HOLD",
        target_pct=0.20,
    )
    assert result["signal"] == "HOLD"
    assert result["shares"] == 0


def test_compute_trade_sizing_invalid_price():
    """Price <= 0 produces a HOLD."""
    result = compute_intraday_trade_sizing(
        cash_balance=10000.0,
        current_shares=0,
        current_price=0.0,
        action="BUY",
        target_pct=0.20,
    )
    assert result["signal"] == "HOLD"
    assert result["shares"] == 0


@pytest.mark.asyncio
async def test_execute_intraday_portfolio_turn_market_closed():
    """Off-hours turn does not mutate positions or submit orders."""
    mock_sb = MagicMock()
    mock_alpaca = MagicMock()

    # Mock DB query for existing portfolio
    mock_port_table = MagicMock()
    mock_port_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": "port-123", "owner_id": LIVE_TRADER_OWNER_ID, "cash_balance": 10000.0, "total_equity": 10000.0}]
    )
    mock_pos_table = MagicMock()
    mock_pos_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

    def table_router(table_name):
        if table_name == "portfolios":
            return mock_port_table
        if table_name == "portfolio_positions":
            return mock_pos_table
        return MagicMock()

    mock_sb.table.side_effect = table_router

    summary = await execute_intraday_portfolio_turn(
        sb_client=mock_sb,
        action="BUY",
        current_price=500.0,
        is_market_open=False,
        alpaca_trading_client=mock_alpaca,
    )

    assert summary["status"] == "MARKET_CLOSED"
    assert summary["signal"] == "HOLD"
    assert not mock_alpaca.submit_order.called


@pytest.mark.asyncio
async def test_execute_intraday_portfolio_turn_buy_success():
    """Market open BUY executes trade in DB and mirrors to Alpaca."""
    mock_sb = MagicMock()
    mock_alpaca = MagicMock()
    mock_alpaca.submit_order.return_value = MagicMock(id="alpaca-buy-999")

    mock_port_table = MagicMock()
    mock_port_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": "port-123", "owner_id": LIVE_TRADER_OWNER_ID, "cash_balance": 10000.0, "total_equity": 10000.0}]
    )
    mock_pos_table = MagicMock()
    mock_pos_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

    mock_trades_table = MagicMock()
    mock_trades_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "trade-abc-1"}])

    def table_router(table_name):
        if table_name == "portfolios":
            return mock_port_table
        if table_name == "portfolio_positions":
            return mock_pos_table
        if table_name == "trades":
            return mock_trades_table
        return MagicMock()

    mock_sb.table.side_effect = table_router

    summary = await execute_intraday_portfolio_turn(
        sb_client=mock_sb,
        action="BUY",
        current_price=500.0,
        is_market_open=True,
        thought="RSI oversold rebound",
        alpaca_trading_client=mock_alpaca,
    )

    assert summary["status"] == "EXECUTED"
    assert summary["signal"] == "BUY"
    assert summary["shares"] == 4
    assert summary["cash_balance"] == 8000.0
    assert summary["total_equity"] == 10000.0
    assert summary["order_id"] == "alpaca-buy-999"
    assert mock_trades_table.insert.called
    assert mock_alpaca.submit_order.called
