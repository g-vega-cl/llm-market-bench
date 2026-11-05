"""Runner tests for the conviction backfill CLI.

Pure scoring and matching behaviour is covered next to its module in
``core/test_conviction_backfill.py``; this file exercises the database I/O.
"""

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
    def __init__(self, rows: list[dict], updates: list[tuple[str, dict]], table: str):
        self._rows = rows
        self._updates = updates
        self._table = table

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
                "model_name": "model-a",
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
                "model_name": "model-a",
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
