"""Hermetic tests for the Max Pain audit island (live-first auto-heal)."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest


@pytest.fixture
def mock_supabase():
    """Mock Supabase client with chainable query builder methods."""
    client = MagicMock()
    table_mock = MagicMock()
    client.table.return_value = table_mock

    table_mock.select.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.execute.return_value = MagicMock(data=[])
    return client


@pytest.mark.asyncio
async def test_audit_max_pain_live_exit_pass_preferred_over_backfill(mock_supabase):
    """Auto-heal must try a live exit pass first and skip the modeled fallback when it clears the book."""
    from audit.max_pain_auditor import _attempt_live_max_pain_exit

    remaining = {"open": True}

    def table_router(table_name):
        mock_t = MagicMock()
        mock_t.select.return_value = mock_t
        mock_t.eq.return_value = mock_t
        mock_t.execute.side_effect = lambda: MagicMock(
            data=[{"ticker": "SPY", "quantity": 10}] if remaining["open"] else []
        )
        return mock_t

    mock_supabase.table.side_effect = table_router

    async def fake_exit(**kwargs):
        remaining["open"] = False
        return {"status": "success", "sales": [{"ticker": "SPY", "shares": 10}]}

    with patch("tasks.max_pain_task.run_max_pain_task", side_effect=fake_exit) as mock_task:
        ok = await _attempt_live_max_pain_exit(mock_supabase, "p-max-pain")

    assert ok is True
    mock_task.assert_awaited_once_with(action="exit", dry_run=False)


@pytest.mark.asyncio
async def test_audit_max_pain_live_exit_failure_returns_false(mock_supabase):
    """When the live pass leaves positions open, the auditor must fall back to the modeled exit."""
    from audit.max_pain_auditor import _attempt_live_max_pain_exit

    def table_router(table_name):
        mock_t = MagicMock()
        mock_t.select.return_value = mock_t
        mock_t.eq.return_value = mock_t
        mock_t.execute.return_value = MagicMock(data=[{"ticker": "SPY", "quantity": 10}])
        return mock_t

    mock_supabase.table.side_effect = table_router

    with patch(
        "tasks.max_pain_task.run_max_pain_task",
        new_callable=AsyncMock,
        return_value={"status": "success", "sales": []},
    ):
        ok = await _attempt_live_max_pain_exit(mock_supabase, "p-max-pain")

    assert ok is False


@pytest.mark.asyncio
async def test_audit_max_pain_portfolio_flags_and_heals_leftover(mock_supabase):
    """A leftover position after the close is flagged, then healed via the modeled RPC fallback."""
    from audit.max_pain_auditor import audit_max_pain_portfolio

    portfolio_id = "p-max-pain"

    def table_router(table_name):
        mock_t = MagicMock()
        mock_t.select.return_value = mock_t
        mock_t.eq.return_value = mock_t
        if table_name == "portfolio_positions":
            mock_t.execute.return_value = MagicMock(
                data=[
                    {
                        "ticker": "SPY",
                        "quantity": 10,
                        "average_cost_basis": 763.0,
                        "last_updated_at": "2026-10-22T14:30:00Z",
                    }
                ]
            )
        else:
            mock_t.execute.return_value = MagicMock(data=[])
        return mock_t

    mock_supabase.table.side_effect = table_router
    mock_supabase.rpc.return_value.execute.return_value = MagicMock(
        data={"trade_id": "trade-1", "cash_balance": 2370.0, "total_equity": 9800.0}
    )

    now_ny = datetime(2026, 10, 22, 16, 30, tzinfo=ZoneInfo("America/New_York"))
    with (
        patch("tasks.max_pain_task.run_max_pain_task", new_callable=AsyncMock),
        patch(
            "tasks.max_pain_task.fetch_quote_snapshot",
            return_value={"price": 0.0, "day_high": 0.0, "day_low": 0.0},
        ),
        patch(
            "tasks.evaluate_daily_predictions.fetch_intraday_prices",
            return_value=(763.0, 769.2, 762.0, 764.5),
        ),
    ):
        anomalies, healed, flagged = await audit_max_pain_portfolio(
            client=mock_supabase,
            port_by_owner={"sys-max-pain": {"id": portfolio_id, "cash_balance": 1000.0}},
            target_date="2026-10-22",
            dates_to_check=["2026-10-22"],
            now_ny=now_ny,
            auto_heal=True,
        )

    assert [a["type"] for a in anomalies] == ["UNLIQUIDATED_MAX_PAIN_POSITION"]
    assert flagged == []
    assert healed[0]["exit_mode"] == "MODELED_CLOSE"
    rpc_name, rpc_payload = mock_supabase.rpc.call_args.args
    assert rpc_name == "execute_portfolio_trade"
    assert rpc_payload["p_signal"] == "SELL"
