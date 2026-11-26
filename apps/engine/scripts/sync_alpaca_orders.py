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

# Only sync orders submitted in the last 96 hours (handles weekends and cron failures)
MAX_AGE_HOURS = 96

# Terminal Alpaca statuses that mean "done, don't poll again"
TERMINAL_STATUSES = {
    OrderStatus.FILLED.value: "FILLED",
    OrderStatus.REJECTED.value: "REJECTED",
    OrderStatus.CANCELED.value: "CANCELED",
    OrderStatus.EXPIRED.value: "EXPIRED",
}

# A row with a NULL alpaca_status only means "no mirror status was ever written".
# Repair therefore looks at the recent window where a failed write is plausible,
# newest-first ordering is explicit (PostgREST has no implicit order), and the
# update is a compare-and-set so it can never clobber a status written by a
# concurrent sync run.
REPAIR_MAX_AGE_HOURS = 24
REPAIR_LIMIT = 100
OPEN_ORDER_STATUSES = {"new", "accepted", "pending_new", "accepted_for_bidding", "partially_filled", "held"}


def _repair_missing_order_ids(supabase, client, counts: dict) -> int:
    """Re-attach the broker order id to trades whose row update failed.

    `client_order_id` is deterministic (`{agent_id}__{ticker}__{signal}__{trade_id}`),
    so an order Alpaca accepted can be found again without re-submitting
    anything — this path must never place an order.

    Writes `alpaca_submitted_at` alongside the status: the reconciler filters on
    it, and a SUBMITTED row without it could never advance to a terminal state.
    """
    repair_cutoff = (datetime.now(UTC) - timedelta(hours=REPAIR_MAX_AGE_HOURS)).isoformat()
    result = (
        supabase.table("trades")
        .select("id,portfolio_id,ticker,signal,executed_at")
        .is_("alpaca_status", "null")
        .gte("executed_at", repair_cutoff)
        .order("executed_at", desc=True)
        .limit(REPAIR_LIMIT)
        .execute()
    )
    rows = result.data if isinstance(getattr(result, "data", None), list) else []
    if not rows:
        return 0

    portfolio_ids = sorted({row["portfolio_id"] for row in rows if row.get("portfolio_id")})
    portfolio_rows = supabase.table("portfolios").select("id,owner_id").in_("id", portfolio_ids).execute()
    portfolios = portfolio_rows.data if isinstance(getattr(portfolio_rows, "data", None), list) else []
    owners = {p["id"]: p["owner_id"] for p in portfolios}

    repaired = 0
    for row in rows:
        agent_id = owners.get(row.get("portfolio_id"))
        if not agent_id:
            continue

        client_order_id = f"{agent_id}__{row['ticker']}__{row['signal']}__{row['id']}"
        try:
            order = client.get_order_by_client_id(client_order_id)
        except APIError as exc:
            if getattr(exc, "status_code", None) == 404:
                logger.debug(f"  repair {row['id']}: no broker order for this client_order_id")
                counts["skipped"] += 1
                continue
            logger.error(f"  repair {row['id']}: Alpaca API error: {exc}")
            counts["errors"] += 1
            continue
        except Exception as exc:
            logger.error(f"  repair {row['id']}: unexpected error: {exc}")
            counts["errors"] += 1
            continue

        order_id = getattr(order, "id", None)
        status = getattr(order, "status", "") or ""
        if not order_id or (status not in TERMINAL_STATUSES and status not in OPEN_ORDER_STATUSES):
            logger.warning(f"  repair {row['id']}: order {order_id} in unmapped state '{status}', leaving row")
            counts["skipped"] += 1
            continue

        payload = {
            "alpaca_order_id": str(order_id),
            "alpaca_status": TERMINAL_STATUSES.get(status, "SUBMITTED"),
            "alpaca_submitted_at": datetime.now(UTC).isoformat(),
        }
        try:
            updated = (
                supabase.table("trades").update(payload).eq("id", row["id"]).is_("alpaca_status", "null").execute()
            )
        except Exception as exc:
            logger.error(f"  repair {row['id']}: could not persist: {exc}")
            counts["errors"] += 1
            continue

        if isinstance(getattr(updated, "data", None), list) and not updated.data:
            # Another writer got there first; nothing was overwritten.
            counts["skipped"] += 1
            continue

        repaired += 1
        logger.info(f"  repair {row['id']}: re-attached order {order_id} ({status})")

    return repaired


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
        "repaired": 0,
    }

    try:
        counts["repaired"] = _repair_missing_order_ids(supabase, client, counts)
    except Exception as exc:
        # A repair failure must never take down the reconciliation that follows.
        logger.error(f"Order-id repair pass failed; continuing with sync: {exc}")

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
