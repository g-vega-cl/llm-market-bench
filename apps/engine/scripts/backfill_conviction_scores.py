"""Backfill conviction scores and recompute ratchet metrics under the new formula.

The conviction metric replaced the ``- mean_brier * 50`` accuracy penalty. Stored
scores computed with the old formula are not comparable with new live scores: the
weekly ratchet compares the active prompt against the highest stored variant score,
so a stale-high baseline would revert the active prompt every week and stall prompt
evolution. This utility rewrites both the per-row conviction values and the
per-experiment metrics so the ratchet resumes from a consistent state.

Usage:
    python scripts/backfill_conviction_scores.py            # dry run (default)
    python scripts/backfill_conviction_scores.py --apply
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import logger
from core.conviction_backfill import (
    as_date,
    recompute_daily_conviction,
    recompute_experiment_metrics,
    recompute_sector_conviction,
)
from core.conviction_scoring import MIN_BASELINE_SAMPLE, select_baseline_candidate
from core.db import get_supabase_client
from tasks.daily_autoresearch import calculate_daily_ratchet_metrics
from tasks.predictor_autoresearch import calculate_baseline_metrics

DAILY_PROMPT = "DAILY_PREDICTOR_PROMPT"
SECTOR_PROMPT = "SECTOR_PREDICTOR_PROMPT"


def _recent_track_score(
    predictions: list[dict],
    track: str,
    calculator,
    days: int,
    date_key: str = "target_date",
) -> tuple[float | None, int]:
    cutoff = date.today() - timedelta(days=days)
    rows = []
    for prediction in predictions:
        if prediction.get("model_name") != track:
            continue
        target = as_date(prediction.get(date_key))
        if target is None or target < cutoff:
            continue
        rows.append(prediction)
    if not rows:
        return None, 0
    return calculator(rows)["score"], len(rows)


def _print_track_health(
    title: str,
    report: list[dict],
    predictions: list[dict],
    calculator,
    days: int,
) -> None:
    """Compare each track's credible ceiling with the score the live ratchet will compute."""
    print(f"\n--- {title}: ceiling vs live {days}-day score ---")
    tracks = sorted(
        {item["track_id"] for item in report if item.get("track_id") and item["track_id"] != "track_default"}
    )
    for track in tracks:
        variants = [
            {"variant_tag": item["variant_tag"], "metrics": item["new_metrics"]}
            for item in report
            if item.get("track_id") == track
        ]
        best = select_baseline_candidate(variants, exclude_tag=None)
        recent, n = _recent_track_score(predictions, track, calculator, days)
        ceiling = f"{best[0]:6.2f}" if best else "  none"
        recent_str = f"{recent:6.2f} (n={n})" if recent is not None else "  none (n=0)"
        verdict = ""
        if best and recent is not None:
            verdict = "reachable" if recent >= best[0] else "BELOW CEILING"
        print(f"  {track:28} ceiling {ceiling} | live {recent_str} {verdict}")


def _print_report(title: str, report: list[dict]) -> None:
    print(f"\n=== {title} ===")
    for item in report:
        old = item["old_score"]
        old_str = f"{old:7.2f}" if isinstance(old, (int, float)) else "   None"
        metrics = item["new_metrics"]
        track = item.get("track_id") or "(none)"
        if metrics is None:
            print(f"  [{track}] {item['variant_tag'][:40]:40} {item['status']:9} {old_str} ->    None (no predictions)")
            continue
        print(
            f"  [{track}] {item['variant_tag'][:40]:40} {item['status']:9} "
            f"{old_str} -> {metrics['score']:7.2f} (n={metrics['predictions_evaluated']})"
        )

    # Per-track ceilings after recompute: only variants with >= MIN_BASELINE_SAMPLE
    # predictions may set the ratchet baseline.
    print(f"\n  --- credible ratchet ceilings per track (n >= {MIN_BASELINE_SAMPLE}) ---")
    tracks = sorted({item.get("track_id") or "(none)" for item in report})
    for track in tracks:
        variants = [
            {"variant_tag": item["variant_tag"], "metrics": item["new_metrics"]}
            for item in report
            if (item.get("track_id") or "(none)") == track
        ]
        best = select_baseline_candidate(variants, exclude_tag=None)
        if best is None:
            print(f"  {track:28} no credible baseline -> active score sets the baseline")
        else:
            print(f"  {track:28} ceiling {best[0]:6.2f}  ({best[1]['variant_tag']})")


def run_backfill(client=None, dry_run: bool = True) -> dict:
    if client is None:
        client = get_supabase_client()

    applied = {"daily_rows": 0, "earnings_rows": 0, "sector_rows": 0, "experiments": 0}

    # --- 1. Per-row conviction scores ---
    daily_rows = (
        client.table("daily_predictions").select("id,confidence,is_correct").eq("status", "evaluated").execute().data
        or []
    )
    earnings_rows = (
        client.table("earnings_predictions").select("id,confidence,is_correct").eq("status", "evaluated").execute().data
        or []
    )
    sector_rows = (
        client.table("sector_predictions")
        .select("id,confidence,worst_confidence,sector_percentile_score,worst_sector_percentile_score")
        .eq("status", "evaluated")
        .execute()
        .data
        or []
    )

    row_updates = {
        "daily_predictions": recompute_daily_conviction(daily_rows),
        "earnings_predictions": recompute_daily_conviction(earnings_rows),
        "sector_predictions": recompute_sector_conviction(sector_rows),
    }

    for table, updates in row_updates.items():
        key = table.split("_")[0] + "_rows"
        applied[key] = len(updates)
        if dry_run:
            continue
        for row_id, score in updates:
            client.table(table).update({"conviction_score": score}).eq("id", row_id).execute()

    # --- 2. Experiment metrics under the new formula ---
    experiments = (
        client.table("prompt_experiments").select("*").in_("prompt_name", [DAILY_PROMPT, SECTOR_PROMPT]).execute().data
        or []
    )
    daily_experiments = [e for e in experiments if e.get("prompt_name") == DAILY_PROMPT]
    sector_experiments = [e for e in experiments if e.get("prompt_name") == SECTOR_PROMPT]

    daily_preds = client.table("daily_predictions").select("*").eq("status", "evaluated").execute().data or []
    sector_preds = client.table("sector_predictions").select("*").eq("status", "evaluated").execute().data or []

    daily_report = recompute_experiment_metrics(
        daily_experiments, daily_preds, "prompt_variant_tag", calculate_daily_ratchet_metrics
    )
    sector_report = recompute_experiment_metrics(
        sector_experiments, sector_preds, "prompt_tag", calculate_baseline_metrics
    )

    _print_report("DAILY_PREDICTOR_PROMPT", daily_report)
    _print_track_health("DAILY", daily_report, daily_preds, calculate_daily_ratchet_metrics, days=7)
    _print_report("SECTOR_PREDICTOR_PROMPT", sector_report)
    _print_track_health("SECTOR", sector_report, sector_preds, calculate_baseline_metrics, days=7)

    for item in daily_report + sector_report:
        if item["new_metrics"] is None:
            continue
        applied["experiments"] += 1
        if dry_run:
            continue
        client.table("prompt_experiments").update({"metrics": item["new_metrics"]}).eq("id", item["id"]).execute()

    return {"dry_run": dry_run, "applied": applied, "daily": daily_report, "sector": sector_report}


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill conviction scores and ratchet metrics.")
    parser.add_argument("--apply", action="store_true", help="Write to the database.")
    args = parser.parse_args()

    result = run_backfill(dry_run=not args.apply)
    print("\nSummary:", result["applied"])
    if result["dry_run"]:
        print("[NOTE] Dry run. Re-run with --apply to write.")


if __name__ == "__main__":
    logger.setLevel("WARNING")
    main()
