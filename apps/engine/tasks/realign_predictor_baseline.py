import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import logger
from core.conviction_backfill import (
    propose_track_realignment,
    recompute_experiment_metrics,
    summarize_tracks,
)
from core.db import get_supabase_client
from tasks.predictor_autoresearch import calculate_baseline_metrics

SECTOR_PROMPT = "SECTOR_PREDICTOR_PROMPT"


def realign_predictor_baselines(client=None, dry_run: bool = True) -> dict:
    """Recalculate sector variant scores and realign each model track's baseline.

    Baseline selection goes through ``select_baseline_candidate``: the active
    variant is excluded, variants with fewer than ``MIN_BASELINE_SAMPLE`` evaluated
    predictions are skipped, and the remaining scores are shrunk toward neutral by
    sample size. Each track is realigned independently so one model's history
    cannot set another model's baseline.
    """
    if client is None:
        client = get_supabase_client()

    predictions = client.table("sector_predictions").select("*").eq("status", "evaluated").execute().data or []
    experiments = (
        client.table("prompt_experiments")
        .select("*")
        .eq("prompt_name", SECTOR_PROMPT)
        .order("created_at")
        .execute()
        .data
        or []
    )

    if not experiments:
        logger.warning("No SECTOR_PREDICTOR_PROMPT experiments found in database.")
        return {
            "dry_run": dry_run,
            "tracks": {},
            "recalculated": [],
            "new_baseline_tag": None,
            "new_baseline_score": None,
        }

    report = recompute_experiment_metrics(experiments, predictions, "prompt_tag", calculate_baseline_metrics)
    proposals = propose_track_realignment(report)
    tracks = summarize_tracks(proposals)

    best_overall = max(
        (entry for entry in tracks.values() if entry["baseline_tag"]),
        key=lambda entry: entry["baseline_score"],
        default=None,
    )

    if not dry_run:
        for proposal in proposals:
            payload: dict = {}
            if proposal["metrics"] is not None:
                payload["metrics"] = proposal["metrics"]
            if proposal["status"] is not None:
                payload["status"] = proposal["status"]
            if proposal["parent_tag"] is not None:
                payload["parent_tag"] = proposal["parent_tag"]
            if not payload:
                continue

            client.table("prompt_experiments").update(payload).eq("id", proposal["id"]).execute()
            logger.info(
                "Updated %s (track=%s): %s",
                proposal["variant_tag"],
                proposal["track_id"],
                payload,
            )

    return {
        "dry_run": dry_run,
        "tracks": tracks,
        "recalculated": report,
        "new_baseline_tag": best_overall["baseline_tag"] if best_overall else None,
        "new_baseline_score": best_overall["baseline_score"] if best_overall else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recalculate sector variant scores and realign each model track's baseline."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply database updates. Default is dry-run mode.",
    )
    args = parser.parse_args()

    dry_run = not args.apply
    mode_str = "DRY RUN" if dry_run else "APPLYING TO DATABASE"
    print(f"=== SECTOR PREDICTOR BASELINE REALIGNMENT ({mode_str}) ===")

    result = realign_predictor_baselines(dry_run=dry_run)

    baseline_tags = {entry["baseline_tag"] for entry in result["tracks"].values()}

    print("\nRecalculated Prompt Variants:")
    for item in result["recalculated"]:
        old = item["old_score"]
        old_s = f"{old:7.4f}" if isinstance(old, (int, float)) else "   None"
        metrics = item["new_metrics"]
        new_s = f"{metrics['score']:7.4f}" if metrics else "   None"
        is_best = " ★ BASELINE" if item["variant_tag"] in baseline_tags else ""
        print(
            f"  [{item['track_id']}] {item['variant_tag'][:34]:34} "
            f"{item['status'] or '-':9} {old_s} -> {new_s} (n={item['prediction_count']}){is_best}"
        )

    print("\nPer-track baselines:")
    for track, entry in sorted(result["tracks"].items()):
        score = f"{entry['baseline_score']:.4f}" if entry["baseline_score"] is not None else "none"
        print(f"  {track:28} {entry['baseline_tag'] or 'no credible baseline'} ({score})")

    if dry_run:
        print("\n[NOTE] No database rows were modified. Run with --apply to commit updates.")


if __name__ == "__main__":
    main()
