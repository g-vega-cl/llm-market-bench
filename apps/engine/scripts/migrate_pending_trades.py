"""One-time migration script to update legacy PENDING trades to terminal states."""

import sys
from pathlib import Path

# Ensure engine parent is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderStatus

from core.config import (
    ALPACA_API_KEY,
    ALPACA_PAPER_ENDPOINT,
    ALPACA_SECRET_KEY,
    logger,
)
from core.db import get_supabase_client

# Terminal Alpaca statuses mapping to Supabase alpaca_status
TERMINAL_STATUSES = {
    OrderStatus.FILLED.value: "FILLED",
    OrderStatus.REJECTED.value: "REJECTED",
    OrderStatus.CANCELED.value: "CANCELED",
    OrderStatus.EXPIRED.value: "EXPIRED",
}


def migrate_pending_trades() -> dict:
    """Find trades with PENDING status, check Alpaca status, and update in Supabase."""
    if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
        logger.error("Alpaca API keys missing. Cannot migrate orders.")
        return {"error": "missing_api_keys"}

    client = TradingClient(
        ALPACA_API_KEY,
        ALPACA_SECRET_KEY,
        paper=True,
        url_override=ALPACA_PAPER_ENDPOINT,
    )
    supabase = get_supabase_client()

    # Query trades in PENDING status
    result = (
        supabase.table("trades")
        .select("id", "alpaca_order_id")
        .eq("alpaca_status", "PENDING")
        .not_.is_("alpaca_order_id", "null")
        .execute()
    )

    trades = result.data or []
    counts = {
        "pending": len(trades),
        "filled": 0,
        "canceled": 0,
        "rejected": 0,
        "expired": 0,
        "skipped": 0,
        "errors": 0,
    }

    if not trades:
        logger.info("No legacy PENDING trades to migrate.")
        return counts

    logger.info(f"Migrating {len(trades)} PENDING trades...")

    for trade in trades:
        trade_id = trade["id"]
        order_id = trade["alpaca_order_id"]

        try:
            order = client.get_order_by_id(order_id)
            # handle both object status (Enum or string) or dict status
            status = order.status if hasattr(order, "status") else order.get("status", "")

            # Extract raw string value of status if it's an Enum (e.g. OrderStatus.FILLED)
            raw_status = status.value if hasattr(status, "value") else str(status)

            if raw_status in TERMINAL_STATUSES:
                new_status = TERMINAL_STATUSES[raw_status]
                update_payload = {"alpaca_status": new_status}

                # If filled, also set filled_at
                if raw_status == OrderStatus.FILLED.value:
                    filled_at = getattr(order, "filled_at", None)
                    if filled_at:
                        if hasattr(filled_at, "isoformat"):
                            update_payload["alpaca_filled_at"] = filled_at.isoformat()
                        else:
                            update_payload["alpaca_filled_at"] = str(filled_at)

                supabase.table("trades").update(update_payload).eq("id", trade_id).execute()
                counts[new_status.lower()] += 1
                logger.info(f"  {order_id}: PENDING → {new_status}")
            else:
                counts["skipped"] += 1
                logger.debug(f"  {order_id}: still {raw_status}, skipping")

        except Exception as exc:
            logger.error(f"  {order_id}: Failed to migrate: {exc}")
            counts["errors"] += 1

    return counts


if __name__ == "__main__":
    migrate_pending_trades()
