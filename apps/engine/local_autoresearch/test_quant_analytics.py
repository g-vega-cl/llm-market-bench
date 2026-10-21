"""Tests for Quantitative Analytics and Feature Conditioning in Autoresearch (Hermetic & TDD)."""

from __future__ import annotations

from local_autoresearch.quant_analytics import (
    calculate_sized_trading_pnl,
    create_walk_forward_splits,
    format_normalized_quant_vector,
    passes_two_sided_gate_discrete,
)


def test_calculate_sized_trading_pnl_positive_alpha():
    """Verify sized trading PnL calculation on a profitable sequence."""
    records = [
        {
            "target_date": "2026-08-12",
            "open_price": 500.0,
            "close_price": 505.0,  # +1.0% return
            "actual_direction": "UP",
            "predicted_direction": "UP",
            "confidence": 75.0,  # size = (75-50)/50 = 0.50 -> return = +0.50%
        },
        {
            "target_date": "2026-08-14",
            "open_price": 505.0,
            "close_price": 500.0,  # -0.99% return
            "actual_direction": "DOWN",
            "predicted_direction": "DOWN",
            "confidence": 100.0,  # size = (100-50)/50 = 1.00 -> return = +0.99%
        },
        {
            "target_date": "2026-08-17",
            "open_price": 500.0,
            "close_price": 502.5,  # +0.50% return
            "actual_direction": "UP",
            "predicted_direction": "DOWN",  # Wrong direction
            "confidence": 60.0,  # size = 0.20 -> return = -0.10%
        },
    ]

    pnl = calculate_sized_trading_pnl(records)

    assert pnl["trade_count"] == 3
    assert pnl["cumulative_return_pct"] > 1.0  # +0.50% + 0.99% - 0.10% ≈ +1.39%
    assert pnl["unweighted_return_pct"] > 1.0
    assert pnl["profit_factor"] > 1.0
    assert pnl["annualized_sharpe"] > 0.0
    assert pnl["max_drawdown_pct"] >= 0.0


def test_calculate_sized_trading_pnl_empty():
    """Verify sized trading PnL handles empty record lists gracefully."""
    pnl = calculate_sized_trading_pnl([])
    assert pnl["trade_count"] == 0
    assert pnl["cumulative_return_pct"] == 0.0
    assert pnl["annualized_sharpe"] == 0.0
    assert pnl["profit_factor"] == 0.0


def test_format_normalized_quant_vector_structure():
    """Verify standardized tabular feature vector extraction from session data."""
    session = {
        "target_date": "2026-09-15",
        "open_price": 550.0,
        "quotes": {
            "SPY": {"gap_pct": 0.35, "price": 550.0},
            "QQQ": {"gap_pct": 0.55, "price": 480.0},
            "TLT": {"gap_pct": -0.25, "price": 95.0},
        },
        "options": {
            "put_call_volume_ratio": 0.82,
            "put_call_oi_ratio": 0.95,
            "max_pain_strike": 548.0,
            "atm_implied_vol": 12.5,
        },
    }

    quant_text = format_normalized_quant_vector(session)

    assert "STANDARDIZED QUANTITATIVE FEATURE VECTOR" in quant_text
    assert "SPY Gap" in quant_text or "overnight_gap" in quant_text
    assert "0.35" in quant_text
    assert "0.82" in quant_text
    assert "Max Pain" in quant_text


def test_format_normalized_quant_vector_handles_missing_fields():
    """Verify graceful fallback when quotes or options are omitted."""
    session = {
        "target_date": "2026-09-15",
        "open_price": 550.0,
    }
    quant_text = format_normalized_quant_vector(session)
    assert "STANDARDIZED QUANTITATIVE FEATURE VECTOR" in quant_text
    assert "N/A" in quant_text or "Not Provided" in quant_text


def test_create_walk_forward_splits():
    """Verify expanding-window walk-forward cross validation fold generation."""
    sessions = [{"target_date": f"2026-08-{i:02d}", "id": i} for i in range(1, 21)]

    folds = create_walk_forward_splits(sessions, n_splits=3, min_train_size=10)

    assert len(folds) == 3
    # First fold: train has at least 10 sessions, test follows chronologically
    train1, test1 = folds[0]
    assert len(train1) >= 10
    assert len(test1) > 0
    assert train1[-1]["target_date"] < test1[0]["target_date"]

    # Final fold: train expands
    train3, test3 = folds[2]
    assert len(train3) > len(train1)
    assert train3[-1]["target_date"] < test3[0]["target_date"]


def test_passes_two_sided_gate_discrete_allows_six_of_eleven():
    """Verify discrete binomial gate correctly accepts 6/11 green days (54.55%) with min_recall_up=54.0."""
    metrics = {
        "recall_up_pct": 54.55,  # 6 / 11
        "recall_down_pct": 81.82,  # 9 / 11
        "balanced_accuracy_pct": 68.18,
        "mcc": 0.38,
    }

    passed, reason = passes_two_sided_gate_discrete(metrics, min_recall_up=54.0, min_recall_down=54.0)
    assert passed is True
    assert "Passed" in reason

    # But 5 / 11 (45.45%) must fail
    metrics_failing = dict(metrics, recall_up_pct=45.45)
    passed_fail, reason_fail = passes_two_sided_gate_discrete(metrics_failing, min_recall_up=54.0)
    assert passed_fail is False
    assert "Bear-biased" in reason_fail
