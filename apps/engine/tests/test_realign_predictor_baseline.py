"""Tests for per-track sector baseline realignment."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from tasks.realign_predictor_baseline import realign_predictor_baselines


class FakeQuery:
    def __init__(self, store: dict[str, list[dict]], table: str):
        self._store = store
        self._table = table
        self._filters: dict[str, object] = {}
        self._payload: dict | None = None

    def select(self, *args, **kwargs):
        return self

    def eq(self, column, value):
        self._filters[column] = value
        return self

    def order(self, *args, **kwargs):
        return self

    def update(self, payload):
        self._payload = payload
        return self

    def execute(self):
        rows = self._store.get(self._table, [])
        matches = [r for r in rows if all(r.get(k) == v for k, v in self._filters.items())]
        if self._payload is not None:
            for row in matches:
                row.update(self._payload)
            return SimpleNamespace(data=matches)
        return SimpleNamespace(data=matches)


class FakeClient:
    def __init__(self, store: dict[str, list[dict]]):
        self.store = store

    def table(self, name: str):
        return FakeQuery(self.store, name)


def _prediction(tag: str, model: str, correct_flags: list[bool], confidence: float = 60.0) -> list[dict]:
    return [
        {
            "id": f"{tag}-{index}",
            "prompt_tag": tag,
            "model_name": model,
            "target_date": "2026-10-05",
            "status": "evaluated",
            "confidence": confidence,
            "sector_percentile_score": 90.0 if correct else 10.0,
            "pair_percentile_score": 90.0 if correct else 10.0,
            "worst_sector_percentile_score": None,
            "sector_sp_diff": 0.0,
        }
        for index, correct in enumerate(correct_flags)
    ]


@pytest.fixture
def store() -> dict[str, list[dict]]:
    experiments = [
        # Track A: an old baseline, a better credible variant, a one-sample fluke, and the active prompt.
        {
            "id": "a-old",
            "variant_tag": "sector-a-old",
            "prompt_name": "SECTOR_PREDICTOR_PROMPT",
            "track_id": "model-a",
            "status": "baseline",
            "week_start": "2026-10-01",
            "week_end": "2026-10-10",
            "metrics": {"score": 40.0, "predictions_evaluated": 10},
            "parent_tag": None,
            "created_at": "2026-10-01T00:00:00Z",
        },
        {
            "id": "a-best",
            "variant_tag": "sector-a-best",
            "prompt_name": "SECTOR_PREDICTOR_PROMPT",
            "track_id": "model-a",
            "status": "discarded",
            "week_start": "2026-10-01",
            "week_end": "2026-10-10",
            "metrics": {"score": 45.0, "predictions_evaluated": 10},
            "parent_tag": "sector-a-old",
            "created_at": "2026-10-02T00:00:00Z",
        },
        {
            "id": "a-fluke",
            "variant_tag": "sector-a-fluke",
            "prompt_name": "SECTOR_PREDICTOR_PROMPT",
            "track_id": "model-a",
            "status": "discarded",
            "week_start": "2026-10-01",
            "week_end": "2026-10-10",
            "metrics": {"score": 99.0, "predictions_evaluated": 1},
            "parent_tag": "sector-a-old",
            "created_at": "2026-10-03T00:00:00Z",
        },
        {
            "id": "a-active",
            "variant_tag": "sector-a-active",
            "prompt_name": "SECTOR_PREDICTOR_PROMPT",
            "track_id": "model-a",
            "status": "active",
            "week_start": "2026-10-11",
            "week_end": "2026-10-18",
            "metrics": {},
            "parent_tag": "sector-a-old",
            "created_at": "2026-10-11T00:00:00Z",
        },
        # Track B: its own baseline must survive even though track A scores higher.
        {
            "id": "b-old",
            "variant_tag": "sector-b-old",
            "prompt_name": "SECTOR_PREDICTOR_PROMPT",
            "track_id": "model-b",
            "status": "baseline",
            "week_start": "2026-10-01",
            "week_end": "2026-10-10",
            "metrics": {"score": 30.0, "predictions_evaluated": 10},
            "parent_tag": None,
            "created_at": "2026-10-01T00:00:00Z",
        },
        {
            "id": "b-active",
            "variant_tag": "sector-b-active",
            "prompt_name": "SECTOR_PREDICTOR_PROMPT",
            "track_id": "model-b",
            "status": "active",
            "week_start": "2026-10-11",
            "week_end": "2026-10-18",
            "metrics": {},
            "parent_tag": "sector-b-old",
            "created_at": "2026-10-11T00:00:00Z",
        },
    ]
    predictions = (
        _prediction("sector-a-old", "model-a", [True, False] * 5)
        + _prediction("sector-a-best", "model-a", [True] * 5, confidence=75.0)
        + _prediction("sector-a-fluke", "model-a", [True], confidence=99.0)
        + _prediction("sector-b-old", "model-b", [True, False] * 5)
    )
    return {"prompt_experiments": experiments, "sector_predictions": predictions}


def test_dry_run_reports_per_track_baselines_without_writing(store):
    client = FakeClient(store)

    result = realign_predictor_baselines(client=client, dry_run=True)

    assert result["dry_run"] is True
    assert result["tracks"]["model-a"]["baseline_tag"] == "sector-a-best"
    assert result["tracks"]["model-b"]["baseline_tag"] == "sector-b-old"
    # No mutation.
    old = next(e for e in store["prompt_experiments"] if e["variant_tag"] == "sector-a-old")
    assert old["status"] == "baseline"


def test_apply_realigns_each_track_and_repoints_its_active_prompt(store):
    client = FakeClient(store)

    realign_predictor_baselines(client=client, dry_run=False)

    by_tag = {e["variant_tag"]: e for e in store["prompt_experiments"]}
    assert by_tag["sector-a-best"]["status"] == "baseline"
    assert by_tag["sector-a-old"]["status"] == "saved"
    assert by_tag["sector-a-active"]["parent_tag"] == "sector-a-best"
    # Track B must not inherit track A's winner.
    assert by_tag["sector-b-old"]["status"] == "baseline"
    assert by_tag["sector-b-active"]["parent_tag"] == "sector-b-old"


def test_apply_never_promotes_a_single_sample_fluke(store):
    client = FakeClient(store)

    realign_predictor_baselines(client=client, dry_run=False)

    by_tag = {e["variant_tag"]: e for e in store["prompt_experiments"]}
    assert by_tag["sector-a-fluke"]["status"] == "discarded"
    assert by_tag["sector-a-fluke"]["metrics"]["score"] > 80.0


def test_apply_writes_full_metrics_not_just_the_score(store):
    client = FakeClient(store)

    realign_predictor_baselines(client=client, dry_run=False)

    best = next(e for e in store["prompt_experiments"] if e["variant_tag"] == "sector-a-best")
    assert "conviction_norm" in best["metrics"]
    assert best["metrics"]["predictions_evaluated"] == 5


def test_missing_track_data_is_a_no_op():
    client = FakeClient({"prompt_experiments": [], "sector_predictions": []})

    result = realign_predictor_baselines(client=client, dry_run=True)

    assert result["tracks"] == {}
