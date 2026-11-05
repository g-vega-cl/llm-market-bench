"""Tests for the shared conviction backfill and baseline-realignment helpers."""

from __future__ import annotations

import pytest

from core.conviction_backfill import (
    match_predictions_by_tag,
    propose_track_realignment,
    recompute_daily_conviction,
    recompute_experiment_metrics,
    recompute_sector_conviction,
)


def test_recompute_daily_conviction_uses_the_log_score():
    rows = [
        {"id": "a", "confidence": 80.0, "is_correct": True},
        {"id": "b", "confidence": 70.0, "is_correct": False},
        {"id": "c", "confidence": None, "is_correct": True},
        {"id": "d", "confidence": 60.0, "is_correct": None},
    ]

    updates = dict(recompute_daily_conviction(rows))

    assert updates["a"] == pytest.approx(47.0002, abs=1e-3)
    assert updates["b"] == pytest.approx(-51.0832, abs=1e-3)
    assert "c" not in updates
    assert "d" not in updates


def test_recompute_sector_conviction_prices_the_worst_leg_separately():
    rows = [
        {
            "id": "both",
            "confidence": 90.0,
            "sector_percentile_score": 100.0,
            "worst_confidence": 60.0,
            "worst_sector_percentile_score": 90.0,
        },
        {
            "id": "best-only",
            "confidence": 90.0,
            "sector_percentile_score": 100.0,
            "worst_confidence": None,
            "worst_sector_percentile_score": 10.0,
        },
    ]

    updates = dict(recompute_sector_conviction(rows))

    # Best leg correct at 90% = 58.78; worst leg correct at 60% = 18.23 -> mean 38.51
    assert updates["both"] == pytest.approx(38.5056, abs=1e-3)
    # Legacy row must not borrow the best-pick probability for the worst leg.
    assert updates["best-only"] == pytest.approx(58.7789, abs=1e-3)


def test_match_predictions_excludes_backtests_and_falls_back_to_window():
    experiments = [
        {"variant_tag": "tagged", "track_id": "model-a", "week_start": "2026-10-01", "week_end": "2026-10-05"},
        {"variant_tag": "untagged", "track_id": "model-a", "week_start": "2026-10-01", "week_end": "2026-10-05"},
        {"variant_tag": "empty", "track_id": "model-a", "week_start": "2026-12-01", "week_end": "2026-12-05"},
    ]
    predictions = [
        {"id": "1", "model_name": "model-a", "prompt_variant_tag": "tagged", "target_date": "2026-10-01"},
        {"id": "2", "model_name": "model-a", "prompt_variant_tag": "tagged-backtest-x", "target_date": "2026-10-02"},
        {"id": "3", "model_name": "model-a", "prompt_variant_tag": None, "target_date": "2026-10-03"},
        {"id": "4", "model_name": "model-b", "prompt_variant_tag": None, "target_date": "2026-10-03"},
    ]

    matched = match_predictions_by_tag(experiments, predictions, "prompt_variant_tag", "target_date")

    assert [p["id"] for p in matched["tagged"]] == ["1"]
    # No tagged rows -> window fallback, scoped to the track and excluding backtests.
    assert [p["id"] for p in matched["untagged"]] == ["1", "3"]
    assert matched["empty"] == []


def test_window_fallback_pools_models_for_shared_default_track():
    experiments = [
        {"variant_tag": "legacy", "track_id": "track_default", "week_start": "2026-10-01", "week_end": "2026-10-05"}
    ]
    predictions = [
        {"id": "1", "model_name": "model-a", "prompt_variant_tag": None, "target_date": "2026-10-02"},
        {"id": "2", "model_name": "model-b", "prompt_variant_tag": None, "target_date": "2026-10-03"},
    ]

    matched = match_predictions_by_tag(experiments, predictions, "prompt_variant_tag", "target_date")

    assert [p["id"] for p in matched["legacy"]] == ["1", "2"]


def test_recompute_experiment_metrics_skips_backtest_experiments():
    experiments = [
        {
            "id": "1",
            "variant_tag": "daily-a",
            "status": "baseline",
            "metrics": {"score": 62.375},
        },
        {
            "id": "2",
            "variant_tag": "daily-pred-backtest-x",
            "status": "saved",
            "is_backtest": True,
            "metrics": {"score": 70.0},
        },
    ]
    predictions = [
        {
            "id": "d1",
            "prompt_variant_tag": "daily-a",
            "target_date": "2026-10-01",
            "model_name": "model-a",
        }
    ]

    report = recompute_experiment_metrics(
        experiments,
        predictions,
        "prompt_variant_tag",
        lambda rows: {"score": 1.0, "predictions_evaluated": len(rows)},
    )

    assert len(report) == 1
    assert report[0]["variant_tag"] == "daily-a"
    assert report[0]["prediction_count"] == 1


def _item(tag: str, track: str, status: str, score: float | None, n: int | None) -> dict:
    metrics = None if score is None else {"score": score, "predictions_evaluated": n}
    return {
        "id": f"id-{tag}",
        "variant_tag": tag,
        "track_id": track,
        "status": status,
        "new_metrics": metrics,
        "prediction_count": n or 0,
        "created_at": "2026-10-01T00:00:00Z",
    }


def test_proposal_realigns_each_track_independently():
    report = [
        _item("a-old-baseline", "track-a", "baseline", 55.0, 10),
        _item("a-best", "track-a", "discarded", 70.0, 10),
        _item("a-active", "track-a", "active", None, None),
        _item("b-old-baseline", "track-b", "baseline", 60.0, 10),
        _item("b-ok", "track-b", "discarded", 40.0, 10),
        _item("b-active", "track-b", "active", None, None),
    ]

    proposals = {p["variant_tag"]: p for p in propose_track_realignment(report)}

    assert proposals["a-best"]["status"] == "baseline"
    assert proposals["a-old-baseline"]["status"] == "saved"
    assert proposals["a-active"]["parent_tag"] == "a-best"
    # Track B keeps its own winner: A's stronger prompt must not leak across tracks.
    assert proposals["b-old-baseline"]["status"] == "baseline"
    assert proposals["b-ok"]["status"] is None
    assert proposals["b-active"]["parent_tag"] == "b-old-baseline"


def test_proposal_ignores_single_sample_flukes():
    report = [
        _item("lucky", "track-a", "discarded", 99.0, 1),
        _item("solid", "track-a", "discarded", 60.0, 10),
        _item("active", "track-a", "active", None, None),
    ]

    proposals = {p["variant_tag"]: p for p in propose_track_realignment(report)}

    assert proposals["solid"]["status"] == "baseline"
    assert proposals["lucky"]["status"] is None


def test_proposal_keeps_status_when_no_credible_candidate_exists():
    report = [
        _item("lucky", "track-a", "discarded", 99.0, 1),
        _item("active", "track-a", "active", None, None),
    ]

    proposals = {p["variant_tag"]: p for p in propose_track_realignment(report)}

    assert proposals["lucky"]["status"] is None
    assert proposals["active"]["parent_tag"] is None


def test_proposal_carries_recomputed_metrics_for_writing():
    report = [_item("solid", "track-a", "discarded", 60.0, 10), _item("active", "track-a", "active", None, None)]

    proposals = {p["variant_tag"]: p for p in propose_track_realignment(report)}

    assert proposals["solid"]["metrics"] == {"score": 60.0, "predictions_evaluated": 10}
    assert proposals["active"]["metrics"] is None
