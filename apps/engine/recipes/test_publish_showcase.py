"""Hermetic tests for the public showcase publisher CLI."""

from __future__ import annotations

import copy
from unittest.mock import MagicMock

import pytest

from recipes.publish_showcase import (
    ShowcasePublishError,
    _build_client,
    publish_showcase,
)
from recipes.runner import load_starter_recipes


def _graph() -> dict:
    # starter-recipes.json stores bare Push v2 graphs (no graph_json wrapper).
    return copy.deepcopy(load_starter_recipes()[0])


def _result_json(day_steps: int = 30) -> dict:
    return {"total_return_pct_net": 5.43, "day_steps": [{"slot": i} for i in range(day_steps)]}


def _job(**overrides) -> dict:
    row = {
        "id": "job-1",
        "recipe_id": "rec-1",
        "mode": "backtest",
        "status": "completed",
        "result_json": _result_json(),
        "completed_at": "2026-11-17T01:34:37.000Z",
    }
    row.update(overrides)
    return row


def _recipe(**overrides) -> dict:
    row = {
        "id": "rec-1",
        "name": "Trump & Chips News Momentum",
        "graph_json": _graph(),
        "updated_at": "2026-11-16T20:00:00.000Z",
        "is_public": True,
    }
    row.update(overrides)
    return row


def _fake_sb(job: dict | None, recipe: dict | None, *, upsert_error: Exception | None = None):
    sb = MagicMock()
    jobs_tbl = MagicMock(name="recipe_execution_queue")
    recipes_tbl = MagicMock(name="strategy_recipes")
    showcase_tbl = MagicMock(name="recipe_showcase")

    tables = {
        "recipe_execution_queue": jobs_tbl,
        "strategy_recipes": recipes_tbl,
        "recipe_showcase": showcase_tbl,
    }
    sb.table.side_effect = lambda name: tables[name]

    jobs_tbl.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [job] if job else []
    recipes_tbl.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = (
        [recipe] if recipe else []
    )
    if upsert_error is not None:
        showcase_tbl.upsert.return_value.execute.side_effect = upsert_error
    else:
        showcase_tbl.upsert.return_value.execute.return_value.data = [{}]
    return sb, recipes_tbl, showcase_tbl


def test_publish_showcase_pins_job_and_marks_recipe_public():
    sb, recipes_tbl, showcase_tbl = _fake_sb(_job(), _recipe())

    outcome = publish_showcase(sb, "job-1", headline="News momentum, long-only")

    recipe_update = recipes_tbl.update.call_args[0][0]
    assert recipe_update["is_public"] is True
    pin_payload = showcase_tbl.upsert.call_args[0][0]
    assert pin_payload["id"] == 1
    assert pin_payload["job_id"] == "job-1"
    assert pin_payload["recipe_id"] == "rec-1"
    assert pin_payload["headline"] == "News momentum, long-only"
    assert pin_payload["recipe_name"] == "Trump & Chips News Momentum"
    assert pin_payload["published_at"]
    assert showcase_tbl.upsert.call_args[1]["on_conflict"] == "id"
    assert outcome["url"] == "https://www.benchify.dev/recipes-demo"
    assert outcome["job_id"] == "job-1"


def test_publish_showcase_writes_the_pin_before_publicising_the_recipe():
    sb, recipes_tbl, _showcase_tbl = _fake_sb(
        _job(), _recipe(), upsert_error=RuntimeError("PGRST205 recipe_showcase missing")
    )

    with pytest.raises(ShowcasePublishError, match="pin"):
        publish_showcase(sb, "job-1")

    # A failed pin must not leave a freshly public recipe behind for the
    # is_public fallback to serve.
    recipes_tbl.update.assert_not_called()


def test_publish_showcase_refuses_when_the_recipe_update_misses():
    # The read-back sees the flag unset, i.e. the update hit no row.
    sb, _recipes_tbl, _showcase_tbl = _fake_sb(_job(), _recipe(is_public=False))

    with pytest.raises(ShowcasePublishError, match="0 rows"):
        publish_showcase(sb, "job-1")


def test_publish_showcase_rejects_a_recipe_edited_after_the_run():
    sb, _recipes_tbl, showcase_tbl = _fake_sb(_job(), _recipe(updated_at="2026-11-17T09:00:00.000Z"))

    with pytest.raises(ShowcasePublishError, match="edited after"):
        publish_showcase(sb, "job-1")

    showcase_tbl.upsert.assert_not_called()


def test_publish_showcase_allows_the_trial_count_bump_after_completion():
    # The worker touches the recipe row seconds after the run settles; that is
    # bookkeeping, not a graph edit.
    sb, _recipes_tbl, showcase_tbl = _fake_sb(_job(), _recipe(updated_at="2026-11-17T01:34:43.000Z"))

    outcome = publish_showcase(sb, "job-1")

    showcase_tbl.upsert.assert_called_once()
    assert outcome["job_id"] == "job-1"


def test_publish_showcase_rejects_a_job_that_has_not_completed():
    sb, _recipes_tbl, showcase_tbl = _fake_sb(_job(status="processing"), _recipe())

    with pytest.raises(ShowcasePublishError, match="not completed"):
        publish_showcase(sb, "job-1")

    showcase_tbl.upsert.assert_not_called()


def test_publish_showcase_rejects_a_short_run():
    sb, _recipes_tbl, showcase_tbl = _fake_sb(_job(result_json=_result_json(day_steps=12)), _recipe())

    with pytest.raises(ShowcasePublishError, match="30"):
        publish_showcase(sb, "job-1")

    showcase_tbl.upsert.assert_not_called()


def test_publish_showcase_rejects_days_completed_without_day_steps():
    # A payload claiming 30 finished days but carrying no slot telemetry would
    # publish a "30-slot" showcase that renders an empty timeline.
    result = {"total_return_pct_net": 5.43, "day_steps": [], "days_completed": 30}
    sb, _recipes_tbl, showcase_tbl = _fake_sb(_job(result_json=result), _recipe())

    with pytest.raises(ShowcasePublishError, match="30"):
        publish_showcase(sb, "job-1")

    showcase_tbl.upsert.assert_not_called()


def test_publish_showcase_rejects_a_multi_stage_recipe():
    multi_stage = _graph()
    stage = multi_stage["stages"][0]
    multi_stage["stages"] = [stage, {**stage, "id": "stage-2"}]
    sb, _recipes_tbl, showcase_tbl = _fake_sb(_job(), _recipe(graph_json=multi_stage))

    with pytest.raises(ShowcasePublishError, match="single-stage"):
        publish_showcase(sb, "job-1")

    showcase_tbl.upsert.assert_not_called()


def test_publish_showcase_dry_run_writes_nothing():
    sb, recipes_tbl, showcase_tbl = _fake_sb(_job(), _recipe())

    outcome = publish_showcase(sb, "job-1", dry_run=True)

    recipes_tbl.update.assert_not_called()
    showcase_tbl.upsert.assert_not_called()
    assert outcome["dry_run"] is True
    assert outcome["job_id"] == "job-1"


def test_build_client_requires_explicit_archive_credentials(monkeypatch):
    monkeypatch.delenv("ARCHIVE_DB_URL", raising=False)
    monkeypatch.delenv("VITE_ARCHIVE_DB_URL", raising=False)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "cloud-key")

    with pytest.raises(ShowcasePublishError, match="ARCHIVE_DB_URL"):
        _build_client()


def test_build_client_refuses_a_non_archive_host(monkeypatch):
    monkeypatch.setenv("ARCHIVE_DB_URL", "https://abcdefghijklmnop.supabase.co")
    monkeypatch.setenv("ARCHIVE_DB_SERVICE_ROLE_KEY", "key")

    with pytest.raises(ShowcasePublishError, match="archive"):
        _build_client()
