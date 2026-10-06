"""Tests for live daily SPY systematic trading lifecycle.

Hermetic tests verifying:
1. execute_daily_moo_entries: Market-On-Open (OPG) submission before 9:28 AM,
   DB trades & portfolio_positions creation for UP, and virtual SHORT for DOWN.
2. place_daily_target_limit_orders: Limit sell order submission at target price for target-exit portfolios.
3. execute_daily_close_exits: Afternoon 3:30 PM liquidation, Alpaca sell order,
   position cleanup, and realized PnL accounting.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from alpaca.trading.enums import TimeInForce


@pytest.fixture
def mock_supabase():
    """Mock Supabase client with chainable query builder methods."""
    client = MagicMock()
    table_mock = MagicMock()
    client.table.return_value = table_mock

    # Support common chain patterns
    table_mock.select.return_value = table_mock
    table_mock.insert.return_value = table_mock
    table_mock.upsert.return_value = table_mock
    table_mock.update.return_value = table_mock
    table_mock.delete.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.gte.return_value = table_mock
    table_mock.lte.return_value = table_mock
    table_mock.order.return_value = table_mock
    table_mock.limit.return_value = table_mock
    table_mock.execute.return_value = MagicMock(data=[])

    return client


@pytest.mark.asyncio
async def test_execute_daily_moo_entries_up_and_down(mock_supabase):
    """Verify pre-market entry executes OPG for UP signals and virtual short for DOWN signals."""
    from execution.daily_trading import execute_daily_moo_entries

    target_date = "2026-09-29"
    pred_up = {
        "id": "pred-1",
        "model_name": "deepseek-v4-flash",
        "predicted_direction": "UP",
        "expected_return_pct": 0.85,
        "target_date": target_date,
        "ticker": "SPY",
    }
    pred_down = {
        "id": "pred-2",
        "model_name": "minimax-m3",
        "predicted_direction": "DOWN",
        "expected_return_pct": -0.60,
        "target_date": target_date,
        "ticker": "SPY",
    }

    # Predictions returned from daily_predictions
    pred_query = MagicMock(data=[pred_up, pred_down])

    def table_router(table_name):
        t = MagicMock()
        t.select.return_value = t
        t.insert.return_value = t
        t.upsert.return_value = t
        t.update.return_value = t
        t.delete.return_value = t
        t.eq.return_value = t
        t.gte.return_value = t
        t.lte.return_value = t
        if table_name == "daily_predictions":
            t.execute.return_value = pred_query
        elif table_name == "trades":
            t.execute.return_value = MagicMock(data=[])
            insert_builder = MagicMock()
            insert_builder.execute.return_value = MagicMock(data=[{"id": str(uuid4())}])
            t.insert.return_value = insert_builder
        else:
            t.execute.return_value = MagicMock(data=[])
        return t

    mock_supabase.table.side_effect = table_router

    mock_portfolio = MagicMock()
    mock_portfolio.id = uuid4()
    mock_portfolio.cash_balance = 10000.0

    mock_market_order = AsyncMock()

    with (
        patch("execution.daily_trading.get_supabase_client", return_value=mock_supabase),
        patch("execution.daily_trading.get_or_create_system_portfolio", new=AsyncMock(return_value=mock_portfolio)),
        patch("execution.market_data.MarketDataManager.get_quote", new=AsyncMock(return_value=MagicMock(price=500.0))),
        patch("execution.alpaca_broker.AlpacaBroker.submit_market_order", new=mock_market_order),
    ):
        result = await execute_daily_moo_entries(target_date=target_date)

    assert result["status"] == "success"
    assert len(result["entries"]) >= 2

    # Verify Alpaca market order was submitted ONLY for the UP prediction (both target and close portfolios)
    # pred_up has sys-daily-spy-deepseek-v4-flash and sys-daily-spy-close-deepseek-v4-flash
    assert mock_market_order.call_count >= 1
    for call in mock_market_order.call_args_list:
        assert call.kwargs["ticker"] == "SPY"
        assert call.kwargs["signal"] == "BUY"
        assert call.kwargs["time_in_force"] == TimeInForce.OPG


@pytest.mark.asyncio
async def test_place_daily_target_limit_orders(mock_supabase):
    """Verify limit sell order is submitted at 9:35 AM for target-exit portfolios."""
    from execution.daily_trading import place_daily_target_limit_orders

    target_date = "2026-09-29"
    portfolio_id = uuid4()

    mock_portfolio_data = [{"id": str(portfolio_id), "owner_id": "sys-daily-spy-deepseek-v4-flash"}]
    mock_positions_data = [
        {"portfolio_id": str(portfolio_id), "ticker": "SPY", "quantity": 20, "average_cost_basis": 500.0}
    ]
    mock_prediction_data = [
        {
            "model_name": "deepseek-v4-flash",
            "predicted_direction": "UP",
            "expected_return_pct": 1.0,
            "target_date": target_date,
        }
    ]

    def table_router(table_name):
        t = MagicMock()
        t.select.return_value = t
        t.eq.return_value = t
        t.like.return_value = t
        if table_name == "portfolios":
            t.execute.return_value = MagicMock(data=mock_portfolio_data)
        elif table_name == "portfolio_positions":
            t.execute.return_value = MagicMock(data=mock_positions_data)
        elif table_name == "daily_predictions":
            t.execute.return_value = MagicMock(data=mock_prediction_data)
        else:
            t.execute.return_value = MagicMock(data=[])
        return t

    mock_supabase.table.side_effect = table_router
    mock_limit_order = AsyncMock()

    with (
        patch("execution.daily_trading.get_supabase_client", return_value=mock_supabase),
        patch("execution.alpaca_broker.AlpacaBroker.submit_limit_order", new=mock_limit_order),
    ):
        result = await place_daily_target_limit_orders(target_date=target_date)

    assert result["status"] == "success"
    assert mock_limit_order.call_count == 1
    call_kwargs = mock_limit_order.call_args.kwargs
    assert call_kwargs["ticker"] == "SPY"
    assert call_kwargs["signal"] == "SELL"
    # Target price = 500 * (1 + 0.01) = 505.0
    assert abs(call_kwargs["limit_price"] - 505.0) < 0.01
    assert call_kwargs["quantity"] == 20


@pytest.mark.asyncio
async def test_execute_daily_close_exits(mock_supabase):
    """Verify afternoon 3:30 PM liquidation cancels limit orders, sells held shares, and records realized PnL."""
    from execution.daily_trading import execute_daily_close_exits

    target_date = "2026-09-29"
    portfolio_id = uuid4()

    mock_portfolio_data = [
        {"id": str(portfolio_id), "owner_id": "sys-daily-spy-close-deepseek-v4-flash", "cash_balance": 0.0}
    ]
    mock_positions_data = [
        {"portfolio_id": str(portfolio_id), "ticker": "SPY", "quantity": 20, "average_cost_basis": 500.0}
    ]
    mock_entry_trades = [
        {
            "id": str(uuid4()),
            "portfolio_id": str(portfolio_id),
            "ticker": "SPY",
            "signal": "BUY",
            "quantity": 20,
            "price": 500.0,
            "executed_at": f"{target_date}T13:30:00Z",
        }
    ]

    def table_router(table_name):
        t = MagicMock()
        t.select.return_value = t
        t.eq.return_value = t
        t.like.return_value = t
        t.gte.return_value = t
        t.lte.return_value = t
        t.insert.return_value = t
        t.update.return_value = t
        t.delete.return_value = t
        t.upsert.return_value = t
        if table_name == "portfolios":
            t.execute.return_value = MagicMock(data=mock_portfolio_data)
        elif table_name == "portfolio_positions":
            t.execute.return_value = MagicMock(data=mock_positions_data)
        elif table_name == "trades":
            t.execute.return_value = MagicMock(data=mock_entry_trades)
        else:
            t.execute.return_value = MagicMock(data=[])
        return t

    mock_supabase.table.side_effect = table_router
    mock_cancel_orders = AsyncMock()
    mock_market_order = AsyncMock()

    with (
        patch("execution.daily_trading.get_supabase_client", return_value=mock_supabase),
        patch("execution.market_data.MarketDataManager.get_quote", new=AsyncMock(return_value=MagicMock(price=505.0))),
        patch("execution.alpaca_broker.AlpacaBroker.cancel_open_orders_for_agent", new=mock_cancel_orders),
        patch("execution.alpaca_broker.AlpacaBroker.submit_market_order", new=mock_market_order),
    ):
        result = await execute_daily_close_exits(target_date=target_date)

    assert result["status"] == "success"
    assert mock_cancel_orders.call_count >= 1
    assert mock_market_order.call_count == 1
    assert mock_market_order.call_args.kwargs["signal"] == "SELL"
    assert mock_market_order.call_args.kwargs["quantity"] == 20


@pytest.mark.asyncio
async def test_daily_close_exit_reconciles_open_price_from_beginning_of_day(mock_supabase):
    """Reproduction test: Close exit must use beginning-of-day session open (770.58), not premarket prev close (763.99)."""
    from execution.daily_trading import execute_daily_close_exits

    target_date = "2026-10-02"
    portfolio_id = uuid4()

    # Pre-market entry was logged with previous day's close ($763.99)
    prev_close = 763.99
    actual_open = 770.58
    actual_close = 769.50
    shares = 13

    mock_portfolio_data = [
        {
            "id": str(portfolio_id),
            "owner_id": "sys-daily-spy-close-MiniMax-M3",
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

    inserted_trades = []
    updated_trades = []

    def table_router(table_name):
        t = MagicMock()
        t.select.return_value = t
        t.eq.return_value = t
        t.like.return_value = t
        t.gte.return_value = t
        t.lte.return_value = t
        t.delete.return_value = t
        t.upsert.return_value = t

        def record_insert(payload):
            inserted_trades.append(payload)
            ib = MagicMock()
            ib.execute.return_value = MagicMock(data=[payload])
            return ib

        def record_update(payload):
            updated_trades.append(payload)
            ub = MagicMock()
            ub.eq.return_value = ub
            ub.execute.return_value = MagicMock(data=[payload])
            return ub

        t.insert.side_effect = record_insert
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
                        "close_price": actual_close,
                        "predicted_direction": "UP",
                    }
                ]
            )
        else:
            t.execute.return_value = MagicMock(data=[])
        return t

    mock_supabase.table.side_effect = table_router

    with (
        patch("execution.daily_trading.get_supabase_client", return_value=mock_supabase),
        patch(
            "execution.daily_trading.fetch_intraday_prices",
            new=AsyncMock(return_value=(actual_open, 772.65, 767.15, actual_close)),
            create=True,
        ),
        patch(
            "execution.market_data.MarketDataManager.get_quote",
            new=AsyncMock(return_value=MagicMock(price=actual_close)),
        ),
        patch("execution.alpaca_broker.AlpacaBroker.cancel_open_orders_for_agent", new=AsyncMock()),
        patch("execution.alpaca_broker.AlpacaBroker.submit_market_order", new=AsyncMock()),
    ):
        result = await execute_daily_close_exits(target_date=target_date)

    assert result["status"] == "success"
    # Exit trade must have PnL calculated from beginning of day open (770.58), which is negative:
    # (769.50 - 770.58) * 13 = -14.04 (or with slippage).
    # It must NOT be (769.50 - 763.99) * 13 = +71.63!
    assert len(result["exits"]) == 1
    exit_pnl = result["exits"][0]["pnl"]
    assert exit_pnl < 0, f"Expected loss from open {actual_open} to close {actual_close}, but got {exit_pnl}"
    expected_pnl = (actual_close - actual_open) * shares
    assert abs(exit_pnl - expected_pnl) < 1.0, f"Expected PnL near {expected_pnl}, got {exit_pnl}"


@pytest.mark.asyncio
async def test_execute_daily_close_exits_for_short_trade_updates_entry_pnl(mock_supabase):
    """Verify afternoon close exit for SHORT trades inserts COVER trade and updates entry SHORT trade realized_pnl."""
    from execution.daily_trading import execute_daily_close_exits

    target_date = "2026-09-25"
    portfolio_id = uuid4()
    entry_trade_id = str(uuid4())

    mock_portfolio_data = [
        {"id": str(portfolio_id), "owner_id": "sys-daily-spy-close-~typesafe/jev-latest", "cash_balance": 10000.0}
    ]
    # No long position in portfolio_positions
    mock_positions_data = []
    mock_day_trades = [
        {
            "id": entry_trade_id,
            "portfolio_id": str(portfolio_id),
            "ticker": "SPY",
            "signal": "SHORT",
            "quantity": 13,
            "price": 768.63,
            "realized_pnl": None,
            "executed_at": f"{target_date}T13:30:00Z",
        }
    ]

    inserted_trades = []
    updated_trades = []

    def table_router(table_name):
        t = MagicMock()
        t.select.return_value = t
        t.eq.return_value = t
        t.like.return_value = t
        t.gte.return_value = t
        t.lte.return_value = t
        t.delete.return_value = t
        t.upsert.return_value = t

        def record_insert(payload):
            inserted_trades.append(payload)
            ib = MagicMock()
            ib.execute.return_value = MagicMock(data=[payload])
            return ib

        def record_update(payload):
            updated_trades.append(payload)
            ub = MagicMock()
            ub.eq.return_value = ub
            ub.execute.return_value = MagicMock(data=[payload])
            return ub

        t.insert.side_effect = record_insert
        t.update.side_effect = record_update

        if table_name == "portfolios":
            t.execute.return_value = MagicMock(data=mock_portfolio_data)
        elif table_name == "portfolio_positions":
            t.execute.return_value = MagicMock(data=mock_positions_data)
        elif table_name == "trades":
            t.execute.return_value = MagicMock(data=mock_day_trades)
        elif table_name == "daily_predictions":
            t.execute.return_value = MagicMock(
                data=[
                    {
                        "model_name": "~typesafe/jev-latest",
                        "target_date": target_date,
                        "open_price": 768.63,
                        "close_price": 771.40,
                        "predicted_direction": "DOWN",
                    }
                ]
            )
        else:
            t.execute.return_value = MagicMock(data=[])
        return t

    mock_supabase.table.side_effect = table_router

    with (
        patch("execution.daily_live_trading.dt.get_supabase_client", return_value=mock_supabase),
        patch("execution.market_data.MarketDataManager.get_quote", new=AsyncMock(return_value=MagicMock(price=771.40))),
        patch("execution.alpaca_broker.AlpacaBroker.cancel_open_orders_for_agent", new=AsyncMock()),
    ):
        result = await execute_daily_close_exits(target_date=target_date)

    assert result["status"] == "success"
    assert len(result["exits"]) == 1
    assert result["exits"][0]["signal"] == "COVER"

    # Assert COVER trade was inserted
    cover_trade = next((t for t in inserted_trades if t.get("signal") == "COVER"), None)
    assert cover_trade is not None
    assert cover_trade["realized_pnl"] is not None

    # Assert entry SHORT trade was updated with realized_pnl
    entry_update = next((u for u in updated_trades if "realized_pnl" in u), None)
    assert entry_update is not None, "Expected entry SHORT trade to be updated with realized_pnl"
    assert entry_update["realized_pnl"] == cover_trade["realized_pnl"]

