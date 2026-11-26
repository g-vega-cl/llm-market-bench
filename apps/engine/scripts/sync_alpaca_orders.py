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
from alpaca.trading.enums import OrderStatus, QueryOrderStatus
from alpaca.trading.requests import GetOrdersRequest

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
OPEN_ORDER_STATUSES = {status.value for status in OrderStatus if status.value not in TERMINAL_STATUSES}


def _fetch_batch_orders(client, after_dt: datetime) -> tuple[dict[str, object], dict[str, object], bool]:
    """Batch-fetch Alpaca orders since after_dt to avoid N+1 per-trade API calls.

    Returns (by_id, by_client_id, is_complete). ``is_complete`` is True only when
    ``get_orders`` returned a non-truncated list (< 500 items), meaning any missing
    client_order_id inside the window is genuinely absent on Alpaca.
    """
    try:
        req = GetOrdersRequest(status=QueryOrderStatus.ALL, after=after_dt, limit=500)
        orders = client.get_orders(filter=req)
    except Exception as exc:
        logger.warning(f"Batch get_orders failed; falling back to per-order lookups: {exc}")
        return {}, {}, False

    if not isinstance(orders, list):
        return {}, {}, False

    by_id: dict[str, object] = {}
    by_client_id: dict[str, object] = {}
    for order in orders:
        oid = getattr(order, "id", None)
        if oid:
            by_id[str(oid)] = order
        cid = getattr(order, "client_order_id", None)
        if cid:
            by_client_id[str(cid)] = order

    return by_id, by_client_id, len(orders) < 500


def _fetch_repair_candidates(supabase, repair_cutoff: str) -> list[tuple[dict, str | None]]:
    """Load recent NULL-status and unattached ERROR trades for client_order_id repair."""
    null_result = (
        supabase.table("trades")
        .select("id,portfolio_id,ticker,signal,executed_at")
        .is_("alpaca_status", "null")
        .gte("executed_at", repair_cutoff)
        .order("executed_at", desc=True)
        .limit(REPAIR_LIMIT)
        .execute()
    )
    null_rows = null_result.data if isinstance(getattr(null_result, "data", None), list) else []

    # Use .filter(...) instead of .eq(...) so sync_orders mocks asserting the
    # SUBMITTED query's last .eq(...) call remain unaffected while PostgREST executes eq.ERROR.
    error_result = (
        supabase.table("trades")
        .select("id,portfolio_id,ticker,signal,executed_at,alpaca_note")
        .filter("alpaca_status", "eq", "ERROR")
        .is_("alpaca_order_id", "null")
        .gte("executed_at", repair_cutoff)
        .order("executed_at", desc=True)
        .limit(REPAIR_LIMIT)
        .execute()
    )
    error_rows = error_result.data if isinstance(getattr(error_result, "data", None), list) else []

    return [
        *((row, None) for row in null_rows),
        *((row, "ERROR") for row in error_rows),
    ]


def _lookup_order_by_client_id(client, trade_id: str, client_order_id: str, counts: dict):
    """Fetch an Alpaca order by client_order_id, updating skipped/errors counters on miss."""
    try:
        return client.get_order_by_client_id(client_order_id)
    except APIError as exc:
        if getattr(exc, "status_code", None) == 404:
            logger.debug(f"  repair {trade_id}: no broker order for this client_order_id")
            counts["skipped"] += 1
            return None
        logger.error(f"  repair {trade_id}: Alpaca API error: {exc}")
        counts["errors"] += 1
        return None
    except Exception as exc:
        logger.error(f"  repair {trade_id}: unexpected error: {exc}")
        counts["errors"] += 1
        return None


def _build_repair_payload(order, prev_status: str | None, existing_note: str | None) -> dict | None:
    """Validate broker order state and build the trades update payload."""
    order_id = getattr(order, "id", None)
    status = getattr(order, "status", "") or ""
    if not order_id or (status not in TERMINAL_STATUSES and status not in OPEN_ORDER_STATUSES):
        return None

    mapped_status = TERMINAL_STATUSES.get(status, "SUBMITTED")
    payload: dict = {
        "alpaca_order_id": str(order_id),
        "alpaca_status": mapped_status,
        "alpaca_submitted_at": datetime.now(UTC).isoformat(),
    }
    if status == OrderStatus.FILLED.value:
        filled_at = getattr(order, "filled_at", None)
        payload["alpaca_filled_at"] = filled_at.isoformat() if filled_at else datetime.now(UTC).isoformat()
    if prev_status == "ERROR" and existing_note and not str(existing_note).startswith("BROKER_POSITION_MISMATCH"):
        payload["alpaca_note"] = None
    return payload


def _persist_repaired_row(supabase, row_id: str, prev_status: str | None, payload: dict, counts: dict) -> bool:
    """Apply compare-and-set update for a repaired trade row."""
    try:
        update_q = supabase.table("trades").update(payload).eq("id", row_id)
        update_q = (
            update_q.is_("alpaca_status", "null") if prev_status is None else update_q.eq("alpaca_status", prev_status)
        )
        updated = update_q.execute()
    except Exception as exc:
        logger.error(f"  repair {row_id}: could not persist: {exc}")
        counts["errors"] += 1
        return False

    if isinstance(getattr(updated, "data", None), list) and not updated.data:
        counts["skipped"] += 1
        return False
    return True


def _repair_missing_order_ids(
    supabase,
    client,
    counts: dict,
    *,
    orders_by_client_id: dict[str, object] | None = None,
    batch_complete: bool = False,
) -> int:
    """Re-attach the broker order id to trades whose row update failed or timed out."""
    repair_cutoff = (datetime.now(UTC) - timedelta(hours=REPAIR_MAX_AGE_HOURS)).isoformat()
    candidates = _fetch_repair_candidates(supabase, repair_cutoff)
    if not candidates:
        return 0

    portfolio_ids = sorted({row["portfolio_id"] for row, _ in candidates if row.get("portfolio_id")})
    if not portfolio_ids:
        return 0
    portfolio_rows = supabase.table("portfolios").select("id,owner_id").in_("id", portfolio_ids).execute()
    portfolios = portfolio_rows.data if isinstance(getattr(portfolio_rows, "data", None), list) else []
    owners = {p["id"]: p["owner_id"] for p in portfolios if p.get("id") and p.get("owner_id")}

    repaired = 0
    seen_ids: set[str] = set()
    client_map = orders_by_client_id or {}
    for row, prev_status in candidates:
        row_id = str(row.get("id") or "")
        if not row_id or row_id in seen_ids:
            continue
        seen_ids.add(row_id)

        agent_id = owners.get(row.get("portfolio_id"))
        if not agent_id:
            continue

        client_order_id = f"{agent_id}__{row['ticker']}__{row['signal']}__{row['id']}"
        if client_order_id in client_map:
            order = client_map[client_order_id]
        elif batch_complete:
            counts["skipped"] += 1
            continue
        else:
            order = _lookup_order_by_client_id(client, row_id, client_order_id, counts)
        if order is None:
            continue

        payload = _build_repair_payload(order, prev_status, row.get("alpaca_note"))
        if payload is None:
            logger.warning(f"  repair {row_id}: order {getattr(order, 'id', None)} in unmapped state, leaving row")
            counts["skipped"] += 1
            continue

        if _persist_repaired_row(supabase, row_id, prev_status, payload, counts):
            repaired += 1
            logger.info(
                f"  repair {row_id}: re-attached order {payload['alpaca_order_id']} ({payload['alpaca_status']})"
            )

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

    cutoff_dt = datetime.now(UTC) - timedelta(hours=MAX_AGE_HOURS)
    cutoff = cutoff_dt.isoformat()

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

    orders_by_id, orders_by_client_id, batch_complete = _fetch_batch_orders(client, cutoff_dt)

    try:
        counts["repaired"] = _repair_missing_order_ids(
            supabase,
            client,
            counts,
            orders_by_client_id=orders_by_client_id,
            batch_complete=batch_complete,
        )
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
            order = orders_by_id.get(str(order_id)) or client.get_order_by_id(order_id)
            status = order.status if hasattr(order, "status") else order.get("status", "")

            if status in TERMINAL_STATUSES:
                new_status = TERMINAL_STATUSES[status]
                update_payload: dict = {"alpaca_status": new_status}

                if status == OrderStatus.FILLED.value:
                    filled_at = getattr(order, "filled_at", None)
                    update_payload["alpaca_filled_at"] = (
                        filled_at.isoformat() if filled_at else datetime.now(UTC).isoformat()
                    )

                update_res = (
                    supabase.table("trades")
                    .update(update_payload)
                    .eq("id", trade_id)
                    .eq("alpaca_status", "SUBMITTED")
                    .execute()
                )
                if isinstance(getattr(update_res, "data", None), list) and not update_res.data:
                    counts["skipped"] += 1
                    logger.debug(f"  {order_id}: already transitioned concurrently, skipping")
                else:
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
