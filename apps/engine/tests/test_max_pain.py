"""Unit tests for Daily Options Max Pain execution and order computation.

Hermetic tests with zero external network calls.
"""

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
