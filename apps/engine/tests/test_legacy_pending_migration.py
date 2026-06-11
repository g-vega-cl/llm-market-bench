"""Tests for the legacy PENDING trades migration script."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from alpaca.trading.enums import OrderStatus

# Ensure engine parent is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.migrate_pending_trades import migrate_pending_trades


def test_migrate_pending_trades_no_keys():
    """Verify that migration returns error dict when Alpaca credentials are missing."""
    with (
        patch("scripts.migrate_pending_trades.ALPACA_API_KEY", ""),
        patch("scripts.migrate_pending_trades.ALPACA_SECRET_KEY", ""),
    ):
        result = migrate_pending_trades()

    assert result == {"error": "missing_api_keys"}


def test_migrate_pending_trades_no_records():
    """Verify migration handles the case where no PENDING records exist in Supabase."""
    mock_supabase = MagicMock()
    mock_table = mock_supabase.table.return_value
    mock_select = mock_table.select.return_value
    mock_eq = mock_select.eq.return_value
    mock_not = mock_eq.not_
    mock_is = mock_not.is_.return_value
    mock_is.execute.return_value = MagicMock(data=[])

    with (
        patch("scripts.migrate_pending_trades.ALPACA_API_KEY", "mock-key"),
        patch("scripts.migrate_pending_trades.ALPACA_SECRET_KEY", "mock-secret"),
        patch("scripts.migrate_pending_trades.get_supabase_client", return_value=mock_supabase),
        patch("scripts.migrate_pending_trades.TradingClient"),
    ):
        result = migrate_pending_trades()

    assert result == {
        "pending": 0,
        "filled": 0,
        "canceled": 0,
        "rejected": 0,
        "expired": 0,
        "skipped": 0,
        "errors": 0,
    }


def test_migrate_pending_trades_updates_correctly():
    """Verify pending trades are resolved to their correct terminal states."""
    mock_supabase = MagicMock()
    mock_alpaca = MagicMock()

    # 3 mock PENDING trades
    mock_trades = [
        {"id": "trade-1", "alpaca_order_id": "order-1"},
        {"id": "trade-2", "alpaca_order_id": "order-2"},
        {"id": "trade-3", "alpaca_order_id": "order-3"},
    ]

    mock_table = mock_supabase.table.return_value
    mock_select = mock_table.select.return_value
    mock_eq = mock_select.eq.return_value
    mock_not = mock_eq.not_
    mock_is = mock_not.is_.return_value
    mock_is.execute.return_value = MagicMock(data=mock_trades)

    # Mock order details from Alpaca
    mock_order_1 = MagicMock()
    mock_order_1.status = OrderStatus.FILLED
    mock_order_1.filled_at = MagicMock()
    mock_order_1.filled_at.isoformat.return_value = "2026-05-01T15:00:00Z"

    mock_order_2 = MagicMock()
    mock_order_2.status = OrderStatus.CANCELED

    mock_order_3 = MagicMock()
    mock_order_3.status = OrderStatus.NEW  # Non-terminal

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
        patch("scripts.migrate_pending_trades.ALPACA_API_KEY", "mock-key"),
        patch("scripts.migrate_pending_trades.ALPACA_SECRET_KEY", "mock-secret"),
        patch("scripts.migrate_pending_trades.get_supabase_client", return_value=mock_supabase),
        patch("scripts.migrate_pending_trades.TradingClient", return_value=mock_alpaca),
    ):
        result = migrate_pending_trades()

    assert result == {
        "pending": 3,
        "filled": 1,
        "canceled": 1,
        "rejected": 0,
        "expired": 0,
        "skipped": 1,
        "errors": 0,
    }

    # Verify update payloads
    mock_table.update.assert_any_call({"alpaca_status": "FILLED", "alpaca_filled_at": "2026-05-01T15:00:00Z"})
    mock_update.eq.assert_any_call("id", "trade-1")

    mock_table.update.assert_any_call({"alpaca_status": "CANCELED"})
    mock_update.eq.assert_any_call("id", "trade-2")

    # The non-terminal one shouldn't update
    assert mock_table.update.call_count == 2
