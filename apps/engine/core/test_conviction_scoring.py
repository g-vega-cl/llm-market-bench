"""Tests for conviction-based confidence scoring.

The contract under test:

    CP(p, outcome) = +100 * ln(2p)     when correct
                   = +100 * ln(2 - 2p) when incorrect
                   = 0                 for p <= 50% (coin flip)

This is the logarithmic scoring rule recentred so that a coin flip scores zero.
It is strictly proper, so the expected score is maximised by reporting the true
probability. That property is what stops the metric from rewarding either
reckless overconfidence or coy hedging.
"""

import math

import pytest

from core.conviction_scoring import (
    CONFIDENCE_CEILING,
    CONFIDENCE_FLOOR,
    TAIL_CONFIDENCE_THRESHOLD,
    clamp_confidence,
    conviction_bundle,
    conviction_normalized,
    conviction_points,
    mean_conviction_points,
    select_baseline_candidate,
    shrunk_baseline_score,
    shrunk_rank_score,
    tail_gap,
)


def _records(confidence: float, correct_count: int, wrong_count: int) -> list[dict]:
    """Build a synthetic evaluated-prediction record set."""
    return [{"confidence": confidence, "is_correct": True} for _ in range(correct_count)] + [
        {"confidence": confidence, "is_correct": False} for _ in range(wrong_count)
    ]


class TestConvictionPoints:
    def test_coin_flip_scores_zero_when_correct(self):
        assert conviction_points(50.0, True) == pytest.approx(0.0, abs=1e-9)

    def test_coin_flip_scores_zero_when_wrong(self):
        assert conviction_points(50.0, False) == pytest.approx(0.0, abs=1e-9)

    def test_correct_high_confidence_is_rewarded(self):
        # 100 * ln(1.9)
        assert conviction_points(95.0, True) == pytest.approx(64.1854, abs=1e-4)

    def test_wrong_high_confidence_is_punished_hard(self):
        # 100 * ln(0.1)
        assert conviction_points(95.0, False) == pytest.approx(-230.2585, abs=1e-4)

    def test_mild_confidence_moves_the_needle_less(self):
        assert conviction_points(55.0, True) == pytest.approx(9.5310, abs=1e-4)
        assert conviction_points(55.0, False) == pytest.approx(-10.5361, abs=1e-4)

    def test_penalty_always_exceeds_reward_at_equal_confidence(self):
        for confidence in (55.0, 60.0, 70.0, 80.0, 90.0, 95.0, 99.0):
            reward = conviction_points(confidence, True)
            penalty = conviction_points(confidence, False)
            assert reward > 0
            assert penalty < 0
            assert abs(penalty) > reward, f"penalty must dominate at {confidence}%"

    def test_below_fifty_is_clamped_to_neutral(self):
        # An internally inconsistent call (predicts UP at 30% confidence) earns nothing.
        assert conviction_points(30.0, True) == pytest.approx(0.0, abs=1e-9)
        assert conviction_points(0.0, False) == pytest.approx(0.0, abs=1e-9)

    def test_ceiling_prevents_infinite_penalty(self):
        assert clamp_confidence(100.0) == CONFIDENCE_CEILING
        assert conviction_points(100.0, False) == pytest.approx(conviction_points(CONFIDENCE_CEILING, False))
        assert math.isfinite(conviction_points(100.0, False))

    def test_floor_is_fifty(self):
        assert CONFIDENCE_FLOOR == 50.0
        assert clamp_confidence(-10.0) == CONFIDENCE_FLOOR


class TestProperness:
    """The central regression: honesty must dominate both coyness and bravado."""

    # 200 calls, true edge 60% => 120 correct, 80 wrong.
    CORRECT = 120
    WRONG = 80

    def test_honest_model_beats_reckless_model(self):
        honest = mean_conviction_points(_records(60.0, self.CORRECT, self.WRONG))
        reckless = mean_conviction_points(_records(95.0, self.CORRECT, self.WRONG))

        assert honest > 0
        assert reckless < 0
        assert honest > reckless

    def test_honest_model_beats_coy_model(self):
        honest = mean_conviction_points(_records(60.0, self.CORRECT, self.WRONG))
        coy = mean_conviction_points(_records(55.0, self.CORRECT, self.WRONG))

        assert honest > coy

    def test_expected_score_is_maximised_at_true_probability(self):
        """Sweep reported confidence and confirm the peak sits on the truth (60%)."""
        true_probability = 0.60
        best_confidence = None
        best_expected = -math.inf

        for reported in range(50, 100):
            expected = true_probability * conviction_points(reported, True) + (
                1 - true_probability
            ) * conviction_points(reported, False)
            if expected > best_expected:
                best_expected = expected
                best_confidence = reported

        assert best_confidence == 60


class TestAggregation:
    def test_empty_records_are_neutral(self):
        bundle = conviction_bundle([])

        assert bundle["n"] == 0
        assert bundle["mean_cp"] == 0.0
        assert bundle["conviction_norm"] == 50.0
        assert bundle["rank_score"] == 0.0
        assert bundle["tail_gap"] is None
        assert bundle["max_single_loss"] == 0.0

    def test_unevaluated_records_are_skipped(self):
        records = [
            {"confidence": 90.0, "is_correct": None},
            {"confidence": None, "is_correct": True},
            {"confidence": 60.0, "is_correct": True},
        ]
        bundle = conviction_bundle(records)

        assert bundle["n"] == 1
        assert bundle["mean_cp"] == pytest.approx(18.2322, abs=1e-3)

    def test_tail_counts_and_worst_loss(self):
        records = _records(95.0, 1, 3)
        bundle = conviction_bundle(records)

        assert bundle["n"] == 4
        assert bundle["n_tail"] == 4
        assert bundle["confident_wrong_count"] == 3
        assert bundle["max_single_loss"] == pytest.approx(-230.2585, abs=1e-3)


class TestNormalization:
    def test_coin_flip_maps_to_fifty(self):
        assert conviction_normalized(0.0) == pytest.approx(50.0)

    def test_positive_and_negative_are_symmetric_around_fifty(self):
        assert conviction_normalized(25.0) + conviction_normalized(-25.0) == pytest.approx(100.0)

    def test_bounds_are_respected(self):
        assert conviction_normalized(10_000.0) <= 100.0
        assert conviction_normalized(-10_000.0) >= 0.0
        assert 50.0 < conviction_normalized(100.0) < 100.0
        assert 0.0 < conviction_normalized(-100.0) < 50.0

    def test_honest_sixty_lands_above_neutral(self):
        norm = conviction_normalized(2.0136)
        assert norm > 50.0
        assert norm < 55.0


class TestShrinkage:
    def test_small_samples_are_discounted(self):
        full = shrunk_rank_score(10.0, n=1000)
        small = shrunk_rank_score(10.0, n=10)

        assert small < full
        assert small == pytest.approx(5.0, abs=1e-9)
        assert full == pytest.approx(9.90099, abs=1e-4)

    def test_zero_samples_score_zero(self):
        assert shrunk_rank_score(25.0, n=0) == 0.0

    def test_negative_scores_shrink_toward_zero(self):
        # Shrinkage must never make an underperformer look better than the raw score
        # in absolute terms; it pulls toward neutral zero.
        assert shrunk_rank_score(-50.0, n=10) == pytest.approx(-25.0, abs=1e-9)


class TestTailGap:
    def test_calibrated_tail_has_no_gap(self):
        # 95% confidence, 95% of 20 calls correct => 19/20 = 0.95
        records = _records(95.0, 19, 1)
        assert tail_gap(records) == pytest.approx(0.95 - 0.95, abs=1e-9)

    def test_overconfident_tail_has_positive_gap(self):
        # Claims 95%, delivers 50% => gap +0.45
        records = _records(95.0, 5, 5)
        assert tail_gap(records) == pytest.approx(0.45, abs=1e-9)

    def test_undershooting_tail_has_negative_gap(self):
        records = _records(90.0, 10, 0)
        assert tail_gap(records) == pytest.approx(0.90 - 1.00, abs=1e-9)

    def test_no_tail_records_returns_none(self):
        assert tail_gap(_records(85.0, 3, 1)) is None
        assert tail_gap([]) is None

    def test_threshold_boundary_is_inclusive(self):
        assert TAIL_CONFIDENCE_THRESHOLD == 90.0
        records = [
            {"confidence": 90.0, "is_correct": True},
            {"confidence": 90.0, "is_correct": False},
            {"confidence": 89.9, "is_correct": False},
        ]
        # Both 90.0% calls are in the tail (claimed 0.90, realised 0.50 => +0.40).
        # The 89.9% call must be excluded from both the claim and the hit rate.
        assert tail_gap(records) == pytest.approx(0.40, abs=1e-9)


class TestBaselineSelection:
    """A tiny fluke sample must not become an unreachable ratchet ceiling."""

    def test_single_lucky_call_cannot_set_the_baseline(self):
        variants = [
            {"variant_tag": "active", "metrics": {"score": 40.0, "predictions_evaluated": 20}},
            {"variant_tag": "lucky", "metrics": {"score": 98.7, "predictions_evaluated": 1}},
            {"variant_tag": "solid", "metrics": {"score": 62.0, "predictions_evaluated": 8}},
        ]

        best = select_baseline_candidate(variants, exclude_tag="active")

        assert best is not None
        assert best[1]["variant_tag"] == "solid"
        # 62 shrunk by 8/(8+10) toward the neutral 50 prior.
        assert best[0] == pytest.approx(55.333, abs=1e-3)

    def test_active_variant_is_excluded(self):
        variants = [{"variant_tag": "active", "metrics": {"score": 90.0, "predictions_evaluated": 10}}]
        assert select_baseline_candidate(variants, exclude_tag="active") is None

    def test_missing_sample_count_shrinks_to_neutral(self):
        # An unknown sample size is no evidence, so it cannot pin the ratchet.
        variants = [{"variant_tag": "legacy", "metrics": {"score": 55.0}}]
        best = select_baseline_candidate(variants, exclude_tag="active")
        assert best is not None and best[0] == 50.0

    def test_no_credible_candidate_means_no_ceiling(self):
        variants = [
            {"variant_tag": "a", "metrics": {"score": 99.0, "predictions_evaluated": 1}},
            {"variant_tag": "b", "metrics": {"score": 97.0, "predictions_evaluated": 2}},
        ]
        assert select_baseline_candidate(variants, exclude_tag="active") is None

    def test_shrinkage_keeps_small_samples_below_large_ones(self):
        small = shrunk_baseline_score(80.0, n=5)
        large = shrunk_baseline_score(80.0, n=40)

        assert small < large < 80.0
        assert small == pytest.approx(60.0, abs=1e-9)
        assert shrunk_baseline_score(80.0, n=0) == 50.0
