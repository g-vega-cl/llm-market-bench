"""Hermetic tests for recipe studio queue worker."""

from unittest.mock import MagicMock

from recipes.schema import DAGEdge, DAGNode, RecipeGraph
from recipes.worker import process_next_recipe_job


def _make_mock_supabase():
    client = MagicMock()
    # Mock tables
    queue_table = MagicMock()
    recipes_table = MagicMock()
    bars_table = MagicMock()
    news_table = MagicMock()
    alerts_table = MagicMock()

    def table_router(table_name):
        if table_name == "recipe_execution_queue":
            return queue_table
        if table_name == "strategy_recipes":
            return recipes_table
        if table_name == "recipe_intraday_bars":
            return bars_table
        if table_name == "recipe_news_corpus":
            return news_table
        if table_name == "recipe_alerts_inbox":
            return alerts_table
        return MagicMock()

    client.table.side_effect = table_router
    bars_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
    bars_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
        {
            "close": 500.0,
            "open": 499.0,
            "high": 502.0,
            "low": 498.0,
            "volume": 10000,
            "bar_time_utc": "2026-03-02T10:00:00Z",
        }
    ]
    news_table.select.return_value.order.return_value.limit.return_value.execute.return_value.data = []
    return client, queue_table, recipes_table, alerts_table


def test_process_next_job_empty_queue():
    client, _, _, _ = _make_mock_supabase()
    client.rpc.return_value.execute.return_value.data = []

    res = process_next_recipe_job(client)
    assert res is False


def test_process_backtest_job_success():
    client, queue_table, recipes_table, _ = _make_mock_supabase()

    # Pop job
    client.rpc.return_value.execute.return_value.data = [
        {
            "job_id": "job-111",
            "job_recipe_id": "rec-222",
            "job_user_id": "usr-333",
            "job_mode": "backtest",
            "job_priority": 10,
            "job_weeks_requested": ["2026-W10"],
        }
    ]

    recipe = RecipeGraph(
        name="SPY Voxel Trend",
        nodes=[
            DAGNode(id="n0", type="price_tape", title="Price Feed", config={"ticker": "SPY"}),
            DAGNode(
                id="n1",
                type="technical_gate",
                config={"conditions": [{"metric": "price", "operator": ">=", "target": 100.0}]},
            ),
            DAGNode(id="n2", type="risk_output", config={"action": "BUY"}),
        ],
        edges=[
            DAGEdge(**{"from": "n0", "to": "n1"}),
            DAGEdge(**{"from": "n1", "to": "n2"}),
        ],
    )

    # Strategy recipe select
    recipe_select = MagicMock()
    recipe_select.execute.return_value.data = {
        "id": "rec-222",
        "name": "SPY Voxel Trend",
        "graph_json": recipe.model_dump(),
        "trial_count": 5,
    }
    recipes_table.select.return_value.eq.return_value.single.return_value = recipe_select

    # Execute queue updates
    queue_update = MagicMock()
    queue_table.update.return_value.eq.return_value = queue_update

    res = process_next_recipe_job(client)
    assert res is True

    # Check that status was updated to completed
    completed_call = False
    for call in queue_table.update.call_args_list:
        payload = call[0][0]
        if payload.get("status") == "completed":
            completed_call = True
            assert payload.get("progress_pct") == 100
            assert "result_json" in payload
    assert completed_call is True


def test_process_live_turn_deposits_alert():
    client, queue_table, recipes_table, alerts_table = _make_mock_supabase()

    client.rpc.return_value.execute.return_value.data = [
        {
            "job_id": "job-live-1",
            "job_recipe_id": "rec-live-2",
            "job_user_id": "usr-live-3",
            "job_mode": "live_turn",
            "job_priority": 1,
            "job_weeks_requested": [],
        }
    ]

    recipe = RecipeGraph(
        name="QQQ Breakout",
        cadence="5m",
        nodes=[
            DAGNode(id="n0", type="price_tape", config={"ticker": "QQQ"}),
            DAGNode(
                id="n1",
                type="technical_gate",
                config={"conditions": [{"metric": "price", "operator": ">", "target": 10.0}]},
            ),
            DAGNode(id="n2", type="risk_output", config={"action": "BUY"}),
        ],
        edges=[
            DAGEdge(**{"from": "n0", "to": "n1"}),
            DAGEdge(**{"from": "n1", "to": "n2"}),
        ],
    )

    recipe_select = MagicMock()
    recipe_select.execute.return_value.data = {
        "id": "rec-live-2",
        "name": "QQQ Breakout",
        "graph_json": recipe.model_dump(),
        "trial_count": 0,
    }
    recipes_table.select.return_value.eq.return_value.single.return_value = recipe_select

    res = process_next_recipe_job(client)
    assert res is True

    # Assert alert was inserted into inbox
    alerts_table.insert.assert_called_once()
    alert_args = alerts_table.insert.call_args[0][0]
    assert alert_args["user_id"] == "usr-live-3"
    assert alert_args["ticker"] == "QQQ"
    assert alert_args["action"] == "BUY"
    assert alert_args["is_read"] is False
