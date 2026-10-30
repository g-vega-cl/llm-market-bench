"""Read-only data and memory retrieval module for the live intraday trader.

Provides comprehensive read-only grounding across all persistent data domains:
- Vector/text memories & lessons learned
- Causal chains (cause_and_effect)
- Past trades & audit decisions
- Market barometer breadth snapshots
- Catalyst radar narrative collisions
"""

from __future__ import annotations

import re
from typing import Any

from core.config import logger


def _extract_keywords(text: str) -> list[str]:
    """Extract clean alphanumeric keywords for fallback text filtering."""
    if not text:
        return []
    words = re.findall(r"\b[A-Za-z0-9]{3,}\b", text)
    stopwords = {"what", "when", "where", "which", "this", "that", "with", "from", "have", "will", "does"}
    return [w for w in words if w.lower() not in stopwords][:5]


async def retrieve_read_only_market_data(
    sb_client: Any,
    query: str | None = None,
    ticker: str = "SPY",
    limit_per_domain: int = 5,
) -> dict[str, Any]:
    """Retrieve read-only context across all database memory and historical data tables."""
    if not sb_client:
        return {
            "memories": [],
            "cause_and_effect": [],
            "trades": [],
            "decisions": [],
            "barometer": None,
            "catalyst_radar": [],
        }

    results: dict[str, Any] = {
        "memories": [],
        "cause_and_effect": [],
        "trades": [],
        "decisions": [],
        "barometer": None,
        "catalyst_radar": [],
    }

    # 1. Memories (vector or recent priority)
    try:
        mem_builder = sb_client.table("memories").select("id, content, ticker, importance_score")
        if ticker:
            mem_builder = mem_builder.ilike("ticker", f"%{ticker}%")
        mem_resp = mem_builder.order("created_at", desc=True).limit(limit_per_domain).execute()
        results["memories"] = mem_resp.data or []
    except Exception:
        logger.exception("Failed to retrieve read-only memories")

    # 2. Causal Chains (cause_and_effect)
    try:
        ce_builder = sb_client.table("cause_and_effect").select("id, cause, effect")
        ce_resp = ce_builder.order("created_at", desc=True).limit(limit_per_domain).execute()
        results["cause_and_effect"] = ce_resp.data or []
    except Exception:
        logger.exception("Failed to retrieve read-only cause_and_effect")

    # 3. Recent Trades
    try:
        trades_builder = sb_client.table("trades").select("id, ticker, action, execution_price, reasoning")
        if ticker:
            trades_builder = trades_builder.ilike("ticker", f"%{ticker}%")
        trades_resp = trades_builder.order("created_at", desc=True).limit(limit_per_domain).execute()
        results["trades"] = trades_resp.data or []
    except Exception:
        logger.exception("Failed to retrieve read-only trades")

    # 4. Recent Decisions
    try:
        dec_builder = sb_client.table("decisions").select("id, ticker, action, confidence_score, reasoning")
        if ticker:
            dec_builder = dec_builder.ilike("ticker", f"%{ticker}%")
        dec_resp = dec_builder.order("created_at", desc=True).limit(limit_per_domain).execute()
        results["decisions"] = dec_resp.data or []
    except Exception:
        logger.exception("Failed to retrieve read-only decisions")

    # 5. Market Barometer (Breadth / Macro)
    try:
        baro_resp = (
            sb_client.table("market_barometer")
            .select("id, score, status, regime")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if baro_resp.data and len(baro_resp.data) > 0:
            results["barometer"] = baro_resp.data[0]
    except Exception:
        logger.exception("Failed to retrieve read-only market_barometer")

    # 6. Catalyst Radar
    try:
        radar_resp = (
            sb_client.table("catalyst_radar")
            .select("id, narrative, catalyst, urgency")
            .order("created_at", desc=True)
            .limit(3)
            .execute()
        )
        results["catalyst_radar"] = radar_resp.data or []
    except Exception:
        logger.exception("Failed to retrieve read-only catalyst_radar")

    return results


def format_read_only_grounding(data: dict[str, Any], max_items_per_section: int = 3) -> str:
    """Format read-only retrieved data into lean prompt sections for model grounding."""
    sections = []

    # Memories section
    mems = data.get("memories", [])
    if mems:
        mem_lines = [
            f"- [{m.get('id', '')}] {m.get('content', '')[:140]} (Score: {m.get('importance_score', 5)})"
            for m in mems[:max_items_per_section]
        ]
        sections.append("### HISTORICAL MEMORIES & LESSONS (READ-ONLY GROUNDING):\n" + "\n".join(mem_lines))

    # Causal chains
    ces = data.get("cause_and_effect", [])
    if ces:
        ce_lines = [
            f"- Cause: {c.get('cause', '')[:80]} -> Effect: {c.get('effect', '')[:80]}"
            for c in ces[:max_items_per_section]
        ]
        sections.append("### CAUSAL CHAINS (cause_and_effect):\n" + "\n".join(ce_lines))

    # Recent trades & decisions
    trades = data.get("trades", [])
    decs = data.get("decisions", [])
    if trades or decs:
        td_lines = []
        for t in trades[:2]:
            td_lines.append(
                f"- Trade: {t.get('action')} {t.get('ticker')} @ ${t.get('execution_price', 0):.2f} - {t.get('reasoning', '')[:100]}"
            )
        for d in decs[:2]:
            td_lines.append(
                f"- Decision: {d.get('action')} {d.get('ticker')} (Conv: {d.get('confidence_score')}%) - {d.get('reasoning', '')[:100]}"
            )
        sections.append("### RECENT TRADES & AUDIT DECISIONS:\n" + "\n".join(td_lines))

    # Barometer and Catalyst Radar
    baro = data.get("barometer")
    radars = data.get("catalyst_radar", [])
    macro_lines = []
    if baro:
        macro_lines.append(
            f"- Barometer: Score {baro.get('score')} ({baro.get('status')}) | Regime: {baro.get('regime')}"
        )
    for r in radars[:2]:
        macro_lines.append(f"- Catalyst: [{r.get('urgency')}] {r.get('narrative')} ({r.get('catalyst')})")
    if macro_lines:
        sections.append("### MACRO & CATALYST CONTEXT:\n" + "\n".join(macro_lines))

    return "\n\n".join(sections)
