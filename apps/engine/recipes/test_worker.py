"""Hermetic tests for recipe studio queue worker (Push v2 only)."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, call, patch

import httpx
import pytest

from recipes.push_schema import PushStrategy
from recipes.worker import (
    STALE_COMPILE_MESSAGE,
    _record_job_failure,
    process_next_recipe_job,
)


def _make_mock_supabase():
    client = MagicMock()
    queue_table = MagicMock()
    recipes_table = MagicMock()
    alerts_table = MagicMock()

    def table_router(table_name):
        if table_name == "recipe_execution_queue":
            return queue_table
        if table_name == "strategy_recipes":
            return recipes_table
        if table_name == "recipe_alerts_inbox":
            return alerts_table
        return MagicMock()

    client.table.side_effect = table_router
    return client, queue_table, recipes_table, alerts_table


def _sample_push_strategy() -> PushStrategy:
    return PushStrategy(
        name="Chip Momentum",
        cadence="1d",
        stages=[
            {
                "id": "stage-1",
                "selected_tools": ["get_technical_indicators"],
                "blocks": [
                    {"id": "b1", "type": "prompt", "text": "Analyze NVDA."},
                    {"id": "b2", "type": "news", "contains": ["NVDA"], "recency_hours": 48},
                ],
            }
        ],
    )


def test_process_next_job_empty_queue():
    client, _, _, _ = _make_mock_supabase()
    client.rpc.return_value.execute.return_value.data = []

    res = process_next_recipe_job(client)
    assert res == "EMPTY"


def test_process_push_backtest_job_success():
    client, queue_table, recipes_table, _ = _make_mock_supabase()
    client.rpc.return_value.execute.return_value.data = [
        {
            "job_id": "job-111",
            "job_recipe_id": "rec-222",
            "job_user_id": "usr-333",
            "job_mode": "backtest",
            "job_priority": 10,
        }
    ]

    strategy = _sample_push_strategy()
    recipe_select = MagicMock()
    recipe_select.execute.return_value.data = {
        "id": "rec-222",
        "name": strategy.name,
        "graph_json": strategy.model_dump(),
        "trial_count": 5,
    }
    recipes_table.select.return_value.eq.return_value.single.return_value = recipe_select

    fake_result = {"mode": "backtest", "total_trades": 1, "total_return_pct_net": 1.2}
    with patch("recipes.worker.run_push_backtest", new=AsyncMock(return_value=fake_result)):
        res = process_next_recipe_job(client)

    assert res == "COMPLETED"
    completed_payloads = [
        call[0][0] for call in queue_table.update.call_args_list if call[0][0].get("status") == "completed"
    ]
    assert len(completed_payloads) == 1
    assert completed_payloads[0]["progress_pct"] == 100
    assert completed_payloads[0]["result_json"] == fake_result


def test_process_push_backtest_job_persists_progress_updates():
    client, queue_table, recipes_table, _ = _make_mock_supabase()
    client.rpc.return_value.execute.return_value.data = [
        {
            "job_id": "job-prog-1",
            "job_recipe_id": "rec-222",
            "job_user_id": "usr-333",
            "job_mode": "backtest",
            "job_priority": 10,
        }
    ]

    strategy = _sample_push_strategy()
    recipe_select = MagicMock()
    recipe_select.execute.return_value.data = {
        "id": "rec-222",
        "name": strategy.name,
        "graph_json": strategy.model_dump(),
        "trial_count": 2,
    }
    recipes_table.select.return_value.eq.return_value.single.return_value = recipe_select

    partial_payload = {"mode": "backtest", "days_completed": 1, "total_days": 10}
    final_payload = {"mode": "backtest", "days_completed": 10, "total_days": 10}

    async def fake_backtest(strat, sb, **kwargs):
        cb = kwargs.get("on_progress")
        assert cb is not None
        cb(18, partial_payload)
        return final_payload

    with patch("recipes.worker.run_push_backtest", side_effect=fake_backtest):
        res = process_next_recipe_job(client)

    assert res == "COMPLETED"
    update_payloads = [call[0][0] for call in queue_table.update.call_args_list]
    assert any(
        u.get("progress_pct") == 18 and u.get("result_json") == partial_payload and "heartbeat_at" in u
        for u in update_payloads
    )


def test_process_push_live_turn_deposits_alert():
    client, queue_table, recipes_table, alerts_table = _make_mock_supabase()
    client.rpc.return_value.execute.return_value.data = [
        {
            "job_id": "job-live-1",
            "job_recipe_id": "rec-live-2",
            "job_user_id": "usr-live-3",
            "job_mode": "live_turn",
            "job_priority": 1,
        }
    ]

    strategy = _sample_push_strategy()
    recipe_select = MagicMock()
    recipe_select.execute.return_value.data = {
        "id": "rec-live-2",
        "name": strategy.name,
        "graph_json": strategy.model_dump(),
        "trial_count": 0,
    }
    recipes_table.select.return_value.eq.return_value.single.return_value = recipe_select

    fake_live = {
        "mode": "live_turn",
        "stages": [{"stage_id": "stage-1", "output": "BUY NVDA"}],
        "final_output": '[{"action": "BUY", "ticker": "NVDA"}]',
        "signals": [{"action": "BUY", "ticker": "NVDA"}],
        "signal_prices": {"NVDA": 142.5},
        "updated_portfolio": {
            "paper_cash": 7500.0,
            "paper_positions": [{"ticker": "NVDA", "entry_price": 142.5}],
            "paper_trades": [],
            "paper_equity_curve": [{"time": "2026-04-06 09:30 ET", "equity": 10000.0}],
        },
    }
    with patch("recipes.worker.run_push_live", new=AsyncMock(return_value=fake_live)):
        res = process_next_recipe_job(client)

    assert res == "COMPLETED"
    alerts_table.insert.assert_called_once()
    alert_args = alerts_table.insert.call_args[0][0]
    assert alert_args["user_id"] == "usr-live-3"
    assert alert_args["ticker"] == "NVDA"
    assert alert_args["action"] == "BUY"
    assert alert_args["entry_price"] == 142.5
    assert alert_args["is_read"] is False
    recipe_updates = [c[0][0] for c in recipes_table.update.call_args_list]
    assert any(u.get("paper_cash") == 7500.0 and len(u.get("paper_positions", [])) == 1 for u in recipe_updates)
    assert any(c[0][0].get("status") == "completed" for c in queue_table.update.call_args_list)


def test_process_legacy_dag_payload_fails_cleanly():
    client, queue_table, recipes_table, _ = _make_mock_supabase()
    client.rpc.return_value.execute.return_value.data = [
        {
            "job_id": "job-legacy-1",
            "job_recipe_id": "rec-legacy-2",
            "job_user_id": "usr-333",
            "job_mode": "backtest",
            "job_priority": 10,
        }
    ]

    legacy_dag = {
        "name": "Legacy DAG",
        "nodes": [{"id": "n0", "type": "price_tape", "config": {"ticker": "SPY"}}],
        "edges": [],
    }
    recipe_select = MagicMock()
    recipe_select.execute.return_value.data = {
        "id": "rec-legacy-2",
        "name": "Legacy DAG",
        "graph_json": legacy_dag,
        "trial_count": 0,
    }
    recipes_table.select.return_value.eq.return_value.single.return_value = recipe_select

    res = process_next_recipe_job(client)
    assert res == "FAILED"
    failed_payloads = [call[0][0] for call in queue_table.update.call_args_list if call[0][0].get("status") == "failed"]
    assert len(failed_payloads) == 1
    assert "stages" in failed_payloads[0]["error_message"].lower()


def test_process_unsupported_mode_fails_cleanly():
    client, queue_table, recipes_table, _ = _make_mock_supabase()
    client.rpc.return_value.execute.return_value.data = [
        {
            "job_id": "job-badmode-1",
            "job_recipe_id": "rec-1",
            "job_user_id": "usr-1",
            "job_mode": "invalid_mode",
            "job_priority": 10,
        }
    ]
    strategy = _sample_push_strategy()
    recipe_select = MagicMock()
    recipe_select.execute.return_value.data = {
        "id": "rec-1",
        "name": strategy.name,
        "graph_json": strategy.model_dump(),
        "trial_count": 0,
    }
    recipes_table.select.return_value.eq.return_value.single.return_value = recipe_select

    res = process_next_recipe_job(client)
    assert res == "FAILED"
    failed_payloads = [call[0][0] for call in queue_table.update.call_args_list if call[0][0].get("status") == "failed"]
    assert len(failed_payloads) == 1
    assert "unsupported" in failed_payloads[0]["error_message"].lower()


def test_process_multi_stage_payload_fails_cleanly():
    client, queue_table, recipes_table, _ = _make_mock_supabase()
    client.rpc.return_value.execute.return_value.data = [
        {
            "job_id": "job-multi-1",
            "job_recipe_id": "rec-multi-2",
            "job_user_id": "usr-333",
            "job_mode": "backtest",
            "job_priority": 10,
        }
    ]

    stage = _sample_push_strategy().model_dump()["stages"][0]
    recipe_select = MagicMock()
    recipe_select.execute.return_value.data = {
        "id": "rec-multi-2",
        "name": "Two Calls",
        "graph_json": {"name": "Two Calls", "cadence": "1d", "stages": [stage, {**stage, "id": "stage-2"}]},
        "trial_count": 0,
    }
    recipes_table.select.return_value.eq.return_value.single.return_value = recipe_select

    fake_backtest = AsyncMock(return_value={"mode": "backtest"})
    with patch("recipes.worker.run_push_backtest", new=fake_backtest):
        res = process_next_recipe_job(client)

    assert res == "FAILED"
    fake_backtest.assert_not_called()
    failed_payloads = [call[0][0] for call in queue_table.update.call_args_list if call[0][0].get("status") == "failed"]
    assert len(failed_payloads) == 1
    assert "one llm stage" in failed_payloads[0]["error_message"].lower()


def test_process_zero_stage_payload_fails_cleanly():
    client, queue_table, recipes_table, _ = _make_mock_supabase()
    client.rpc.return_value.execute.return_value.data = [
        {
            "job_id": "job-zero-1",
            "job_recipe_id": "rec-zero-2",
            "job_user_id": "usr-333",
            "job_mode": "backtest",
            "job_priority": 10,
        }
    ]

    recipe_select = MagicMock()
    recipe_select.execute.return_value.data = {
        "id": "rec-zero-2",
        "name": "No Call",
        "graph_json": {"name": "No Call", "cadence": "1d", "stages": []},
        "trial_count": 0,
    }
    recipes_table.select.return_value.eq.return_value.single.return_value = recipe_select

    fake_backtest = AsyncMock(return_value={"mode": "backtest"})
    with patch("recipes.worker.run_push_backtest", new=fake_backtest):
        res = process_next_recipe_job(client)

    assert res == "FAILED"
    fake_backtest.assert_not_called()
    failed_payloads = [call[0][0] for call in queue_table.update.call_args_list if call[0][0].get("status") == "failed"]
    assert len(failed_payloads) == 1
    assert "exactly one llm stage" in failed_payloads[0]["error_message"].lower()


def test_process_live_turn_inserts_alerts_only_for_executed_signals_and_applies_cas():
    client, _queue_table, recipes_table, alerts_table = _make_mock_supabase()
    client.rpc.return_value.execute.return_value.data = [
        {
            "job_id": "job-live-cas-1",
            "job_recipe_id": "rec-live-cas-1",
            "job_user_id": "usr-cas-1",
            "job_mode": "live_turn",
            "job_priority": 1,
        }
    ]
    strategy = _sample_push_strategy()
    recipe_select = MagicMock()
    recipe_select.execute.return_value.data = {
        "id": "rec-live-cas-1",
        "user_id": "usr-cas-1",
        "name": strategy.name,
        "graph_json": strategy.model_dump(),
        "trial_count": 3,
    }
    recipes_table.select.return_value.eq.return_value.single.return_value = recipe_select

    fake_live = {
        "mode": "live_turn",
        "stages": [],
        "final_output": '[{"action": "BUY", "ticker": "NVDA"}, {"action": "BUY", "ticker": "AAPL"}]',
        "signals": [{"action": "BUY", "ticker": "NVDA"}, {"action": "BUY", "ticker": "AAPL"}],
        "executed_signals": [{"action": "BUY", "ticker": "NVDA", "price": 142.5}],
        "signal_prices": {"NVDA": 142.5, "AAPL": 210.0},
        "updated_portfolio": {"paper_cash": 7500.0},
    }
    with patch("recipes.worker.run_push_live", new=AsyncMock(return_value=fake_live)):
        res = process_next_recipe_job(client)

    assert res == "COMPLETED"
    alerts_table.insert.assert_called_once()
    assert alerts_table.insert.call_args[0][0]["ticker"] == "NVDA"
    cas_eq_trial = recipes_table.update.return_value.eq.return_value.eq
    cas_eq_trial.assert_called_once_with("trial_count", 3)


def test_process_next_job_forwards_target_mode_model_and_heartbeat():
    import asyncio

    from recipes.worker import async_process_next_recipe_job

    client, queue_table, recipes_table, _alerts_table = _make_mock_supabase()
    client.rpc.return_value.execute.return_value.data = [
        {
            "job_id": "job-lane-1",
            "job_recipe_id": "rec-lane-1",
            "job_user_id": "usr-lane-1",
            "job_mode": "live_turn",
            "job_priority": 1,
            "job_model": "auto-go",
        }
    ]
    strategy = _sample_push_strategy()
    recipe_select = MagicMock()
    recipe_select.execute.return_value.data = {
        "id": "rec-lane-1",
        "user_id": "usr-lane-1",
        "name": strategy.name,
        "graph_json": strategy.model_dump(),
        "trial_count": 0,
    }
    recipes_table.select.return_value.eq.return_value.single.return_value = recipe_select
    queue_table.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
        "status": "processing"
    }

    fake_live = {"mode": "live_turn", "stages": [], "final_output": "HOLD", "signals": []}
    with patch("recipes.worker.run_push_live", new=AsyncMock(return_value=fake_live)) as mock_live:
        res = asyncio.run(async_process_next_recipe_job(client, target_mode="live_turn"))

    assert res == "COMPLETED"
    client.rpc.assert_called_once_with("pop_next_recipe_job", {"target_mode": "live_turn"})
    assert mock_live.await_args.kwargs.get("model") == "auto-go"
    processing_updates = [c[0][0] for c in queue_table.update.call_args_list if c[0][0].get("status") == "processing"]
    assert processing_updates and "heartbeat_at" in processing_updates[0]


def test_process_push_backtest_does_not_overwrite_cancelled_job():
    client, queue_table, recipes_table, _ = _make_mock_supabase()
    client.rpc.return_value.execute.return_value.data = [
        {
            "job_id": "job-cancel-1",
            "job_recipe_id": "rec-cancel-1",
            "job_user_id": "usr-1",
            "job_mode": "backtest",
            "job_priority": 10,
            "job_model": "auto-go",
        }
    ]
    strategy = _sample_push_strategy()
    recipe_select = MagicMock()
    recipe_select.execute.return_value.data = {
        "id": "rec-cancel-1",
        "name": strategy.name,
        "graph_json": strategy.model_dump(),
        "trial_count": 4,
    }
    recipes_table.select.return_value.eq.return_value.single.return_value = recipe_select
    queue_table.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
        "status": "cancelled"
    }

    with patch("recipes.worker.run_push_backtest", new=AsyncMock(return_value={"mode": "backtest"})):
        res = process_next_recipe_job(client)

    assert res == "CANCELLED"
    completed_updates = [c[0][0] for c in queue_table.update.call_args_list if c[0][0].get("status") == "completed"]
    assert completed_updates == []
    recipes_table.update.assert_not_called()


# --- mode=compile: the daemon is a dumb auto-go executor ---------------------


class _FakeCompileResponse:
    def __init__(self, content: str) -> None:
        self._content = content

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


def _compile_client(events, *, content='{"status":"question","question":"Which?","options":["A"]}'):
    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            self.timeout = kwargs.get("timeout")

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, json=None, headers=None):
            events.append(("post", url, json, headers))
            return _FakeCompileResponse(content)

    return _FakeAsyncClient


def _compile_job_client(payload=None, *, usage=1, created_at=None):
    client, queue_table, _recipes_table, _alerts = _make_mock_supabase()
    client.rpc.return_value.execute.return_value.data = [
        {
            "job_id": "job-compile-1",
            "job_recipe_id": None,
            "job_user_id": "usr-operator",
            "job_mode": "compile",
            "job_priority": 10,
        }
    ]
    row = {
        "payload_json": payload
        or {
            "model": "auto-go",
            "temperature": 0.2,
            "messages": [{"role": "user", "content": "buy chipmakers"}],
        },
        "user_id": "usr-operator",
    }
    if created_at is not None:
        row["created_at"] = created_at
    queue_table.select.return_value.eq.return_value.single.return_value.execute.return_value.data = row
    return client, queue_table


_COMPILE_JOB = {
    "job_id": "job-compile-1",
    "job_recipe_id": None,
    "job_user_id": "usr-operator",
    "job_mode": "compile",
    "job_priority": 10,
}


def _rpc_router(events, *, usage=1, jobs=None):
    """Route the pop RPC to a job list and the meter RPC to a usage count."""

    def router(name, params=None):
        events.append(("rpc", name, params))
        result = MagicMock()
        result.execute.return_value.data = (
            (jobs if jobs is not None else [_COMPILE_JOB]) if name == "pop_next_recipe_job" else usage
        )
        return result

    return router


def test_compile_job_completes_with_raw_reply_and_meters_first():
    events = []
    client, queue_table = _compile_job_client()
    client.rpc.side_effect = _rpc_router(events)

    with patch("recipes.worker.httpx.AsyncClient", new=_compile_client(events)):
        res = process_next_recipe_job(client, target_mode="compile")

    assert res == "COMPLETED"
    # the meter is spent before any provider call is made
    kinds = [e[0] for e in events]
    assert "consume_builder_compile" in [e[1] for e in events if e[0] == "rpc"]
    assert kinds.index("rpc") < kinds.index("post")
    assert [e[1] for e in events if e[0] == "rpc"] == [
        "pop_next_recipe_job",
        "consume_builder_compile",
    ]

    completed = [c[0][0] for c in queue_table.update.call_args_list if c[0][0].get("status") == "completed"]
    assert len(completed) == 1
    assert completed[0]["result_json"] == {"content": '{"status":"question","question":"Which?","options":["A"]}'}
    assert completed[0]["progress_pct"] == 100


def test_compile_job_stops_at_the_daily_limit_without_calling_the_model():
    events = []
    client, queue_table = _compile_job_client()
    client.rpc.side_effect = _rpc_router(events, usage=26)

    with patch("recipes.worker.httpx.AsyncClient", new=_compile_client(events)):
        res = process_next_recipe_job(client, target_mode="compile")

    assert res == "FAILED"
    assert [e for e in events if e[0] == "post"] == []
    failed = [c[0][0] for c in queue_table.update.call_args_list if c[0][0].get("status") == "failed"]
    assert len(failed) == 1
    assert "Daily builder limit reached" in failed[0]["error_message"]


def test_compile_job_records_a_provider_failure():
    events = []
    client, queue_table = _compile_job_client()

    client.rpc.side_effect = _rpc_router(events)

    class _BoomingClient(_compile_client(events)):
        async def post(self, url, json=None, headers=None):
            raise RuntimeError("Builder model call failed (503)")

    with patch("recipes.worker.httpx.AsyncClient", new=_BoomingClient):
        res = process_next_recipe_job(client, target_mode="compile")

    assert res == "FAILED"
    failed = [c[0][0] for c in queue_table.update.call_args_list if c[0][0].get("status") == "failed"]
    assert len(failed) == 1
    assert "503" in failed[0]["error_message"]


def test_compile_job_requires_a_payload():
    client, queue_table = _compile_job_client(payload=None)
    client.rpc.side_effect = _rpc_router([], usage=1)
    queue_table.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
        "payload_json": None,
        "user_id": "usr-operator",
    }

    with patch("recipes.worker.httpx.AsyncClient", new=_compile_client([])):
        res = process_next_recipe_job(client, target_mode="compile")

    assert res == "FAILED"


def test_compile_job_enforces_locked_model_tokens_and_json_mode():
    events = []
    client, _ = _compile_job_client(
        payload={
            "model": "gpt-4o-paid-override",
            "temperature": 1.9,
            "max_tokens": 999999,
            "messages": [
                {"role": "system", "content": "system"},
                {"role": "user", "content": "buy chipmakers"},
            ],
        }
    )
    client.rpc.side_effect = _rpc_router(events)

    with patch("recipes.worker.httpx.AsyncClient", new=_compile_client(events)):
        res = process_next_recipe_job(client, target_mode="compile")

    assert res == "COMPLETED"
    post_events = [e for e in events if e[0] == "post"]
    assert len(post_events) == 1
    sent_payload = post_events[0][2]
    assert sent_payload["model"] == "auto-go"
    assert sent_payload["max_tokens"] == 32_768
    assert sent_payload["temperature"] == 0.5
    assert sent_payload["response_format"] == {"type": "json_object"}


def test_compile_job_timeout_covers_proxy_pass_budget():
    from recipes.worker import COMPILE_TIMEOUT_SECONDS

    assert COMPILE_TIMEOUT_SECONDS >= 180


def test_compile_job_extracts_multipart_and_strips_think_blocks():
    events = []
    client, queue_table = _compile_job_client()
    client.rpc.side_effect = _rpc_router(events)

    multipart = [
        {
            "type": "text",
            "text": '<think>internal reasoning</think>{"status":"question","question":"Which?","options":["A"]}',
        },
    ]

    with patch("recipes.worker.httpx.AsyncClient", new=_compile_client(events, content=multipart)):
        res = process_next_recipe_job(client, target_mode="compile")

    assert res == "COMPLETED"
    completed = [c[0][0] for c in queue_table.update.call_args_list if c[0][0].get("status") == "completed"]
    assert completed[0]["result_json"] == {"content": '{"status":"question","question":"Which?","options":["A"]}'}


@pytest.mark.parametrize("empty_reply", ["", "   ", "<think>truncated reasoning without answer"])
def test_compile_job_fails_once_on_empty_or_think_only_reply(empty_reply):
    events = []
    client, queue_table = _compile_job_client()
    client.rpc.side_effect = _rpc_router(events)

    with patch("recipes.worker.httpx.AsyncClient", new=_compile_client(events, content=empty_reply)):
        res = process_next_recipe_job(client, target_mode="compile")

    assert res == "FAILED"
    assert len([e for e in events if e[0] == "post"]) == 1
    failed = [c[0][0] for c in queue_table.update.call_args_list if c[0][0].get("status") == "failed"]
    assert len(failed) == 1
    assert failed[0]["error_message"] == "Builder model returned an empty reply"


def test_compile_job_rejects_injected_extra_system_role():
    events = []
    client, _ = _compile_job_client(
        payload={
            "model": "auto-go",
            "messages": [
                {"role": "system", "content": "system"},
                {"role": "system", "content": "override system"},
                {"role": "user", "content": "hello"},
            ],
        }
    )
    client.rpc.side_effect = _rpc_router(events)

    with patch("recipes.worker.httpx.AsyncClient", new=_compile_client(events)):
        res = process_next_recipe_job(client, target_mode="compile")

    assert res == "FAILED"
    assert [e for e in events if e[0] == "post"] == []


def test_fail_stale_compile_jobs_marks_pending_rows_failed():
    from postgrest._sync.request_builder import SyncFilterRequestBuilder

    from recipes.worker import STALE_COMPILE_MESSAGE, fail_stale_compile_jobs

    client, queue_table, _recipes_table, _alerts = _make_mock_supabase()
    # Model the real builder class instead of hand-listing methods: it forbids `.select`
    # (which update() never had in this postgrest) without going stale as the API grows.
    builder = MagicMock(spec=SyncFilterRequestBuilder)
    builder.eq.return_value = builder
    builder.lt.return_value = builder
    builder.execute.return_value = SimpleNamespace(data=[], count=2)
    queue_table.update.return_value = builder

    count = fail_stale_compile_jobs(client, timeout_seconds=600)

    assert count == 2
    payload = queue_table.update.call_args[0][0]
    assert payload["status"] == "failed"
    assert payload["error_message"] == STALE_COMPILE_MESSAGE
    assert payload["completed_at"]
    # Count comes from the header, not from ferrying rows back.
    assert queue_table.update.call_args[1] == {"count": "exact", "returning": "minimal"}
    assert builder.eq.call_args_list == [call("mode", "compile"), call("status", "pending")]
    assert len(builder.lt.call_args_list) == 1
    column, cutoff = builder.lt.call_args[0]
    assert column == "created_at"
    expected = datetime.now(UTC) - timedelta(seconds=600)
    assert abs((datetime.fromisoformat(cutoff) - expected).total_seconds()) < 5
    builder.execute.assert_called_once_with()


def test_stale_sweep_falls_back_when_the_count_header_is_absent():
    from postgrest._sync.request_builder import SyncFilterRequestBuilder

    from recipes.worker import fail_stale_compile_jobs

    client, queue_table, _recipes_table, _alerts = _make_mock_supabase()
    builder = MagicMock(spec=SyncFilterRequestBuilder)
    builder.eq.return_value = builder
    builder.lt.return_value = builder
    builder.execute.return_value = SimpleNamespace(data=[{"id": "a"}, {"id": "b"}, {"id": "c"}], count=None)
    queue_table.update.return_value = builder

    assert fail_stale_compile_jobs(client) == 3


def test_compile_job_refuses_a_row_that_aged_past_the_window():
    """The pop poll (5s) can beat the sweep (60s): refuse a stale row before metering."""
    events = []
    stale = (datetime.now(UTC) - timedelta(minutes=20)).isoformat()
    client, queue_table = _compile_job_client(created_at=stale)
    client.rpc.side_effect = _rpc_router(events)

    with patch("recipes.worker.httpx.AsyncClient", new=_compile_client(events)):
        res = process_next_recipe_job(client, target_mode="compile")

    assert res == "FAILED"
    # no meter and no provider call: the user is not charged for a stale row
    assert [e[1] for e in events if e[0] == "rpc"] == ["pop_next_recipe_job"]
    assert not any(e[0] == "post" for e in events)
    failed = [c[0][0] for c in queue_table.update.call_args_list if c[0][0].get("status") == "failed"]
    assert failed
    assert failed[0]["error_message"] == STALE_COMPILE_MESSAGE


def test_failure_recording_never_stores_an_empty_message():
    """Found live: a 45s httpx timeout recorded error_message = "" and the UI could only say "failed"."""
    from recipes.worker import _record_job_failure

    client, queue_table, _recipes, _alerts = _make_mock_supabase()
    _record_job_failure(client, {"job_id": "job-timeout"}, httpx.ReadTimeout(""))

    payload = queue_table.update.call_args[0][0]
    assert payload["status"] == "failed"
    assert payload["error_message"]
    assert "too long" in payload["error_message"]
    assert "try again" in payload["error_message"].lower()


def test_failure_recording_falls_back_to_the_exception_type():
    from recipes.worker import _record_job_failure

    client, queue_table, _recipes, _alerts = _make_mock_supabase()
    _record_job_failure(client, {"job_id": "job-weird"}, RuntimeError(""))

    assert queue_table.update.call_args[0][0]["error_message"] == "RuntimeError: the job stopped without a message."


def test_record_job_failure_refunds_the_token():
    client, queue_table, _, _ = _make_mock_supabase()

    _record_job_failure(client, {"job_id": "job-refund-1"}, RuntimeError("boom"))

    # A failed run must not cost the user a token.
    client.rpc.assert_called_once_with(
        "settle_token",
        {"p_ref": "job-refund-1", "p_outcome": "failed"},
    )
    assert queue_table.update.call_args[0][0]["status"] == "failed"


def test_record_job_failure_refunds_nothing_when_the_status_write_fails():
    client, queue_table, _, _ = _make_mock_supabase()
    queue_table.update.return_value.eq.return_value.execute.side_effect = RuntimeError("db down")

    _record_job_failure(client, {"job_id": "job-refund-2"}, RuntimeError("boom"))

    client.rpc.assert_not_called()
