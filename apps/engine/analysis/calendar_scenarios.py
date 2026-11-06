"""Forward Calendar & Scenario Analysis Engine.

Retrieves upcoming economic/corporate calendar triggers, consensus scenario trees,
conditional trading plans, and relevant historical precedent memories.
"""

import re
from datetime import UTC, date, datetime, timedelta
from typing import Any

from core.config import logger
from core.db import get_supabase_client


def parse_date(date_str: str | None) -> date | None:
    """Parses date from YYYY-MM-DD string or extracts it via regex."""
    if not date_str:
        return None
    match = re.search(r"(\d{4}-\d{2}-\d{2})", str(date_str))
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y-%m-%d").date()
    except ValueError:
        return None


def calculate_target_window(timeframe: str = "next_week", ref_date: date | None = None) -> tuple[date, date, str]:
    """Calculates start and end dates for a requested forecast horizon."""
    if ref_date is None:
        ref_date = datetime.now(UTC).date()

    tf = (timeframe or "next_week").lower().strip()

    if tf == "today":
        start = ref_date
        end = ref_date
        label = f"Today ({start.strftime('%A, %b %d, %Y')})"
    elif tf == "tomorrow":
        start = ref_date + timedelta(days=1)
        end = start
        label = f"Tomorrow ({start.strftime('%A, %b %d, %Y')})"
    elif tf in ("next_week", "week", "7d"):
        start = ref_date + timedelta(days=1)
        end = ref_date + timedelta(days=8)
        label = f"Next 7 Days ({start.strftime('%b %d')} to {end.strftime('%b %d, %Y')})"
    elif tf in ("next_14_days", "14d", "two_weeks"):
        start = ref_date + timedelta(days=1)
        end = ref_date + timedelta(days=14)
        label = f"Next 14 Days ({start.strftime('%b %d')} to {end.strftime('%b %d, %Y')})"
    elif tf in ("all_upcoming", "30d", "month"):
        start = ref_date
        end = ref_date + timedelta(days=30)
        label = f"Upcoming Month ({start.strftime('%b %d')} to {end.strftime('%b %d, %Y')})"
    else:
        # Default to next 7 days
        start = ref_date + timedelta(days=1)
        end = ref_date + timedelta(days=8)
        label = f"Horizon: {timeframe} ({start.strftime('%b %d')} to {end.strftime('%b %d, %Y')})"

    return start, end, label


def fetch_upcoming_events(
    start_date: date,
    end_date: date,
    min_importance: int = 5,
    sb_client: Any | None = None,
) -> list[dict[str, Any]]:
    """Queries memories for upcoming CALENDAR_EVENT and consensus_event triggers."""
    if sb_client is None:
        sb_client = get_supabase_client()

    try:
        resp = (
            sb_client.table("memories")
            .select("id, content, memory_type, target_date, importance_score, metadata")
            .gte("target_date", start_date.isoformat())
            .lte("target_date", end_date.isoformat())
            .gte("importance_score", min_importance)
            .order("target_date", desc=False)
            .limit(50)
            .execute()
        )
        return resp.data or []
    except Exception as e:
        logger.exception("Error fetching upcoming calendar events: %s", e)
        return []


def fetch_historical_lessons(
    event_keywords: list[str],
    sb_client: Any | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Retrieves relevant historical memories and lessons for matched catalysts."""
    if sb_client is None:
        sb_client = get_supabase_client()

    try:
        resp = (
            sb_client.table("memories")
            .select("id, content, memory_type, importance_score, metadata")
            .gte("importance_score", 7)
            .order("created_at", desc=True)
            .limit(40)
            .execute()
        )
        rows = resp.data or []
        if not rows or not event_keywords:
            return rows[:limit]

        # Filter memories that relate to keywords
        scored = []
        for r in rows:
            text = (r.get("content") or "").lower()
            meta_str = str(r.get("metadata") or {}).lower()
            score = 0
            for kw in event_keywords:
                kw_lower = kw.lower()
                if len(kw_lower) >= 3 and (kw_lower in text or kw_lower in meta_str):
                    score += 2
            if score > 0 or r.get("memory_type") == "LESSON":
                scored.append((score, r))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:limit]]
    except Exception as e:
        logger.debug("Error fetching historical lessons: %s", e)
        return []


def clean_event_title(content: str, metadata: dict[str, Any] | None = None) -> str:
    """Extracts clean catalyst headline from memory content or metadata."""
    meta = metadata or {}
    if meta.get("event_name"):
        return str(meta["event_name"])

    title = re.sub(r"^\[CALENDAR EVENT\]\s*", "", content, flags=re.IGNORECASE)
    title = re.sub(r"^\([^)]*\)\s*", "", title)
    title = re.sub(r"^\d{4}-\d{2}-\d{2}:\s*", "", title)
    if "|" in title:
        title = title.split("|")[0].strip()
    if ":" in title:
        parts = title.split(":", 1)
        if len(parts[0].strip()) > 3:
            return parts[0].strip()
    return title.strip() or content.strip()


def _filter_events_by_ticker(events: list[dict[str, Any]], ticker_filter: str | None) -> list[dict[str, Any]]:
    """Filters calendar events to those matching ticker_filter if specified."""
    if not ticker_filter:
        return list(events)
    filtered = []
    for ev in events:
        meta = ev.get("metadata") or {}
        scenarios = meta.get("scenarios") or []
        discovered = meta.get("discovered_assets") or []
        related = meta.get("tickers") or []
        content = ev.get("content") or ""
        matches_ticker = (
            ticker_filter in str(discovered).upper()
            or ticker_filter in str(related).upper()
            or ticker_filter in str(scenarios).upper()
            or ticker_filter in content.upper()
        )
        if matches_ticker:
            filtered.append(ev)
    return filtered


def _format_scenario_lines(scenarios: list[Any]) -> list[str]:
    """Formats structured scenarios into markdown bullet lines."""
    s_lines = ["- **Multi-Scenario Partition & Trading Plans:**"]
    for sc in scenarios:
        if not isinstance(sc, dict):
            continue
        header = sc.get("header") or "Scenario"
        prob = sc.get("probability")
        prob_str = f" ({prob}% probability)" if prob is not None else ""
        desc = sc.get("description") or ""
        plan = sc.get("trading_plan") or ""
        assets = sc.get("assets") or []

        asset_tickers = []
        for a in assets:
            if isinstance(a, dict) and a.get("ticker"):
                asset_tickers.append(a["ticker"])
            elif isinstance(a, str):
                asset_tickers.append(a)

        s_lines.append(f"  * **{header}**{prob_str}: {desc}")
        if plan:
            s_lines.append(f"    - **Trading Plan / Profit Mechanism**: {plan}")
        if asset_tickers:
            s_lines.append(f"    - **Target Assets**: {', '.join(asset_tickers)}")
    return s_lines


def _format_single_event_block(ev: dict[str, Any], tomorrow_date_str: str) -> list[str]:
    """Formats a single calendar event dictionary into markdown lines."""
    meta = ev.get("metadata") or {}
    t_date = ev.get("target_date") or "Unknown"
    title = clean_event_title(ev.get("content", ""), meta)
    time_str = meta.get("event_time") or "Time: N/A"
    impact = meta.get("impact") or "MODERATE"
    importance = ev.get("importance_score") or 7

    date_badge = "📅 TOMORROW" if t_date == tomorrow_date_str else f"📅 {t_date}"
    ev_lines = [
        f"#### {date_badge} | {title} (Impact: {impact}, Score: {importance}/10)",
        f"- **Scheduled Time**: {time_str}",
    ]

    scenarios = meta.get("scenarios")
    if scenarios and isinstance(scenarios, list):
        ev_lines.extend(_format_scenario_lines(scenarios))
    elif meta.get("scenario_analysis"):
        ev_lines.append(f"- **Scenario Analysis & Playbook**: {meta['scenario_analysis']}")
    else:
        ev_lines.append(f"- **Event Details**: {ev.get('content')}")

    ev_lines.append("")
    return ev_lines


def format_calendar_scenarios_context(
    events: list[dict[str, Any]],
    historical_memories: list[dict[str, Any]],
    window_label: str,
    detail: bool = True,
    ticker: str | None = None,
    ref_date: date | None = None,
) -> str:
    """Formats upcoming calendar events, scenarios, trading plans, and past memories into markdown."""
    if ref_date is None:
        ref_date = datetime.now(UTC).date()

    ticker_filter = ticker.upper().strip() if ticker else None
    filtered_events = _filter_events_by_ticker(events, ticker_filter)

    if not filtered_events:
        msg = f"### Upcoming Calendar & Scenario Analysis ({window_label})\n\n"
        if ticker_filter:
            msg += f"No scheduled high-impact catalysts or scenario analyses found matching ticker '{ticker_filter}'.\n"
        else:
            msg += "No scheduled high-impact calendar events or consensus scenarios found within this horizon.\n"
        return msg.strip()

    tomorrow_date_str = (ref_date + timedelta(days=1)).isoformat()

    lines = [
        f"### 🗓️ Upcoming Calendar & Scenario Analysis ({window_label})",
        "Chronological scheduled triggers paired with probability-weighted scenario trading plans.",
        "",
    ]

    for ev in filtered_events:
        lines.extend(_format_single_event_block(ev, tomorrow_date_str))

    if historical_memories:
        lines.append("### 🧠 Historical Precedent & Playbook Lessons")
        lines.append("Lessons learned from past market reactions to similar catalysts:")
        for mem in historical_memories:
            meta = mem.get("metadata") or {}
            content = mem.get("content") or ""
            parallel = meta.get("historical_parallel")
            header_prefix = f"**[{parallel}]** " if parallel else ""
            lines.append(f"- {header_prefix}{content}")
        lines.append("")

    return "\n".join(lines).strip()


async def execute_get_calendar_scenario_analysis_tool(
    timeframe: str = "next_week",
    ticker: str | None = None,
    min_importance: int = 5,
    detail: bool = True,
    include_historical_memories: bool = True,
    ref_date: date | None = None,
) -> str:
    """Executor for the get_calendar_scenario_analysis LLM tool."""
    try:
        start_date, end_date, window_label = calculate_target_window(timeframe, ref_date=ref_date)
        events = fetch_upcoming_events(start_date, end_date, min_importance=min_importance)

        historical = []
        if include_historical_memories:
            # Gather keywords from matched events
            keywords = []
            for ev in events:
                title = clean_event_title(ev.get("content", ""), ev.get("metadata"))
                keywords.extend([w for w in title.split() if len(w) > 3])
            historical = fetch_historical_lessons(keywords[:8])

        return format_calendar_scenarios_context(
            events=events,
            historical_memories=historical,
            window_label=window_label,
            detail=detail,
            ticker=ticker,
            ref_date=ref_date,
        )
    except Exception as e:
        logger.exception("Error executing get_calendar_scenario_analysis: %s", e)
        return f"Error executing calendar scenario analysis: {str(e)}"
