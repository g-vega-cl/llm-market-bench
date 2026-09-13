"""Vertical slice module for fetching and formatting real-time stock news by ticker."""

import re
from typing import Any

import httpx

from core.config import FMP_API_KEY, logger

FMP_STABLE_NEWS_URL = "https://financialmodelingprep.com/stable/news/stock"
FMP_TIMEOUT = httpx.Timeout(10.0)


def sanitize_ticker(ticker: str) -> str:
    """Sanitize and validate a raw ticker string."""
    if not ticker:
        return ""
    # Strip leading dollar signs, surrounding whitespace, and punctuation
    cleaned = re.sub(r"^[\$]+", "", ticker.strip()).strip()
    cleaned = cleaned.strip(",.:;'\"()[]{}")
    return cleaned.upper()


async def fetch_ticker_news(
    ticker: str,
    limit: int = 5,
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch recent stock news articles from FMP stable API.

    Args:
        ticker: Stock symbol (e.g. 'AAPL', 'NVDA', 'SPY').
        limit: Number of articles to retrieve (1 to 20).
        api_key: Optional FMP API key override. Defaults to FMP_API_KEY.

    Returns:
        List of news article dicts containing title, publisher, date, text, and url.
    """
    clean_ticker = sanitize_ticker(ticker)
    if not clean_ticker:
        return []

    key = api_key or FMP_API_KEY
    if not key:
        logger.warning("FMP_API_KEY not found in environment. Cannot fetch ticker news.")
        return []

    clamped_limit = max(1, min(limit, 20))

    try:
        async with httpx.AsyncClient(timeout=FMP_TIMEOUT) as client:
            resp = await client.get(
                FMP_STABLE_NEWS_URL,
                params={"symbols": clean_ticker, "limit": clamped_limit, "apikey": key},
            )

            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    return data[:clamped_limit]
                logger.warning(
                    "Unexpected response structure from FMP news endpoint for %s: %s",
                    clean_ticker,
                    type(data),
                )
                return []

            if resp.status_code in (401, 403):
                logger.error(
                    "FMP authentication or tier error (%d) fetching news for %s: %s",
                    resp.status_code,
                    clean_ticker,
                    resp.text[:200],
                )
            elif resp.status_code == 429:
                logger.warning("FMP rate limit reached (429) fetching news for %s", clean_ticker)
            else:
                logger.warning(
                    "FMP news endpoint returned HTTP %d for %s: %s",
                    resp.status_code,
                    clean_ticker,
                    resp.text[:200],
                )
            return []

    except httpx.TimeoutException:
        logger.warning("Timeout fetching news from FMP for ticker %s", clean_ticker)
        return []
    except Exception as e:
        logger.exception("Unexpected error fetching ticker news for %s: %s", clean_ticker, e)
        return []


async def execute_get_ticker_news_tool(ticker: str, limit: int = 5) -> str:
    """Executes the get_ticker_news LLM tool to retrieve structured company news.

    Args:
        ticker: Stock symbol (e.g. 'AAPL', 'NVDA', 'SPY').
        limit: Max news items to format (default 5).

    Returns:
        Formatted markdown summary of recent news for the ticker.
    """
    clean_ticker = sanitize_ticker(ticker)
    if not clean_ticker:
        return "Error: Invalid or empty ticker symbol provided."

    articles = await fetch_ticker_news(ticker=clean_ticker, limit=limit)
    if not articles:
        return f"No recent news found for ticker '{clean_ticker}'."

    lines = [f"=== REAL-TIME NEWS: {clean_ticker} ({len(articles)} articles) ==="]
    for i, item in enumerate(articles, 1):
        title = item.get("title", "Untitled").strip()
        pub_date = item.get("publishedDate", "Unknown Date")
        publisher = item.get("publisher", item.get("site", "Unknown Source"))
        summary = item.get("text", "").strip()
        url = item.get("url", "").strip()

        lines.append(f"{i}. {title}")
        lines.append(f"   Source: {publisher} | Date: {pub_date}")
        if summary:
            lines.append(f"   Summary: {summary}")
        if url:
            lines.append(f"   URL: {url}")
        lines.append("")

    return "\n".join(lines).strip()
