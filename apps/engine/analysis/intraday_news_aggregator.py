"""Multi-source real-time news aggregator and Jaccard deduplication engine.

Aggregates breaking market news from Alpaca Benzinga wire, Polygon reference news,
and FMP stable stock news, filtering out syndicated duplicate stories using
Jaccard word-overlap tokenization.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
from datetime import UTC, datetime
from typing import Any

import httpx

from core.config import (
    ALPACA_API_KEY,
    ALPACA_SECRET_KEY,
    logger,
)


def generate_source_id_hash(headline: str, source: str, event_timestamp: str) -> str:
    """Generate deterministic SHA-256 hash for deduplicating incoming events."""
    raw = f"{headline.strip().lower()}|{source.strip().lower()}|{str(event_timestamp)[:19]}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


_NOISE_HEADLINE_RE = re.compile(
    r"class action"
    r"|lead plaintiff"
    r"|securities (?:fraud|litigation)"
    r"|investors? (?:who|that) (?:lost|suffered)"
    r"|on behalf of (?:\w+ ){0,3}(?:investors|shareholders)"
    r"|reminds? .{0,80}investors"
    r"|market size,? share"
    r"|market (?:report|analysis)\b.*\b20\d\d"
    r"|global (?:industry )?forecast",
    re.IGNORECASE,
)


def is_noise_headline(headline: str) -> bool:
    """Return True for law-firm solicitations and market-research press releases."""
    return bool(_NOISE_HEADLINE_RE.search(headline or ""))


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


def deduplicate_news(items: list[dict[str, Any]], similarity_threshold: float = 0.5) -> list[dict[str, Any]]:
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
    alpaca_news_client: Any = None,
    limit: int = 10,
    symbols: str = "SPY",
    api_key: str | None = None,
    secret_key: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch recent headlines from the Alpaca Benzinga wire."""
    client = alpaca_news_client
    if client is None or not hasattr(client, "get_news"):
        k = api_key or ALPACA_API_KEY
        s = secret_key or ALPACA_SECRET_KEY
        if k and s:
            try:
                from alpaca.data.historical.news import NewsClient

                client = NewsClient(api_key=k, secret_key=s)
            except Exception:
                client = None
    if not client or not hasattr(client, "get_news"):
        return []

    try:
        from alpaca.data.requests import NewsRequest

        req = NewsRequest(limit=limit, symbols=symbols)
        loop = asyncio.get_running_loop()
        news_res = await loop.run_in_executor(None, client.get_news, req)

        raw_news = news_res.data.get("news", []) if hasattr(news_res, "data") else getattr(news_res, "news", [])
        articles: list[dict[str, Any]] = []
        for item in raw_news:
            headline = getattr(item, "headline", "")
            if not headline:
                continue
            created_at = getattr(item, "created_at", None)
            created_str = (
                created_at.isoformat()
                if hasattr(created_at, "isoformat")
                else (str(created_at) if created_at else datetime.now(UTC).isoformat())
            )
            summary = (getattr(item, "summary", "") or "")[:250]
            url = getattr(item, "url", None)
            symbols_list = getattr(item, "symbols", []) or []
            articles.append(
                {
                    "source": "Alpaca Benzinga",
                    "headline": headline,
                    "published_at": str(created_str),
                    "summary": summary,
                    "url": url,
                    "tickers": symbols_list,
                    "source_id_hash": generate_source_id_hash(headline, "Alpaca Benzinga", str(created_str)),
                }
            )
        return articles
    except Exception:
        logger.exception("Failed to fetch news from Alpaca Benzinga")
        return []


async def fetch_polygon_news(http_client: httpx.AsyncClient, api_key: str, limit: int = 10) -> list[dict[str, Any]]:
    """Fetch reference market news from Polygon."""
    if not api_key:
        return []

    url = "https://api.polygon.io/v2/reference/news"
    params = {"apiKey": api_key, "limit": limit, "order": "desc"}
    try:
        resp = await http_client.get(url, params=params)
        if resp.status_code != 200:
            logger.warning(f"Polygon news returned HTTP {resp.status_code}: {resp.text[:120]}")
            return []

        articles: list[dict[str, Any]] = []
        for r in resp.json().get("results", []):
            title = r.get("title", "").strip()
            if not title:
                continue
            pub_time = r.get("published_utc", datetime.now(UTC).isoformat())
            url = r.get("article_url")
            tickers = r.get("tickers") or []
            articles.append(
                {
                    "source": "Polygon Wire",
                    "headline": title,
                    "published_at": pub_time,
                    "summary": (r.get("description", "") or "")[:250],
                    "url": url,
                    "tickers": tickers,
                    "source_id_hash": generate_source_id_hash(title, "Polygon Wire", pub_time),
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
            raw_date = r.get("publishedDate")
            pub_date = raw_date
            if raw_date and " " in raw_date and not raw_date.endswith("Z"):
                pub_date = raw_date.replace(" ", "T") + "Z"
            elif not raw_date:
                pub_date = datetime.now(UTC).isoformat()

            url = r.get("url")
            summary_text = (r.get("text", "") or "")[:250]
            queried = [s.strip().upper() for s in symbols.split(",") if s.strip()]
            raw_sym = str(r.get("symbol") or "").upper().strip()
            if raw_sym:
                tickers = [raw_sym]
            elif len(queried) == 1:
                tickers = queried
            else:
                haystack = f"{title} {summary_text}".upper()
                tickers = [s for s in queried if re.search(rf"\b{re.escape(s)}\b", haystack)]
            articles.append(
                {
                    "source": f"FMP ({publisher})",
                    "headline": title,
                    "published_at": pub_date,
                    "summary": summary_text,
                    "url": url,
                    "tickers": tickers,
                    "source_id_hash": generate_source_id_hash(title, f"FMP ({publisher})", pub_date),
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
    alpaca_api_key: str = "",
    alpaca_secret_key: str = "",
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
            fetch_alpaca_news(
                alpaca_news_client=alpaca_client,
                limit=limit_per_source,
                symbols=symbols,
                api_key=alpaca_api_key,
                secret_key=alpaca_secret_key,
            ),
            fetch_polygon_news(http_client, api_key=massive_api_key, limit=limit_per_source),
            fetch_fmp_news(http_client, api_key=fmp_api_key, symbols=symbols, limit=limit_per_source),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        combined: list[dict[str, Any]] = []
        for res in results:
            if isinstance(res, list):
                combined.extend(r for r in res if not is_noise_headline(r.get("headline", "")))

        deduped = deduplicate_news(combined, similarity_threshold=similarity_threshold)
        for item in deduped:
            if "source_id_hash" not in item:
                item["source_id_hash"] = generate_source_id_hash(
                    item.get("headline", ""),
                    item.get("source", ""),
                    item.get("published_at", ""),
                )
        return deduped
    finally:
        if should_close_http:
            await http_client.aclose()
