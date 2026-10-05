"""Unit tests for PEAD Drift portfolio execution and order computation.

Hermetic tests with zero external network calls.
"""

from execution.pead_drift import (
    SYS_PEAD_DRIFT_OWNER_ID,
    compute_pead_rebalance_orders,
    evaluate_holding_exit,
)


def test_sys_pead_owner_id():
    assert SYS_PEAD_DRIFT_OWNER_ID == "sys-pead-drift"


def test_evaluate_holding_exit_time_expiration():
    """Verify position is liquidated when holding days exceed max_holding_days."""
    holding_info = {
        "ticker": "AAPL",
        "holding_days": 31,
        "entry_price": 200.0,
        "peak_price": 220.0,
    }
    should_exit, reason = evaluate_holding_exit(
        holding_info, current_price=215.0, max_holding_days=30, trailing_stop_pct=5.0
    )
    assert should_exit is True
    assert "Holding horizon expired" in reason


def test_evaluate_holding_exit_trailing_stop():
    """Verify position is liquidated when price drops more than trailing_stop_pct from peak."""
    holding_info = {
        "ticker": "NVDA",
        "holding_days": 10,
        "entry_price": 100.0,
        "peak_price": 120.0,  # 5% below 120 is 114
    }
    should_exit, reason = evaluate_holding_exit(
        holding_info, current_price=113.0, max_holding_days=30, trailing_stop_pct=5.0
    )
    assert should_exit is True
    assert "Trailing stop triggered" in reason


def test_evaluate_holding_exit_retain():
    """Verify position is retained when within holding period and above trailing stop."""
    holding_info = {
        "ticker": "MSFT",
        "holding_days": 15,
        "entry_price": 400.0,
        "peak_price": 420.0,
    }
    should_exit, reason = evaluate_holding_exit(
        holding_info, current_price=415.0, max_holding_days=30, trailing_stop_pct=5.0
    )
    assert should_exit is False
    assert reason == "Holding criteria healthy"


def test_compute_pead_rebalance_orders_liquidation_and_buying():
    """Verify rebalance orders plan sells for exiting holdings and buys for qualified entries."""
    current_holdings = [
        {"ticker": "OLD1", "shares": 10, "current_price": 100.0, "cost_basis": 90.0},
        {"ticker": "KEEP1", "shares": 5, "current_price": 200.0, "cost_basis": 190.0},
    ]
    holding_evaluations = {
        "OLD1": {"should_exit": True, "reason": "Holding horizon expired (31d > 30d)"},
        "KEEP1": {"should_exit": False, "reason": "Holding criteria healthy"},
    }
    qualified_candidates = [
        {"ticker": "NEW1", "price": 50.0, "sue_score": 3.5, "jev_confidence": 85.0},
        {"ticker": "NEW2", "price": 100.0, "sue_score": 2.8, "jev_confidence": 75.0},
    ]

    available_cash = 1000.0  # Plus $1000 freed from selling OLD1 = $2000 total freed cash
    plan = compute_pead_rebalance_orders(
        current_holdings=current_holdings,
        holding_evaluations=holding_evaluations,
        qualified_candidates=qualified_candidates,
        available_cash=available_cash,
        max_holdings=4,
        slippage_bps=5.0,
    )

    # 1. Sales
    assert len(plan["sales"]) == 1
    assert plan["sales"][0]["ticker"] == "OLD1"
    assert plan["sales"][0]["shares"] == 10

    # 2. Retained
    assert len(plan["retained"]) == 1
    assert plan["retained"][0]["ticker"] == "KEEP1"

    # 3. Buys
    buy_tickers = [b["ticker"] for b in plan["buys"]]
    assert "NEW1" in buy_tickers
    assert "NEW2" in buy_tickers
    assert all(b["shares"] > 0 for b in plan["buys"])
