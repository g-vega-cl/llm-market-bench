"""Rejected Trade Persistence Logic.

This module ensures that all rejected trades (whether by guardrails,
verification, or margin checks) are atomically persisted for benchmark analysis.
"""

import logging
from typing import Any, Dict, Optional
from core.models import DecisionObject
from attribution.service import save_decision

logger = logging.getLogger("engine")

def persist_rejection(
    sb_client: Any,
    decision: DecisionObject,
    rejection_reason: str,
    status: str = "REJECTED",
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Ensures a rejected trade is written to the decisions table with full audit context.

    Args:
        sb_client: The Supabase client instance.
        decision: The decision object that was rejected.
        rejection_reason: Exact reason for the rejection.
        status: Status code (e.g., REJECTED_GUARDRAIL, REJECTED_VERIFICATION).
        metadata: Additional context (portfolio state, price snapshots, etc.).

    Returns:
        The upserted decision row.
    """
    meta = metadata or {}
    meta["rejection_reason"] = rejection_reason

    logger.warning(f"[{decision.ticker}] {status}: {rejection_reason}")

    return save_decision(
        client=sb_client,
        decision=decision,
        status=status,
        metadata=meta
    )
