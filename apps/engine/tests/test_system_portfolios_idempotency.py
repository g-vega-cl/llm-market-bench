from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from execution.system_portfolios import (
    SYS_SECTOR_UNCORR_20D_OWNER_ID,
    execute_mechanical_sector_rebalance,
    execute_system_daily_trade,
    execute_system_sector_rebalance,
)


@pytest.mark.asyncio
async def test_execute_system_daily_trade_idempotent_replacement():
    """Verify that calling execute_system_daily_trade twice removes existing trades and avoids double-crediting PnL."""
    mock_client = MagicMock()
    mock_portfolio_id = uuid4()
    mock_port = MagicMock()
    mock_port.id = mock_portfolio_id
    mock_port.cash_balance = 10024.77  # Already credited with +$24.77 from first run

    prediction = {
        "model_name": "deepseek-v4-flash",
        "target_date": "2026-09-01",
        "ticker": "SPY",
        "predicted_direction": "DOWN",
        "expected_return_pct": -0.3,
    }
    intraday_data = {
        "open_price": 762.04,
        "high_price": 764.67,
        "low_price": 759.5,
        "close_price": 761.48,
        "intraday_hit": True,
    }

    # Simulate existing trades for 2026-09-01 already in DB
    existing_trades = [
        {
            "id": "old-trade-1",
            "executed_at": "2026-09-01T13:30:00Z",
            "signal": "SHORT",
            "realized_pnl": None,
        },
        {
            "id": "old-trade-2",
            "executed_at": "2026-09-01T20:00:00Z",
            "signal": "COVER",
            "realized_pnl": 24.77,
        },
    ]

    deleted_trade_ids = []

    def mock_table(table_name):
        chain = MagicMock()
        chain.select.return_value = chain
        chain.insert.return_value = chain
        chain.update.return_value = chain
        chain.upsert.return_value = chain
        chain.eq.return_value = chain
        chain.gte.return_value = chain
        chain.lte.return_value = chain

        if table_name == "trades":
            chain.execute.return_value = MagicMock(data=existing_trades)

            def mock_delete():
                del_chain = MagicMock()

                def mock_del_eq(col, val):
                    if col == "id":
                        deleted_trade_ids.append(val)
                    res = MagicMock()
                    res.execute.return_value = MagicMock()
                    return res

                del_chain.eq.side_effect = mock_del_eq
                return del_chain

            chain.delete.side_effect = mock_delete
        elif table_name == "portfolios" or table_name == "portfolio_performance":
            chain.execute.return_value = MagicMock(data=[])
        return chain

    mock_client.table.side_effect = mock_table

    with (
        patch("execution.system_portfolios.get_supabase_client", return_value=mock_client),
        patch("execution.system_portfolios.get_or_create_system_portfolio", return_value=mock_port),
    ):
        res = await execute_system_daily_trade(prediction, intraday_data)

    assert res["status"] == "success"
    # Verify old trades were deleted
    assert "old-trade-1" in deleted_trade_ids
    assert "old-trade-2" in deleted_trade_ids

    # New equity should be ~10024.77 (10000 base + 24.77 new pnl), NOT 10049.54 (double credited)
    assert abs(res["new_equity"] - 10024.77) < 1.0


@pytest.mark.asyncio
async def test_execute_system_sector_rebalance_idempotent_replacement():
    """Verify that calling execute_system_sector_rebalance removes previous window trades and does not compound PnL."""
    mock_client = MagicMock()
    mock_portfolio_id = uuid4()
    mock_port = MagicMock()
    mock_port.id = mock_portfolio_id
    mock_port.cash_balance = 10050.0  # Already credited with +$50 from first run

    predictions = [
        {"predicted_sector": "XLK", "predicted_worst_sector": "XLU"},
    ]
    price_map = {
        "XLK": {"start_price": 100.0, "end_price": 105.0},
        "XLU": {"start_price": 50.0, "end_price": 52.0},
    }

    existing_trades = [
        {
            "id": "old-sec-trade-1",
            "executed_at": "2026-08-17T13:30:00Z",
            "signal": "BUY",
            "realized_pnl": None,
        },
        {
            "id": "old-sec-trade-2",
            "executed_at": "2026-08-24T20:00:00Z",
            "signal": "SELL",
            "realized_pnl": 50.0,
        },
    ]

    deleted_trade_ids = []

    def mock_table(table_name):
        chain = MagicMock()
        chain.select.return_value = chain
        chain.insert.return_value = chain
        chain.update.return_value = chain
        chain.upsert.return_value = chain
        chain.eq.return_value = chain
        chain.in_.return_value = chain

        if table_name == "trades":
            chain.execute.return_value = MagicMock(data=existing_trades)

            def mock_delete():
                del_chain = MagicMock()

                def mock_del_eq(col, val):
                    if col == "id":
                        deleted_trade_ids.append(val)
                    res = MagicMock()
                    res.execute.return_value = MagicMock()
                    return res

                del_chain.eq.side_effect = mock_del_eq
                return del_chain

            chain.delete.side_effect = mock_delete
        else:
            chain.execute.return_value = MagicMock(data=[])
        return chain

    mock_client.table.side_effect = mock_table

    with (
        patch("execution.system_portfolios.get_supabase_client", return_value=mock_client),
        patch("execution.system_portfolios.get_or_create_system_portfolio", return_value=mock_port),
    ):
        res = await execute_system_sector_rebalance(
            week_start_date="2026-08-17",
            week_end_date="2026-08-24",
            predictions=predictions,
            price_map=price_map,
        )

    assert res["status"] == "success"
    assert "old-sec-trade-1" in deleted_trade_ids
    assert "old-sec-trade-2" in deleted_trade_ids


@pytest.mark.asyncio
async def test_execute_mechanical_sector_rebalance_idempotent_replacement():
    """Verify mechanical sector rebalance deletes old window trades before inserting new ones."""
    mock_client = MagicMock()
    mock_portfolio_id = uuid4()
    mock_port = MagicMock()
    mock_port.id = mock_portfolio_id
    mock_port.cash_balance = 10100.0

    existing_trades = [
        {
            "id": "old-mech-1",
            "executed_at": "2026-08-17T13:30:00Z",
            "signal": "BUY",
            "realized_pnl": None,
        },
        {
            "id": "old-mech-2",
            "executed_at": "2026-08-24T20:00:00Z",
            "signal": "SELL",
            "realized_pnl": 100.0,
        },
    ]

    deleted_trade_ids = []

    def mock_table(table_name):
        chain = MagicMock()
        chain.select.return_value = chain
        chain.insert.return_value = chain
        chain.update.return_value = chain
        chain.upsert.return_value = chain
        chain.eq.return_value = chain
        chain.in_.return_value = chain

        if table_name == "trades":
            chain.execute.return_value = MagicMock(data=existing_trades)

            def mock_delete():
                del_chain = MagicMock()

                def mock_del_eq(col, val):
                    if col == "id":
                        deleted_trade_ids.append(val)
                    res = MagicMock()
                    res.execute.return_value = MagicMock()
                    return res

                del_chain.eq.side_effect = mock_del_eq
                return del_chain

            chain.delete.side_effect = mock_delete
        else:
            chain.execute.return_value = MagicMock(data=[])
        return chain

    mock_client.table.side_effect = mock_table

    with (
        patch("execution.system_portfolios.get_supabase_client", return_value=mock_client),
        patch("execution.system_portfolios.get_or_create_system_portfolio", return_value=mock_port),
    ):
        res = await execute_mechanical_sector_rebalance(
            owner_id=SYS_SECTOR_UNCORR_20D_OWNER_ID,
            sectors=["XLK", "XLE"],
            week_start_date="2026-08-17",
            week_end_date="2026-08-24",
            price_map={
                "XLK": {"start_price": 100.0, "end_price": 105.0},
                "XLE": {"start_price": 50.0, "end_price": 52.0},
            },
        )

    assert res["status"] == "success"
    assert "old-mech-1" in deleted_trade_ids
    assert "old-mech-2" in deleted_trade_ids


def test_evaluate_predictions_only_groups_7d_timeframe():
    """Verify that predictions with non-7d timeframes (30d, 60d, 90d) are excluded from weekly rebalance grouping."""
    predictions = [
        {
            "id": "p-7d",
            "prediction_date": "2026-08-17",
            "target_date": "2026-08-24",
            "timeframe": "7d",
            "predicted_sector": "XLK",
        },
        {
            "id": "p-30d",
            "prediction_date": "2026-08-17",
            "target_date": "2026-09-16",
            "timeframe": "30d",
            "predicted_sector": "XLK",
        },
        {
            "id": "p-60d",
            "prediction_date": "2026-08-17",
            "target_date": "2026-10-16",
            "timeframe": "60d",
            "predicted_sector": "XLK",
        },
    ]

    evaluated_windows = {}
    ticker_prices = {"XLK": {"start_price": 100.0, "end_price": 105.0}}

    for p in predictions:
        pred_date_str = p["prediction_date"]
        target_date_str = p["target_date"]
        if p.get("timeframe") == "7d":
            window_key = (pred_date_str, target_date_str)
            if window_key not in evaluated_windows:
                evaluated_windows[window_key] = {"predictions": [], "price_map": {}}
            evaluated_windows[window_key]["predictions"].append(p)
            evaluated_windows[window_key]["price_map"].update(ticker_prices)

    assert len(evaluated_windows) == 1
    assert ("2026-08-17", "2026-08-24") in evaluated_windows
    assert ("2026-08-17", "2026-09-16") not in evaluated_windows
