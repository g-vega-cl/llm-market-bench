"""Unit tests for Small/Mid-Cap Quality Compounder portfolio rebalancing and execution logic.

Pure unit tests with zero external network calls.
Verifies:
1. Candidate ranking by combined Quality (ROIC) and Momentum.
2. Holding retention: Large-cap winners are held without selling.
3. Liquidation of broken holdings: Unprofitable or negative FCF positions are sold.
4. Capital recycling: Cash freed from sales is allocated to top new small-cap entries.
5. Sizing and slippage calculation.
"""

import pytest

from analytics.smid_quality import rank_and_select_candidates
from execution.smid_compounder import (
    SYS_SMID_COMPOUNDER_OWNER_ID,
    compute_smid_rebalance_orders,
)


def test_sys_smid_owner_id_constant():
    assert SYS_SMID_COMPOUNDER_OWNER_ID == "sys-smid-quality-compounder"


def test_rank_and_select_candidates_filters_and_sorts():
    """Verifies that candidates are filtered for quality and positive momentum, then ranked by composite score."""
    candidates = [
        # Candidate 1: Passed quality, high momentum, solid ROIC -> Top pick
        {
            "symbol": "WIN1",
            "market_cap": 3000000000.0,
            "quality": {"is_quality_pass": True, "roic": 0.18, "ttm_fcf": 50000000.0},
            "momentum_12m": 45.0,
            "price": 50.0,
        },
        # Candidate 2: Failed quality (negative FCF) -> Excluded
        {
            "symbol": "FAIL_QUAL",
            "market_cap": 2500000000.0,
            "quality": {"is_quality_pass": False, "roic": 0.12, "ttm_fcf": -10000000.0},
            "momentum_12m": 60.0,
            "price": 40.0,
        },
        # Candidate 3: Passed quality, negative momentum -> Excluded
        {
            "symbol": "FAIL_MOM",
            "market_cap": 4000000000.0,
            "quality": {"is_quality_pass": True, "roic": 0.15, "ttm_fcf": 30000000.0},
            "momentum_12m": -15.0,
            "price": 30.0,
        },
        # Candidate 4: Passed quality, moderate momentum -> Second pick
        {
            "symbol": "WIN2",
            "market_cap": 5000000000.0,
            "quality": {"is_quality_pass": True, "roic": 0.14, "ttm_fcf": 40000000.0},
            "momentum_12m": 25.0,
            "price": 100.0,
        },
    ]

    selected = rank_and_select_candidates(candidates, target_count=2)

    assert len(selected) == 2
    assert selected[0]["symbol"] == "WIN1"
    assert selected[1]["symbol"] == "WIN2"


def test_compute_rebalance_orders_zero_ceiling_retention():
    """Existing holding grew to $40B (now mega cap) and remains profitable.

    Must NOT be sold. Sells should be empty.
    """
    current_holdings = [
        {
            "ticker": "DECK",
            "shares": 100,
            "cost_basis": 50.0,
            "current_price": 250.0,  # $25,000 position value
            "market_cap": 40000000000.0,  # $40B large cap
        }
    ]
    # Holding evaluation indicates healthy quality
    holding_evaluations = {
        "DECK": {"should_sell": False, "reason": "hold_quality_winner"}
    }
    candidate_pool = []
    available_cash = 1000.0

    plan = compute_smid_rebalance_orders(
        current_holdings=current_holdings,
        holding_evaluations=holding_evaluations,
        candidate_pool=candidate_pool,
        available_cash=available_cash,
        target_holdings_count=10,
    )

    assert len(plan["sales"]) == 0
    assert len(plan["retained"]) == 1
    assert plan["retained"][0]["ticker"] == "DECK"
    assert plan["retained"][0]["reason"] == "hold_quality_winner"


def test_compute_rebalance_orders_liquidates_failing_holding_and_buys_candidate():
    """Holding turns into a zombie. It must be sold, and freed cash used to buy a new candidate."""
    current_holdings = [
        # Failing holding: 50 shares at $20 = $1,000 liquidation value
        {
            "ticker": "ZOM",
            "shares": 50,
            "cost_basis": 40.0,
            "current_price": 20.0,
            "market_cap": 800000000.0,
        }
    ]
    holding_evaluations = {
        "ZOM": {"should_sell": True, "reason": "unprofitable_zombie"}
    }
    candidate_pool = [
        {
            "symbol": "NEW1",
            "price": 50.0,
            "market_cap": 3000000000.0,
            "composite_score": 85.0,
        }
    ]
    initial_cash = 500.0

    plan = compute_smid_rebalance_orders(
        current_holdings=current_holdings,
        holding_evaluations=holding_evaluations,
        candidate_pool=candidate_pool,
        available_cash=initial_cash,
        target_holdings_count=2,
        slippage_bps=5.0,
    )

    # 1. ZOM must be sold
    assert len(plan["sales"]) == 1
    sale = plan["sales"][0]
    assert sale["ticker"] == "ZOM"
    assert sale["shares"] == 50
    assert sale["reason"] == "unprofitable_zombie"
    # Exit price with 5 bps slippage: 20.0 * (1 - 0.0005) = 19.99
    assert sale["execution_price"] == pytest.approx(19.99)
    # Freed cash = 50 * 19.99 = 999.50. Total cash = 500 + 999.50 = 1499.50
    assert plan["freed_cash"] == pytest.approx(999.50)

    # 2. NEW1 must be bought with available cash
    assert len(plan["buys"]) == 1
    buy = plan["buys"][0]
    assert buy["ticker"] == "NEW1"
    # Entry price with 5 bps slippage: 50.0 * (1 + 0.0005) = 50.025
    assert buy["execution_price"] == pytest.approx(50.025)
    # Available cash (~1499.50) / 50.025 = 29 shares
    assert buy["shares"] == 29
    assert buy["total_cost"] <= 1499.50
