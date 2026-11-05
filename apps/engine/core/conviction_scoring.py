"""Conviction-based confidence scoring for prediction surfaces.

This module is the single source of truth for how self-reported model confidence
is scored. It replaces the ``- mean_brier * 50`` penalty that previously made
confidence worth at most ~12 points on a 0-100 composite.

Brier remains stored as a diagnostic. It is deliberately *not* replaced inside
``apps/engine/local_autoresearch`` because that loop imports
``calculate_brier_score`` directly for champion training.

The score is the logarithmic scoring rule recentred so that a coin flip is
worth exactly zero:

    CP(p, correct) = 100 * ln(2p)
    CP(p, wrong)   = 100 * ln(2 - 2p)
    CP(p <= 0.5, *) = 0

It is strictly proper: the expected score is maximised by reporting the true
probability. That property is what makes the metric ungameable -- a naive
"reward generously when right, punish heavily when wrong" score collapses to
"always claim 100%", because only the confidence term survives the expectation.
"""

from __future__ import annotations

import math
from typing import Any

# A directional model predicting the wrong side at 40% confidence is internally
# inconsistent, so it is scored as neutral rather than rewarded.
CONFIDENCE_FLOOR = 50.0

# Guard against ln(0) = -inf. 99% is the most conviction a model may claim.
CONFIDENCE_CEILING = 99.0

# The "high conviction" bucket used by the tail calibration diagnostic.
TAIL_CONFIDENCE_THRESHOLD = 90.0

# Pseudo-count for Bayesian shrinkage of small samples toward neutral.
SHRINKAGE_K = 10.0

# CP magnitude that maps to ~76 on the 0-100 normalised scale.
NORM_SCALE = 50.0

_NEUTRAL_BUNDLE: dict[str, Any] = {
    "mean_cp": 0.0,
    "conviction_norm": 50.0,
    "rank_score": 0.0,
    "tail_gap": None,
    "n": 0,
    "n_tail": 0,
    "confident_wrong_count": 0,
    "max_single_loss": 0.0,
}


def clamp_confidence(confidence: float | None) -> float:
    """Clamp a 0-100 confidence into the scorable band."""
    if confidence is None:
        return CONFIDENCE_FLOOR
    try:
        value = float(confidence)
    except (TypeError, ValueError):
        return CONFIDENCE_FLOOR
    if math.isnan(value) or math.isinf(value):
        return CONFIDENCE_FLOOR
    return min(max(value, CONFIDENCE_FLOOR), CONFIDENCE_CEILING)


def conviction_points(confidence: float | None, correct: bool) -> float:
    """Score a single prediction on the conviction scale.

    Positive when correct, negative when wrong, exactly zero at a coin flip.
    The penalty at any given confidence always exceeds the reward, and the
    ratio grows with confidence (1.1x at 55%, 3.6x at 95%).
    """
    p = clamp_confidence(confidence) / 100.0
    if correct:
        return 100.0 * math.log(2.0 * p)
    return 100.0 * math.log(2.0 - 2.0 * p)


def _evaluated_records(records: list[dict[str, Any]] | None) -> list[tuple[float, bool]]:
    """Extract (confidence, correct) pairs, skipping unevaluated rows."""
    pairs: list[tuple[float, bool]] = []
    for record in records or []:
        outcome = record.get("is_correct")
        if outcome is None:
            continue
        confidence = record.get("confidence")
        if confidence is None:
            continue
        pairs.append((confidence, bool(outcome)))
    return pairs


def mean_conviction_points(records: list[dict[str, Any]] | None) -> float:
    """Average conviction points across evaluated predictions."""
    points = [conviction_points(c, ok) for c, ok in _evaluated_records(records)]
    if not points:
        return 0.0
    return sum(points) / len(points)


def conviction_normalized(mean_cp: float) -> float:
    """Map mean conviction points onto a 0-100 composite term centred at 50."""
    return round(50.0 + 50.0 * math.tanh(mean_cp / NORM_SCALE), 4)


def shrunk_rank_score(mean_cp: float, n: int) -> float:
    """Discount a conviction score by sample size so luck cannot rank first.

    ``n / (n + SHRINKAGE_K)`` gives 50% credit at 10 calls and 91% at 100.
    """
    if n <= 0:
        return 0.0
    return round(mean_cp * n / (n + SHRINKAGE_K), 4)


def tail_gap(records: list[dict[str, Any]] | None) -> float | None:
    """Return claimed-minus-realised hit rate inside the high-conviction tail.

    Zero means calibrated. Positive means overconfident. ``None`` when no
    prediction cleared ``TAIL_CONFIDENCE_THRESHOLD``.
    """
    tail = [(c, ok) for c, ok in _evaluated_records(records) if clamp_confidence(c) >= TAIL_CONFIDENCE_THRESHOLD]
    if not tail:
        return None

    claimed = sum(clamp_confidence(c) for c, _ in tail) / len(tail) / 100.0
    realised = sum(1 for _, ok in tail if ok) / len(tail)
    return round(claimed - realised, 6)


def conviction_bundle(records: list[dict[str, Any]] | None) -> dict[str, Any]:
    """Compute the full conviction diagnostic bundle for a set of predictions."""
    pairs = _evaluated_records(records)
    if not pairs:
        return dict(_NEUTRAL_BUNDLE)

    points = [conviction_points(c, ok) for c, ok in pairs]
    tail = [(c, ok) for c, ok in pairs if clamp_confidence(c) >= TAIL_CONFIDENCE_THRESHOLD]
    mean_cp = sum(points) / len(points)

    return {
        "mean_cp": round(mean_cp, 4),
        "conviction_norm": conviction_normalized(mean_cp),
        "rank_score": shrunk_rank_score(mean_cp, len(points)),
        "tail_gap": tail_gap(records),
        "n": len(points),
        "n_tail": len(tail),
        "confident_wrong_count": sum(1 for _, ok in tail if not ok),
        "max_single_loss": round(min(points), 4),
    }
