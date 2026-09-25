"""Unit tests for sys-future-forces execution engine and scheduled task."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from execution.future_forces import (
    SYS_FUTURE_FORCES_OWNER_ID,
    compute_future_forces_rebalance_orders,
    execute_force_invalidation,
)


def test_sys_future_forces_owner_id():
    """Verify owner_id constant."""
    assert SYS_FUTURE_FORCES_OWNER_ID == "sys-future-forces"


def test_compute_future_forces_rebalance_orders():
    """Verify order computation generates sales for invalidations and sizes new buys."""
    current_holdings = [
        {"ticker": "FRO", "shares": 100, "current_price": 25.0},
        {"ticker": "CRWD", "shares": 10, "current_price": 300.0},
    ]

    holding_evaluations = {
        "FRO": {"should_exit": True, "reason": "demilitarization_treaty"},
        "CRWD": {"should_exit": False},
    }

    candidate_forces = [
        {
            "force_title": "World Cup Travel",
            "archetype": "mega_event",
            "tickers": ["ABNB"],
            "quotes": {"ABNB": {"price": 150.0}},
        }
    ]

    available_cash = 2000.0
    total_equity = 10000.0  # target 8% = $800

    result = compute_future_forces_rebalance_orders(
        current_holdings=current_holdings,
        holding_evaluations=holding_evaluations,
        candidate_forces=candidate_forces,
        available_cash=available_cash,
        total_equity=total_equity,
        target_position_weight=0.08,
        slippage_bps=5.0,
    )

    # 1. FRO should be sold (100 shares * 25 * (1 - 0.0005) = $2498.75)
    assert len(result["sales"]) == 1
    assert result["sales"][0]["ticker"] == "FRO"
    assert result["sales"][0]["shares"] == 100
    assert "treaty" in result["sales"][0]["reason"]

    # 2. CRWD should be retained
    assert len(result["retained"]) == 1
    assert result["retained"][0]["ticker"] == "CRWD"

    # 3. ABNB should have a BUY order
    assert len(result["new_buys"]) == 1
    assert result["new_buys"][0]["ticker"] == "ABNB"
    assert result["new_buys"][0]["shares"] > 0


@pytest.mark.asyncio
async def test_execute_force_invalidation_market_closed_defers():
    """Verify that when market is closed, invalidation is marked pending_liquidation without trade execution."""
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[
            {
                "id": "force-123",
                "force_title": "Hormuz Squeeze",
                "tickers": ["FRO"],
                "status": "active",
            }
        ]
    )

    with (
        patch("execution.future_forces.get_supabase_client", return_value=mock_supabase),
        patch("execution.future_forces.is_market_open_with_logging", new_callable=AsyncMock, return_value=False),
    ):
        res = await execute_force_invalidation(
            force_id="force-123",
            reason="Treaty signed",
            force_market_check=True,
        )

    assert res["status"] == "deferred_market_closed"
    assert "FRO" in res["tickers"]

    # Verify DB updated to pending_liquidation
    update_calls = mock_supabase.table.return_value.update.call_args_list
    assert len(update_calls) == 1
    payload = update_calls[0][0][0]
    assert payload["status"] == "pending_liquidation"
    assert payload["invalidation_reason"] == "Treaty signed"


@pytest.mark.asyncio
async def test_execute_force_invalidation_market_open_executes_live():
    """Verify that when market is open, force invalidation executes live SELL mirrored to Alpaca."""
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[
            {
                "id": "force-123",
                "force_title": "Hormuz Squeeze",
                "tickers": ["FRO"],
                "status": "active",
            }
        ]
    )

    mock_portfolio = MagicMock()
    mock_portfolio.initialize = AsyncMock()
    mock_portfolio.get_position.return_value = {
        "ticker": "FRO",
        "quantity": 100,
        "current_price": 25.0,
    }
    mock_portfolio.execute_trade = AsyncMock(return_value={"trade_id": "t-1", "ticker": "FRO", "signal": "SELL"})

    with (
        patch("execution.future_forces.get_supabase_client", return_value=mock_supabase),
        patch("execution.future_forces.is_market_open_with_logging", new_callable=AsyncMock, return_value=True),
        patch("execution.future_forces.Portfolio", return_value=mock_portfolio),
    ):
        res = await execute_force_invalidation(
            force_id="force-123",
            reason="Treaty signed",
            is_realized=False,
            force_market_check=True,
        )

    assert res["status"] == "executed"
    assert res["target_status"] == "invalidated"

    # Verify portfolio executed trade with skip_alpaca_mirror=False
    mock_portfolio.execute_trade.assert_awaited_once()
    trade_kwargs = mock_portfolio.execute_trade.call_args[1]
    assert trade_kwargs["ticker"] == "FRO"
    assert trade_kwargs["signal"] == "SELL"
    assert trade_kwargs["skip_alpaca_mirror"] is False


@pytest.mark.asyncio
async def test_run_future_forces_task_bootstraps_portfolio():
    """Verify run_future_forces_task initializes portfolio and seeds default forces."""
    from tasks.future_forces_task import run_future_forces_task

    mock_supabase = MagicMock()
    mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "port-new-123"}])

    mock_portfolio = MagicMock()
    mock_portfolio.id = None
    mock_portfolio.initialize = AsyncMock()
    mock_portfolio.positions = {}
    mock_portfolio.cash_balance = 10000.0
    mock_portfolio.total_equity = 10000.0

    with (
        patch("tasks.future_forces_task.get_supabase_client", return_value=mock_supabase),
        patch("tasks.future_forces_task.Portfolio", return_value=mock_portfolio),
        patch("tasks.future_forces_task.is_market_open_with_logging", new_callable=AsyncMock, return_value=False),
        patch("tasks.future_forces_task.seed_baseline_future_forces", new_callable=AsyncMock, return_value=[]),
    ):
        res = await run_future_forces_task(mode="rebalance", dry_run=True, force_market=False)

    assert "rebalance_orders" in res
    assert res["rebalance_orders"]["remaining_cash"] == 10000.0
    mock_portfolio.initialize.assert_awaited_once()
