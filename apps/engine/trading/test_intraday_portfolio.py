"""Unit tests for intraday portfolio sizing, execution, and persistence."""

from unittest.mock import AsyncMock, MagicMock

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


# ---------------------------------------------------------------------------
# Execution turn — ledger first, Alpaca mirror reported honestly
# ---------------------------------------------------------------------------


def _build_sb_client(cash: float = 10000.0, shares: int | None = None):
    """Mocked Supabase client with table routing for a single portfolio turn."""
    mock_port_table = MagicMock()
    mock_port_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": "port-123", "owner_id": LIVE_TRADER_OWNER_ID, "cash_balance": cash, "total_equity": cash}]
    )

    mock_pos_table = MagicMock()
    position_rows = [{"quantity": shares, "average_cost_basis": 500.0}] if shares else []
    mock_pos_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=position_rows
    )

    mock_trades_table = MagicMock()
    mock_trades_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "trade-abc-1"}])

    mock_sb = MagicMock()
    mock_sb.table.side_effect = lambda name: {
        "portfolios": mock_port_table,
        "portfolio_positions": mock_pos_table,
        "trades": mock_trades_table,
    }.get(name, MagicMock())

    return mock_sb, {"trades": mock_trades_table, "positions": mock_pos_table}


def _broker(result: dict | None = None):
    broker = MagicMock()
    broker.submit_market_order = AsyncMock(return_value=result or {"status": "SUBMITTED", "order_id": "alpaca-1"})
    return broker


@pytest.mark.asyncio
async def test_execute_intraday_portfolio_turn_market_closed():
    """Off-hours turn does not mutate positions or submit orders."""
    mock_sb, _ = _build_sb_client()
    broker = _broker()

    summary = await execute_intraday_portfolio_turn(
        sb_client=mock_sb,
        action="BUY",
        current_price=500.0,
        is_market_open=False,
        alpaca_broker=broker,
    )

    assert summary["status"] == "MARKET_CLOSED"
    assert summary["signal"] == "HOLD"
    assert summary["alpaca_status"] is None
    broker.submit_market_order.assert_not_awaited()


@pytest.mark.asyncio
async def test_execute_intraday_portfolio_turn_buy_success():
    """Market open BUY executes in the DB and mirrors to Alpaca."""
    mock_sb, mocks = _build_sb_client()
    broker = _broker({"status": "SUBMITTED", "order_id": "alpaca-buy-999"})

    summary = await execute_intraday_portfolio_turn(
        sb_client=mock_sb,
        action="BUY",
        current_price=500.0,
        is_market_open=True,
        thought="RSI oversold rebound",
        alpaca_broker=broker,
    )

    assert summary["status"] == "EXECUTED"
    assert summary["signal"] == "BUY"
    assert summary["shares"] == 4
    assert summary["cash_balance"] == 8000.0
    assert summary["total_equity"] == 10000.0
    assert summary["order_id"] == "alpaca-buy-999"
    assert summary["alpaca_status"] == "SUBMITTED"
    assert mocks["trades"].insert.called

    kwargs = broker.submit_market_order.await_args.kwargs
    assert kwargs["signal"] == "BUY"
    assert kwargs["quantity"] == 4
    assert kwargs["ticker"] == "SPY"
    assert kwargs["agent_id"] == LIVE_TRADER_OWNER_ID
    assert kwargs["guard_sells"] is False


@pytest.mark.asyncio
async def test_buy_mirror_error_keeps_ledger_trade():
    """A rejected Alpaca order leaves the ledger intact but is recorded as ERROR."""
    mock_sb, _ = _build_sb_client()
    broker = _broker({"status": "ERROR", "order_id": None})

    summary = await execute_intraday_portfolio_turn(
        sb_client=mock_sb,
        action="BUY",
        current_price=500.0,
        is_market_open=True,
        alpaca_broker=broker,
    )

    assert summary["status"] == "EXECUTED"
    assert summary["cash_balance"] == 8000.0
    assert summary["order_id"] is None
    assert summary["alpaca_status"] == "ERROR"


@pytest.mark.asyncio
async def test_sell_is_attempted_without_broker_position_guard():
    """SELL mirrors the full ledger quantity even when the broker holds nothing."""
    mock_sb, _ = _build_sb_client(cash=8000.0, shares=2)
    broker = _broker({"status": "SUBMITTED", "order_id": "alpaca-sell-1"})

    summary = await execute_intraday_portfolio_turn(
        sb_client=mock_sb,
        action="SELL",
        current_price=500.0,
        is_market_open=True,
        alpaca_broker=broker,
    )

    assert summary["status"] == "EXECUTED"
    assert summary["signal"] == "SELL"
    assert summary["shares"] == 2
    assert summary["alpaca_status"] == "SUBMITTED"

    kwargs = broker.submit_market_order.await_args.kwargs
    assert kwargs["signal"] == "SELL"
    assert kwargs["quantity"] == 2
    assert kwargs["guard_sells"] is False


@pytest.mark.asyncio
async def test_sell_records_broker_position_mismatch():
    """A SELL larger than the broker holding is mirrored, but the divergence is stamped."""
    mock_sb, mocks = _build_sb_client(cash=8000.0, shares=2)
    broker = _broker({"status": "SUBMITTED", "order_id": "alpaca-sell-2"})
    broker.try_get_alpaca_position.return_value = 1.0

    summary = await execute_intraday_portfolio_turn(
        sb_client=mock_sb,
        action="SELL",
        current_price=500.0,
        is_market_open=True,
        alpaca_broker=broker,
    )

    assert summary["status"] == "EXECUTED"
    notes = [call.args[0].get("alpaca_note") for call in mocks["trades"].update.call_args_list if call.args]
    assert any(note and "BROKER_POSITION_MISMATCH" in note for note in notes)


@pytest.mark.asyncio
async def test_missing_broker_records_disabled_mirror():
    """With no broker wired, the trade row records that mirroring was disabled."""
    mock_sb, mocks = _build_sb_client()

    summary = await execute_intraday_portfolio_turn(
        sb_client=mock_sb,
        action="BUY",
        current_price=500.0,
        is_market_open=True,
        alpaca_broker=None,
    )

    assert summary["status"] == "EXECUTED"
    assert summary["alpaca_status"] == "DISABLED"
    update_payload = mocks["trades"].update.call_args[0][0]
    assert update_payload["alpaca_status"] == "DISABLED"
    mocks["trades"].update.return_value.eq.assert_called_once_with("id", "trade-abc-1")


@pytest.mark.asyncio
async def test_broker_without_client_records_disabled_mirror():
    """A broker whose Alpaca client is absent (missing keys) still stamps DISABLED."""
    mock_sb, mocks = _build_sb_client()
    broker = _broker({"status": "DISABLED", "order_id": None})

    summary = await execute_intraday_portfolio_turn(
        sb_client=mock_sb,
        action="BUY",
        current_price=500.0,
        is_market_open=True,
        alpaca_broker=broker,
    )

    assert summary["status"] == "EXECUTED"
    assert summary["alpaca_status"] == "DISABLED"
    update_payload = mocks["trades"].update.call_args[0][0]
    assert update_payload["alpaca_status"] == "DISABLED"


@pytest.mark.asyncio
async def test_retry_after_failed_row_write_records_submitted_at():
    """A retried mirror write must carry alpaca_submitted_at, or the row can never reconcile."""
    mock_sb, mocks = _build_sb_client()
    broker = _broker({"status": "SUBMITTED", "order_id": "alpaca-9", "persisted": False})

    summary = await execute_intraday_portfolio_turn(
        sb_client=mock_sb,
        action="BUY",
        current_price=500.0,
        is_market_open=True,
        alpaca_broker=broker,
    )

    assert summary["status"] == "EXECUTED"
    assert summary["alpaca_status"] == "SUBMITTED"

    retries = [
        call.args[0]
        for call in mocks["trades"].update.call_args_list
        if call.args and call.args[0].get("alpaca_status") == "SUBMITTED" and "alpaca_order_id" in call.args[0]
    ]
    assert retries, "the failed write was never retried"
    assert retries[0]["alpaca_order_id"] == "alpaca-9"
    assert retries[0]["alpaca_submitted_at"], "retried SUBMITTED row has no submission timestamp"


@pytest.mark.asyncio
async def test_unknown_broker_position_is_not_recorded_as_mismatch():
    """A failed position read must leave the row unflagged instead of claiming a 0-share book."""
    mock_sb, mocks = _build_sb_client(cash=8000.0, shares=2)
    broker = _broker({"status": "SUBMITTED", "order_id": "alpaca-sell-3"})
    broker.try_get_alpaca_position.return_value = None

    await execute_intraday_portfolio_turn(
        sb_client=mock_sb,
        action="SELL",
        current_price=500.0,
        is_market_open=True,
        alpaca_broker=broker,
    )

    notes = [call.args[0].get("alpaca_note") for call in mocks["trades"].update.call_args_list if call.args]
    assert not any(notes), f"unexpected mismatch note from an unreadable position: {notes}"
