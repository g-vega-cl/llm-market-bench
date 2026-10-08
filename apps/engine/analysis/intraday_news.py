"""Intraday market news aggregation, TypeSafe Jev relevance sieve, and agent tool execution."""

import asyncio
import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from core.config import (
    ALPACA_API_KEY,
    ALPACA_SECRET_KEY,
    JEV_MODEL,
    MASSIVE_API_KEY,
    OPENROUTER_API_KEY,
    logger,
)
from core.db import get_supabase_client
from core.economic_releases import fetch_economic_calendar_events

JEV_DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"
DEFAULT_SYNC_COOLDOWN_SECONDS = 900  # 15 minutes cache freshness guard

JEV_NEWS_QUESTION_KEY = "market_relevance"
JEV_NEWS_QUESTION_TYPE = "choice"
JEV_NEWS_INSTRUCTIONS = (
    "Evaluate whether this financial headline and event context constitutes a genuine "
    "market-moving catalyst for broad US equities or major sectors, vs routine corporate PR/noise."
)
JEV_NEWS_DEFAULT_CRITERIA = {
    "MARKET_MOVING": (
        "Major macroeconomic surprise (e.g. ISM PMI, CPI, Jobs print vs consensus), "
        "Federal Reserve governor remarks on rate policy, significant geopolitical developments, "
        "large-cap (> $20B) earnings/guidance shocks, major M&A, regulatory or legal interventions, "
        "or sudden systemic liquidity shocks that alter index or sector trajectory."
    ),
    "NOISE": (
        "Routine promotional corporate press releases, law firm class action solicitation, "
        "sub-$2B penny stock moves, generic technical analysis commentary, standard scheduled dividend announcements, "
        "recycled opinion pieces, or news already fully priced with no directional impact."
    ),
}


def generate_source_id_hash(headline: str, source: str, event_timestamp: str) -> str:
    """Generate deterministic SHA-256 hash for deduplicating incoming events."""
    raw = f"{headline.strip().lower()}|{source.strip().lower()}|{event_timestamp[:19]}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def evaluate_news_with_jev(
    event: dict[str, Any],
    api_key: str | None = None,
    model_name: str = JEV_MODEL,
) -> dict[str, Any]:
    """Evaluates an event headline and context using TypeSafe Jev on the OpenRouter Decisions API."""
    key = api_key or OPENROUTER_API_KEY
    if not key:
        logger.warning("OPENROUTER_API_KEY is not set. Defaulting Jev news evaluation to NOISE.")
        return {"choice": "NOISE", "confidence": 0.0, "probabilities": {}, "is_market_moving": False}

    headline = event.get("headline", "")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {
        "model": model_name,
        "state": {
            "headline": headline,
            "source": event.get("source", "Unknown"),
            "tickers": event.get("tickers", []),
            "context": event.get("context", ""),
        },
        "questions": {
            JEV_NEWS_QUESTION_KEY: {
                "type": JEV_NEWS_QUESTION_TYPE,
                "instructions": JEV_NEWS_INSTRUCTIONS,
                "criteria": JEV_NEWS_DEFAULT_CRITERIA,
            }
        },
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(JEV_DECISIONS_URL, headers=headers, json=payload)
            if resp.status_code != 200:
                logger.warning(
                    "OpenRouter Decisions API error %s for '%s': %s", resp.status_code, headline[:60], resp.text[:200]
                )
                return {"choice": "NOISE", "confidence": 0.0, "probabilities": {}, "is_market_moving": False}
            data = resp.json()
    except Exception as e:
        logger.exception("Exception querying Jev Decisions API for '%s': %s", headline[:60], e)
        return {"choice": "NOISE", "confidence": 0.0, "probabilities": {}, "is_market_moving": False}

    ans = data.get("answers", {}).get(JEV_NEWS_QUESTION_KEY, {})
    choice = str(ans.get("choice", "NOISE")).upper()
    probabilities = ans.get("probabilities", {})
    prob = float(probabilities.get(choice, ans.get("confidence", 0.5)))
    confidence = round(prob * 100.0, 1) if prob <= 1.0 else round(prob, 1)

    return {
        "choice": choice,
        "confidence": confidence,
        "probabilities": probabilities,
        "is_market_moving": (choice == "MARKET_MOVING") and (confidence >= 70.0),
    }


async def _fetch_polygon_news_events(limit: int = 20) -> list[dict[str, Any]]:
    """Fetch recent market news from Polygon reference news endpoint."""
    if not MASSIVE_API_KEY:
        return []
    url = "https://api.polygon.io/v2/reference/news"
    params = {"limit": limit, "order": "desc", "apiKey": MASSIVE_API_KEY}
    events = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                for a in resp.json().get("results", []):
                    title = a.get("title", "").strip()
                    if not title:
                        continue
                    pub_utc = a.get("published_utc") or datetime.now(UTC).isoformat()
                    insights = a.get("insights") or []
                    ins_text = (
                        f"Sentiment: {insights[0].get('sentiment')}" if insights else a.get("description", "")[:200]
                    )
                    events.append(
                        {
                            "headline": title,
                            "summary": a.get("description", "")[:400],
                            "source": "Polygon Wire",
                            "url": a.get("article_url"),
                            "tickers": a.get("tickers") or [],
                            "event_timestamp": pub_utc,
                            "source_id_hash": generate_source_id_hash(title, "Polygon Wire", pub_utc),
                            "context": ins_text,
                        }
                    )
    except Exception as e:
        logger.warning("Failed to fetch news from Polygon: %s", e)
    return events


async def _fetch_alpaca_news_events(limit: int = 20) -> list[dict[str, Any]]:
    """Fetch real-time news from Alpaca Benzinga wire if credentials are configured."""
    if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
        return []
    events = []
    try:
        from alpaca.data.historical.news import NewsClient
        from alpaca.data.requests import NewsRequest

        client = NewsClient(api_key=ALPACA_API_KEY, secret_key=ALPACA_SECRET_KEY)
        start_time = datetime.now(UTC) - timedelta(hours=24)
        news_set = client.get_news(NewsRequest(start=start_time, limit=limit, include_content=False))
        articles = news_set.news if hasattr(news_set, "news") else news_set
        for a in articles:
            headline = getattr(a, "headline", "") or ""
            if not headline:
                continue
            created_at = getattr(a, "created_at", None)
            created_str = created_at.isoformat() if created_at else datetime.now(UTC).isoformat()
            summary = getattr(a, "summary", "") or ""
            events.append(
                {
                    "headline": headline,
                    "summary": summary[:400],
                    "source": "Benzinga Wire",
                    "url": getattr(a, "url", None),
                    "tickers": getattr(a, "symbols", []) or [],
                    "event_timestamp": created_str,
                    "source_id_hash": generate_source_id_hash(headline, "Benzinga Wire", created_str),
                    "context": summary[:200],
                }
            )
    except Exception as e:
        logger.warning("Failed to fetch news from Alpaca Benzinga: %s", e)
    return events


async def fetch_raw_intraday_events() -> list[dict[str, Any]]:
    """Aggregate raw events from today's economic releases, Alpaca Benzinga, and Polygon."""
    events: list[dict[str, Any]] = []
    target_date = datetime.now(ZoneInfo("America/New_York")).date().isoformat()

    try:
        for e in await fetch_economic_calendar_events(from_date=target_date, to_date=target_date):
            if e.impact in ("High", "Medium") or e.status == "RELEASED":
                act_str = f"Actual {e.actual:,.2f}" if e.actual is not None else "Pending"
                est_str = f"vs Est {e.estimate:,.2f}" if e.estimate is not None else ""
                prev_str = f"(Prev {e.previous:,.2f})" if e.previous is not None else ""
                surprise_str = f" | Surprise {e.surprise:+,.2f}" if e.surprise is not None else ""
                headline = f"[{e.country}] {e.event}: {act_str} {est_str} {prev_str}{surprise_str}".strip()
                iso_time = (
                    datetime.now(UTC).isoformat()
                    if not e.date
                    else datetime.fromisoformat(e.date.strip()[:19].replace(" ", "T")).replace(tzinfo=UTC).isoformat()
                )
                source_name = "FMP Macro Calendar"
                events.append(
                    {
                        "headline": headline,
                        "summary": f"Impact: {e.impact} | Status: {e.status} | Time: {e.time_et}",
                        "source": source_name,
                        "url": None,
                        "tickers": ["SPY", "QQQ", "TLT"],
                        "event_timestamp": iso_time,
                        "source_id_hash": generate_source_id_hash(headline, source_name, iso_time),
                        "context": f"Macro release: {e.event}, Status: {e.status}, Surprise: {e.surprise}",
                    }
                )
    except Exception as e:
        logger.warning("Error aggregating economic calendar events: %s", e)

    events.extend(await _fetch_alpaca_news_events(limit=15))
    events.extend(await _fetch_polygon_news_events(limit=15))

    unique_events = {}
    for ev in events:
        h = ev.get("source_id_hash") or generate_source_id_hash(
            ev.get("headline", ""), ev.get("source", ""), ev.get("event_timestamp", "")
        )
        ev["source_id_hash"] = h
        unique_events.setdefault(h, ev)
    return list(unique_events.values())


async def get_recent_vetted_news(limit: int = 15, sb_client=None) -> list[dict[str, Any]]:
    """Retrieve recently vetted MARKET_MOVING news from Supabase."""
    sb = sb_client or get_supabase_client()
    since_iso = (datetime.now(UTC) - timedelta(hours=24)).isoformat()
    try:
        resp = (
            sb.table("intraday_market_news")
            .select("*")
            .gte("event_timestamp", since_iso)
            .order("event_timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        return resp.data or []
    except Exception as e:
        logger.warning("Could not query intraday_market_news from Supabase: %s", e)
        return []


async def sync_intraday_market_news(force: bool = False, sb_client=None) -> list[dict[str, Any]]:
    """Ingests raw intraday events, screens them with TypeSafe Jev, and persists MARKET_MOVING items."""
    sb = sb_client or get_supabase_client()
    recent = await get_recent_vetted_news(limit=20, sb_client=sb)
    if not force and recent:
        newest = recent[0].get("created_at")
        if newest:
            try:
                if (
                    datetime.now(UTC) - datetime.fromisoformat(newest.replace("Z", "+00:00"))
                ).total_seconds() < DEFAULT_SYNC_COOLDOWN_SECONDS:
                    return recent
            except Exception:
                pass

    candidates = await fetch_raw_intraday_events()
    if not candidates:
        return recent

    hashes = [c["source_id_hash"] for c in candidates]
    existing_hashes = set()
    try:
        check_resp = sb.table("intraday_market_news").select("source_id_hash").in_("source_id_hash", hashes).execute()
        existing_hashes = {r["source_id_hash"] for r in (check_resp.data or [])}
    except Exception as e:
        logger.warning("Error checking existing news hashes in Supabase: %s", e)

    new_candidates = [c for c in candidates if c["source_id_hash"] not in existing_hashes]
    if not new_candidates:
        return recent

    sem = asyncio.Semaphore(3)

    async def _evaluate(candidate: dict[str, Any]) -> dict[str, Any] | None:
        async with sem:
            res = await evaluate_news_with_jev(candidate)
            if res.get("is_market_moving"):
                return {
                    "headline": candidate["headline"],
                    "summary": candidate.get("summary") or candidate.get("context"),
                    "source": candidate["source"],
                    "url": candidate.get("url"),
                    "tickers": candidate.get("tickers", []),
                    "event_timestamp": candidate["event_timestamp"],
                    "jev_choice": res["choice"],
                    "jev_confidence": res["confidence"],
                    "source_id_hash": candidate["source_id_hash"],
                }
            return None

    results = await asyncio.gather(*[_evaluate(c) for c in new_candidates[:10]], return_exceptions=True)
    to_insert = [r for r in results if isinstance(r, dict) and r is not None]
    if to_insert:
        try:
            sb.table("intraday_market_news").upsert(to_insert, on_conflict="source_id_hash").execute()
            logger.info("Successfully upserted %d Jev-vetted market-moving news items.", len(to_insert))
        except Exception as e:
            logger.exception("Failed to upsert intraday_market_news to Supabase: %s", e)

    stored = await get_recent_vetted_news(limit=20, sb_client=sb)
    return stored if stored else to_insert


async def execute_get_market_moving_news_tool(limit: int = 8, force_refresh: bool = False) -> str:
    """Executes the get_market_moving_news LLM tool to retrieve high-impact catalysts."""
    clamped_limit = max(1, min(limit, 20))
    vetted_items = await sync_intraday_market_news(force=force_refresh)

    if not vetted_items:
        return "No high-impact market-moving events or macro surprises detected today so far."

    lines = [f"=== TODAY'S INTRADAY MARKET-MOVING EVENTS (JEV VETTED) ({len(vetted_items[:clamped_limit])} items) ==="]
    for i, item in enumerate(vetted_items[:clamped_limit], 1):
        headline = item.get("headline", "Untitled").strip()
        source = item.get("source", "Unknown")
        raw_ts = item.get("event_timestamp", "")
        time_str = raw_ts
        if raw_ts:
            try:
                time_str = (
                    datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
                    .astimezone(ZoneInfo("America/New_York"))
                    .strftime("%H:%M ET")
                )
            except Exception:
                time_str = raw_ts[:16]

        conf = item.get("jev_confidence", 0.0)
        choice = item.get("jev_choice", "MARKET_MOVING")
        tickers = item.get("tickers") or []
        tickers_str = f" | Tickers: {', '.join(tickers)}" if tickers else ""
        summary = item.get("summary") or ""

        lines.append(f"{i}. [{time_str}] {headline}")
        lines.append(f"   Impact: {choice} ({conf:.0f}% Conf) | Source: {source}{tickers_str}")
        if summary:
            lines.append(f"   Context: {summary.strip()}")
        lines.append("")

    return "\n".join(lines).strip()
