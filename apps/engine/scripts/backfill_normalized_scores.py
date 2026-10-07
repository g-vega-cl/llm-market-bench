"""Backfill historical prompt experiments with the Unified Risk-Adjusted Z-Score formula."""

import argparse
import asyncio
import json
import logging
import math
import sys
from datetime import date
from pathlib import Path

# Add engine directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from autoresearch.metrics import _spy_returns, compute_score
from core.db import get_async_supabase_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("backfill_normalized_scores")


async def backfill_scores(dry_run: bool = True, track_id: str | None = None) -> None:
    sb_client = await get_async_supabase_client()

    query = (
        sb_client.table("prompt_experiments")
        .select("id, variant_tag, week_start, week_end, metrics, track_id")
        .eq("prompt_name", "CORE_ANALYSIS_SYSTEM_PROMPT")
        .order("created_at")
    )
    if track_id:
        query = query.eq("track_id", track_id)

    res = await query.execute()
    rows = res.data or []
    logger.info("Fetched %d prompt experiment records to inspect.", len(rows))

    updated_count = 0
    for r in rows:
        row_id = r["id"]
        tag = r["variant_tag"]
        raw_m = r.get("metrics")

        if isinstance(raw_m, str):
            try:
                metrics = json.loads(raw_m)
            except Exception:
                metrics = {}
        elif isinstance(raw_m, dict):
            metrics = dict(raw_m)
        else:
            metrics = {}

        if not metrics or "score" not in metrics:
            continue

        old_score = float(metrics.get("score") or 0.0)
        port_ret = float(metrics.get("portfolio_return_pct") or 0.0)
        spy_ret = float(metrics.get("spy_return_pct") or 0.0)
        max_dd = float(metrics.get("max_drawdown") or 0.0)
        port_vol = float(metrics.get("volatility") or 0.0)
        bond_ret = float(metrics.get("bond_return_pct") or 0.0)
        dollar_ret = float(metrics.get("dollar_return_pct") or 0.0)
        do_nothing_ret = float(metrics.get("do_nothing_return_pct") or 0.0)

        # SPY volatility
        spy_vol = metrics.get("spy_volatility")
        if spy_vol is None or float(spy_vol) <= 0.0:
            # Attempt to compute from price history if week_start / week_end are present
            w_start_str = r.get("week_start")
            w_end_str = r.get("week_end")
            computed_spy_vol = 0.0
            if w_start_str and w_end_str:
                try:
                    w_start = date.fromisoformat(w_start_str[:10])
                    w_end = date.fromisoformat(w_end_str[:10])
                    spy_rets = await _spy_returns(sb_client, w_start, w_end)
                    if spy_rets and len(spy_rets) > 1:
                        mean_spy = sum(spy_rets) / len(spy_rets)
                        var_spy = sum((x - mean_spy) ** 2 for x in spy_rets) / (len(spy_rets) - 1)
                        computed_spy_vol = math.sqrt(var_spy) * math.sqrt(252) * 100
                except Exception as ex:
                    logger.debug("Could not compute SPY vol for %s: %s", tag, ex)

            spy_vol = computed_spy_vol if computed_spy_vol > 0.0 else 16.0

        spy_vol = float(spy_vol)

        new_metrics_res = compute_score(
            portfolio_return_pct=port_ret,
            spy_return_pct=spy_ret,
            max_drawdown_pct=max_dd,
            bond_return_pct=bond_ret,
            dollar_return_pct=dollar_ret,
            volatility_pct=port_vol,
            spy_volatility_pct=spy_vol,
            do_nothing_return_pct=do_nothing_ret,
        )

        new_score = new_metrics_res["score"]

        # Preserve extra keys from original metrics (e.g. rejection_stats, evaluated_at, portfolio_details)
        updated_metrics = {**metrics, **new_metrics_res}

        logger.info(
            "[%s] %s | Old Score: %+.4f -> New Z-Score: %+.4fσ | Net Excess: %+.2f%% | Eff Vol: %.2f%% (W: %.2f%%)",
            "DRY-RUN" if dry_run else "UPDATING",
            tag,
            old_score,
            new_score,
            new_metrics_res["net_excess_return"],
            new_metrics_res["effective_volatility"],
            new_metrics_res["weekly_effective_volatility"],
        )

        if not dry_run:
            await sb_client.table("prompt_experiments").update({"metrics": updated_metrics}).eq("id", row_id).execute()

        updated_count += 1

    logger.info(
        "Finished backfill. Total records inspected with scores: %d. Mode: %s",
        updated_count,
        "DRY-RUN (No changes applied)" if dry_run else "COMMITTED TO DATABASE",
    )


def main():
    parser = argparse.ArgumentParser(description="Backfill prompt experiment scores to Unified Z-Score.")
    parser.add_argument("--commit", action="store_true", help="Apply updates to Supabase (default is dry-run).")
    parser.add_argument("--track-id", type=str, default=None, help="Filter by specific track ID.")
    args = parser.parse_args()

    asyncio.run(backfill_scores(dry_run=not args.commit, track_id=args.track_id))


if __name__ == "__main__":
    main()
