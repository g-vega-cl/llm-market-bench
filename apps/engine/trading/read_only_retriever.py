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


def _retrieve_memories(sb_client: Any, ticker: str, limit_per_domain: int) -> list[dict[str, Any]]:
    try:
        mem_builder = (
            sb_client.table("memories")
            .select(
                "id, content, importance_score, relevance_score, status, memory_type, target_date, created_at, metadata"
            )
            .eq("status", "ACTIVE")
        )
        if ticker:
            mem_builder = mem_builder.ilike("content", f"%{ticker}%")
        mem_resp = mem_builder.order("importance_score", desc=True).limit(limit_per_domain * 2).execute()
        raw_mems = mem_resp.data or []

        from datetime import UTC, datetime

        today_str = datetime.now(UTC).strftime("%Y-%m-%d")
        filtered_mems = []
        for m in raw_mems:
            mtype = (m.get("memory_type") or "").upper()
            if mtype == "ACADEMIC_PAPER":
                continue
            if mtype == "CALENDAR_EVENT" and m.get("target_date") and str(m.get("target_date")) < today_str:
                continue
            filtered_mems.append(m)
        return filtered_mems[:limit_per_domain] if filtered_mems else raw_mems[:limit_per_domain]
    except Exception:
        try:
            mem_builder = sb_client.table("memories").select("id, content, importance_score, metadata")
            if ticker:
                mem_builder = mem_builder.ilike("content", f"%{ticker}%")
            mem_resp = mem_builder.order("importance_score", desc=True).limit(limit_per_domain).execute()
            return mem_resp.data or []
        except Exception:
            logger.exception("Failed to retrieve read-only memories")
            return []


def _retrieve_tabular_signals(sb_client: Any, ticker: str, limit_per_domain: int) -> dict[str, Any]:
    res = {"cause_and_effect": [], "trades": [], "decisions": []}
    try:
        ce_builder = sb_client.table("cause_and_effect").select("id, analysis, market_outcome, confidence, tags")
        ce_resp = ce_builder.order("created_at", desc=True).limit(limit_per_domain).execute()
        res["cause_and_effect"] = ce_resp.data or []
    except Exception:
        logger.exception("Failed to retrieve read-only cause_and_effect")

    try:
        trades_builder = sb_client.table("trades").select("id, ticker, signal, price, reasoning")
        if ticker:
            trades_builder = trades_builder.ilike("ticker", f"%{ticker}%")
        trades_resp = trades_builder.order("executed_at", desc=True).limit(limit_per_domain).execute()
        res["trades"] = trades_resp.data or []
    except Exception:
        logger.exception("Failed to retrieve read-only trades")

    try:
        dec_builder = sb_client.table("decisions").select("id, ticker, signal, confidence, reasoning")
        if ticker:
            dec_builder = dec_builder.ilike("ticker", f"%{ticker}%")
        dec_resp = dec_builder.order("created_at", desc=True).limit(limit_per_domain).execute()
        res["decisions"] = dec_resp.data or []
    except Exception:
        logger.exception("Failed to retrieve read-only decisions")
    return res


def _retrieve_barometer_and_radar(sb_client: Any) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    baro = None
    try:
        baro_resp = (
            sb_client.table("market_barometer_history")
            .select("date, pe_ratio, forward_pe, pb_ratio, ps_ratio, earnings_surprise_momentum, pfcf_ratio")
            .order("date", desc=True)
            .limit(1)
            .execute()
        )
        if baro_resp.data and len(baro_resp.data) > 0:
            baro = baro_resp.data[0]
    except Exception:
        logger.exception("Failed to retrieve read-only market_barometer_history")

    radar = []
    try:
        radar_resp = (
            sb_client.table("catalyst_radar")
            .select("id, concept_name, catalyst_title, impact, memory_content, target_date")
            .order("created_at", desc=True)
            .limit(3)
            .execute()
        )
        radar = radar_resp.data or []
    except Exception:
        logger.exception("Failed to retrieve read-only catalyst_radar")
    return baro, radar


async def retrieve_read_only_market_data(
    sb_client: Any,
    query: str | None = None,
    ticker: str = "SPY",
    limit_per_domain: int = 5,
) -> dict[str, Any]:
    """Retrieve read-only context across all database memory and historical data tables."""
    empty_result = {
        "memories": [],
        "cause_and_effect": [],
        "trades": [],
        "decisions": [],
        "barometer": None,
        "catalyst_radar": [],
    }
    if not sb_client:
        return empty_result

    baro, radar = _retrieve_barometer_and_radar(sb_client)
    tab_signals = _retrieve_tabular_signals(sb_client, ticker, limit_per_domain)

    return {
        "memories": _retrieve_memories(sb_client, ticker, limit_per_domain),
        "cause_and_effect": tab_signals["cause_and_effect"],
        "trades": tab_signals["trades"],
        "decisions": tab_signals["decisions"],
        "barometer": baro,
        "catalyst_radar": radar,
    }


def format_read_only_grounding(data: dict[str, Any], max_items_per_section: int = 3) -> str:
    """Format read-only retrieved data into lean prompt sections for model grounding."""
    sections = []

    # Memories section
    mems = data.get("memories", [])
    if mems:
        mem_lines = [
            f"- [{m.get('id', '')}] {(m.get('content') or '')[:140]} (Score: {m.get('importance_score') or 5})"
            for m in mems[:max_items_per_section]
        ]
        sections.append("### HISTORICAL MEMORIES & LESSONS (READ-ONLY GROUNDING):\n" + "\n".join(mem_lines))

    # Causal chains
    ces = data.get("cause_and_effect", [])
    if ces:
        ce_lines = []
        for c in ces[:max_items_per_section]:
            cause = c.get("analysis") or c.get("cause") or ""
            outcome = c.get("market_outcome") or c.get("effect") or ""
            ce_lines.append(f"- Cause: {cause[:80]} -> Outcome: {outcome[:80]}")
        sections.append("### CAUSAL CHAINS (cause_and_effect):\n" + "\n".join(ce_lines))

    # Recent trades & decisions
    trades = data.get("trades", [])
    decs = data.get("decisions", [])
    if trades or decs:
        td_lines = []
        for t in trades[:2]:
            act = t.get("signal") or t.get("action") or "TRADE"
            price = t.get("price") if t.get("price") is not None else t.get("execution_price")
            reasoning = t.get("reasoning") or ""
            td_lines.append(f"- Trade: {act} {t.get('ticker')} @ ${float(price or 0):.2f} - {reasoning[:100]}")
        for d in decs[:2]:
            act = d.get("signal") or d.get("action") or "DECISION"
            conf = d.get("confidence") if d.get("confidence") is not None else d.get("confidence_score")
            reasoning = d.get("reasoning") or ""
            td_lines.append(f"- Decision: {act} {d.get('ticker')} (Conv: {conf or 0}%) - {reasoning[:100]}")
        sections.append("### RECENT TRADES & AUDIT DECISIONS:\n" + "\n".join(td_lines))

    # Barometer and Catalyst Radar
    baro = data.get("barometer")
    radars = data.get("catalyst_radar", [])
    macro_lines = []
    if baro:
        if "pe_ratio" in baro:
            dt = baro.get("date", "Latest")
            macro_lines.append(
                f"- Barometer ({dt}): P/E {baro.get('pe_ratio')} | Fwd P/E {baro.get('forward_pe')} | Momentum {baro.get('earnings_surprise_momentum')}"
            )
        elif "score" in baro:
            macro_lines.append(
                f"- Barometer: Score {baro.get('score')} ({baro.get('status')}) | Regime: {baro.get('regime')}"
            )
    for r in radars[:2]:
        concept = r.get("concept_name") or r.get("narrative") or ""
        cat = r.get("catalyst_title") or r.get("catalyst") or ""
        impact = r.get("impact") or r.get("urgency") or "NEUTRAL"
        macro_lines.append(f"- Catalyst: [{impact}] {concept} ({cat})")
    if macro_lines:
        sections.append("### MACRO & CATALYST CONTEXT:\n" + "\n".join(macro_lines))

    return "\n\n".join(sections)
