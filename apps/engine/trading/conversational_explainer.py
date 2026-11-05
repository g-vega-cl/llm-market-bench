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
    get_latest_news_synthesis,
    query_multi_tier_llm,
)

COMMON_STOPWORDS = {
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
    "the",
    "can",
    "some",
    "more",
    "get",
    "put",
    "puts",
    "call",
    "calls",
    "into",
    "onto",
    "than",
    "then",
    "been",
    "being",
    "were",
    "went",
    "going",
    "just",
    "like",
    "make",
    "much",
    "most",
    "also",
    "over",
    "lower",
    "higher",
}


def extract_search_keywords(query: str) -> list[str]:
    """Extract clean alphanumeric keywords from user query for database search."""
    if not query:
        return []
    words = re.findall(r"\b[A-Za-z0-9]{3,}\b", query)
    extracted = [w.lower() for w in words if w.lower() not in COMMON_STOPWORDS]
    return extracted[:6] or [w.lower() for w in words[:3] if w.lower() not in {"the", "and", "for"}]


def _parse_iso_datetime(dt_str: str | None) -> datetime | None:
    if not dt_str:
        return None
    try:
        clean = dt_str.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(clean)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed
    except Exception:
        return None


def rank_and_filter_memories(
    memories: list[dict[str, Any]],
    query: str = "",
    now_dt: datetime | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Filter out resolved/expired/academic memories and rank active items by composite score.

    Composite score considers:
    - importance_score (1-10)
    - relevance_score (0.0-1.0 decay)
    - recency decay (exponential half-life against now_dt)
    - query keyword match boost
    """
    if not memories:
        return []

    if now_dt is None:
        now_dt = datetime.now(UTC)
    elif now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=UTC)

    today_str = now_dt.strftime("%Y-%m-%d")
    query_kws = {kw.lower() for kw in extract_search_keywords(query)}

    valid: list[tuple[float, dict[str, Any]]] = []
    seen_ids = set()

    for m in memories:
        mid = m.get("id")
        if mid and mid in seen_ids:
            continue

        status = (m.get("status") or "ACTIVE").upper()
        if status != "ACTIVE":
            continue

        mtype = (m.get("memory_type") or "").upper()
        if mtype == "ACADEMIC_PAPER":
            continue

        # Drop expired calendar events
        target_date = m.get("target_date")
        if target_date and str(target_date) < today_str and mtype == "CALENDAR_EVENT":
            continue

        relevance = float(m.get("relevance_score") if m.get("relevance_score") is not None else 1.0)
        if relevance < 0.20:
            continue

        importance = float(m.get("importance_score") or 5.0)

        # Recency calculation
        created_dt = _parse_iso_datetime(m.get("created_at"))
        recency_weight = 1.0
        if created_dt:
            age_days = max(0.0, (now_dt - created_dt).total_seconds() / 86400.0)
            # 60-day half life for recency weighting
            recency_weight = 0.5 ** (age_days / 60.0)

        # Keyword match boost
        content = (m.get("content") or "").lower()
        match_count = sum(1 for kw in query_kws if kw in content)
        match_boost = 1.0 + (0.35 * match_count)

        score = (importance / 10.0) * relevance * recency_weight * match_boost
        valid.append((score, m))
        if mid:
            seen_ids.add(mid)

    valid.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in valid[:limit]]


async def retrieve_qa_grounding(
    sb_client: Any,
    query: str,
    ticker: str = "SPY",
    limit_memories: int = 5,
) -> dict[str, Any]:
    """Retrieve desk decisions, positioning, live news, and query-relevant memories for conversational Q&A."""
    results: dict[str, Any] = {
        "recent_decisions": [],
        "recent_trades": [],
        "memories": [],
        "cause_and_effect": [],
        "barometer": None,
        "catalyst_radar": [],
        "breaking_news": [],
        "news_summary": None,
        "current_timestamp": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
    }
    if not sb_client:
        return results

    now_utc = datetime.now(UTC)
    today_str = now_utc.strftime("%Y-%m-%d")

    # 1. Recent Desk Decisions (market_feeling)
    try:
        mf_res = (
            sb_client.table("market_feeling")
            .select("id, sentiment_label, confidence_score, why_explanation, trades_summary, news_summary, created_at")
            .order("created_at", desc=True)
            .limit(3)
            .execute()
        )
        results["recent_decisions"] = mf_res.data or []
        for row in results["recent_decisions"]:
            if row.get("news_summary") and not results["news_summary"]:
                results["news_summary"] = row.get("news_summary")
    except Exception:
        logger.exception("Failed to retrieve market_feeling for QA grounding")

    if not results["news_summary"]:
        results["news_summary"] = get_latest_news_synthesis()

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

    # 3. Memories searched by query keywords and augmented with fresh active memories
    keywords = extract_search_keywords(query)
    raw_memories: list[dict[str, Any]] = []
    try:
        if keywords:
            or_filter = ",".join([f"content.ilike.%{kw}%" for kw in keywords])
            try:
                mem_res = (
                    sb_client.table("memories")
                    .select(
                        "id, content, importance_score, relevance_score, status, memory_type, target_date, metadata, created_at"
                    )
                    .eq("status", "ACTIVE")
                    .or_(or_filter)
                    .order("created_at", desc=True)
                    .limit(limit_memories * 3)
                    .execute()
                )
                raw_memories.extend(mem_res.data or [])
            except Exception:
                pass

            if not raw_memories:
                try:
                    mem_res = (
                        sb_client.table("memories")
                        .select("id, content, importance_score, metadata")
                        .or_(or_filter)
                        .order("importance_score", desc=True)
                        .limit(limit_memories * 3)
                        .execute()
                    )
                    raw_memories.extend(mem_res.data or [])
                except Exception:
                    pass

        # Fresh active memories pool
        try:
            fresh_res = (
                sb_client.table("memories")
                .select(
                    "id, content, importance_score, relevance_score, status, memory_type, target_date, metadata, created_at"
                )
                .eq("status", "ACTIVE")
                .gte("relevance_score", 0.20)
                .order("created_at", desc=True)
                .limit(10)
                .execute()
            )
            raw_memories.extend(fresh_res.data or [])
        except Exception:
            pass

        results["memories"] = rank_and_filter_memories(raw_memories, query=query, now_dt=now_utc, limit=limit_memories)
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
                    .select("id, analysis, market_outcome, confidence, tags, created_at")
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
                .select("id, analysis, market_outcome, confidence, tags, created_at")
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

    # 6. Catalyst Radar (prioritize upcoming or current catalysts)
    try:
        radar_res = (
            sb_client.table("catalyst_radar")
            .select("id, concept_name, catalyst_title, impact, memory_content, target_date, created_at")
            .gte("target_date", today_str)
            .order("target_date", desc=False)
            .limit(3)
            .execute()
        )
        radar_items = radar_res.data or []
        if not radar_items:
            fallback_radar = (
                sb_client.table("catalyst_radar")
                .select("id, concept_name, catalyst_title, impact, memory_content, target_date, created_at")
                .order("created_at", desc=True)
                .limit(2)
                .execute()
            )
            radar_items = fallback_radar.data or []
        results["catalyst_radar"] = radar_items
    except Exception:
        logger.exception("Failed to retrieve catalyst_radar for QA grounding")

    # 7. Breaking Intraday News Headlines
    try:
        news_res = (
            sb_client.table("intraday_market_news")
            .select("source, headline, event_timestamp")
            .order("event_timestamp", desc=True)
            .limit(5)
            .execute()
        )
        results["breaking_news"] = news_res.data or []
    except Exception:
        logger.exception("Failed to retrieve breaking news for QA grounding")

    return results


def format_qa_context(grounding: dict[str, Any]) -> str:
    """Format retrieved grounding into clean sections for the conversational LLM."""
    sections = []

    # Clock Header
    clock_str = grounding.get("current_timestamp") or datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    sections.append(f"### CURRENT MARKET CLOCK: {clock_str}")

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
            turn_dt = (d.get("created_at") or "")[:16].replace("T", " ")
            dt_tag = f"[{turn_dt} UTC] " if turn_dt else ""
            lines.append(f"- {dt_tag}Stance: {d.get('sentiment_label')} | Action: {act} {stats}")
            if d.get("why_explanation"):
                lines.append(f"  Rationale: {d.get('why_explanation')[:180]}")
        sections.append("### TRADING DESK RECENT CHOICES & POSITIONING:\n" + "\n".join(lines))

    # 2. Breaking News & 30-Minute Intelligence Synthesis
    news_items = grounding.get("breaking_news", [])
    news_summary = grounding.get("news_summary")
    if news_items or news_summary:
        news_lines = []
        if news_summary:
            news_lines.append(f"- Rolling Synthesis: {news_summary.strip()}")
        for n in news_items[:4]:
            t_str = (n.get("event_timestamp") or "")[:16].replace("T", " ")
            src = n.get("source") or "Wire"
            head = n.get("headline") or ""
            news_lines.append(f"- [{t_str} | {src}] {head}")
        sections.append("### BREAKING LIVE NEWS & MACRO INTELLIGENCE:\n" + "\n".join(news_lines))

    # 3. Historical Precedents & Active Memories
    mems = grounding.get("memories", [])
    if mems:
        mem_lines = []
        for m in mems[:4]:
            created = (m.get("created_at") or "")[:10]
            target = f" | Target: {m.get('target_date')}" if m.get("target_date") else ""
            content = (m.get("content") or "")[:220]
            mem_lines.append(f"- [{created}{target}] {content}")
        # Section title preserves backwards compatibility with existing assertions
        sections.append("### HISTORICAL PRECEDENTS & RETRIEVED MEMORIES:\n" + "\n".join(mem_lines))

    # 4. Causal Chains
    ces = grounding.get("cause_and_effect", [])
    if ces:
        ce_lines = []
        for c in ces[:2]:
            cause = (c.get("analysis") or c.get("cause") or "")[:120]
            outcome = (c.get("market_outcome") or c.get("effect") or "")[:120]
            ce_lines.append(f"- Causal Thesis: {cause} -> Market Outcome: {outcome}")
        sections.append("### CAUSAL CHAINS (cause_and_effect):\n" + "\n".join(ce_lines))

    # 5. Macro Breadth & Catalysts
    baro = grounding.get("barometer")
    radars = grounding.get("catalyst_radar", [])
    macro_items = []
    if baro:
        b_date = baro.get("date") or "Latest"
        pe = f"{float(baro['pe_ratio']):.2f}" if baro.get("pe_ratio") is not None else "N/A"
        fpe = f"{float(baro['forward_pe']):.2f}" if baro.get("forward_pe") is not None else "N/A"
        mom = (
            f"{float(baro['earnings_surprise_momentum']):.1f}"
            if baro.get("earnings_surprise_momentum") is not None
            else "N/A"
        )
        macro_items.append(
            f"- Macro Barometer (As of {b_date}): S&P 500 P/E {pe}, Forward P/E {fpe}, Earnings Surprise Momentum {mom}"
        )
    for r in radars[:2]:
        t_date = f" ({r.get('target_date')})" if r.get("target_date") else ""
        macro_items.append(
            f"- Catalyst{t_date}: [{r.get('impact', 'NEUTRAL')}] {r.get('concept_name')} - {r.get('catalyst_title')}"
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
        "2. Provide deeply researched, well-founded market commentary on macroeconomic, policy, or catalyst questions (such as election cycles, midterms, earnings, or interest rates) grounded strictly in our current live data, historical memories, causal chains, and macro data.\n\n"
        "Time & Date Grounding Guidelines (CRITICAL):\n"
        "- Anchor your analysis strictly in the CURRENT MARKET CLOCK date provided in context. Never treat past months or past calendar meetings as upcoming future catalysts.\n"
        "- When referencing historical memories or prior rate decisions, explicitly contextualize them as past precedent (e.g. 'In late 2025/early 2026...').\n"
        "- Prioritize active breaking headlines, the latest tape, and upcoming catalysts (e.g. tomorrow's jobs report, next week's PPI) over historical records.\n\n"
        "Tone and Formatting Guidelines:\n"
        "- Directly answer the user's inquiry with articulate, analytical, and professional prose.\n"
        "- Format your response using clean Markdown with bullet points or numbered sections where appropriate.\n"
        "- Cite relevant technical indicators, breaking wire headlines, or memory precedents when explaining your stance.\n"
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
