"""Entry point for the AI Wall Street Engine.

This module provides the CLI interface for running the daily pipeline,
including newsletter ingestion, database snapshotting, and LLM analysis.
"""

import argparse
import asyncio

from analyze import analyze_chunks
from core.config import COMMAND_INGEST, logger
from core.db import get_supabase_client, upsert_newsletter_snapshot
from ingest.newsletter import ingest_newsletters
from attribution.service import save_decision


def main():
    """Main entry point for the AI Wall Street Engine CLI."""
    parser = argparse.ArgumentParser(description="AI Wall Street Engine")
    parser.add_argument(
        "command",
        choices=[COMMAND_INGEST],
        help="Action to perform"
    )

    args = parser.parse_args()

    if args.command == COMMAND_INGEST:
        logger.info("Starting Newsletter Ingestion...")
        data = ingest_newsletters()

        if not data:
            logger.warning(
                "No new newsletters found to ingest. "
                "Skipping snapshotting and analysis."
            )
            return

        logger.info(f"Successfully ingested {len(data)} newsletters.")

        logger.info("Starting Database Snapshotting...")
        sb_client = get_supabase_client()

        saved_count = 0
        for item in data:
            try:
                upsert_newsletter_snapshot(sb_client, item)
                saved_count += 1
            except Exception as e:
                logger.error(
                    f"Error saving snapshot for "
                    f"{item.get('source_id', 'unknown')}: {e}"
                )

        logger.info(f"Successfully saved {saved_count} snapshots to Supabase.")

        # --- Parallel LLM Analysis ---
        logger.info("Starting Parallel LLM Analysis...")

        try:
            decisions = asyncio.run(analyze_chunks(data))
            logger.info(f"Analysis complete. Generated {len(decisions)} decisions.")
            
            saved_decisions = 0
            for d in decisions:
                try:
                    save_decision(sb_client, d)
                    saved_decisions += 1
                    logger.info(
                        f"[{d.ticker}] {d.signal} (Conf: {d.confidence}%): "
                        f"Saved attribution for {d.model_provider}/{d.model_name}"
                    )
                except Exception as e:
                    logger.error(f"Failed to save decision for {d.ticker}: {e}")
            
            logger.info(f"Successfully saved {saved_decisions}/{len(decisions)} decisions.")
        except Exception as e:
            logger.error(f"Analysis failed: {e}")


if __name__ == "__main__":
    main()
