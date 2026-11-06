"""Vetted, deduplicated persistence of intraday news into public.intraday_market_news."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from analysis.intraday_news import evaluate_news_with_jev
from analysis.intraday_news_aggregator import (
    deduplicate_news,
    generate_source_id_hash,
)
from core.config import logger
from core.db import get_supabase_client

RECENT_WINDOW_HOURS = 24
RECENT_HEADLINE_LIMIT = 500
EVAL_CONCURRENCY = 3

Evaluator = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


def _stored_hashes(sb: Any, hashes: list[str]) -> set[str]:
    try:
        resp = sb.table("intraday_market_news").select("source_id_hash").in_("source_id_hash", hashes).execute()
        return {r["source_id_hash"] for r in (resp.data or [])}
    except Exception:
        logger.exception("Could not check existing intraday news hashes")
        return set()


def _recent_headlines(sb: Any) -> list[str]:
    since = (datetime.now(UTC) - timedelta(hours=RECENT_WINDOW_HOURS)).isoformat()
    try:
        resp = (
            sb.table("intraday_market_news")
            .select("headline")
            .gte("event_timestamp", since)
            .limit(RECENT_HEADLINE_LIMIT)
            .execute()
        )
        return [r["headline"] for r in (resp.data or []) if r.get("headline")]
    except Exception:
        logger.exception("Could not load recent intraday news headlines")
        return []


async def persist_intraday_news(
    news_items: list[dict[str, Any]],
    sb_client: Any = None,
    evaluate: Evaluator = evaluate_news_with_jev,
) -> int:
    """Upsert new, non-duplicate, Jev-vetted MARKET_MOVING items; return the number stored."""
    if not news_items:
        return 0

    sb = sb_client or get_supabase_client()
    if not sb:
        return 0

    candidates: list[dict[str, Any]] = []
    for item in news_items:
        headline = (item.get("headline") or "").strip()
        if not headline:
            continue
        source = item.get("source", "Unknown")
        pub_time = item.get("published_at") or datetime.now(UTC).isoformat()
        candidates.append(
            {
                "headline": headline,
                "summary": item.get("summary") or "",
                "source": source,
                "url": item.get("url"),
                "tickers": item.get("tickers") or [],
                "event_timestamp": pub_time,
                "source_id_hash": item.get("source_id_hash") or generate_source_id_hash(headline, source, pub_time),
            }
        )
    if not candidates:
        return 0

    known = _stored_hashes(sb, [c["source_id_hash"] for c in candidates])
    fresh = [c for c in candidates if c["source_id_hash"] not in known]

    # Cross-cycle / cross-source dedupe: placeholders for stored headlines come first so they win.
    recent = _recent_headlines(sb)
    if recent and fresh:
        marked = [{"headline": h, "_stored": True} for h in recent] + fresh
        fresh = [i for i in deduplicate_news(marked) if not i.get("_stored")]
    if not fresh:
        return 0

    if not _vetting_enabled():
        logger.info("Intraday news: Jev vetting disabled, storing %d items as UNVETTED", len(fresh))
        return _upsert(sb, [{**c, "jev_choice": "UNVETTED", "jev_confidence": 0.0} for c in fresh])

    sem = asyncio.Semaphore(EVAL_CONCURRENCY)

    async def _vet(c: dict[str, Any]) -> dict[str, Any] | None:
        async with sem:
            res = await evaluate({**c, "context": c["summary"][:200]})
        if not res.get("is_market_moving"):
            return None
        return {**c, "jev_choice": res["choice"], "jev_confidence": res["confidence"]}

    results = await asyncio.gather(*[_vet(c) for c in fresh], return_exceptions=True)
    to_insert = [r for r in results if isinstance(r, dict)]
    # One line per cycle: grep "Jev calls" to total OpenRouter usage over several days.
    logger.info("Intraday news Jev calls: %d, market-moving kept: %d", len(fresh), len(to_insert))
    return _upsert(sb, to_insert)


def _vetting_enabled() -> bool:
    """Kill switch: set INTRADAY_NEWS_JEV_VETTING=false to stop all Jev calls from news ingest."""
    return os.getenv("INTRADAY_NEWS_JEV_VETTING", "true").lower() == "true"


def _upsert(sb: Any, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    try:
        sb.table("intraday_market_news").upsert(rows, on_conflict="source_id_hash").execute()
        return len(rows)
    except Exception:
        logger.exception("Failed to upsert intraday news to database")
        return 0
