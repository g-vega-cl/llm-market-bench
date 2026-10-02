"""Unit tests for the isolated Laya dataset distillation pipeline.

Verifies schema compliance with Laya typed decisions, zero lookahead leakage
in chronological splitting, and fallback context reconstruction.
"""

import pytest
from export_dataset import (
    chronological_split,
    format_laya_record,
    reconstruct_context,
)


def test_format_laya_record_valid():
    context = "Pre-market report: SPY gaps up +0.45% on strong earnings."
    record = format_laya_record(
        context=context,
        target_date="2026-09-25",
        actual_direction="UP",
        ticker="SPY",
    )

    assert record is not None
    assert record["state"] == context
    assert "direction" in record["questions"]
    assert record["questions"]["direction"]["type"] == "choice"
    assert "UP" in record["questions"]["direction"]["options"]
    assert "DOWN" in record["questions"]["direction"]["options"]
    assert record["gold"]["direction"]["choice"] == "UP"
    assert record["metadata"]["target_date"] == "2026-09-25"
    assert record["metadata"]["ticker"] == "SPY"


def test_format_laya_record_down():
    context = "Pre-market report: Yields surge, futures down -0.80%."
    record = format_laya_record(
        context=context,
        target_date="2026-09-26",
        actual_direction="DOWN",
        ticker="SPY",
    )

    assert record["gold"]["direction"]["choice"] == "DOWN"


def test_format_laya_record_invalid_direction():
    with pytest.raises(ValueError, match="Invalid actual_direction"):
        format_laya_record(
            context="Some context",
            target_date="2026-09-25",
            actual_direction="FLAT",
        )


def test_chronological_split_zero_leakage():
    sample_records = [
        {"metadata": {"target_date": "2026-09-10"}},
        {"metadata": {"target_date": "2026-09-01"}},
        {"metadata": {"target_date": "2026-09-15"}},
        {"metadata": {"target_date": "2026-09-20"}},
        {"metadata": {"target_date": "2026-09-05"}},
    ]

    train, val = chronological_split(sample_records, val_ratio=0.4)

    assert len(train) == 3
    assert len(val) == 2

    train_dates = [r["metadata"]["target_date"] for r in train]
    val_dates = [r["metadata"]["target_date"] for r in val]

    assert train_dates == ["2026-09-01", "2026-09-05", "2026-09-10"]
    assert val_dates == ["2026-09-15", "2026-09-20"]
    assert max(train_dates) < min(val_dates)


def test_reconstruct_context_direct():
    pred_row = {
        "target_date": "2026-09-25",
        "market_context": "Direct full market context already stored.",
    }
    ctx = reconstruct_context(pred_row, newsletter_map={})
    assert ctx == "Direct full market context already stored."


def test_reconstruct_context_fallback_newsletter():
    pred_row = {
        "target_date": "2026-08-15",
        "market_context": None,
    }
    newsletter_map = {
        "2026-08-15": "Synthesized morning briefing: Market flat ahead of CPI.",
    }
    ctx = reconstruct_context(pred_row, newsletter_map=newsletter_map)
    assert ctx is not None
    assert "Morning Newsletter Briefing (2026-08-15):" in ctx
    assert "Synthesized morning briefing: Market flat ahead of CPI." in ctx


def test_reconstruct_context_missing():
    pred_row = {
        "target_date": "2026-07-01",
        "market_context": None,
    }
    ctx = reconstruct_context(pred_row, newsletter_map={})
    assert ctx is None


def test_compute_calibrated_probability_default():
    from evaluate import compute_calibrated_probability

    # Equal logits should produce exactly 0.5 probability
    prob = compute_calibrated_probability(logit_down=2.0, logit_up=2.0)
    assert abs(prob - 0.5) < 1e-5

    # Positive delta produces > 0.5
    prob_up = compute_calibrated_probability(logit_down=0.0, logit_up=2.0)
    assert prob_up > 0.5


def test_compute_calibrated_probability_platt():
    from evaluate import compute_calibrated_probability

    cfg = {
        "method": "platt_scaling",
        "platt_w": 0.5,
        "platt_b": -0.2,
    }
    # delta = 2.0. scaled = 0.5 * 2.0 - 0.2 = 0.8. sigmoid(0.8) ~= 0.68997
    prob = compute_calibrated_probability(logit_down=0.0, logit_up=2.0, calibration_cfg=cfg)
    assert 0.68 < prob < 0.70

    # With negative bias, delta = 0 produces < 0.5 (DOWN bias)
    prob_zero = compute_calibrated_probability(logit_down=1.0, logit_up=1.0, calibration_cfg=cfg)
    assert prob_zero < 0.5


def test_compute_calibrated_probability_temperature():
    from evaluate import compute_calibrated_probability

    cfg = {"fitted_temperature": 2.0}
    # raw delta = 2.0, scaled delta = 1.0, sigmoid(1.0) ~= 0.731
    prob = compute_calibrated_probability(logit_down=0.0, logit_up=2.0, calibration_cfg=cfg)
    assert 0.72 < prob < 0.74

