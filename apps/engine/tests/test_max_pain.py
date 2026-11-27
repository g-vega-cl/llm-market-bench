"""Unit tests for Daily Options Max Pain execution and order computation.

Hermetic tests with zero external network calls.
"""

import pytest

from execution.max_pain import (
    DEFAULT_MAX_PAIN_SLIPPAGE_BPS,
    SYS_MAX_PAIN_OWNER_ID,
    compute_max_pain_rebalance_orders,
    evaluate_max_pain_holding_exit,
)


def test_sys_max_pain_owner_id():
    assert SYS_MAX_PAIN_OWNER_ID == "sys-max-pain"
    assert DEFAULT_MAX_PAIN_SLIPPAGE_BPS == 1.0  # 1 bps = 0.01%


def test_evaluate_holding_exit_target_strike_reached():
    """Verify position is liquidated when price converges to within 0.05% of Max Pain strike."""
    holding_info = {
        "ticker": "SPY",
        "entry_price": 555.0,
        "target_strike": 560.0,
    }
    # 560 * (1 - 0.0005) = 559.72
    should_exit, reason = evaluate_max_pain_holding_exit(
        holding_info,
        current_price=559.80,
        session_high=559.85,
        target_proximity_pct=0.05,
    )
    assert should_exit is True
    assert "Target strike $560.00 reached" in reason


def test_evaluate_holding_exit_moc_close_window():
    """Verify position is liquidated before session close (3:50 PM MOC) to guarantee zero overnight hold."""
    holding_info = {
        "ticker": "QQQ",
        "entry_price": 480.0,
        "target_strike": 485.0,
    }
    should_exit, reason = evaluate_max_pain_holding_exit(
        holding_info,
        current_price=482.0,
        is_market_close_window=True,
    )
    assert should_exit is True
    assert "Session close liquidation" in reason


def test_evaluate_holding_exit_adverse_stop_loss():
    """Verify position is liquidated when price drops >1.0% below entry price (gamma unpinning)."""
    holding_info = {
        "ticker": "SPY",
        "entry_price": 560.0,
        "target_strike": 565.0,
    }
    # 1.0% drop below 560 is 554.40
    should_exit, reason = evaluate_max_pain_holding_exit(
        holding_info,
        current_price=553.0,
        stop_loss_pct=1.0,
    )
    assert should_exit is True
    assert "Adverse stop loss triggered" in reason


def test_evaluate_holding_exit_retain():
    """Verify position is retained during regular hours when target has not hit and stop loss not reached."""
    holding_info = {
        "ticker": "SPY",
        "entry_price": 555.0,
        "target_strike": 560.0,
    }
    should_exit, reason = evaluate_max_pain_holding_exit(
        holding_info,
        current_price=556.50,
        session_high=557.0,
        is_market_close_window=False,
    )
    assert should_exit is False
    assert reason == "Holding criteria healthy"


def test_compute_max_pain_rebalance_orders():
    """Verify rebalance orders plan sells for exiting holdings and buys for qualified entries with 1 bps friction."""
    current_holdings = [
        {"ticker": "OLD_SPY", "shares": 10, "current_price": 560.0, "cost_basis": 555.0},
        {"ticker": "KEEP_QQQ", "shares": 5, "current_price": 480.0, "cost_basis": 480.0},
    ]
    holding_evaluations = {
        "OLD_SPY": {"should_exit": True, "reason": "Target strike $560.00 reached (pin achieved)"},
        "KEEP_QQQ": {"should_exit": False, "reason": "Holding criteria healthy"},
    }
    qualified_candidates = [
        {"ticker": "SPY", "price": 555.0, "max_pain_strike": 560.0, "discount_pct": 0.90, "jev_confidence": 85.0},
    ]

    available_cash = 1000.0  # Plus proceeds from selling OLD_SPY: 10 * 560 * (1 - 0.0001) = $5,599.44 -> ~$6599 total
    plan = compute_max_pain_rebalance_orders(
        current_holdings=current_holdings,
        holding_evaluations=holding_evaluations,
        qualified_candidates=qualified_candidates,
        available_cash=available_cash,
        max_holdings=2,
        slippage_bps=1.0,  # 0.01%
    )

    # 1. Sales
    assert len(plan["sales"]) == 1
    assert plan["sales"][0]["ticker"] == "OLD_SPY"
    assert plan["sales"][0]["shares"] == 10
    # Price with 1 bps slippage: 560 * (1 - 0.0001) = 559.944
    assert round(plan["sales"][0]["execution_price"], 3) == 559.944

    # 2. Retained
    assert len(plan["retained"]) == 1
    assert plan["retained"][0]["ticker"] == "KEEP_QQQ"

    # 3. Buys
    assert len(plan["buys"]) == 1
    assert plan["buys"][0]["ticker"] == "SPY"
    # Price with 1 bps buy slippage: 555 * (1 + 0.0001) = 555.0555
    assert round(plan["buys"][0]["execution_price"], 4) == 555.0555
    assert plan["buys"][0]["shares"] > 0


def test_compute_max_pain_rebalance_orders_uses_target_strike_on_pin_achieved():
    """When session_high touches the target strike intraday and price pulls back, sale fills at target strike - 1bps."""
    current_holdings = [
        {
            "ticker": "SPY",
            "shares": 10,
            "current_price": 765.0,
            "cost_basis": 763.0,
            "entry_price": 763.0,
            "target_strike": 769.0,
        },
    ]
    holding_evaluations = {
        "SPY": {
            "should_exit": True,
            "reason": "Target strike $769.00 reached (pin achieved)",
        },
    }
    plan = compute_max_pain_rebalance_orders(
        current_holdings=current_holdings,
        holding_evaluations=holding_evaluations,
        qualified_candidates=[],
        available_cash=2000.0,
        max_holdings=2,
        slippage_bps=1.0,
    )
    assert len(plan["sales"]) == 1
    # Target strike $769.00 * (1 - 0.0001) = 768.9231 (not pullback price 765.0)
    assert round(plan["sales"][0]["execution_price"], 4) == round(769.0 * (1.0 - 0.0001), 4)


def test_compute_max_pain_rebalance_orders_uses_close_price_when_pin_not_achieved():
    """When exiting on MOC session close without touching target strike, sale fills at current/close price - 1bps."""
    current_holdings = [
        {
            "ticker": "SPY",
            "shares": 10,
            "current_price": 765.0,
            "cost_basis": 763.0,
            "entry_price": 763.0,
            "target_strike": 769.0,
        },
    ]
    holding_evaluations = {
        "SPY": {
            "should_exit": True,
            "reason": "Session close liquidation (3:50 PM MOC)",
        },
    }
    plan = compute_max_pain_rebalance_orders(
        current_holdings=current_holdings,
        holding_evaluations=holding_evaluations,
        qualified_candidates=[],
        available_cash=2000.0,
        max_holdings=2,
        slippage_bps=1.0,
    )
    assert len(plan["sales"]) == 1
    assert round(plan["sales"][0]["execution_price"], 4) == round(765.0 * (1.0 - 0.0001), 4)


@pytest.mark.asyncio
async def test_reconcile_unliquidated_exits_via_ledger_rpc_at_pass_time():
    """Unliquidated 0DTE positions must exit via the canonical trade RPC now, not a backdated BACKFILLED insert."""
    from unittest.mock import MagicMock, patch

    from execution.max_pain import reconcile_unliquidated_max_pain_positions

    client = MagicMock()
    exec_result = MagicMock()
    exec_result.data = {"trade_id": "trade-1", "cash_balance": 1800.0, "total_equity": 9800.0}
    client.rpc.return_value.execute.return_value = exec_result

    with (
        patch(
            "tasks.max_pain_task.fetch_quote_snapshot",
            return_value={"price": 770.0, "day_high": 770.5, "day_low": 760.0},
        ),
        patch(
            "tasks.evaluate_daily_predictions.fetch_intraday_prices",
            return_value=(763.0, 769.2, 762.0, 764.5),
        ),
    ):
        result = await reconcile_unliquidated_max_pain_positions(
            portfolio_row={"id": "p-max-pain", "cash_balance": 1000.0},
            positions=[{"ticker": "SPY", "quantity": 10, "average_cost_basis": 763.0}],
            audit_date="2026-10-22",
            client=client,
        )

    client.rpc.assert_called_once()
    rpc_name, rpc_payload = client.rpc.call_args.args
    assert rpc_name == "execute_portfolio_trade"
    assert rpc_payload["p_signal"] == "SELL"
    assert rpc_payload["p_ticker"] == "SPY"
    assert rpc_payload["p_quantity"] == 10
    assert round(rpc_payload["p_price"], 4) == round(770.0 * (1.0 - 0.0001), 4)
    assert result["exit_mode"] == "LIVE_QUOTE"
    assert result["new_equity"] == 9800.0
    assert all(call.args[0] != "trades" for call in client.table.call_args_list)
    assert "2026-10-22T20:00:00Z" not in str(result)
