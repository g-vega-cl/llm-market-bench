"""Decoupled conversational trader and audience Q&A explainer.

Provides articulate, researched answers to audience questions about the live trader's
past choices, current market positioning, and macroeconomic hypotheses (such as election
cycles, midterms, and rate decisions) grounded strictly in historical memories and database records.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

import httpx

from core.config import logger
from trading.live_intraday_agent import (
    DEFAULT_CHEAP_PROXY_URL,
    DEFAULT_STRATA_URL,
    query_multi_tier_llm,
)


def extract_search_keywords(query: str) -> list[str]:
    """Extract clean alphanumeric keywords from user query for database search."""
    if not query:
        return []
    words = re.findall(r"\b[A-Za-z0-9]{3,}\b", query)
    stopwords = {
        "what",
        "when",
        "where",
        "which",
        "this",
        "that",
        "with",
        "from",
        "have",
        "will",
        "does",
        "about",
        "your",
        "their",
        "there",
        "would",
        "could",
        "should",
        "think",
        "after",
    }
    extracted = [w.lower() for w in words if w.lower() not in stopwords]
    return extracted[:6] or [w.lower() for w in words[:3]]


async def retrieve_qa_grounding(
    sb_client: Any,
    query: str,
    ticker: str = "SPY",
    limit_memories: int = 5,
) -> dict[str, Any]:
    """Retrieve desk decisions, positioning, and query-relevant memories for conversational Q&A."""
    results: dict[str, Any] = {
        "recent_decisions": [],
        "recent_trades": [],
        "memories": [],
        "cause_and_effect": [],
        "barometer": None,
        "catalyst_radar": [],
    }
    if not sb_client:
        return results

    # 1. Recent Desk Decisions (market_feeling)
    try:
        mf_res = (
            sb_client.table("market_feeling")
            .select("id, sentiment_label, confidence_score, why_explanation, trades_summary, created_at")
            .order("created_at", desc=True)
            .limit(3)
            .execute()
        )
        results["recent_decisions"] = mf_res.data or []
    except Exception:
        logger.exception("Failed to retrieve market_feeling for QA grounding")

    # 2. Recent Trades
    try:
        trades_res = (
            sb_client.table("trades")
            .select("id, ticker, signal, price, reasoning, executed_at")
            .order("executed_at", desc=True)
            .limit(3)
            .execute()
        )
        results["recent_trades"] = trades_res.data or []
    except Exception:
        logger.exception("Failed to retrieve trades for QA grounding")

    # 3. Memories searched by query keywords
    keywords = extract_search_keywords(query)
    try:
        mem_data: list[dict[str, Any]] = []
        if keywords:
            or_filter = ",".join([f"content.ilike.%{kw}%" for kw in keywords])
            mem_res = (
                sb_client.table("memories")
                .select("id, content, importance_score, metadata")
                .or_(or_filter)
                .order("importance_score", desc=True)
                .limit(limit_memories)
                .execute()
            )
            mem_data = mem_res.data or []

        if len(mem_data) < 2:
            top_res = (
                sb_client.table("memories")
                .select("id, content, importance_score, metadata")
                .order("importance_score", desc=True)
                .limit(3)
                .execute()
            )
            existing_ids = {m.get("id") for m in mem_data}
            for m in top_res.data or []:
                if m.get("id") not in existing_ids:
                    mem_data.append(m)

        results["memories"] = mem_data
    except Exception:
        logger.exception("Failed to retrieve memories for QA grounding")

    # 4. Causal Chains
    try:
        ce_data: list[dict[str, Any]] = []
        if keywords:
            or_filter = ",".join([f"analysis.ilike.%{kw}%" for kw in keywords])
            try:
                ce_res = (
                    sb_client.table("cause_and_effect")
                    .select("id, analysis, market_outcome, confidence, tags")
                    .or_(or_filter)
                    .order("created_at", desc=True)
                    .limit(3)
                    .execute()
                )
                ce_data = ce_res.data or []
            except Exception:
                pass

        if not ce_data:
            ce_res = (
                sb_client.table("cause_and_effect")
                .select("id, analysis, market_outcome, confidence, tags")
                .order("created_at", desc=True)
                .limit(3)
                .execute()
            )
            ce_data = ce_res.data or []
        results["cause_and_effect"] = ce_data
    except Exception:
        logger.exception("Failed to retrieve cause_and_effect for QA grounding")

    # 5. Market Barometer
    try:
        baro_res = (
            sb_client.table("market_barometer_history")
            .select("date, pe_ratio, forward_pe, pb_ratio, ps_ratio, earnings_surprise_momentum")
            .order("date", desc=True)
            .limit(1)
            .execute()
        )
        if baro_res.data:
            results["barometer"] = baro_res.data[0]
    except Exception:
        logger.exception("Failed to retrieve barometer for QA grounding")

    # 6. Catalyst Radar
    try:
        radar_res = (
            sb_client.table("catalyst_radar")
            .select("id, concept_name, catalyst_title, impact, memory_content")
            .order("created_at", desc=True)
            .limit(2)
            .execute()
        )
        results["catalyst_radar"] = radar_res.data or []
    except Exception:
        logger.exception("Failed to retrieve catalyst_radar for QA grounding")

    return results


def format_qa_context(grounding: dict[str, Any]) -> str:
    """Format retrieved grounding into clean sections for the conversational LLM."""
    sections = []

    # 1. Trading Desk Recent Choices & Positioning
    recent_decs = grounding.get("recent_decisions", [])
    if recent_decs:
        lines = []
        for d in recent_decs[:2]:
            ts = d.get("trades_summary") or {}
            tech = ts.get("technicals") or {}
            act = ts.get("action") or "POSITION"
            vwap_str = f"VWAP: ${tech.get('vwap')}" if tech.get("vwap") else ""
            rsi_str = f"RSI: {tech.get('rsi_14')}" if tech.get("rsi_14") else ""
            stats = f"({', '.join(filter(None, [vwap_str, rsi_str]))})" if (vwap_str or rsi_str) else ""
            lines.append(f"- Stance: {d.get('sentiment_label')} | Action: {act} {stats}")
            if d.get("why_explanation"):
                lines.append(f"  Rationale: {d.get('why_explanation')[:180]}")
        sections.append("### TRADING DESK RECENT CHOICES & POSITIONING:\n" + "\n".join(lines))

    # 2. Historical Precedents & Memories
    mems = grounding.get("memories", [])
    if mems:
        mem_lines = [
            f"- [{m.get('id', '')}] {m.get('content', '')[:200]} (Importance: {m.get('importance_score', 5)}/10)"
            for m in mems[:4]
        ]
        sections.append("### HISTORICAL PRECEDENTS & RETRIEVED MEMORIES:\n" + "\n".join(mem_lines))

    # 3. Causal Chains
    ces = grounding.get("cause_and_effect", [])
    if ces:
        ce_lines = []
        for c in ces[:2]:
            cause = (c.get("analysis") or c.get("cause") or "")[:120]
            outcome = (c.get("market_outcome") or c.get("effect") or "")[:120]
            ce_lines.append(f"- Causal Thesis: {cause} -> Market Outcome: {outcome}")
        sections.append("### CAUSAL CHAINS (cause_and_effect):\n" + "\n".join(ce_lines))

    # 4. Macro Breadth & Catalysts
    baro = grounding.get("barometer")
    radars = grounding.get("catalyst_radar", [])
    macro_items = []
    if baro:
        macro_items.append(
            f"- Macro Barometer: P/E {baro.get('pe_ratio')}, Forward P/E {baro.get('forward_pe')}, Momentum {baro.get('earnings_surprise_momentum')}"
        )
    for r in radars[:2]:
        macro_items.append(
            f"- Catalyst: [{r.get('impact', 'NEUTRAL')}] {r.get('concept_name')} - {r.get('catalyst_title')}"
        )
    if macro_items:
        sections.append("### MACRO BREADTH & CATALYSTS:\n" + "\n".join(macro_items))

    return "\n\n".join(sections)


FALLBACK_DESK_PROSE = (
    "> **Desk Notice**: Our quantitative commentary models and local inference desk are temporarily "
    "experiencing high inquiry volume or endpoint maintenance. The desk is maintaining a neutral risk posture, "
    "and your inquiry has been recorded for the strategists on the next evaluation turn."
)


def is_llm_outage_fallback(text: str | None) -> bool:
    """Detect if response is an emergency trading JSON fallback or outage payload."""
    if not text:
        return True
    trimmed = text.strip()
    if "All LLM endpoints currently unavailable" in trimmed:
        return True
    return trimmed.startswith("{") and '"action"' in trimmed


EXPLAINER_MAX_TOKENS = 16384
EXPLAINER_REASONING_BUDGET = 12288


async def answer_audience_question(
    query: str,
    author: str = "Analyst",
    grounding: dict[str, Any] | None = None,
    http_client: httpx.AsyncClient | None = None,
    strata_url: str = DEFAULT_STRATA_URL,
    cheap_proxy_url: str = DEFAULT_CHEAP_PROXY_URL,
) -> str:
    """Generate a conversational, well-researched desk response to an audience inquiry."""
    formatted_context = format_qa_context(grounding or {})

    system_prompt = (
        "You are the Chief Market Strategist and Conversational Trader for the autonomous quantitative trading desk managing a paper portfolio in SPY.\n"
        "Your role is twofold:\n"
        "1. Clearly explain the trading desk's recent choices, current positioning, and technical view when asked.\n"
        "2. Provide deeply researched, well-founded market commentary on macroeconomic, policy, or catalyst questions (such as election cycles, midterms, earnings, or interest rates) grounded strictly in our historical memories, causal chains, and macro data.\n\n"
        "Tone and Formatting Guidelines:\n"
        "- Directly answer the user's inquiry with articulate, analytical, and professional prose.\n"
        "- Format your response using clean Markdown with bullet points or numbered sections where appropriate.\n"
        "- Cite relevant historical precedents, memories, or technical indicators when explaining your stance.\n"
        "- Be transparent about market risks and counter-theses.\n"
        "- Do NOT output JSON. Output clear, well-structured commentary.\n"
    )

    user_prompt = (
        f"Audience Inquiry from @{author}:\n"
        f'"{query}"\n\n'
        f"{formatted_context}\n\n"
        "Provide your articulate, well-researched answer to this inquiry:"
    )

    response = await query_multi_tier_llm(
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        strata_url=strata_url,
        cheap_proxy_url=cheap_proxy_url,
        http_client=http_client,
        max_tokens=EXPLAINER_MAX_TOKENS,
        reasoning_budget_tokens=EXPLAINER_REASONING_BUDGET,
    )
    trimmed = response.strip() if response else ""
    if is_llm_outage_fallback(trimmed):
        logger.warning(
            f"Audience QA received emergency LLM fallback response for @{author}; serving clean desk notice."
        )
        return FALLBACK_DESK_PROSE
    return trimmed


async def process_pending_queue_item(
    sb_client: Any,
    http_client: httpx.AsyncClient | None = None,
    strata_url: str = DEFAULT_STRATA_URL,
    cheap_proxy_url: str = DEFAULT_CHEAP_PROXY_URL,
) -> dict[str, Any] | None:
    """Check for next pending audience question, answer it, and update agent_chat_queue."""
    if not sb_client:
        return None

    queue_item: dict[str, Any] | None = None

    # Atomic dequeue via RPC
    try:
        rpc_res = sb_client.rpc("pop_next_queue_item").execute()
        if rpc_res.data and len(rpc_res.data) > 0:
            queue_item = rpc_res.data[0]
    except Exception:
        # Fallback to direct select
        try:
            res = (
                sb_client.table("agent_chat_queue")
                .select("*")
                .eq("status", "pending")
                .order("created_at")
                .limit(1)
                .execute()
            )
            if res.data and len(res.data) > 0:
                queue_item = res.data[0]
                sb_client.table("agent_chat_queue").update(
                    {"status": "injected", "injected_turn_at": datetime.now(UTC).isoformat()}
                ).eq("id", queue_item["id"]).execute()
        except Exception:
            logger.exception("Failed to query audience chat queue for QA processing")
            return None

    if not queue_item:
        return None

    item_id = queue_item.get("id")
    message = queue_item.get("message", "").strip()
    author = queue_item.get("display_name", "Visitor")

    logger.info(f"Processing audience inquiry id={item_id} from @{author}: {message[:60]}")

    grounding = await retrieve_qa_grounding(sb_client, query=message)
    answer = await answer_audience_question(
        query=message,
        author=author,
        grounding=grounding,
        http_client=http_client,
        strata_url=strata_url,
        cheap_proxy_url=cheap_proxy_url,
    )

    try:
        sb_client.table("agent_chat_queue").update(
            {
                "status": "answered",
                "agent_response": answer,
                "injected_turn_at": datetime.now(UTC).isoformat(),
            }
        ).eq("id", item_id).execute()
        logger.info(f"Successfully answered audience inquiry id={item_id}")
    except Exception:
        logger.exception(f"Failed to update agent_chat_queue with answer for id={item_id}")

    return {
        "id": item_id,
        "author": author,
        "message": message,
        "response": answer,
    }
