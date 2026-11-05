"""Tests for the conviction score backfill utility."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "backfill_conviction_scores.py"
_spec = importlib.util.spec_from_file_location("backfill_conviction_scores", _SCRIPT)
backfill = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(backfill)


class _Query:
    def __init__(self, rows: list[dict], updates: list[tuple[str, dict]], table: str, payload=None):
        self._rows = rows
        self._updates = updates
        self._table = table
        self._payload = payload

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def in_(self, *args, **kwargs):
        return self

    def update(self, payload):
        self._updates.append((self._table, payload))
        return self

    def execute(self):
        return SimpleNamespace(data=self._rows)


class FakeClient:
    def __init__(self, tables: dict[str, list[dict]]):
        self._tables = tables
        self.updates: list[tuple[str, dict]] = []

    def table(self, name: str):
        return _Query(self._tables.get(name, []), self.updates, name)


def _metrics_table():
    return {
        "daily_predictions": [
            {
                "id": "d1",
                "status": "evaluated",
                "confidence": 80.0,
                "is_correct": True,
                "prompt_variant_tag": "daily-a",
                "target_date": "2026-10-01",
                "predicted_direction": "UP",
                "expected_return_pct": 0.0,
                "open_price": 500.0,
                "high_price": 500.0,
                "low_price": 500.0,
                "close_price": 500.0,
                "intraday_hit": True,
                "brier_score": 0.04,
            }
        ],
        "earnings_predictions": [{"id": "e1", "status": "evaluated", "confidence": 70.0, "is_correct": False}],
        "sector_predictions": [
            {
                "id": "s1",
                "status": "evaluated",
                "confidence": 90.0,
                "sector_percentile_score": 90.0,
                "prompt_tag": "sector-a",
                "target_date": "2026-10-01",
            }
        ],
        "prompt_experiments": [
            {
                "id": "exp-daily",
                "prompt_name": "DAILY_PREDICTOR_PROMPT",
                "variant_tag": "daily-a",
                "track_id": "model-a",
                "status": "baseline",
                "metrics": {"score": 62.375},
            },
            {
                "id": "exp-sector",
                "prompt_name": "SECTOR_PREDICTOR_PROMPT",
                "variant_tag": "sector-a",
                "track_id": "model-a",
                "status": "baseline",
                "metrics": {"score": 70.0},
            },
        ],
    }


def test_recompute_daily_conviction_uses_the_log_score():
    rows = [
        {"id": "a", "confidence": 80.0, "is_correct": True},
        {"id": "b", "confidence": 70.0, "is_correct": False},
        {"id": "c", "confidence": None, "is_correct": True},
        {"id": "d", "confidence": 60.0, "is_correct": None},
    ]

    updates = dict(backfill.recompute_daily_conviction(rows))

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

    updates = dict(backfill.recompute_sector_conviction(rows))

    # Best leg correct at 90% = 58.78; worst leg correct at 60% = 18.23 -> mean 38.50
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

    matched = backfill.match_predictions_by_tag(experiments, predictions, "prompt_variant_tag", "target_date")

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

    matched = backfill.match_predictions_by_tag(experiments, predictions, "prompt_variant_tag", "target_date")

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

    report = backfill.recompute_experiment_metrics(
        experiments,
        _metrics_table()["daily_predictions"],
        "prompt_variant_tag",
        lambda rows: {
            "score": 1.0,
            "predictions_evaluated": len(rows),
        },
    )

    assert len(report) == 1
    assert report[0]["variant_tag"] == "daily-a"
    assert report[0]["prediction_count"] == 1


def test_dry_run_writes_nothing():
    client = FakeClient(_metrics_table())

    result = backfill.run_backfill(client=client, dry_run=True)

    assert result["dry_run"] is True
    assert client.updates == []
    assert result["applied"]["daily_rows"] == 1
    assert result["applied"]["earnings_rows"] == 1
    assert result["applied"]["sector_rows"] == 1


def test_apply_writes_conviction_and_recomputed_metrics():
    client = FakeClient(_metrics_table())

    backfill.run_backfill(client=client, dry_run=False)

    tables = [name for name, _ in client.updates]
    assert tables.count("daily_predictions") == 1
    assert tables.count("earnings_predictions") == 1
    assert tables.count("sector_predictions") == 1
    assert tables.count("prompt_experiments") == 2

    daily_metrics = next(
        payload["metrics"]
        for name, payload in client.updates
        if name == "prompt_experiments" and payload["metrics"]["predictions_evaluated"] == 1
    )
    # Composite = 0.90 * accuracy_block + 0.10 * conviction_norm.
    expected = 0.9 * 100.0 + 0.1 * daily_metrics["conviction_norm"]
    assert daily_metrics["score"] == pytest.approx(expected, abs=1e-3)
    assert daily_metrics["conviction_norm"] > 50.0
