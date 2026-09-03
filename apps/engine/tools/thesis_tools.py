"""Thesis Tracker and Disconfirming Evidence Ledger Tool.

Allows trading agents and investment chat users to maintain falsifiable multi-day
investment theses with structured pillars, tracked invalidation risks, and an explicit
disconfirming evidence ledger that dynamically transitions conviction states.
"""

from datetime import UTC, datetime
from typing import Any

from core.config import logger
from core.db import get_supabase_client

# In-memory session cache for environments without a dedicated 'theses' table
_IN_MEMORY_THESES: dict[str, dict[str, Any]] = {}


def format_thesis_markdown(thesis: dict[str, Any]) -> str:
    """Format thesis record into structured Markdown for agent or chat display."""
    ticker = thesis.get("ticker", "UNKNOWN")
    statement = thesis.get("thesis_statement", "No statement provided")
    conviction = thesis.get("conviction", "MEDIUM")
    status = thesis.get("status", "ACTIVE")
    target = thesis.get("price_target")
    stop = thesis.get("stop_loss")
    pillars = thesis.get("pillars", [])
    risks = thesis.get("risks", [])
    disconfirming = thesis.get("disconfirming_evidence", [])

    pillars_md = "\n".join(f"  {i + 1}. {p}" for i, p in enumerate(pillars)) if pillars else "  * None defined"
    risks_md = "\n".join(f"  {i + 1}. {r}" for i, r in enumerate(risks)) if risks else "  * None defined"

    if disconfirming:
        disconf_lines = []
        for d in disconfirming:
            date = d.get("date", "Recent")
            factor = d.get("factor", "")
            impacted = d.get("pillar_impacted", "General")
            disconf_lines.append(f"  - **[{date}]** {factor} *(Impacts: {impacted})*")
        disconf_md = "\n".join(disconf_lines)
    else:
        disconf_md = "  * Zero disconfirming signals registered. Thesis intact."

    target_str = f"${target:.2f}" if target is not None else "N/A"
    stop_str = f"${stop:.2f}" if stop is not None else "N/A"

    return (
        f"### 📋 Investment Thesis: {ticker} (`{conviction}` | `{status}`)\n\n"
        f"**Thesis Statement**: {statement}\n\n"
        f"- **Price Target**: `{target_str}`  ·  **Stop Loss**: `{stop_str}`\n\n"
        f"**Core Supporting Pillars**:\n{pillars_md}\n\n"
        f"**Key Invalidation Risks**:\n{risks_md}\n\n"
        f"**Disconfirming Evidence Ledger**:\n{disconf_md}\n"
    )


async def execute_track_thesis_pillars(
    ticker: str,
    action: str = "get",
    thesis_statement: str | None = None,
    pillars: list[str] | None = None,
    risks: list[str] | None = None,
    disconfirming_factor: str | None = None,
    pillar_impacted: str | None = None,
    price_target: float | None = None,
    stop_loss: float | None = None,
    conviction: str | None = None,
) -> dict[str, Any]:
    """Execute thesis tracking operations (get, create, disconfirm, invalidate)."""
    ticker = ticker.upper().strip()
    action = action.lower().strip()
    now_iso = datetime.now(UTC).isoformat()
    sb = get_supabase_client()

    # 1. CREATE ACTION
    if action == "create":
        initial_conviction = conviction or "HIGH"
        thesis_data = {
            "ticker": ticker,
            "thesis_statement": thesis_statement or f"Core conviction thesis on {ticker}.",
            "pillars": pillars or [],
            "risks": risks or [],
            "disconfirming_evidence": [],
            "conviction": initial_conviction,
            "status": "ACTIVE",
            "price_target": price_target,
            "stop_loss": stop_loss,
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        _IN_MEMORY_THESES[ticker] = thesis_data

        if sb:
            try:
                res = sb.table("theses").insert(thesis_data).execute()
                if res.data:
                    thesis_data["id"] = res.data[0].get("id")
            except Exception as e:
                logger.debug(f"Could not persist thesis to database (falling back to memory): {e}")

        result = dict(thesis_data)
        result["status"] = "CREATED"
        result["markdown"] = format_thesis_markdown(thesis_data)
        return result

    # 2. DISCONFIRM ACTION
    if action == "disconfirm":
        existing = _IN_MEMORY_THESES.get(ticker)
        if not existing and sb:
            try:
                res = (
                    sb.table("theses")
                    .select("*")
                    .eq("ticker", ticker)
                    .order("updated_at", desc=True)
                    .limit(1)
                    .execute()
                )
                if res.data:
                    existing = res.data[0]
            except Exception as e:
                logger.debug(f"Error reading thesis from database: {e}")

        if not existing:
            existing = {
                "ticker": ticker,
                "thesis_statement": f"Baseline trade thesis on {ticker}.",
                "pillars": [pillar_impacted or "Momentum / Fundamental Support"],
                "risks": ["Adverse price trend"],
                "disconfirming_evidence": [],
                "conviction": "HIGH",
                "status": "ACTIVE",
            }

        disconf_entry = {
            "date": datetime.now(UTC).date().isoformat(),
            "factor": disconfirming_factor or "Unspecified disconfirming signal observed.",
            "pillar_impacted": pillar_impacted or "General Thesis",
        }
        evidence_list = list(existing.get("disconfirming_evidence", []))
        evidence_list.append(disconf_entry)
        existing["disconfirming_evidence"] = evidence_list
        existing["conviction"] = "WEAKENED"
        existing["updated_at"] = now_iso

        _IN_MEMORY_THESES[ticker] = existing
        if sb and existing.get("id"):
            try:
                sb.table("theses").update(existing).eq("id", existing["id"]).execute()
            except Exception as e:
                logger.debug(f"Error updating thesis in database: {e}")

        result = dict(existing)
        result["markdown"] = format_thesis_markdown(existing)
        return result

    # 3. GET ACTION
    existing = _IN_MEMORY_THESES.get(ticker)
    if not existing and sb:
        try:
            res = sb.table("theses").select("*").eq("ticker", ticker).order("updated_at", desc=True).limit(1).execute()
            if res.data:
                existing = res.data[0]
        except Exception as e:
            logger.debug(f"Error querying thesis from database: {e}")

    if not existing:
        not_found = {
            "ticker": ticker,
            "status": "NO_THESIS_FOUND",
            "conviction": "NEUTRAL",
            "markdown": f"No active multi-day thesis registered for `{ticker}`. Use `action='create'` to establish one.",
        }
        return not_found

    result = dict(existing)
    result["markdown"] = format_thesis_markdown(existing)
    return result
