"""Rejected Trade Persistence Logic.

This module ensures that all rejected trades (whether by guardrails,
verification, or margin checks) are atomically persisted for benchmark analysis.
"""

import logging
from datetime import datetime, UTC
from typing import Any, Dict, Optional
from core.models import DecisionObject
from attribution.service import save_decision

logger = logging.getLogger("engine")

def persist_rejection(
    sb_client: Any,
    decision: DecisionObject,
    rejection_reason: str,
    status: str = "REJECTED",
    metadata: Optional[Dict[str, Any]] = None,
    portfolio_state: Optional[Dict[str, Any]] = None,
    market_price: Optional[float] = None,
    tool_trace_id: Optional[str] = None
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

    # 1. Update Decision Status
    saved_dec = save_decision(
        client=sb_client,
        decision=decision,
        status=status,
        metadata=meta
    )

    # 2. Write to dedicated trade_rejections table for detailed audit
    try:
        rejection_payload = {
            "provider": decision.model_provider or "unknown",
            "ticker": decision.ticker,
            "requested_action": decision.signal,
            "requested_quantity": getattr(decision, "quantity", None),
            "market_price": market_price,
            "rejection_reason": rejection_reason,
            "decision_trace_id": saved_dec.get("id"),
            "tool_trace_id": tool_trace_id,
            "created_at": datetime.now(UTC).isoformat()
        }

        if portfolio_state:
            rejection_payload.update({
                "portfolio_id": portfolio_state.get("portfolio_id"),
                "cash_before": portfolio_state.get("cash_before"),
                "position_before": portfolio_state.get("position_before")
            })

        sb_client.table("trade_rejections").insert(rejection_payload).execute()
    except Exception as e:
        logger.error(f"Failed to persist detailed rejection for {decision.ticker}: {e}")

    return saved_dec
