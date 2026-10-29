"""Multi-source real-time news aggregator and Jaccard deduplication engine.

Aggregates breaking market news from Alpaca Benzinga wire, Polygon reference news,
and FMP stable stock news, filtering out syndicated duplicate stories using
Jaccard word-overlap tokenization.
"""

from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime
from typing import Any

import httpx

from core.config import logger


def normalize_headline(headline: str) -> set[str]:
    """Tokenize and normalize headline words for Jaccard overlap."""
    clean = re.sub(r"[^\w\s]", "", headline.lower())
    words = clean.split()
    stops = {
        "the",
        "a",
        "an",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "and",
        "or",
        "is",
        "are",
        "as",
        "by",
        "with",
        "from",
    }
    return {w for w in words if w not in stops and len(w) > 2}


def deduplicate_news(
    items: list[dict[str, Any]], similarity_threshold: float = 0.5
) -> list[dict[str, Any]]:
    """Deduplicate news articles across providers using Jaccard word overlap."""
    unique: list[dict[str, Any]] = []
    seen_token_sets: list[set[str]] = []

    for item in items:
        headline = item.get("headline", "")
        tokens = normalize_headline(headline)
        if not tokens:
            unique.append(item)
            continue

        is_duplicate = False
        for seen in seen_token_sets:
            intersection = tokens.intersection(seen)
            union = tokens.union(seen)
            similarity = len(intersection) / len(union) if union else 0.0
            if similarity >= similarity_threshold:
                is_duplicate = True
                break

        if not is_duplicate:
            unique.append(item)
            seen_token_sets.append(tokens)

    return unique


async def fetch_alpaca_news(
    alpaca_news_client: Any, limit: int = 10, symbols: str = "SPY"
) -> list[dict[str, Any]]:
    """Fetch recent headlines from the Alpaca Benzinga wire."""
    if not alpaca_news_client:
        return []

    try:
        from alpaca.data.requests import NewsRequest

        req = NewsRequest(limit=limit, symbols=symbols)
        loop = asyncio.get_running_loop()
        news_res = await loop.run_in_executor(None, alpaca_news_client.get_news, req)

        raw_news = news_res.data.get("news", []) if hasattr(news_res, "data") else []
        articles: list[dict[str, Any]] = []
        for item in raw_news:
            headline = getattr(item, "headline", "")
            if not headline:
                continue
            created_at = getattr(item, "created_at", None)
            created_str = (
                created_at.isoformat()
                if hasattr(created_at, "isoformat")
                else (created_at or datetime.now(UTC).isoformat())
            )
            articles.append(
                {
                    "source": "Alpaca Benzinga",
                    "headline": headline,
                    "published_at": str(created_str),
                    "summary": (getattr(item, "summary", "") or "")[:250],
                }
            )
        return articles
    except Exception:
        logger.exception("Failed to fetch news from Alpaca Benzinga")
        return []


async def fetch_polygon_news(
    http_client: httpx.AsyncClient, api_key: str, limit: int = 10
) -> list[dict[str, Any]]:
    """Fetch reference market news from Polygon."""
    if not api_key:
        return []

    url = "https://api.polygon.io/v2/reference/news"
    params = {"apiKey": api_key, "limit": limit, "order": "desc"}
    try:
        resp = await http_client.get(url, params=params)
        if resp.status_code != 200:
            logger.warning(
                f"Polygon news returned HTTP {resp.status_code}: {resp.text[:120]}"
            )
            return []

        articles: list[dict[str, Any]] = []
        for r in resp.json().get("results", []):
            title = r.get("title", "").strip()
            if not title:
                continue
            articles.append(
                {
                    "source": "Polygon Wire",
                    "headline": title,
                    "published_at": r.get("published_utc", datetime.now(UTC).isoformat()),
                    "summary": (r.get("description", "") or "")[:250],
                }
            )
        return articles
    except Exception:
        logger.exception("Failed to fetch news from Polygon")
        return []


async def fetch_fmp_news(
    http_client: httpx.AsyncClient, api_key: str, symbols: str = "SPY", limit: int = 10
) -> list[dict[str, Any]]:
    """Fetch stock news from FMP stable endpoint."""
    if not api_key:
        return []

    url = "https://financialmodelingprep.com/stable/news/stock"
    params = {"symbols": symbols, "limit": limit, "apikey": api_key}
    try:
        resp = await http_client.get(url, params=params)
        if resp.status_code != 200:
            logger.warning(f"FMP news returned HTTP {resp.status_code}: {resp.text[:120]}")
            return []

        data = resp.json()
        if not isinstance(data, list):
            return []

        articles: list[dict[str, Any]] = []
        for r in data:
            title = r.get("title", "").strip()
            if not title:
                continue
            publisher = r.get("publisher") or "Market"
            articles.append(
                {
                    "source": f"FMP ({publisher})",
                    "headline": title,
                    "published_at": r.get("publishedDate", datetime.now(UTC).isoformat()),
                    "summary": (r.get("text", "") or "")[:250],
                }
            )
        return articles
    except Exception:
        logger.exception("Failed to fetch news from FMP stable")
        return []


async def aggregate_intraday_news(
    alpaca_client: Any = None,
    http_client: httpx.AsyncClient | None = None,
    massive_api_key: str = "",
    fmp_api_key: str = "",
    symbols: str = "SPY",
    limit_per_source: int = 10,
    similarity_threshold: float = 0.5,
) -> list[dict[str, Any]]:
    """Aggregate breaking news across Alpaca, Polygon, and FMP, returning deduplicated items."""
    should_close_http = False
    if http_client is None:
        http_client = httpx.AsyncClient(timeout=10.0)
        should_close_http = True

    try:
        tasks = [
            fetch_alpaca_news(alpaca_client, limit=limit_per_source, symbols=symbols),
            fetch_polygon_news(http_client, api_key=massive_api_key, limit=limit_per_source),
            fetch_fmp_news(
                http_client, api_key=fmp_api_key, symbols=symbols, limit=limit_per_source
            ),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        combined: list[dict[str, Any]] = []
        for res in results:
            if isinstance(res, list):
                combined.extend(res)

        return deduplicate_news(combined, similarity_threshold=similarity_threshold)
    finally:
        if should_close_http:
            await http_client.aclose()
