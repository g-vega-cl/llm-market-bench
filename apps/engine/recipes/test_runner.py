"""Hermetic tests for the Recipe Studio hourly runner, news sync, and template seeder."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from recipes.push_schema import PushStrategy
from recipes.runner import (
    enqueue_live_recipes,
    load_starter_recipes,
    run_hourly_cycle,
    seed_starter_recipes,
)


def test_seed_starter_recipes_inserts_missing_templates():
    sb = MagicMock()
    tbl = MagicMock()
    sb.table.return_value = tbl

    # Existing templates query returns empty -> every starter template inserted
    tbl.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

    count = seed_starter_recipes(sb)
    assert count == len(load_starter_recipes())
    assert tbl.insert.call_count == count
    first_row = tbl.insert.call_args_list[0][0][0]
    assert first_row["is_template"] is True
    assert first_row["is_public"] is True
    assert first_row["graph_json"]["version"] == "2.0-push"


def test_seed_starter_recipes_is_idempotent():
    sb = MagicMock()
    tbl = MagicMock()
    sb.table.return_value = tbl

    from recipes.runner import load_starter_recipes

    existing_names = [{"name": r["name"]} for r in load_starter_recipes()]
    tbl.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = existing_names

    count = seed_starter_recipes(sb)
    assert count == 0
    tbl.insert.assert_not_called()


def test_enqueue_live_recipes_skips_if_already_pending():
    sb = MagicMock()
    recipes_tbl = MagicMock()
    queue_tbl = MagicMock()

    def _router(name: str):
        if name == "strategy_recipes":
            return recipes_tbl
        if name == "recipe_execution_queue":
            return queue_tbl
        return MagicMock()

    sb.table.side_effect = _router
    recipes_chain = recipes_tbl.select.return_value.eq.return_value.limit.return_value
    recipes_chain.execute.return_value.data = [
        {"id": "rec-legacy", "user_id": "u0", "name": "Legacy DAG", "graph_json": {"nodes": [], "edges": []}},
        {"id": "rec-1", "user_id": "u1", "name": "Live 1", "graph_json": {"stages": [{"id": "s1"}]}},
        {"id": "rec-2", "user_id": "u2", "name": "Live 2", "graph_json": {"stages": [{"id": "s1"}]}},
    ]
    queue_tbl.select.return_value.in_.return_value.limit.return_value.execute.return_value.data = [
        {"recipe_id": "rec-1"}
    ]

    enqueued = enqueue_live_recipes(sb)
    assert enqueued == 1
    queue_tbl.insert.assert_called_once()
    inserted_batch = queue_tbl.insert.call_args[0][0]
    assert isinstance(inserted_batch, list)
    assert len(inserted_batch) == 1
    assert inserted_batch[0]["recipe_id"] == "rec-2"
    assert inserted_batch[0]["mode"] == "live_turn"
    assert inserted_batch[0]["priority"] == 1


def test_enqueue_live_recipes_skips_multi_stage_recipes():
    sb = MagicMock()
    recipes_tbl = MagicMock()
    queue_tbl = MagicMock()

    def _router(name: str):
        if name == "strategy_recipes":
            return recipes_tbl
        if name == "recipe_execution_queue":
            return queue_tbl
        return MagicMock()

    sb.table.side_effect = _router
    recipes_chain = recipes_tbl.select.return_value.eq.return_value.limit.return_value
    recipes_chain.execute.return_value.data = [
        {
            "id": "rec-two-calls",
            "user_id": "u1",
            "name": "Two Calls",
            "graph_json": {"stages": [{"id": "s1"}, {"id": "s2"}]},
        },
    ]
    queue_tbl.select.return_value.in_.return_value.limit.return_value.execute.return_value.data = []

    assert enqueue_live_recipes(sb) == 0
    queue_tbl.insert.assert_not_called()


def test_starter_templates_are_single_llm_stage():
    templates = load_starter_recipes()
    assert templates
    for tmpl in templates:
        assert len(tmpl["stages"]) == 1, tmpl["name"]
        PushStrategy(**tmpl)


@pytest.mark.asyncio
async def test_run_hourly_cycle_syncs_enqueues_and_drains_queue():
    sb = MagicMock()
    with (
        patch("recipes.runner.sync_live_news_to_corpus", new=AsyncMock(return_value={"inserted": 4})) as mock_sync,
        patch("recipes.runner.enqueue_live_recipes", return_value=2) as mock_enqueue,
        patch(
            "recipes.runner.async_process_next_recipe_job",
            new=AsyncMock(side_effect=["COMPLETED", "FAILED", "COMPLETED", "EMPTY"]),
        ) as mock_pop,
    ):
        stats = await run_hourly_cycle(sb, as_of_utc=datetime(2026, 11, 13, 16, 0, tzinfo=UTC))

    mock_sync.assert_awaited_once()
    mock_enqueue.assert_called_once_with(sb)
    # FAILED job must not starve subsequent jobs; stops only on EMPTY.
    assert mock_pop.call_count == 4
    assert stats == {"news_synced": 4, "live_enqueued": 2, "jobs_processed": 2, "jobs_failed": 1}


@pytest.mark.asyncio
async def test_run_hourly_cycle_drains_real_worker_without_nested_event_loop_crash():
    """Reproduction test: calling real worker inside async run_hourly_cycle must not raise asyncio.run RuntimeError."""
    sb = MagicMock()
    recipes_tbl = MagicMock()
    queue_tbl = MagicMock()
    alerts_tbl = MagicMock()

    def _router(name: str):
        return {
            "strategy_recipes": recipes_tbl,
            "recipe_execution_queue": queue_tbl,
            "recipe_alerts_inbox": alerts_tbl,
        }.get(name, MagicMock())

    sb.table.side_effect = _router
    sb.rpc.return_value.execute.side_effect = [
        MagicMock(
            data=[
                {
                    "job_id": "j-1",
                    "job_recipe_id": "r-1",
                    "job_user_id": "u-1",
                    "job_mode": "live_turn",
                    "job_priority": 1,
                }
            ]
        ),
        MagicMock(data=[]),
    ]
    recipes_tbl.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    recipes_tbl.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
        "id": "r-1",
        "name": "Live Chip Momentum",
        "trial_count": 0,
        "graph_json": {
            "name": "Live Chip Momentum",
            "cadence": "1d",
            "stages": [
                {
                    "id": "s1",
                    "title": "Stage 1",
                    "selected_tools": [],
                    "blocks": [{"id": "b1", "type": "prompt", "text": "Analyze NVDA"}],
                }
            ],
        },
    }

    fake_live = {"mode": "live_turn", "stages": [], "final_output": "HOLD", "signals": []}
    with (
        patch("recipes.runner.sync_live_news_to_corpus", new=AsyncMock(return_value={"inserted": 0})),
        patch("recipes.worker.run_push_live", new=AsyncMock(return_value=fake_live)),
    ):
        stats = await run_hourly_cycle(sb, as_of_utc=datetime(2026, 11, 13, 16, 0, tzinfo=UTC))

    assert stats["jobs_processed"] == 1
    assert stats["jobs_failed"] == 0
