"""Attribution Reconstruction Validator for AI Wall Street.

This utility verifies the end-to-end lineage of a trade, ensuring that the entire
truth chain from news event to post-trade lesson is fully reconstructible.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from core.repositories import audit_repo

class AttributionAuditResult(BaseModel):
    trade_id: str
    ticker: str
    is_valid: bool
    lineage_found: List[str]
    missing_elements: List[str]
    failure_reasons: List[str] = Field(default_factory=list)

def validate_trade_attribution(trade_id: str, strict: bool = True) -> AttributionAuditResult:
    """Verifies end-to-end lineage for any trade_id.

    Args:
        trade_id: The ID of the trade to audit.
        strict: If True, requires full audit evidence including normalized transcripts.
                If False, allows historical benchmark runs for longitudinal comparability.
    """
    lineage_found = []
    missing_elements = []
    failure_reasons = []

    # 1. Fetch the trade record
    trade = audit_repo.fetch_trade_by_id(trade_id)
    if not trade:
        return AttributionAuditResult(
            trade_id=trade_id,
            ticker="UNKNOWN",
            is_valid=False,
            lineage_found=[],
            missing_elements=["trade_record"],
            failure_reasons=["Trade record not found in DB."]
        )

    ticker = trade["ticker"]
    decision_id = trade.get("decision_id")
    lineage_found.append("trade_record")

    # 2. Check Decision Linkage
    if not decision_id:
        missing_elements.append("decision_link")
        failure_reasons.append("orphaned_trade: No decision_id linked.")
    else:
        decision = audit_repo.fetch_decision_by_id(decision_id)
        if not decision:
            missing_elements.append("decision_record")
            failure_reasons.append(f"missing_decision: Linked decision {decision_id} not found.")
        else:
            lineage_found.append("decision_record")

            # 3. Check News Source Linkage
            source_id = decision.get("source_id")
            if not source_id or source_id == "unknown":
                missing_elements.append("news_link")
                failure_reasons.append("orphaned_decision: No valid source_id found.")
            else:
                news = audit_repo.fetch_news_by_source_id(source_id)
                if not news:
                    missing_elements.append("news_source")
                    failure_reasons.append(f"missing_news: Source newsletter {source_id} not found.")
                else:
                    lineage_found.append("news_source")

            # 4. Check LLM Reasoning Log
            # Prefer precise decision_id anchoring, fallback to ticker/source
            logs = audit_repo.fetch_reasoning_logs_by_decision_id(decision_id)

            if not logs:
                # Fallback for historical logs that might not have decision_id anchor
                logs = audit_repo.fetch_reasoning_logs_for_ticker_source(ticker, source_id)

            if not logs:
                missing_elements.append("reasoning_log")
                failure_reasons.append(f"missing_reasoning: No LLM reasoning logs found for decision {decision_id} or ticker {ticker}")
            else:
                lineage_found.append("reasoning_log")

                # 5. Check Tool Transcript in Logs
                # For trades, we expect tool usage (get_stock_quote, calculate_buy_quantity, etc.)
                verification_logs = [l for l in logs if l["task_type"] == "VERIFICATION"]
                if not verification_logs:
                     missing_elements.append("verification_trace")
                else:
                     lineage_found.append("verification_trace")
                     # deliverable 4 check: verify transcript exists
                     # Handle both legacy metadata and hardened column
                     found_transcript = False
                     for v_log in verification_logs:
                         if v_log.get("normalized_transcript") or v_log.get("metadata", {}).get("normalized_transcript"):
                             lineage_found.append("normalized_transcript")
                             found_transcript = True
                             break

                     if strict and not found_transcript:
                         missing_elements.append("normalized_transcript")

    # 6. Check Post-Trade Lesson
    lessons = audit_repo.fetch_lessons_for_trade(trade_id)

    if not lessons:
        missing_elements.append("post_trade_lesson")
    else:
        lineage_found.append("post_trade_lesson")

    # 7. Check for explicit rejections in trade_rejections table
    rejections = audit_repo.fetch_trade_rejections_by_ticker(ticker)
    # This is a supplemental check - a trade existence means it wasn't rejected,
    # but the validator can note if there were prior rejections for this ticker.
    if rejections:
        lineage_found.append("historical_rejections")

    is_valid = len(missing_elements) == 0
    return AttributionAuditResult(
        trade_id=trade_id,
        ticker=ticker,
        is_valid=is_valid,
        lineage_found=lineage_found,
        missing_elements=missing_elements,
        failure_reasons=failure_reasons
    )
