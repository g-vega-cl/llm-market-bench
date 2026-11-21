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
    recipes_chain = (
        recipes_tbl.select.return_value.eq.return_value.is_.return_value.order.return_value.range.return_value
    )
    recipes_chain.execute.return_value.data = [
        {"id": "rec-legacy", "user_id": "u0", "name": "Legacy DAG", "graph_json": {"nodes": [], "edges": []}},
        {"id": "rec-1", "user_id": "u1", "name": "Live 1", "graph_json": {"stages": [{"id": "s1"}]}},
        {"id": "rec-2", "user_id": "u2", "name": "Live 2", "graph_json": {"stages": [{"id": "s1"}]}},
    ]
    queue_tbl.select.return_value.in_.return_value.order.return_value.range.return_value.execute.return_value.data = [
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


def test_enqueue_live_recipes_excludes_archived_recipes():
    """A removed strategy keeps is_live rows only if the DB filter is missing."""
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
    recipes_chain = (
        recipes_tbl.select.return_value.eq.return_value.is_.return_value.order.return_value.range.return_value
    )
    recipes_chain.execute.return_value.data = []

    assert enqueue_live_recipes(sb) == 0
    recipes_tbl.select.return_value.eq.assert_called_once_with("is_live", True)
    recipes_tbl.select.return_value.eq.return_value.is_.assert_called_once_with("archived_at", "null")
    queue_tbl.insert.assert_not_called()


def test_load_starter_recipes_are_all_valid_single_stage_graphs():
    """Every seeded template must pass the same validator the worker enforces."""
    templates = load_starter_recipes()
    assert len(templates) == 5
    assert len({tmpl["name"] for tmpl in templates}) == 5
    for tmpl in templates:
        PushStrategy.model_validate(tmpl)


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
    recipes_chain = (
        recipes_tbl.select.return_value.eq.return_value.is_.return_value.order.return_value.range.return_value
    )
    recipes_chain.execute.return_value.data = [
        {
            "id": "rec-two-calls",
            "user_id": "u1",
            "name": "Two Calls",
            "graph_json": {"stages": [{"id": "s1"}, {"id": "s2"}]},
        },
    ]
    queue_tbl.select.return_value.in_.return_value.order.return_value.range.return_value.execute.return_value.data = []

    assert enqueue_live_recipes(sb) == 0
    queue_tbl.insert.assert_not_called()


def test_enqueue_live_recipes_skips_graph_that_fails_strategy_validation():
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
    recipes_chain = (
        recipes_tbl.select.return_value.eq.return_value.is_.return_value.order.return_value.range.return_value
    )
    recipes_chain.execute.return_value.data = [
        {
            "id": "rec-broken",
            "user_id": "u1",
            "name": "Broken Block",
            # One stage, but the block type is not a valid push block.
            "graph_json": {"stages": [{"id": "s1", "blocks": [{"id": "b1", "type": "bogus"}]}]},
        },
    ]
    queue_tbl.select.return_value.in_.return_value.order.return_value.range.return_value.execute.return_value.data = []

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
    assert stats == {
        "news_synced": 4,
        "live_enqueued": 2,
        "jobs_processed": 2,
        "jobs_failed": 1,
        "public_stats_rows": 0,
    }


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
    recipes_tbl.select.return_value.eq.return_value.is_.return_value.order.return_value.range.return_value.execute.return_value.data = []
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
                    "blocks": [
                        {"id": "b1", "type": "prompt", "text": "Analyze NVDA"},
                        {"id": "b2", "type": "output_format"},
                    ],
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


def test_due_trading_slot_matches_30m_market_hours_et_only_once():
    from zoneinfo import ZoneInfo

    from recipes.runner import LIVE_SLOTS_ET, due_trading_slot, is_us_market_hours_et

    et = ZoneInfo("America/New_York")
    assert len(LIVE_SLOTS_ET) == 14
    assert LIVE_SLOTS_ET[0] == (9, 30)
    assert LIVE_SLOTS_ET[-1] == (16, 0)

    # Monday 2026-04-06 (EDT) -> 09:32 ET matches slot 09:30; second call w/ same key skipped
    slot1 = due_trading_slot(datetime(2026, 4, 6, 9, 32, tzinfo=et), last_slot_key=None)
    assert slot1 == "2026-04-06T09:30"
    assert due_trading_slot(datetime(2026, 4, 6, 9, 35, tzinfo=et), last_slot_key=slot1) is None

    # 30-min slots throughout the session match; pre-open, post-close, weekends, and holidays do NOT
    assert due_trading_slot(datetime(2026, 4, 6, 10, 2, tzinfo=et), last_slot_key=slot1) == "2026-04-06T10:00"
    assert due_trading_slot(datetime(2026, 4, 6, 11, 5, tzinfo=et), last_slot_key=slot1) == "2026-04-06T11:00"
    assert due_trading_slot(datetime(2026, 4, 6, 15, 34, tzinfo=et), last_slot_key=None) == "2026-04-06T15:30"
    assert due_trading_slot(datetime(2026, 4, 6, 16, 1, tzinfo=et), last_slot_key=None) == "2026-04-06T16:00"
    assert due_trading_slot(datetime(2026, 4, 6, 9, 15, tzinfo=et), last_slot_key=None) is None
    assert due_trading_slot(datetime(2026, 4, 6, 16, 25, tzinfo=et), last_slot_key=None) is None
    assert due_trading_slot(datetime(2026, 4, 4, 9, 31, tzinfo=et), last_slot_key=None) is None  # Saturday
    assert due_trading_slot(datetime(2026, 11, 26, 10, 0, tzinfo=et), last_slot_key=None) is None  # Thanksgiving
    assert due_trading_slot(datetime(2026, 4, 3, 10, 0, tzinfo=et), last_slot_key=None) is None  # Good Friday

    assert is_us_market_hours_et(datetime(2026, 4, 6, 11, 0, tzinfo=et)) is True
    assert is_us_market_hours_et(datetime(2026, 4, 6, 9, 29, tzinfo=et)) is False
    assert is_us_market_hours_et(datetime(2026, 4, 6, 16, 1, tzinfo=et)) is False
    assert is_us_market_hours_et(datetime(2026, 11, 26, 11, 0, tzinfo=et)) is False
    assert is_us_market_hours_et(datetime(2026, 4, 3, 11, 0, tzinfo=et)) is False


def test_enqueue_live_recipes_dedups_already_enqueued_in_same_slot():
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
    recipes_tbl.select.return_value.eq.return_value.is_.return_value.order.return_value.range.return_value.execute.return_value.data = [
        {"id": "rec-1", "user_id": "u1", "name": "Live 1", "graph_json": {"stages": [{"id": "s1"}]}},
        {"id": "rec-2", "user_id": "u2", "name": "Live 2", "graph_json": {"stages": [{"id": "s1"}]}},
    ]
    queue_tbl.select.return_value.in_.return_value.order.return_value.range.return_value.execute.return_value.data = []
    queue_tbl.select.return_value.eq.return_value.gte.return_value.order.return_value.range.return_value.execute.return_value.data = [
        {"recipe_id": "rec-1"}
    ]

    enqueued = enqueue_live_recipes(sb, slot_start_utc=datetime(2026, 4, 6, 13, 30, tzinfo=UTC))
    assert enqueued == 1
    inserted_batch = queue_tbl.insert.call_args[0][0]
    assert [row["recipe_id"] for row in inserted_batch] == ["rec-2"]
    assert inserted_batch[0]["model"] == "auto-go"
    assert inserted_batch[0]["provider"] == "free-llm-proxy"


@pytest.mark.asyncio
async def test_drain_lane_passes_target_mode_independently():
    from recipes.runner import drain_lane

    sb = MagicMock()
    with patch(
        "recipes.runner.async_process_next_recipe_job",
        new=AsyncMock(side_effect=["COMPLETED", "EMPTY", "COMPLETED", "EMPTY"]),
    ) as mock_worker:
        live_done = await drain_lane(sb, mode="live_turn", max_jobs=5)
        bt_done = await drain_lane(sb, mode="backtest", max_jobs=1)

    assert live_done == 1
    assert bt_done == 1
    assert mock_worker.await_args_list[0].kwargs == {"target_mode": "live_turn"}
    assert mock_worker.await_args_list[2].kwargs == {"target_mode": "backtest"}


def _enqueue_client(recipes, open_ids, ops_tbl=None):
    """Router stub for enqueue_live_recipes_with_stats."""
    sb = MagicMock()
    recipes_tbl = MagicMock()
    queue_tbl = MagicMock()
    ops = ops_tbl if ops_tbl is not None else MagicMock()

    def _router(name: str):
        if name == "strategy_recipes":
            return recipes_tbl
        if name == "recipe_execution_queue":
            return queue_tbl
        if name == "recipe_ops_events":
            return ops
        return MagicMock()

    sb.table.side_effect = _router
    recipes_tbl.select.return_value.eq.return_value.is_.return_value.order.return_value.range.return_value.execute.return_value.data = recipes
    queue_tbl.select.return_value.in_.return_value.order.return_value.range.return_value.execute.return_value.data = [
        {"recipe_id": rid} for rid in open_ids
    ]
    return sb, recipes_tbl, queue_tbl, ops


def test_enqueue_live_recipes_with_stats_reports_every_counter():
    from recipes.runner import enqueue_live_recipes_with_stats

    # 11 live recipes, 1 already open (9.1% of seen, under the 10% alarm) and 1 invalid.
    recipes = [
        {"id": f"rec-{i}", "user_id": "u1", "name": f"Live {i}", "graph_json": {"stages": [{"id": "s1"}]}}
        for i in range(9)
    ] + [
        {"id": "rec-open", "user_id": "u2", "name": "Open", "graph_json": {"stages": [{"id": "s1"}]}},
        {"id": "rec-bad", "user_id": "u3", "name": "Bad", "graph_json": {"stages": [{"id": "s1"}, {"id": "s2"}]}},
    ]
    sb, _recipes, _queue, ops = _enqueue_client(recipes, open_ids=["rec-open"])

    stats = enqueue_live_recipes_with_stats(sb)

    assert stats == {
        "seen": 11,
        "enqueued": 9,
        "skipped_open": 1,
        "skipped_invalid_graph": 1,
    }
    ops.insert.assert_not_called()


def test_enqueue_live_recipes_records_high_skip_ratio_event():
    """More than 10% of live recipes skipped as already-open is a scheduler smell, not noise."""
    from recipes.runner import enqueue_live_recipes_with_stats

    recipes = [
        {"id": "rec-1", "user_id": "u1", "name": "Live 1", "graph_json": {"stages": [{"id": "s1"}]}},
        {"id": "rec-2", "user_id": "u2", "name": "Live 2", "graph_json": {"stages": [{"id": "s1"}]}},
    ]
    sb, _recipes, _queue, ops = _enqueue_client(recipes, open_ids=["rec-1"])

    stats = enqueue_live_recipes_with_stats(sb)

    assert stats["skipped_open"] == 1
    ops.insert.assert_called_once()
    payload = ops.insert.call_args[0][0]
    assert payload["event"] == "live_enqueue_high_skip_ratio"
    assert payload["detail"]["seen"] == 2


def test_enqueue_live_recipes_pages_past_the_first_page_of_live_recipes():
    """A single .limit() silently stopped scheduling recipe 201; pagination must not."""
    from recipes.runner import LIVE_PAGE_SIZE, enqueue_live_recipes_with_stats

    page_one = [
        {"id": f"rec-{i}", "user_id": "u1", "name": f"R{i}", "graph_json": {"stages": [{"id": "s1"}]}}
        for i in range(LIVE_PAGE_SIZE)
    ]
    page_two = [{"id": "rec-last", "user_id": "u2", "name": "Last", "graph_json": {"stages": [{"id": "s1"}]}}]
    sb, recipes_tbl, queue_tbl, _ops = _enqueue_client([], open_ids=[])
    range_mock = recipes_tbl.select.return_value.eq.return_value.is_.return_value.order.return_value.range
    first_page = MagicMock()
    first_page.execute.return_value.data = page_one
    second_page = MagicMock()
    second_page.execute.return_value.data = page_two
    range_mock.side_effect = [first_page, second_page]

    stats = enqueue_live_recipes_with_stats(sb)

    assert range_mock.call_count == 2
    assert stats["seen"] == LIVE_PAGE_SIZE + 1
    assert stats["enqueued"] == LIVE_PAGE_SIZE + 1
    inserted = queue_tbl.insert.call_args[0][0]
    assert len(inserted) == LIVE_PAGE_SIZE + 1
    assert inserted[-1]["recipe_id"] == "rec-last"


@pytest.mark.asyncio
async def test_backtest_lane_runs_three_jobs_concurrently():
    """Three concurrent backtests are the product promise; a serial lane would deadlock here."""
    import asyncio

    from recipes.runner import drain_lane

    started = 0
    all_started = asyncio.Event()

    async def fake_process(_client, target_mode=None):
        nonlocal started
        started += 1
        if started == 3:
            all_started.set()
        await asyncio.wait_for(all_started.wait(), timeout=2)
        return "COMPLETED"

    with patch("recipes.runner.async_process_next_recipe_job", side_effect=fake_process):
        processed = await drain_lane(MagicMock(), mode="backtest", max_jobs=3)

    assert processed == 3


@pytest.mark.asyncio
async def test_scheduled_slot_refreshes_the_public_board():
    """The deployed --loop daemon drives this path; the board must materialise here."""
    from recipes.runner import run_scheduled_slot

    sb = MagicMock()
    with (
        patch(
            "recipes.runner.sync_live_news_to_corpus",
            new=AsyncMock(return_value={"inserted": 3}),
        ),
        patch("recipes.runner.enqueue_live_recipes", return_value=2),
        patch("recipes.runner.drain_lane", new=AsyncMock(return_value=2)),
        patch("recipes.runner.snapshot_live_intraday_bars", new=AsyncMock(return_value=0)),
        patch("recipes.runner._collect_recipe_watchlist", return_value=[]),
        patch("recipes.runner.refresh_public_stats") as refresh,
    ):
        stats = await run_scheduled_slot(sb, "2026-11-19T09:30", datetime(2026, 11, 19, 14, 30, tzinfo=UTC))

    refresh.assert_called_once_with(sb)
    assert stats == {"live_enqueued": 2, "live_done": 2, "bars_snapped": 0}


@pytest.mark.asyncio
async def test_scheduled_slot_survives_a_stats_refresh_failure():
    """A board write must never abort the trading cycle."""
    from recipes.runner import run_scheduled_slot

    sb = MagicMock()
    with (
        patch("recipes.runner.sync_live_news_to_corpus", new=AsyncMock(return_value={})),
        patch("recipes.runner.enqueue_live_recipes", return_value=0),
        patch("recipes.runner.drain_lane", new=AsyncMock(return_value=0)),
        patch("recipes.runner.snapshot_live_intraday_bars", new=AsyncMock(return_value=0)),
        patch("recipes.runner._collect_recipe_watchlist", return_value=[]),
        patch("recipes.runner.refresh_public_stats", side_effect=RuntimeError("db down")),
    ):
        stats = await run_scheduled_slot(sb, "2026-11-19T12:30", datetime(2026, 11, 19, 17, 30, tzinfo=UTC))

    assert stats["live_enqueued"] == 0


def test_enqueue_turbo_recipes_enqueues_unexpired_during_market_hours_and_respects_5m_spacing():
    from zoneinfo import ZoneInfo

    from recipes.runner import enqueue_turbo_recipes

    et = ZoneInfo("America/New_York")
    now_et = datetime(2026, 4, 6, 10, 12, tzinfo=et)

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
    recipes_tbl.select.return_value.eq.return_value.is_.return_value.gt.return_value.order.return_value.range.return_value.execute.return_value.data = [
        {"id": "rec-turbo-1", "user_id": "u1", "name": "Turbo 1", "graph_json": {"stages": [{"id": "s1"}]}},
        {"id": "rec-turbo-recent", "user_id": "u2", "name": "Turbo 2", "graph_json": {"stages": [{"id": "s1"}]}},
    ]
    queue_tbl.select.return_value.in_.return_value.order.return_value.range.return_value.execute.return_value.data = []
    queue_tbl.select.return_value.eq.return_value.gte.return_value.order.return_value.range.return_value.execute.return_value.data = [
        {"recipe_id": "rec-turbo-recent"}
    ]

    enqueued = enqueue_turbo_recipes(sb, now_utc=now_et.astimezone(UTC))
    assert enqueued == 1
    inserted = queue_tbl.insert.call_args[0][0]
    assert [r["recipe_id"] for r in inserted] == ["rec-turbo-1"]
    assert inserted[0]["mode"] == "live_turn"

    # Outside market hours: does not query or enqueue
    queue_tbl.insert.reset_mock()
    after_hours = datetime(2026, 4, 6, 16, 15, tzinfo=et)
    assert enqueue_turbo_recipes(sb, now_utc=after_hours.astimezone(UTC)) == 0
    queue_tbl.insert.assert_not_called()


@pytest.mark.asyncio
async def test_run_live_lane_tick_handles_turbo_throttles_and_slot_retry():
    from datetime import timedelta
    from zoneinfo import ZoneInfo

    from recipes.runner import LiveLaneState, run_live_lane_tick

    et = ZoneInfo("America/New_York")
    # 10:22 ET is outside the 20m window of 10:00 ET and before 10:30 ET -> idle/turbo tick
    now_utc = datetime(2026, 4, 6, 10, 22, tzinfo=et).astimezone(UTC)
    sb = MagicMock()
    state = LiveLaneState(last_slot_key="2026-04-06T10:00")

    with (
        patch("recipes.runner._is_trading_day_et", new=AsyncMock(return_value=True)),
        patch("recipes.runner.enqueue_turbo_recipes", return_value=1) as mock_turbo,
        patch("recipes.runner.sync_live_news_to_corpus", new=AsyncMock(return_value={"inserted": 2})) as mock_news,
        patch("recipes.runner.drain_lane", new=AsyncMock(return_value=1)) as mock_drain,
        patch("recipes.runner.refresh_public_stats") as mock_stats,
    ):
        state = await run_live_lane_tick(sb, now_utc, state)

    mock_turbo.assert_called_once_with(sb, now_utc=now_utc)
    mock_news.assert_awaited_once()
    mock_drain.assert_awaited_once()
    mock_stats.assert_called_once_with(sb)
    assert state.last_slot_key == "2026-04-06T10:00"
    assert state.last_news_sync_utc == now_utc

    # Second tick 10s later must NOT re-poll turbo or refresh stats within throttle windows
    now_10s = now_utc + timedelta(seconds=10)
    with (
        patch("recipes.runner._is_trading_day_et", new=AsyncMock(return_value=True)),
        patch("recipes.runner.enqueue_turbo_recipes", return_value=1) as mock_turbo_2,
        patch("recipes.runner.sync_live_news_to_corpus", new=AsyncMock()) as mock_news_2,
        patch("recipes.runner.drain_lane", new=AsyncMock(return_value=1)),
        patch("recipes.runner.refresh_public_stats") as mock_stats_2,
    ):
        state = await run_live_lane_tick(sb, now_10s, state)

    mock_turbo_2.assert_not_called()
    mock_news_2.assert_not_awaited()
    mock_stats_2.assert_not_called()

    # Third tick 31s later re-polls turbo (but still throttles news & stats < 60s/300s)
    now_31s = now_utc + timedelta(seconds=31)
    with (
        patch("recipes.runner._is_trading_day_et", new=AsyncMock(return_value=True)),
        patch("recipes.runner.enqueue_turbo_recipes", return_value=1) as mock_turbo_3,
        patch("recipes.runner.sync_live_news_to_corpus", new=AsyncMock()) as mock_news_3,
        patch("recipes.runner.drain_lane", new=AsyncMock(return_value=0)),
        patch("recipes.runner.refresh_public_stats") as mock_stats_3,
    ):
        state = await run_live_lane_tick(sb, now_31s, state)

    mock_turbo_3.assert_called_once_with(sb, now_utc=now_31s)
    mock_news_3.assert_not_awaited()
    mock_stats_3.assert_not_called()

    # Scheduled slot transient failure must NOT advance last_slot_key so it retries
    slot_utc = datetime(2026, 4, 6, 10, 31, tzinfo=et).astimezone(UTC)
    with (
        patch("recipes.runner._is_trading_day_et", new=AsyncMock(return_value=True)),
        patch("recipes.runner.run_scheduled_slot", new=AsyncMock(side_effect=RuntimeError("transient"))),
    ):
        state = await run_live_lane_tick(sb, slot_utc, state)
    assert state.last_slot_key == "2026-04-06T10:00"


@pytest.mark.asyncio
async def test_run_scheduled_slot_passes_separate_recent_turbo_cutoff():
    from recipes.runner import run_scheduled_slot

    sb = MagicMock()
    now_utc = datetime(2026, 11, 19, 15, 0, 10, tzinfo=UTC)  # 10:00:10 ET
    with (
        patch("recipes.runner.sync_live_news_to_corpus", new=AsyncMock(return_value={})),
        patch("recipes.runner.enqueue_live_recipes", return_value=0) as mock_enqueue,
        patch("recipes.runner.drain_lane", new=AsyncMock(return_value=0)),
        patch("recipes.runner.snapshot_live_intraday_bars", new=AsyncMock(return_value=0)),
        patch("recipes.runner._collect_recipe_watchlist", return_value=[]),
        patch("recipes.runner.refresh_public_stats"),
    ):
        await run_scheduled_slot(sb, "2026-11-19T10:00", now_utc)

    assert mock_enqueue.call_args.kwargs["slot_start_utc"] == datetime(2026, 11, 19, 15, 0, tzinfo=UTC)
    assert mock_enqueue.call_args.kwargs["recent_turbo_cutoff_utc"] == datetime(2026, 11, 19, 14, 55, 10, tzinfo=UTC)


def test_enqueue_live_recipes_with_stats_does_not_alert_when_skip_is_recent_turbo():
    from recipes.runner import enqueue_live_recipes_with_stats

    recipes = [
        {"id": "rec-turbo", "user_id": "u1", "name": "Turbo", "graph_json": {"stages": [{"id": "s1"}]}},
        {"id": "rec-normal", "user_id": "u2", "name": "Normal", "graph_json": {"stages": [{"id": "s1"}]}},
    ]
    sb = MagicMock()
    recipes_tbl = MagicMock()
    queue_tbl = MagicMock()
    ops_tbl = MagicMock()

    def _router(name: str):
        return {
            "strategy_recipes": recipes_tbl,
            "recipe_execution_queue": queue_tbl,
            "recipe_ops_events": ops_tbl,
        }.get(name, MagicMock())

    sb.table.side_effect = _router
    recipes_tbl.select.return_value.eq.return_value.is_.return_value.order.return_value.range.return_value.execute.return_value.data = recipes
    queue_tbl.select.return_value.in_.return_value.order.return_value.range.return_value.execute.return_value.data = []
    # First gte call = slot_start_utc (empty), second gte call = recent_turbo_cutoff_utc (rec-turbo)
    gte_slot = MagicMock()
    gte_slot.order.return_value.range.return_value.execute.return_value.data = []
    gte_turbo = MagicMock()
    gte_turbo.order.return_value.range.return_value.execute.return_value.data = [{"recipe_id": "rec-turbo"}]
    queue_tbl.select.return_value.eq.return_value.gte.side_effect = [gte_slot, gte_turbo]

    stats = enqueue_live_recipes_with_stats(
        sb,
        slot_start_utc=datetime(2026, 11, 19, 15, 0, tzinfo=UTC),
        recent_turbo_cutoff_utc=datetime(2026, 11, 19, 14, 55, tzinfo=UTC),
    )

    assert stats["enqueued"] == 1
    assert stats["skipped_open"] == 0
    ops_tbl.insert.assert_not_called()


def test_insert_live_jobs_idempotent_falls_back_on_duplicate_key():
    from recipes.runner import _insert_live_jobs_idempotent

    sb = MagicMock()
    tbl = MagicMock()
    sb.table.return_value = tbl
    tbl.insert.return_value.execute.side_effect = [
        RuntimeError("duplicate key value violates unique constraint (23505)"),
        RuntimeError("duplicate key value violates unique constraint (23505)"),
        MagicMock(),
    ]

    inserted = _insert_live_jobs_idempotent(sb, [{"recipe_id": "r1"}, {"recipe_id": "r2"}])
    assert inserted == 1
