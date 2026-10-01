"""CLI sub-command router for ingestion, calendar, and analysis pipelines."""

import argparse
import asyncio

from core.config import logger
from ingest.calendar import run_calendar_pipeline
from ingest.government import run_government_pipeline
from pipeline.runner import (
    run_cause_and_effect,
    run_ingest,
    run_post_analysis,
    run_weekend_ingest,
)
from tasks.lin_renko_task import run_lin_renko_flow


def handle_ingest(args: argparse.Namespace) -> None:
    """Run full morning/midday newsletter ingestion and analysis pipeline."""
    asyncio.run(run_ingest(force=args.force, dry_run=args.dry_run))


def handle_weekend_ingest(args: argparse.Namespace) -> None:
    """Run weekend read-only pipeline."""
    asyncio.run(run_weekend_ingest())


def handle_post_analysis(args: argparse.Namespace) -> None:
    """Run historical trade post-analysis."""
    asyncio.run(run_post_analysis())


def handle_government(args: argparse.Namespace) -> None:
    """Run government contract and macro data pipeline."""
    asyncio.run(run_government_pipeline())


def handle_calendar(args: argparse.Namespace) -> None:
    """Run economic calendar pipeline and update catalyst radar."""
    asyncio.run(run_calendar_pipeline())
    try:
        from analysis.catalyst_radar import compute_and_store_catalyst_radar

        compute_and_store_catalyst_radar()
    except Exception as radar_err:
        logger.warning(f"Could not auto-update catalyst radar after calendar pipeline: {radar_err}")


def handle_cause_and_effect(args: argparse.Namespace) -> None:
    """Run cause-and-effect market event analysis."""
    asyncio.run(run_cause_and_effect())


def handle_lin_renko(args: argparse.Namespace) -> None:
    """Run isolated Linde (LIN) single-stock Renko strategy flow."""
    asyncio.run(run_lin_renko_flow())
