"""Attribution Reconstruction Validator for AI Wall Street.

This utility verifies the end-to-end lineage of a trade, ensuring that the entire
truth chain from news event to post-trade lesson is fully reconstructible.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from core.db import get_supabase_client

class AttributionAuditResult(BaseModel):
    trade_id: str
    ticker: str
    is_valid: bool
    lineage_found: List[str]
    missing_elements: List[str]
    failure_reasons: List[str] = Field(default_factory=list)

def validate_trade_attribution(trade_id: str) -> AttributionAuditResult:
    """Verifies end-to-end lineage for any trade_id."""
    sb_client = get_supabase_client()

    lineage_found = []
    missing_elements = []
    failure_reasons = []

    # 1. Fetch the trade record
    trade_res = sb_client.table("trades").select("*").eq("id", trade_id).execute()
    if not trade_res.data:
        return AttributionAuditResult(
            trade_id=trade_id,
            ticker="UNKNOWN",
            is_valid=False,
            lineage_found=[],
            missing_elements=["trade_record"],
            failure_reasons=["Trade record not found in DB."]
        )

    trade = trade_res.data[0]
    ticker = trade["ticker"]
    decision_id = trade.get("decision_id")
    lineage_found.append("trade_record")

    # 2. Check Decision Linkage
    if not decision_id:
        missing_elements.append("decision_link")
        failure_reasons.append("orphaned_trade: No decision_id linked.")
    else:
        dec_res = sb_client.table("decisions").select("*").eq("id", decision_id).execute()
        if not dec_res.data:
            missing_elements.append("decision_record")
            failure_reasons.append(f"missing_decision: Linked decision {decision_id} not found.")
        else:
            decision = dec_res.data[0]
            lineage_found.append("decision_record")

            # 3. Check News Source Linkage
            source_id = decision.get("source_id")
            if not source_id or source_id == "unknown":
                missing_elements.append("news_link")
                failure_reasons.append("orphaned_decision: No valid source_id found.")
            else:
                news_res = sb_client.table("newsletter_snapshots").select("id").eq("source_id", source_id).execute()
                if not news_res.data:
                    missing_elements.append("news_source")
                    failure_reasons.append(f"missing_news: Source newsletter {source_id} not found.")
                else:
                    lineage_found.append("news_source")

            # 4. Check LLM Reasoning Log
            # The metadata in reasoning logs should contain the ticker and task_type 'INGESTION' or 'VERIFICATION'
            # For a trade, we expect a reasoning log associated with this ticker and source_id.
            log_res = sb_client.table("llm_reasoning_logs") \
                .select("id, task_type") \
                .filter("metadata->>ticker", "eq", ticker) \
                .filter("metadata->>source_id", "eq", source_id) \
                .execute()

            if not log_res.data:
                missing_elements.append("reasoning_log")
                failure_reasons.append("missing_reasoning: No LLM reasoning logs found for this ticker/source.")
            else:
                lineage_found.append("reasoning_log")

                # 5. Check Tool Transcript in Logs
                # For trades, we expect tool usage (get_stock_quote, calculate_buy_quantity, etc.)
                verification_logs = [l for l in log_res.data if l["task_type"] == "VERIFICATION"]
                if not verification_logs:
                     missing_elements.append("verification_trace")
                     # failure_reasons.append("missing_tool_verification: No verification-task reasoning logs found.")
                else:
                     lineage_found.append("verification_trace")

    # 6. Check Post-Trade Lesson
    lesson_res = sb_client.table("memories") \
        .select("id") \
        .eq("memory_type", "LESSON_LEARNED") \
        .filter("metadata->>trade_id", "eq", trade_id) \
        .execute()

    if not lesson_res.data:
        missing_elements.append("post_trade_lesson")
        # Lessons might not be generated immediately, but we track the gap
    else:
        lineage_found.append("post_trade_lesson")

    is_valid = len(missing_elements) == 0
    return AttributionAuditResult(
        trade_id=trade_id,
        ticker=ticker,
        is_valid=is_valid,
        lineage_found=lineage_found,
        missing_elements=missing_elements,
        failure_reasons=failure_reasons
    )
