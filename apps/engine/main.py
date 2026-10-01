"""Entry point for the AI Wall Street Engine.

This module provides the primary CLI entry point for running the daily pipeline,
thematic execution, audits, and autoresearch tasks.

Refactored following Martin Fowler's "Separate Presentation from Domain":
- Sub-command routing decomposed into vertical slice routers under `apps/engine/cli/`.
- Pipeline orchestration extracted into `apps/engine/pipeline/`.
- This file remains as the thin CLI entry point (< 150 LOC) with backwards-compatible
  symbol re-exports for hermetic test suites.
"""

import asyncio
from datetime import datetime

from analysis.analyze import analyze_chunks
from analysis.consensus import process_consensus
from analysis.market_feeling import analyze_market_feeling
from analysis.momentum import analyze_momentum, decay_stale_concepts
from analysis.pca_utils import update_pca_coordinates
from attribution.service import save_decision
from cli import run_cli
from core.config import logger
from core.db import bulk_upsert_newsletter_snapshots, get_supabase_client, upsert_newsletter_snapshot
from core.llm.verification import verify_trading_decision
from execution.portfolio import Portfolio
from execution.validation import validate_decision, validate_semantic_overlap
from ingest.newsletter import ingest_newsletters
from pipeline.decision_processor import _process_single_decision, _stage_decision_processing
from pipeline.runner import (
    run_cause_and_effect,
    run_ingest,
    run_post_analysis,
    run_weekend_ingest,
)
from pipeline.stages import (
    _stage_analysis_and_consensus,
    _stage_dust_cleanup,
    _stage_ingest_and_snapshot,
    _stage_snapshots_and_pca,
)

__all__ = [
    "main",
    "run_ingest",
    "run_weekend_ingest",
    "run_post_analysis",
    "run_cause_and_effect",
    "_stage_ingest_and_snapshot",
    "_stage_dust_cleanup",
    "_stage_analysis_and_consensus",
    "_stage_decision_processing",
    "_process_single_decision",
    "_stage_snapshots_and_pca",
    "ingest_newsletters",
    "get_supabase_client",
    "bulk_upsert_newsletter_snapshots",
    "upsert_newsletter_snapshot",
    "analyze_chunks",
    "process_consensus",
    "analyze_momentum",
    "decay_stale_concepts",
    "analyze_market_feeling",
    "validate_decision",
    "validate_semantic_overlap",
    "Portfolio",
    "verify_trading_decision",
    "save_decision",
    "update_pca_coordinates",
    "logger",
    "datetime",
    "asyncio",
]


def main() -> None:
    """Main CLI entry point delegating to the CLI router."""
    run_cli()


if __name__ == "__main__":
    main()
