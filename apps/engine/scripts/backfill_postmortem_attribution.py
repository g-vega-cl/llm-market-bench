"""Backfill script for post-mortem attribution and importance scores in Supabase memories.

Scans memories of type POST_MORTEM where model_name is missing/Unknown
or importance_score is defaulted to 5. Resolves true model attribution
via trades -> portfolios(owner_id) and calibrates importance score
based on trade regret and price impact.

Usage:
    ./apps/engine/.venv/bin/python3 apps/engine/scripts/backfill_postmortem_attribution.py          # Dry run
    ./apps/engine/.venv/bin/python3 apps/engine/scripts/backfill_postmortem_attribution.py --apply  # Apply updates
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import logger
from core.db import get_supabase_client


def calibrate_importance_score(
    price_change_pct: float | None,
    is_regret: bool | None,
    current_score: int | None,
) -> int:
    """Calibrate importance score on a 1-10 scale based on outcome severity."""
    # If the current score is already set and not the default 5, preserve it
    if current_score is not None and current_score != 5 and 1 <= current_score <= 10:
        return current_score

    pnl = abs(price_change_pct) if price_change_pct is not None else 0.0

    if is_regret:
        if pnl >= 5.0:
            return 9  # Major regret / critical error
        if pnl >= 2.0:
            return 8  # Substantial regret
        return 7  # Moderate regret

    if pnl >= 7.0:
        return 8  # Major winner / outlier move
    if pnl >= 3.0:
        return 7  # Significant trend capture
    if pnl >= 1.0:
        return 6  # Standard trend day
    return 5  # Baseline chop / small move


def resolve_model_name_for_trade(
    trade: dict[str, Any] | None,
    portfolios_by_id: dict[str, dict[str, Any]],
) -> str | None:
    """Resolve model name from trade and related portfolio/decision."""
    if not trade:
        return None

    # 1. From linked portfolio owner_id
    portfolio_id = trade.get("portfolio_id")
    if portfolio_id and portfolio_id in portfolios_by_id:
        owner_id = portfolios_by_id[portfolio_id].get("owner_id")
        if owner_id and str(owner_id).strip().lower() != "unknown":
            return str(owner_id).strip()

    # 2. Check if trade has an embedded decision model_name
    decisions = trade.get("decisions") or []
    if decisions and isinstance(decisions, list) and len(decisions) > 0:
        dec_model = decisions[0].get("model_name")
        if dec_model and str(dec_model).strip().lower() != "unknown":
            return str(dec_model).strip()

    return None


def run_backfill(client=None, apply: bool = False) -> dict[str, int]:
    """Execute the postmortem attribution and importance backfill."""
    sb = client or get_supabase_client()

    logger.info("Fetching POST_MORTEM memories...")
    mem_res = (
        sb.table("memories")
        .select("id, content, metadata, importance_score")
        .eq("memory_type", "POST_MORTEM")
        .execute()
    )
    memories = mem_res.data or []

    if not memories:
        logger.info("No POST_MORTEM memories found.")
        return {"scanned": 0, "updated": 0, "skipped": 0}

    logger.info(f"Found {len(memories)} POST_MORTEM memories. Fetching trades and portfolios cache...")

    # Fetch portfolios map
    port_res = sb.table("portfolios").select("id, owner_id").execute()
    portfolios_by_id = {p["id"]: p for p in (port_res.data or []) if "id" in p}

    # Fetch all relevant trades
    trade_ids = [
        str(m.get("metadata", {}).get("trade_id"))
        for m in memories
        if m.get("metadata") and m["metadata"].get("trade_id")
    ]
    trades_by_id: dict[str, dict[str, Any]] = {}
    if trade_ids:
        # Fetch trades in chunks of 50
        chunk_size = 50
        for i in range(0, len(trade_ids), chunk_size):
            chunk = trade_ids[i : i + chunk_size]
            tr_res = (
                sb.table("trades")
                .select("id, portfolio_id, reasoning, decisions(model_name)")
                .in_("id", chunk)
                .execute()
            )
            for tr in tr_res.data or []:
                trades_by_id[str(tr["id"])] = tr

    updated_count = 0
    skipped_count = 0

    for mem in memories:
        mem_id = mem["id"]
        metadata = dict(mem.get("metadata") or {})
        current_score = mem.get("importance_score")
        existing_model = metadata.get("model_name")

        needs_model_fix = not existing_model or str(existing_model).strip().lower() == "unknown"
        needs_score_fix = current_score is None or current_score == 5

        if not needs_model_fix and not needs_score_fix:
            skipped_count += 1
            continue

        trade_id = metadata.get("trade_id")
        trade = trades_by_id.get(str(trade_id)) if trade_id else None

        # Resolve model name
        new_model_name = existing_model
        if needs_model_fix:
            resolved = resolve_model_name_for_trade(trade, portfolios_by_id)
            if resolved:
                new_model_name = resolved
            elif "sys-" in mem.get("content", ""):
                new_model_name = "system"

        # Calibrate score
        price_change_pct = metadata.get("price_change_pct")
        is_regret = metadata.get("is_regret")
        new_score = calibrate_importance_score(price_change_pct, is_regret, current_score)

        update_payload: dict[str, Any] = {}
        if new_score != current_score:
            update_payload["importance_score"] = new_score

        if new_model_name != existing_model and new_model_name:
            metadata["model_name"] = new_model_name
            update_payload["metadata"] = metadata

        if not update_payload:
            skipped_count += 1
            continue

        updated_count += 1
        logger.info(
            f"[{'APPLY' if apply else 'DRY-RUN'}] Memory {mem_id}: "
            f"model_name='{existing_model}' -> '{new_model_name}', "
            f"score={current_score} -> {new_score}"
        )

        if apply:
            sb.table("memories").update(update_payload).eq("id", mem_id).execute()

    action = "Updated" if apply else "Identified for update"
    logger.info(f"Done. Scanned: {len(memories)}, {action}: {updated_count}, Skipped: {skipped_count}")
    return {"scanned": len(memories), "updated": updated_count, "skipped": skipped_count}


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill post-mortem attribution and importance scores.")
    parser.add_argument("--apply", action="store_true", help="Apply changes to Supabase database.")
    args = parser.parse_args()

    run_backfill(apply=args.apply)


if __name__ == "__main__":
    main()
