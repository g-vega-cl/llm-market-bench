"""Pipeline script to pre-compute and update catalyst radar collisions.

Runs after calendar ingestion or concept momentum updates. Matches high-velocity
narrative concepts to upcoming calendar triggers via vector cosine similarity,
persisting the resulting collisions to the `catalyst_radar` table in Supabase.
"""

import argparse
import sys
from pathlib import Path

# Add apps/engine to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analysis.catalyst_radar import compute_and_store_catalyst_radar
from core.config import logger
from core.db import get_supabase_client


def main():
    parser = argparse.ArgumentParser(description="Update catalyst radar collisions in Supabase.")
    parser.add_argument(
        "--days-ahead",
        type=int,
        default=30,
        help="Forward window in days to search for calendar triggers (default: 30).",
    )
    parser.add_argument(
        "--min-velocity",
        type=float,
        default=1.0,
        help="Minimum velocity score for concepts (default: 1.0).",
    )
    parser.add_argument(
        "--min-similarity",
        type=float,
        default=0.35,
        help="Minimum cosine similarity threshold (default: 0.35).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute matches without writing to Supabase.",
    )
    args = parser.parse_args()

    logger.info(
        "Starting catalyst radar pre-compute (days_ahead=%d, min_velocity=%.1f, min_similarity=%.2f)...",
        args.days_ahead,
        args.min_velocity,
        args.min_similarity,
    )

    sb = get_supabase_client()
    if args.dry_run:
        from analysis.catalyst_radar import fetch_catalyst_radar
        items = fetch_catalyst_radar(
            sb_client=sb,
            days_ahead=args.days_ahead,
            min_velocity=args.min_velocity,
            min_similarity=args.min_similarity,
        )
        logger.info("[DRY RUN] Matched %d concept-catalyst collisions.", len(items))
        if items:
            logger.info("[DRY RUN] Top collision: %s <-> %s (target: %s, sim: %.2f)",
                        items[0].concept_name, items[0].catalyst_title, items[0].target_date, items[0].similarity)
        return

    stored = compute_and_store_catalyst_radar(
        sb_client=sb,
        days_ahead=args.days_ahead,
        min_velocity=args.min_velocity,
        min_similarity=args.min_similarity,
    )
    logger.info("Successfully updated catalyst radar with %d active collisions.", stored)


if __name__ == "__main__":
    main()
