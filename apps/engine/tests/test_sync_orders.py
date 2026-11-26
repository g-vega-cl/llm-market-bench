"""Tests for the Alpaca order status sync script."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from alpaca.trading.enums import OrderStatus

# Ensure engine parent is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.sync_alpaca_orders import sync_orders


def test_max_age_hours_is_96():
    """Verify that MAX_AGE_HOURS is set to 96 to handle weekend gaps and cron failures.

    This acts as our TDD reproduction/invariant test. It will fail when MAX_AGE_HOURS is 24.
    """
    from scripts import sync_alpaca_orders

    assert sync_alpaca_orders.MAX_AGE_HOURS == 96


def test_sync_orders_queries_with_correct_cutoff():
    """Verify sync_orders queries Supabase with the correct gte cutoff timestamp."""
    mock_supabase = MagicMock()
    mock_alpaca = MagicMock()

    # Mock the chain: supabase.table().select().eq().not_.is_().gte().execute()
    mock_table = mock_supabase.table.return_value
    mock_select = mock_table.select.return_value
    mock_eq = mock_select.eq.return_value
    mock_not = mock_eq.not_  # accessed as a property/attribute
    mock_is = mock_not.is_.return_value
    mock_gte = mock_is.gte.return_value
    mock_gte.execute.return_value = MagicMock(data=[])

    with (
        patch("scripts.sync_alpaca_orders.ALPACA_API_KEY", "mock-key"),
        patch("scripts.sync_alpaca_orders.ALPACA_SECRET_KEY", "mock-secret"),
        patch("scripts.sync_alpaca_orders.get_supabase_client", return_value=mock_supabase),
        patch("scripts.sync_alpaca_orders.TradingClient", return_value=mock_alpaca),
    ):
        result = sync_orders()

    assert result == {
        "submitted": 0,
        "filled": 0,
        "rejected": 0,
        "canceled": 0,
        "expired": 0,
        "errors": 0,
        "skipped": 0,
        "repaired": 0,
    }

    # Verify query structure
    mock_supabase.table.assert_called_with("trades")
    mock_table.select.assert_any_call("id", "alpaca_order_id", "alpaca_status")
    mock_select.eq.assert_called_with("alpaca_status", "SUBMITTED")
    mock_not.is_.assert_called_with("alpaca_order_id", "null")
    mock_is.gte.assert_called()  # Verifies gte was called with cutoff


def test_sync_orders_updates_terminal_and_skips_non_terminal():
    """Verify sync_orders updates terminal states and skips non-terminal states."""
    mock_supabase = MagicMock()
    mock_alpaca = MagicMock()

    # We mock 3 trades:
    # 1. Filled trade
    # 2. Rejected trade
    # 3. Still pending trade
    mock_trades = [
        {"id": "trade-1", "alpaca_order_id": "order-1", "alpaca_status": "SUBMITTED"},
        {"id": "trade-2", "alpaca_order_id": "order-2", "alpaca_status": "SUBMITTED"},
        {"id": "trade-3", "alpaca_order_id": "order-3", "alpaca_status": "SUBMITTED"},
    ]

    mock_table = mock_supabase.table.return_value
    mock_select = mock_table.select.return_value
    mock_eq = mock_select.eq.return_value
    mock_not = mock_eq.not_  # accessed as a property/attribute
    mock_is = mock_not.is_.return_value
    mock_gte = mock_is.gte.return_value
    mock_gte.execute.return_value = MagicMock(data=mock_trades)

    # Mock order details from Alpaca
    mock_order_1 = MagicMock()
    mock_order_1.status = OrderStatus.FILLED.value
    mock_order_1.filled_at = MagicMock()
    mock_order_1.filled_at.isoformat.return_value = "2026-05-24T16:00:00Z"

    mock_order_2 = MagicMock()
    mock_order_2.status = OrderStatus.REJECTED.value

    mock_order_3 = MagicMock()
    mock_order_3.status = OrderStatus.PARTIALLY_FILLED.value  # Non-terminal

    orders_map = {
        "order-1": mock_order_1,
        "order-2": mock_order_2,
        "order-3": mock_order_3,
    }

    def get_order_by_id_mock(order_id):
        if order_id in orders_map:
            return orders_map[order_id]
        raise ValueError("Unknown order ID")

    mock_alpaca.get_order_by_id.side_effect = get_order_by_id_mock

    # Mock update calls
    mock_update = mock_table.update.return_value
    mock_update_eq = mock_update.eq.return_value
    mock_update_eq.execute.return_value = MagicMock()

    with (
        patch("scripts.sync_alpaca_orders.ALPACA_API_KEY", "mock-key"),
        patch("scripts.sync_alpaca_orders.ALPACA_SECRET_KEY", "mock-secret"),
        patch("scripts.sync_alpaca_orders.get_supabase_client", return_value=mock_supabase),
        patch("scripts.sync_alpaca_orders.TradingClient", return_value=mock_alpaca),
    ):
        result = sync_orders()

    assert result == {
        "submitted": 3,
        "filled": 1,
        "rejected": 1,
        "canceled": 0,
        "expired": 0,
        "errors": 0,
        "skipped": 1,
        "repaired": 0,
    }

    # Verify update calls (including CAS predicate on SUBMITTED)
    mock_table.update.assert_any_call({"alpaca_status": "FILLED", "alpaca_filled_at": "2026-05-24T16:00:00Z"})
    mock_update.eq.assert_any_call("id", "trade-1")

    mock_table.update.assert_any_call({"alpaca_status": "REJECTED"})
    mock_update.eq.assert_any_call("id", "trade-2")
    mock_update_eq.eq.assert_any_call("alpaca_status", "SUBMITTED")

    # The third (non-terminal) order should not have triggered an update call
    assert mock_table.update.call_count == 2


def test_sync_repairs_trade_missing_its_order_id():
    """A NULL alpaca_order_id is re-attached via the deterministic client_order_id."""
    mock_supabase = MagicMock()
    mock_alpaca = MagicMock()

    trades_table = MagicMock()
    portfolios_table = MagicMock()
    mock_supabase.table.side_effect = lambda name: {
        "trades": trades_table,
        "portfolios": portfolios_table,
    }.get(name, MagicMock())

    # Repair pass: one trade with a null status; the SUBMITTED pass finds nothing.
    repair_chain = (
        trades_table.select.return_value.is_.return_value.gte.return_value.order.return_value.limit.return_value
    )
    repair_chain.execute.return_value = MagicMock(
        data=[{"id": "trade-x", "portfolio_id": "pf-1", "ticker": "SPY", "signal": "BUY"}],
    )
    (
        trades_table.select.return_value.eq.return_value.not_.is_.return_value.gte.return_value.execute.return_value
    ) = MagicMock(data=[])
    portfolios_table.select.return_value.in_.return_value.execute.return_value = MagicMock(
        data=[{"id": "pf-1", "owner_id": "live-spy-trader"}]
    )

    order = MagicMock()
    order.id = "alpaca-order-9"
    order.status = "filled"
    mock_alpaca.get_order_by_client_id.return_value = order

    with (
        patch("scripts.sync_alpaca_orders.ALPACA_API_KEY", "mock-key"),
        patch("scripts.sync_alpaca_orders.ALPACA_SECRET_KEY", "mock-secret"),
        patch("scripts.sync_alpaca_orders.get_supabase_client", return_value=mock_supabase),
        patch("scripts.sync_alpaca_orders.TradingClient", return_value=mock_alpaca),
    ):
        result = sync_orders()

    assert result["repaired"] == 1
    mock_alpaca.get_order_by_client_id.assert_called_once_with("live-spy-trader__SPY__BUY__trade-x")

    updates = [call.args[0] for call in trades_table.update.call_args_list if call.args]
    assert any(
        payload.get("alpaca_order_id") == "alpaca-order-9"
        and payload.get("alpaca_status") == "FILLED"
        and payload.get("alpaca_submitted_at")
        for payload in updates
    )


def test_sync_workflow_runs_intraday():
    """The sync job must run during the session, not once after the close."""
    from pathlib import Path

    workflow = Path(__file__).resolve().parents[3] / ".github" / "workflows" / "sync-alpaca.yml"
    cron_lines = [line.strip() for line in workflow.read_text().splitlines() if line.strip().startswith("- cron:")]

    assert '- cron: "*/15 13-21 * * 1-5"' in cron_lines


def test_sync_repairs_error_trade_and_clears_error_note():
    """ERROR rows without an order_id are recovered by client_order_id and clear stale error notes."""
    mock_supabase = MagicMock()
    mock_alpaca = MagicMock()

    trades_table = MagicMock()
    portfolios_table = MagicMock()
    mock_supabase.table.side_effect = lambda name: {
        "trades": trades_table,
        "portfolios": portfolios_table,
    }.get(name, MagicMock())

    trades_table.select.return_value.is_.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[]
    )
    # ERROR query returns one timed-out BUY that Alpaca actually accepted
    trades_table.select.return_value.filter.return_value.is_.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[
            {
                "id": "trade-err",
                "portfolio_id": "pf-live",
                "ticker": "SPY",
                "signal": "BUY",
                "alpaca_note": "HTTP 503: upstream timeout",
            }
        ]
    )
    # SUBMITTED query returns empty
    trades_table.select.return_value.eq.return_value.not_.is_.return_value.gte.return_value.execute.return_value = (
        MagicMock(data=[])
    )
    portfolios_table.select.return_value.in_.return_value.execute.return_value = MagicMock(
        data=[{"id": "pf-live", "owner_id": "live-spy-trader"}]
    )

    order = MagicMock()
    order.id = "alpaca-recovered-1"
    order.status = "filled"
    order.filled_at = MagicMock()
    order.filled_at.isoformat.return_value = "2026-11-26T15:00:00Z"
    mock_alpaca.get_order_by_client_id.return_value = order

    with (
        patch("scripts.sync_alpaca_orders.ALPACA_API_KEY", "mock-key"),
        patch("scripts.sync_alpaca_orders.ALPACA_SECRET_KEY", "mock-secret"),
        patch("scripts.sync_alpaca_orders.get_supabase_client", return_value=mock_supabase),
        patch("scripts.sync_alpaca_orders.TradingClient", return_value=mock_alpaca),
    ):
        result = sync_orders()

    assert result["repaired"] == 1
    mock_alpaca.get_order_by_client_id.assert_called_once_with("live-spy-trader__SPY__BUY__trade-err")
    trades_table.update.return_value.eq.return_value.eq.assert_called_with("alpaca_status", "ERROR")
    update_payload = trades_table.update.call_args[0][0]
    assert update_payload["alpaca_filled_at"] == "2026-11-26T15:00:00Z"
    assert update_payload["alpaca_note"] is None


def test_sync_uses_batch_get_orders_without_owner_prefix_rules():
    """Batch get_orders repairs NULL rows directly without upfront owner-prefix splitting."""
    mock_supabase = MagicMock()
    mock_alpaca = MagicMock()

    trades_table = MagicMock()
    portfolios_table = MagicMock()
    mock_supabase.table.side_effect = lambda name: {
        "trades": trades_table,
        "portfolios": portfolios_table,
    }.get(name, MagicMock())

    trades_table.select.return_value.is_.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"id": "trade-null-1", "portfolio_id": "pf-live", "ticker": "SPY", "signal": "BUY"}]
    )
    trades_table.select.return_value.filter.return_value.is_.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[]
    )
    trades_table.select.return_value.eq.return_value.not_.is_.return_value.gte.return_value.execute.return_value = (
        MagicMock(data=[{"id": "trade-sub-1", "alpaca_order_id": "ord-sub-1", "alpaca_status": "SUBMITTED"}])
    )
    portfolios_table.select.return_value.in_.return_value.execute.return_value = MagicMock(
        data=[{"id": "pf-live", "owner_id": "live-spy-trader"}]
    )

    repaired_order = MagicMock(
        id="ord-rep-1", status="accepted", client_order_id="live-spy-trader__SPY__BUY__trade-null-1"
    )
    synced_order = MagicMock(id="ord-sub-1", status="canceled", client_order_id="other")
    mock_alpaca.get_orders.return_value = [repaired_order, synced_order]

    with (
        patch("scripts.sync_alpaca_orders.ALPACA_API_KEY", "mock-key"),
        patch("scripts.sync_alpaca_orders.ALPACA_SECRET_KEY", "mock-secret"),
        patch("scripts.sync_alpaca_orders.get_supabase_client", return_value=mock_supabase),
        patch("scripts.sync_alpaca_orders.TradingClient", return_value=mock_alpaca),
    ):
        result = sync_orders()

    assert result["repaired"] == 1
    assert result["canceled"] == 1
    mock_alpaca.get_order_by_client_id.assert_not_called()
    mock_alpaca.get_order_by_id.assert_not_called()


def test_sync_orders_cas_skips_concurrent_transition_and_sets_filled_at_fallback():
    """Concurrent transitions matching 0 rows increment skipped; FILLED without filled_at falls back to UTC now."""
    mock_supabase = MagicMock()
    mock_alpaca = MagicMock()

    trades_table = MagicMock()
    mock_supabase.table.return_value = trades_table
    trades_table.select.return_value.eq.return_value.not_.is_.return_value.gte.return_value.execute.return_value = (
        MagicMock(
            data=[
                {"id": "trade-race", "alpaca_order_id": "ord-race", "alpaca_status": "SUBMITTED"},
            ]
        )
    )
    trades_table.select.return_value.is_.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[]
    )
    trades_table.select.return_value.filter.return_value.is_.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[]
    )
    # CAS update matches 0 rows (already transitioned elsewhere)
    trades_table.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

    order = MagicMock(id="ord-race", status=OrderStatus.FILLED.value, filled_at=None, client_order_id="c-1")
    mock_alpaca.get_orders.return_value = [order]

    with (
        patch("scripts.sync_alpaca_orders.ALPACA_API_KEY", "mock-key"),
        patch("scripts.sync_alpaca_orders.ALPACA_SECRET_KEY", "mock-secret"),
        patch("scripts.sync_alpaca_orders.get_supabase_client", return_value=mock_supabase),
        patch("scripts.sync_alpaca_orders.TradingClient", return_value=mock_alpaca),
    ):
        result = sync_orders()

    assert result["filled"] == 0
    assert result["skipped"] == 1
    update_payload = trades_table.update.call_args[0][0]
    assert update_payload["alpaca_status"] == "FILLED"
    assert isinstance(update_payload["alpaca_filled_at"], str) and len(update_payload["alpaca_filled_at"]) > 0
