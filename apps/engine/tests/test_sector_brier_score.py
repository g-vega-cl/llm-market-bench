import pytest

from tasks.evaluate_predictions import calculate_sector_brier_score
from tasks.predictor_autoresearch import calculate_baseline_score
from tasks.sector_predictor import SectorPredictionResponse


def test_calculate_sector_brier_score_success():
    """Verify Brier score calculation when prediction outperforms median sector."""
    # Confidence 80% (p = 0.8), percentile >= 50 (y = 1.0) -> (0.8 - 1.0)^2 = 0.04
    score = calculate_sector_brier_score(confidence=80.0, sector_percentile_score=100.0)
    assert score == pytest.approx(0.04)


def test_calculate_sector_brier_score_failure():
    """Verify Brier score calculation when prediction underperforms median sector."""
    # Confidence 80% (p = 0.8), percentile < 50 (y = 0.0) -> (0.8 - 0.0)^2 = 0.64
    score = calculate_sector_brier_score(confidence=80.0, sector_percentile_score=30.0)
    assert score == pytest.approx(0.64)


def test_calculate_sector_brier_score_legacy_fallback():
    """Verify fallback behavior when confidence is None."""
    # Confidence None (default p = 0.5), percentile >= 50 (y = 1.0) -> (0.5 - 1.0)^2 = 0.25
    score = calculate_sector_brier_score(confidence=None, sector_percentile_score=75.0)
    assert score == pytest.approx(0.25)


def test_calculate_sector_brier_score_with_worst_sector_both_success():
    """Verify Brier score calculation when both best and worst sector calls succeed."""
    # p = 0.8, y_best = 1.0 (100% >= 50), y_worst = 1.0 (90% >= 50)
    # BS_best = (0.8 - 1.0)^2 = 0.04
    # BS_worst = (0.8 - 1.0)^2 = 0.04
    # BS_composite = (0.04 + 0.04) / 2 = 0.04
    score = calculate_sector_brier_score(
        confidence=80.0,
        sector_percentile_score=100.0,
        worst_sector_percentile_score=90.0,
    )
    assert score == pytest.approx(0.04)


def test_calculate_sector_brier_score_with_worst_sector_mixed():
    """Verify Brier score calculation when best succeeds but worst sector fails."""
    # p = 0.8, y_best = 1.0 (100% >= 50), y_worst = 0.0 (30% < 50)
    # BS_best = (0.8 - 1.0)^2 = 0.04
    # BS_worst = (0.8 - 0.0)^2 = 0.64
    # BS_composite = (0.04 + 0.64) / 2 = 0.34
    score = calculate_sector_brier_score(
        confidence=80.0,
        sector_percentile_score=100.0,
        worst_sector_percentile_score=30.0,
    )
    assert score == pytest.approx(0.34)


def test_calculate_sector_brier_score_with_worst_sector_both_failed():
    """Verify Brier score calculation when both best and worst sector calls fail."""
    # p = 0.8, y_best = 0.0 (20% < 50), y_worst = 0.0 (10% < 50)
    # BS_best = (0.8 - 0.0)^2 = 0.64
    # BS_worst = (0.8 - 0.0)^2 = 0.64
    # BS_composite = 0.64
    score = calculate_sector_brier_score(
        confidence=80.0,
        sector_percentile_score=20.0,
        worst_sector_percentile_score=10.0,
    )
    assert score == pytest.approx(0.64)


def test_calculate_baseline_score_with_brier_penalty():
    """Verify sector predictor autoresearch baseline score includes mean Brier penalty."""
    predictions = [
        {"sector_percentile_score": 100.0, "pair_percentile_score": 100.0, "brier_score": 0.04},
        {"sector_percentile_score": 80.0, "pair_percentile_score": 80.0, "brier_score": 0.04},
    ]
    # Avg percentile = (100 + 80) / 2 = 90.0
    # Mean Brier = 0.04 -> penalty = 0.04 * 50.0 = 2.0
    # Baseline ratchet score = 90.0 - 2.0 = 88.0
    score = calculate_baseline_score(predictions)
    assert score == pytest.approx(88.0)


def test_sector_prediction_response_schema():
    """Verify SectorPredictionResponse model requires confidence field."""
    payload = {
        "predicted_sector": "XLK",
        "predicted_pair": ["XLK", "XLU"],
        "confidence": 85.0,
        "reasoning": "Strong tech momentum with utility hedge.",
    }
    resp = SectorPredictionResponse(**payload)
    assert resp.predicted_sector == "XLK"
    assert resp.confidence == 85.0
