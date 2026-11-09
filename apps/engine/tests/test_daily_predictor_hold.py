from __future__ import annotations

import math

from core.conviction_scoring import conviction_points
from core.llm.daily_predictor_prompts import (
    HOLD_CONFIDENCE_THRESHOLD,
    apply_confidence_hold_gate,
)
from tasks.daily_autoresearch import (
    calculate_daily_ratchet_metrics,
    calculate_hold_session_credit,
    compute_magnitude_postmortem_summary,
)


def test_hold_confidence_threshold_constant():
    assert HOLD_CONFIDENCE_THRESHOLD == 56.0


def test_apply_confidence_hold_gate_converts_low_confidence():
    # Below 56.0% -> HOLD
    pred_dir, exp_ret, rationale = apply_confidence_hold_gate(
        direction="UP",
        confidence=53.0,
        expected_return_pct=0.35,
        rationale="Strong pre-market rally expected.",
    )
    assert pred_dir == "HOLD"
    assert exp_ret == 0.0
    assert "[HOLD - Gated from UP (53.0%)]" in rationale
    assert "Strong pre-market rally expected." in rationale

    # 56.0% or above -> remains original
    pred_dir2, exp_ret2, rationale2 = apply_confidence_hold_gate(
        direction="DOWN",
        confidence=56.0,
        expected_return_pct=-0.45,
        rationale="Bearish yields surge.",
    )
    assert pred_dir2 == "DOWN"
    assert exp_ret2 == -0.45
    assert rationale2 == "Bearish yields surge."


def test_tempered_conviction_scoring_curve():
    # 50.0% -> p_eff = 0.50 -> exactly 0.0 CP
    assert conviction_points(50.0, True) == 0.0
    assert conviction_points(50.0, False) == 0.0

    # 56.0% -> p = 0.56
    # CP win: 100 * ln(2 * 0.56) = 100 * ln(1.12) ~ 11.333
    # CP loss: 100 * ln(2 - 2 * 0.56) = 100 * ln(0.88) ~ -12.783
    cp_win_56 = conviction_points(56.0, True)
    cp_loss_56 = conviction_points(56.0, False)
    assert math.isclose(cp_win_56, 11.333, abs_tol=0.05)
    assert math.isclose(cp_loss_56, -12.783, abs_tol=0.05)

    # 75.0% -> p = 0.75
    # CP win: 100 * ln(1.50) ~ 40.55
    # CP loss: 100 * ln(0.50) ~ -69.31
    cp_win_75 = conviction_points(75.0, True)
    cp_loss_75 = conviction_points(75.0, False)
    assert math.isclose(cp_win_75, 40.55, abs_tol=0.05)
    assert math.isclose(cp_loss_75, -69.31, abs_tol=0.05)


def test_calculate_hold_session_credit_regimes():
    # Flat/chop move (< 0.25%): 52.0 pts
    chop_pred = {"open_price": 500.0, "close_price": 500.5}  # 0.10% move
    assert calculate_hold_session_credit(chop_pred) == 52.0

    # Normal move (0.25% <= move <= 0.75%): 45.0 pts
    normal_pred = {"open_price": 500.0, "close_price": 502.5}  # 0.50% move
    assert calculate_hold_session_credit(normal_pred) == 45.0

    # Missed trend move (> 0.75%): 35.0 pts
    trend_pred = {"open_price": 500.0, "close_price": 506.0}  # 1.20% move
    assert calculate_hold_session_credit(trend_pred) == 35.0


def test_calculate_daily_ratchet_metrics_with_hold_and_participation():
    # 4 correct trades + 1 chop hold (trade rate = 4/5 = 80% >= 75% -> factor 1.0)
    preds = [
        {
            "predicted_direction": "UP",
            "confidence": 75.0,
            "is_correct": True,
            "intraday_hit": True,
            "open_price": 100.0,
            "close_price": 101.0,
            "high_price": 101.5,
            "expected_return_pct": 0.5,
        },
        {
            "predicted_direction": "UP",
            "confidence": 75.0,
            "is_correct": True,
            "intraday_hit": True,
            "open_price": 100.0,
            "close_price": 101.0,
            "high_price": 101.5,
            "expected_return_pct": 0.5,
        },
        {
            "predicted_direction": "UP",
            "confidence": 75.0,
            "is_correct": True,
            "intraday_hit": True,
            "open_price": 100.0,
            "close_price": 101.0,
            "high_price": 101.5,
            "expected_return_pct": 0.5,
        },
        {
            "predicted_direction": "UP",
            "confidence": 75.0,
            "is_correct": True,
            "intraday_hit": True,
            "open_price": 100.0,
            "close_price": 101.0,
            "high_price": 101.5,
            "expected_return_pct": 0.5,
        },
        {
            "predicted_direction": "HOLD",
            "confidence": 53.0,
            "is_correct": None,
            "intraday_hit": None,
            "open_price": 100.0,
            "close_price": 100.1,
        },
    ]
    metrics = calculate_daily_ratchet_metrics(preds)
    assert metrics["traded_count"] == 4
    assert metrics["hold_count"] == 1
    assert metrics["trade_rate_pct"] == 80.0
    assert metrics["participation_factor"] == 1.0
    assert metrics["score"] > 80.0

    # 1 correct trade + 4 normal holds (trade rate = 1/5 = 20% < 75% -> factor = 0.20 / 0.75)
    cowardly_preds = [
        {
            "predicted_direction": "UP",
            "confidence": 75.0,
            "is_correct": True,
            "intraday_hit": True,
            "open_price": 100.0,
            "close_price": 101.0,
            "high_price": 101.5,
            "expected_return_pct": 0.5,
        },
        {
            "predicted_direction": "HOLD",
            "confidence": 53.0,
            "is_correct": None,
            "intraday_hit": None,
            "open_price": 100.0,
            "close_price": 100.4,
        },
        {
            "predicted_direction": "HOLD",
            "confidence": 53.0,
            "is_correct": None,
            "intraday_hit": None,
            "open_price": 100.0,
            "close_price": 100.4,
        },
        {
            "predicted_direction": "HOLD",
            "confidence": 53.0,
            "is_correct": None,
            "intraday_hit": None,
            "open_price": 100.0,
            "close_price": 100.4,
        },
        {
            "predicted_direction": "HOLD",
            "confidence": 53.0,
            "is_correct": None,
            "intraday_hit": None,
            "open_price": 100.0,
            "close_price": 100.4,
        },
    ]
    cowardly_metrics = calculate_daily_ratchet_metrics(cowardly_preds)
    assert cowardly_metrics["traded_count"] == 1
    assert cowardly_metrics["hold_count"] == 4
    assert cowardly_metrics["trade_rate_pct"] == 20.0
    assert math.isclose(cowardly_metrics["participation_factor"], 0.20 / 0.75, abs_tol=0.001)
    assert cowardly_metrics["score"] < 20.0


def test_postmortem_summary_includes_conf_and_conviction_columns():
    preds = [
        {
            "target_date": "2026-11-09",
            "predicted_direction": "HOLD",
            "confidence": 53.0,
            "expected_return_pct": 0.0,
            "open_price": 500.0,
            "close_price": 500.8,
            "high_price": 501.0,
            "low_price": 499.5,
            "is_correct": None,
            "intraday_hit": None,
            "brier_score": None,
            "conviction_score": 0.0,
        }
    ]
    summary = compute_magnitude_postmortem_summary(preds)
    assert "Conf %" in summary
    assert "Conv CP" in summary
    assert "HOLD" in summary
