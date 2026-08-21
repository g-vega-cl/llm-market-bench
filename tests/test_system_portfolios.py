import os
import sys
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

# Add apps/engine to path BEFORE importing any engine or local modules
sys.path.append(os.path.join(os.getcwd(), "apps", "engine"))

from execution.system_portfolios import (
    SYS_SECTOR_LS_OWNER_ID,
    compute_daily_trade_execution,
    execute_system_daily_trade,
    execute_system_sector_rebalance,
    resolve_sector_predictions,
)


def test_resolve_sector_predictions_basic():
    predictions = [
        {"predicted_sector": "XLE", "predicted_worst_sector": "XLU"},
        {"predicted_sector": "XOP", "predicted_worst_sector": "XLY"},
        {"predicted_sector": "XLE", "predicted_worst_sector": "XLU"},
    ]
    longs, shorts = resolve_sector_predictions(predictions)
    assert sorted(longs) == ["XLE", "XOP"]
    assert sorted(shorts) == ["XLU", "XLY"]


def test_resolve_sector_predictions_conflict_netting():
    # If XLE is predicted as best by model 1 and worst by model 2, net it out
    predictions = [
        {"predicted_sector": "XLE", "predicted_worst_sector": "XLU"},
        {"predicted_sector": "XLF", "predicted_worst_sector": "XLE"},
    ]
    longs, shorts = resolve_sector_predictions(predictions)
    assert longs == ["XLF"]
    assert shorts == ["XLU"]
    assert "XLE" not in longs
    assert "XLE" not in shorts


def test_resolve_sector_predictions_filters_unknown_and_empty():
    predictions = [
        {"predicted_sector": "XLK", "predicted_worst_sector": "UNKNOWN"},
        {"predicted_sector": "", "predicted_worst_sector": None},
    ]
    longs, shorts = resolve_sector_predictions(predictions)
    assert longs == ["XLK"]
    assert shorts == []


def test_compute_daily_trade_execution_up_target_hit():
    # UP prediction, target hit intraday
    pred = {
        "predicted_direction": "UP",
        "expected_return_pct": 0.50,  # +0.50%
        "confidence": 70.0,
    }
    intraday = {
        "open_price": 500.0,
        "high_price": 505.0,  # Max +1.0%, hits +0.50% target
        "low_price": 498.0,
        "close_price": 501.0,
        "intraday_exit_price": 502.0,  # 3:30 PM price
        "intraday_hit": True,
    }
    capital = 10000.0
    result = compute_daily_trade_execution(
        pred, intraday, capital=capital, slippage_bps=5.0
    )

    assert result["direction"] == "UP"
    assert result["target_hit"] is True
    # Slippage 5 bps = 0.05% -> Entry = 500 * 1.0005 = 500.25
    assert result["entry_price"] == pytest.approx(500.25)
    # Target price = 500 * (1 + 0.005) = 502.50
    assert result["exit_price"] == pytest.approx(502.50)
    # Shares = int(10000 / 500.25) = 19
    assert result["shares"] == 19
    expected_pnl = (502.50 - 500.25) * 19
    assert result["realized_pnl"] == pytest.approx(expected_pnl)
    assert result["realized_pnl"] > 0


def test_compute_daily_trade_execution_up_target_missed():
    # UP prediction, target not hit, exit at 3:30 PM price
    pred = {
        "predicted_direction": "UP",
        "expected_return_pct": 1.50,  # +1.50%
        "confidence": 60.0,
    }
    intraday = {
        "open_price": 500.0,
        "high_price": 502.0,  # Max +0.40%, misses 1.5% target
        "low_price": 496.0,
        "close_price": 497.0,
        "intraday_exit_price": 498.0,  # 3:30 PM price
        "intraday_hit": False,
    }
    capital = 10000.0
    result = compute_daily_trade_execution(
        pred, intraday, capital=capital, slippage_bps=5.0
    )

    assert result["direction"] == "UP"
    assert result["target_hit"] is False
    assert result["entry_price"] == pytest.approx(500.25)
    # Exit price at 3:30 PM with exit slippage: 498.0 * (1 - 0.0005) = 497.751
    assert result["exit_price"] == pytest.approx(498.0 * 0.9995)
    assert result["realized_pnl"] < 0


def test_compute_daily_trade_execution_down_target_hit():
    # DOWN prediction, target hit intraday
    pred = {
        "predicted_direction": "DOWN",
        "expected_return_pct": -0.80,  # -0.80%
        "confidence": 75.0,
    }
    intraday = {
        "open_price": 500.0,
        "high_price": 502.0,
        "low_price": 495.0,  # Low dropped -1.0%, hits -0.80% target
        "close_price": 496.0,
        "intraday_exit_price": 497.0,
        "intraday_hit": True,
    }
    capital = 10000.0
    result = compute_daily_trade_execution(
        pred, intraday, capital=capital, slippage_bps=5.0
    )

    assert result["direction"] == "DOWN"
    assert result["target_hit"] is True
    # Short Entry = 500 * (1 - 0.0005) = 499.75
    assert result["entry_price"] == pytest.approx(499.75)
    # Target exit = 500 * (1 - 0.008) = 496.00
    assert result["exit_price"] == pytest.approx(496.00)
    # Shares = int(10000 / 499.75) = 20
    assert result["shares"] == 20
    expected_pnl = (499.75 - 496.00) * 20
    assert result["realized_pnl"] == pytest.approx(expected_pnl)
    assert result["realized_pnl"] > 0


def create_mock_supabase(owner_id: str, initial_cash: float = 10000.0):
    port_id = str(uuid4())
    mock_client = MagicMock()

    def mock_table(table_name: str):
        table_mock = MagicMock()
        if table_name == "portfolios":
            table_mock.select.return_value.eq.return_value.execute.return_value.data = [
                {
                    "id": port_id,
                    "owner_id": owner_id,
                    "cash_balance": initial_cash,
                    "sma": 0.0,
                }
            ]
            table_mock.insert.return_value.execute.return_value.data = [{"id": port_id}]
            table_mock.update.return_value.eq.return_value.execute.return_value.data = [
                {"id": port_id}
            ]
        elif table_name == "portfolio_positions":
            table_mock.select.return_value.eq.return_value.execute.return_value.data = []
            table_mock.insert.return_value.execute.return_value.data = []
            table_mock.update.return_value.eq.return_value.execute.return_value.data = []
            table_mock.delete.return_value.eq.return_value.execute.return_value.data = []
        elif table_name in ("trades", "portfolio_performance"):
            table_mock.insert.return_value.execute.return_value.data = [
                {"id": str(uuid4())}
            ]
            table_mock.upsert.return_value.execute.return_value.data = [
                {"id": str(uuid4())}
            ]
        return table_mock

    mock_client.table.side_effect = mock_table
    return mock_client


@pytest.mark.asyncio
async def test_execute_system_sector_rebalance_flow():
    mock_supabase = create_mock_supabase(SYS_SECTOR_LS_OWNER_ID, 10000.0)

    predictions = [
        {"predicted_sector": "XLE", "predicted_worst_sector": "XLU"},
        {"predicted_sector": "XOP", "predicted_worst_sector": "XLY"},
    ]
    # Price map: XLE gained 2%, XOP gained 4%, XLU gained 1%, XLY dropped 3%
    price_map = {
        "XLE": {"start_price": 100.0, "end_price": 102.0, "return_pct": 2.0},
        "XOP": {"start_price": 50.0, "end_price": 52.0, "return_pct": 4.0},
        "XLU": {"start_price": 80.0, "end_price": 80.8, "return_pct": 1.0},
        "XLY": {"start_price": 200.0, "end_price": 194.0, "return_pct": -3.0},
    }

    with (
        patch(
            "execution.system_portfolios.get_supabase_client",
            return_value=mock_supabase,
        ),
        patch("execution.portfolio.get_supabase_client", return_value=mock_supabase),
    ):
        res = await execute_system_sector_rebalance(
            week_start_date="2026-08-10",
            week_end_date="2026-08-14",
            predictions=predictions,
            price_map=price_map,
        )

        assert res["status"] == "success"
        assert res["long_sectors"] == ["XLE", "XOP"]
        assert res["short_sectors"] == ["XLU", "XLY"]
        assert len(res["trades"]) == 4
        assert res["total_realized_pnl"] > 0


@pytest.mark.asyncio
async def test_execute_system_daily_trade_flow():
    mock_supabase = create_mock_supabase("sys-daily-spy-deepseek-v4-flash", 10000.0)

    prediction = {
        "id": str(uuid4()),
        "model_name": "deepseek-v4-flash",
        "ticker": "SPY",
        "target_date": "2026-08-18",
        "predicted_direction": "UP",
        "confidence": 75.0,
        "expected_return_pct": 0.40,
    }
    intraday_data = {
        "open_price": 550.0,
        "high_price": 553.0,
        "low_price": 548.0,
        "close_price": 551.0,
        "intraday_hit": True,
    }

    with (
        patch(
            "execution.system_portfolios.get_supabase_client",
            return_value=mock_supabase,
        ),
        patch("execution.portfolio.get_supabase_client", return_value=mock_supabase),
    ):
        res = await execute_system_daily_trade(
            prediction=prediction, intraday_data=intraday_data
        )

        assert res["status"] == "success"
        assert res["owner_id"] == "sys-daily-spy-deepseek-v4-flash"
        assert res["execution"]["target_hit"] is True
        assert res["execution"]["realized_pnl"] > 0
