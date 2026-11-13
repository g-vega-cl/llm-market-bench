"""Hermetic tests for recipe studio queue worker (Push v2 only)."""

from unittest.mock import AsyncMock, MagicMock, patch

from recipes.push_schema import PushStrategy
from recipes.worker import process_next_recipe_job


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
                "title": "Stage 1",
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
    }
    with patch("recipes.worker.run_push_live", new=AsyncMock(return_value=fake_live)):
        res = process_next_recipe_job(client)

    assert res == "COMPLETED"
    alerts_table.insert.assert_called_once()
    alert_args = alerts_table.insert.call_args[0][0]
    assert alert_args["user_id"] == "usr-live-3"
    assert alert_args["ticker"] == "NVDA"
    assert alert_args["action"] == "BUY"
    assert alert_args["is_read"] is False
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
