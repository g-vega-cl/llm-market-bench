"""Point-in-time news/memories filtering and stage prompt hydration."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

from core.config import logger
from recipes.push_schema import (
    MemoriesBlock,
    NewsBlock,
    PromptBlock,
    StrategyStage,
    TechnicalsBlock,
    TechnicalsRule,
)


def _parse_utc(raw: str | datetime | None) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=UTC)
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    except ValueError:
        return None


def _matches_contains(haystack: str, keywords: list[str]) -> bool:
    cleaned = [k.strip().lower() for k in keywords if k.strip()]
    if not cleaned:
        return True
    lower = haystack.lower()
    return any(kw in lower for kw in cleaned)


EXCERPT_RADIUS = 150
EXCERPT_LEAD_CHARS = 300
_WS_RUN = re.compile(r"[ \t\r\n\f\v\u00a0]+")


def build_news_excerpt(full_text: str | None, keywords: list[str]) -> str:
    """Return a bounded body excerpt centered on the first keyword hit (else the lead)."""
    text = _WS_RUN.sub(" ", full_text or "").strip(" ")
    if not text:
        return ""
    lower = text.lower()
    if len(lower) != len(text):  # case folding changed length; keep indices aligned
        lower = text
    hits = [i for kw in keywords if kw.strip() and (i := lower.find(kw.strip().lower())) >= 0]
    if not hits:
        return text if len(text) <= EXCERPT_LEAD_CHARS else text[:EXCERPT_LEAD_CHARS].rstrip() + "…"
    pos = min(hits)
    start = max(0, pos - EXCERPT_RADIUS)
    end = min(len(text), pos + EXCERPT_RADIUS)
    if start > 0 and (sp := text.find(" ", start)) != -1 and sp < pos:
        start = sp + 1
    if end < len(text) and (sp := text.rfind(" ", pos, end)) != -1:
        end = sp
    return ("…" if start > 0 else "") + text[start:end] + ("…" if end < len(text) else "")


def filter_news_rows(
    rows: list[dict[str, Any]],
    contains: list[str],
    recency_hours: int,
    as_of_utc: datetime,
    limit: int = 15,
) -> list[dict[str, Any]]:
    """Filter news rows by point-in-time recency and keyword contains."""
    floor_dt = as_of_utc - timedelta(hours=max(1, recency_hours))
    matched: list[dict[str, Any]] = []
    for row in rows:
        pub = _parse_utc(row.get("date_published"))
        if pub is None or pub > as_of_utc or pub < floor_dt:
            continue
        blob = f"{row.get('title', '')} {row.get('full_text', '')}"
        if _matches_contains(blob, contains):
            matched.append(row)
            if len(matched) >= limit:
                break
    return matched


def filter_memory_rows(
    rows: list[dict[str, Any]],
    contains: list[str],
    recency_hours: int,
    category: str,
    min_importance: int,
    as_of_utc: datetime,
    limit: int = 15,
) -> list[dict[str, Any]]:
    """Filter memory rows by point-in-time recency, category, importance, and keywords."""
    floor_dt = as_of_utc - timedelta(hours=max(1, recency_hours))
    cat_norm = (category or "ALL").upper().strip()
    matched: list[dict[str, Any]] = []
    for row in rows:
        created = _parse_utc(row.get("created_at"))
        if created is None or created > as_of_utc or created < floor_dt:
            continue
        importance = int(row.get("importance_score") or 5)
        if importance < min_importance:
            continue
        mem_type = str(row.get("memory_type") or "MARKET_EVENT").upper().strip()
        if cat_norm != "ALL" and mem_type != cat_norm:
            continue
        if _matches_contains(str(row.get("content", "")), contains):
            matched.append(row)
            if len(matched) >= limit:
                break
    return matched


def format_technicals_block(rules: list[TechnicalsRule]) -> str:
    """Serialize technical/fundamental rules into clear LLM screening instructions."""
    if not rules:
        return "[Technicals Filter]: No technical filters configured."
    lines = ["[Technicals & Fundamentals Criteria (apply when selecting or filtering tickers)]:"]
    for r in rules:
        lines.append(f"- {r.metric} {r.operator} {r.target}")
    return "\n".join(lines)


def fetch_push_context_batch(
    sb_client: Any,
    as_of_utc: datetime,
    lookback_hours: int = 336,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Prefetch news and memories once up to as_of_utc (zero N+1 queries, strips embeddings)."""
    news_rows: list[dict[str, Any]] = []
    memory_rows: list[dict[str, Any]] = []
    floor_iso = (as_of_utc - timedelta(hours=max(24, lookback_hours))).isoformat()
    as_of_iso = as_of_utc.isoformat()

    try:
        res_news = (
            sb_client.table("recipe_news_corpus")
            .select("article_id, title, full_text, date_published, tickers")
            .gte("date_published", floor_iso)
            .lte("date_published", as_of_iso)
            .order("date_published", desc=True)
            .limit(2000)
            .execute()
        )
        news_rows = res_news.data or []
    except Exception:
        logger.exception("Failed prefetching recipe_news_corpus batch")

    try:
        res_mem = (
            sb_client.table("memories")
            .select("id, content, created_at, memory_type, importance_score, metadata")
            .gte("created_at", floor_iso)
            .lte("created_at", as_of_iso)
            .order("created_at", desc=True)
            .limit(2000)
            .execute()
        )
        memory_rows = res_mem.data or []
    except Exception:
        logger.exception("Failed prefetching memories batch")

    return news_rows, memory_rows


def hydrate_stage_prompt(
    stage: StrategyStage,
    news_rows: list[dict[str, Any]],
    memory_rows: list[dict[str, Any]],
    as_of_utc: datetime,
    prev_output: str | None = None,
) -> str:
    """Assemble the exact prompt text for a Stage from its 4 push blocks."""
    sections: list[str] = []
    used_prev_placeholder = False

    for block in stage.blocks:
        if isinstance(block, PromptBlock):
            text = block.text.strip()
            if "{{prev_output}}" in text:
                text = text.replace("{{prev_output}}", prev_output or "")
                used_prev_placeholder = True
            if text:
                sections.append(text)
        elif isinstance(block, NewsBlock):
            matched_news = filter_news_rows(
                news_rows,
                contains=block.contains,
                recency_hours=block.recency_hours,
                as_of_utc=as_of_utc,
            )
            kw_label = ", ".join(block.contains) if block.contains else "ALL"
            header = f"[News (contains: {kw_label} | recency: {block.recency_hours}h)]:"
            if not matched_news:
                sections.append(f"{header}\n- (No matching news in window)")
            else:
                items = []
                for n in matched_news:
                    line = (
                        f"- [{str(n.get('date_published', ''))[:16]}] {n.get('title', '')} "
                        f"(Tickers: {', '.join(n.get('tickers') or []) or 'MARKET'})"
                    )
                    excerpt = build_news_excerpt(n.get("full_text"), block.contains)
                    items.append(f"{line}\n  {excerpt}" if excerpt else line)
                sections.append("\n".join([header, *items]))
        elif isinstance(block, MemoriesBlock):
            matched_mem = filter_memory_rows(
                memory_rows,
                contains=block.contains,
                recency_hours=block.recency_hours,
                category=block.category,
                min_importance=block.min_importance,
                as_of_utc=as_of_utc,
            )
            kw_label = ", ".join(block.contains) if block.contains else "ALL"
            header = (
                f"[Memories (contains: {kw_label} | recency: {block.recency_hours}h | "
                f"category: {block.category} | min_importance: {block.min_importance})]:"
            )
            if not matched_mem:
                sections.append(f"{header}\n- (No matching memories in window)")
            else:
                items = [
                    f"- [{m.get('memory_type', 'EVENT')} | imp={m.get('importance_score', 5)}] {m.get('content', '')}"
                    for m in matched_mem
                ]
                sections.append("\n".join([header, *items]))
        elif isinstance(block, TechnicalsBlock):
            sections.append(format_technicals_block(block.rules))

    if prev_output and not used_prev_placeholder:
        sections.append(f"[Previous Stage Output]:\n{prev_output}")

    return "\n\n".join(sections)
