"""Sync Alpaca order fill status back to Supabase trades table.

Decoupled from the engine run lifecycle. Designed to be called as a cron job
(every 5-10 minutes during market hours). Queries trades with alpaca_status
= 'SUBMITTED' and checks their fill status in Alpaca.

Usage:
    ./apps/engine/.venv/bin/python3 apps/engine/scripts/sync_alpaca_orders.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import UTC, datetime, timedelta

from alpaca.common.exceptions import APIError
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderStatus

from core.config import (
    ALPACA_API_KEY,
    ALPACA_PAPER_ENDPOINT,
    ALPACA_SECRET_KEY,
    logger,
)
from core.db import get_supabase_client

# Only sync orders submitted in the last 24 hours (DAY orders expire end of day)
MAX_AGE_HOURS = 24

# Terminal Alpaca statuses that mean "done, don't poll again"
TERMINAL_STATUSES = {
    OrderStatus.FILLED.value: "FILLED",
    OrderStatus.REJECTED.value: "REJECTED",
    OrderStatus.CANCELED.value: "CANCELED",
    OrderStatus.EXPIRED.value: "EXPIRED",
}


def sync_orders() -> dict:
    """Query SUBMITTED trades, check Alpaca, update status.

    Returns:
        dict with counts: {submitted, filled, rejected, canceled, expired, errors, skipped}
    """
    if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
        logger.error("Alpaca API keys missing. Cannot sync orders.")
        return {"error": "missing_api_keys"}

    client = TradingClient(
        ALPACA_API_KEY,
        ALPACA_SECRET_KEY,
        paper=True,
        url_override=ALPACA_PAPER_ENDPOINT,
    )
    supabase = get_supabase_client()

    cutoff = (datetime.now(UTC) - timedelta(hours=MAX_AGE_HOURS)).isoformat()

    # Query SUBMITTED trades
    result = (
        supabase.table("trades")
        .select("id", "alpaca_order_id", "alpaca_status")
        .eq("alpaca_status", "SUBMITTED")
        .not_.is_("alpaca_order_id", "null")
        .gte("alpaca_submitted_at", cutoff)
        .execute()
    )

    trades = result.data or []
    counts = {
        "submitted": len(trades),
        "filled": 0,
        "rejected": 0,
        "canceled": 0,
        "expired": 0,
        "errors": 0,
        "skipped": 0,
    }

    if not trades:
        logger.info("No SUBMITTED orders to sync.")
        return counts

    logger.info(f"Syncing {len(trades)} SUBMITTED orders...")

    for trade in trades:
        trade_id = trade["id"]
        order_id = trade["alpaca_order_id"]

        try:
            order = client.get_order_by_id(order_id)
            status = order.status if hasattr(order, "status") else order.get("status", "")

            if status in TERMINAL_STATUSES:
                new_status = TERMINAL_STATUSES[status]
                update_payload: dict = {"alpaca_status": new_status}

                if status == OrderStatus.FILLED.value and hasattr(order, "filled_at") and order.filled_at:
                    update_payload["alpaca_filled_at"] = order.filled_at.isoformat()

                supabase.table("trades").update(update_payload).eq("id", trade_id).execute()
                counts[new_status.lower()] += 1
                logger.info(f"  {order_id}: {status} → {new_status}")
            else:
                # Still pending — skip, will retry next sync
                counts["skipped"] += 1
                logger.debug(f"  {order_id}: still {status}, skipping")

        except APIError as exc:
            if hasattr(exc, "status_code") and exc.status_code == 404:
                logger.warning(f"  {order_id}: not found in Alpaca (may have been cancelled)")
                counts["skipped"] += 1
            else:
                logger.error(f"  {order_id}: Alpaca API error: {exc}")
                counts["errors"] += 1
        except Exception as exc:
            logger.error(f"  {order_id}: unexpected error: {exc}")
            counts["errors"] += 1

    logger.info(
        f"Sync complete: {counts['filled']} filled, {counts['rejected']} rejected, "
        f"{counts['canceled']} canceled, {counts['expired']} expired, "
        f"{counts['skipped']} still pending, {counts['errors']} errors "
        f"(out of {counts['submitted']} total)"
    )
    return counts


if __name__ == "__main__":
    sync_orders()
