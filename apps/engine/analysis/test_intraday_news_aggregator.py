"""Hermetic tests for multi-source intraday news aggregator and deduplication engine."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from analysis.intraday_news_aggregator import (
    aggregate_intraday_news,
    deduplicate_news,
    fetch_alpaca_news,
    fetch_fmp_news,
    fetch_polygon_news,
    normalize_headline,
)


def test_normalize_headline():
    headline = "Senior Iranian Security Official: U.S. Sent Letters on Ceasefire!"
    tokens = normalize_headline(headline)
    assert "iranian" in tokens
    assert "security" in tokens
    assert "official" in tokens
    assert "letters" in tokens
    # Short words or stopwords filtered
    assert "the" not in tokens
    assert "on" not in tokens


def test_deduplicate_news_removes_syndicated_stories():
    articles = [
        {
            "source": "Alpaca Benzinga",
            "headline": "Alphabet Stock Drops 12% As AI Threatens Search Monopoly",
            "published_at": "2026-10-29T14:00:00Z",
            "summary": "Google parent sees deep losses.",
        },
        {
            "source": "Polygon Wire",
            "headline": "Alphabet Stock Falls 12% As AI Threatens Search Monopoly Profitability",
            "published_at": "2026-10-29T14:05:00Z",
            "summary": "Shares tumbled on AI news.",
        },
        {
            "source": "FMP Stable",
            "headline": "Oil Prices Surge Above 85 Dollars On Middle East Tensions",
            "published_at": "2026-10-29T14:10:00Z",
            "summary": "Brent crude climbed strongly.",
        },
    ]

    deduped = deduplicate_news(articles, similarity_threshold=0.5)
    assert len(deduped) == 2
    # The first Alphabet story is retained, the syndicated duplicate is dropped
    assert deduped[0]["source"] == "Alpaca Benzinga"
    assert deduped[1]["source"] == "FMP Stable"


@pytest.mark.asyncio
async def test_fetch_alpaca_news_hermetic():
    mock_alpaca_client = MagicMock()
    mock_article = MagicMock()
    mock_article.headline = "Tesla Unveils Cheaper EV Sedan in Europe"
    mock_article.created_at = "2026-10-29T15:00:00Z"
    mock_article.summary = "New model starting under 30k."
    mock_alpaca_client.get_news.return_value = MagicMock(data={"news": [mock_article]})

    results = await fetch_alpaca_news(mock_alpaca_client, limit=5, symbols="TSLA")
    assert len(results) == 1
    assert results[0]["source"] == "Alpaca Benzinga"
    assert "Tesla" in results[0]["headline"]


@pytest.mark.asyncio
async def test_fetch_polygon_news_hermetic():
    mock_http = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": [
            {
                "title": "Fed Signals High Rates for Longer Ahead of Jobs Print",
                "published_utc": "2026-10-29T15:30:00Z",
                "description": "Officials caution on inflation.",
            }
        ]
    }
    mock_http.get.return_value = mock_resp

    results = await fetch_polygon_news(mock_http, api_key="mock_key", limit=5)
    assert len(results) == 1
    assert results[0]["source"] == "Polygon Wire"
    assert "Fed Signals" in results[0]["headline"]


@pytest.mark.asyncio
async def test_fetch_fmp_news_hermetic():
    mock_http = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {
            "title": "Apple Prepares New Silicon Upgrades For Mac Lineup",
            "publishedDate": "2026-10-29T15:45:00Z",
            "publisher": "Reuters",
            "text": "M5 chip rollout scheduled for fall.",
        }
    ]
    mock_http.get.return_value = mock_resp

    results = await fetch_fmp_news(mock_http, api_key="mock_key", symbols="SPY", limit=5)
    assert len(results) == 1
    assert results[0]["source"] == "FMP (Reuters)"
    assert "Apple Prepares" in results[0]["headline"]


@pytest.mark.asyncio
async def test_aggregate_intraday_news_combines_and_deduplicates():
    mock_alpaca_client = MagicMock()
    mock_article = MagicMock()
    mock_article.headline = "Microsoft Announces Massive Cloud Expansion in Tokyo"
    mock_article.created_at = "2026-10-29T16:00:00Z"
    mock_article.summary = "Data centers opening across Japan."
    mock_alpaca_client.get_news.return_value = MagicMock(data={"news": [mock_article]})

    mock_http = AsyncMock()

    async def mock_get(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        if "polygon.io" in str(url):
            # Same Microsoft story from Polygon
            resp.json.return_value = {
                "results": [
                    {
                        "title": "Microsoft Announces Massive Cloud Expansion in Tokyo Regions",
                        "published_utc": "2026-10-29T16:02:00Z",
                        "description": "Cloud capacity boosted in Japan.",
                    }
                ]
            }
        else:
            # Different story from FMP
            resp.json.return_value = [
                {
                    "title": "US Treasury Yields Tumble After Weak Housing Starts",
                    "publishedDate": "2026-10-29T16:05:00Z",
                    "publisher": "Bloomberg",
                    "text": "10-year yield fell 6 basis points.",
                }
            ]
        return resp

    mock_http.get.side_effect = mock_get

    aggregated = await aggregate_intraday_news(
        alpaca_client=mock_alpaca_client,
        http_client=mock_http,
        massive_api_key="mock_key",
        fmp_api_key="mock_key",
        symbols="SPY",
    )

    # 3 raw articles total, 2 are duplicate Microsoft stories -> 2 unique stories returned
    assert len(aggregated) == 2
    assert any("Microsoft" in item["headline"] for item in aggregated)
    assert any("Treasury Yields" in item["headline"] for item in aggregated)
