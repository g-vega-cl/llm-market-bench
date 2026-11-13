"""Hermetic tests for the Recipe Studio hourly runner, news sync, and template seeder."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from recipes.runner import (
    enqueue_live_recipes,
    run_hourly_cycle,
    seed_starter_recipes,
)


def test_seed_starter_recipes_inserts_missing_templates():
    sb = MagicMock()
    tbl = MagicMock()
    sb.table.return_value = tbl

    # Existing templates query returns empty -> both templates inserted
    tbl.select.return_value.eq.return_value.execute.return_value.data = []

    count = seed_starter_recipes(sb)
    assert count >= 2
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
    tbl.select.return_value.eq.return_value.execute.return_value.data = existing_names

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
    recipes_tbl.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "rec-1", "user_id": "u1", "name": "Live 1"},
        {"id": "rec-2", "user_id": "u2", "name": "Live 2"},
    ]
    queue_tbl.select.return_value.in_.return_value.execute.return_value.data = [{"recipe_id": "rec-1"}]

    enqueued = enqueue_live_recipes(sb)
    assert enqueued == 1
    queue_tbl.insert.assert_called_once()
    inserted = queue_tbl.insert.call_args[0][0]
    assert inserted["recipe_id"] == "rec-2"
    assert inserted["mode"] == "live_turn"
    assert inserted["priority"] == 1


@pytest.mark.asyncio
async def test_run_hourly_cycle_syncs_enqueues_and_drains_queue():
    sb = MagicMock()
    with (
        patch("recipes.runner.sync_live_news_to_corpus", new=AsyncMock(return_value={"inserted": 4})) as mock_sync,
        patch("recipes.runner.enqueue_live_recipes", return_value=2) as mock_enqueue,
        patch("recipes.runner.process_next_recipe_job", side_effect=[True, True, False]) as mock_pop,
    ):
        stats = await run_hourly_cycle(sb, as_of_utc=datetime(2026, 11, 13, 16, 0, tzinfo=UTC))

    mock_sync.assert_awaited_once()
    mock_enqueue.assert_called_once_with(sb)
    assert mock_pop.call_count == 3
    assert stats == {"news_synced": 4, "live_enqueued": 2, "jobs_processed": 2}
