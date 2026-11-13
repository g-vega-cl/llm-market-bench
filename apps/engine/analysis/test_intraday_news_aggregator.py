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
    assert all("source_id_hash" in item for item in aggregated)


@pytest.mark.asyncio
async def test_fetch_alpaca_news_includes_url_and_tickers():
    mock_client = MagicMock()
    mock_article = MagicMock()
    mock_article.headline = "NVIDIA Hits New Record Ahead of Blackwell Shipments"
    mock_article.created_at = "2026-11-01T18:00:00Z"
    mock_article.summary = "Blackwell shipments ramp up."
    mock_article.url = "https://benzinga.com/news/nvda"
    mock_article.symbols = ["NVDA", "SPY"]
    mock_client.get_news.return_value = MagicMock(data={"news": [mock_article]})

    results = await fetch_alpaca_news(mock_client, limit=5, symbols="NVDA")
    assert len(results) == 1
    assert results[0]["url"] == "https://benzinga.com/news/nvda"
    assert results[0]["tickers"] == ["NVDA", "SPY"]


@pytest.mark.asyncio
async def test_fetch_polygon_news_includes_url_and_tickers():
    mock_http = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": [
            {
                "title": "Amazon AWS Inks Defense Department Cloud Contract",
                "published_utc": "2026-11-01T19:00:00Z",
                "description": "Multi-billion dollar contract signed.",
                "article_url": "https://polygon.io/news/amzn",
                "tickers": ["AMZN", "SPY"],
            }
        ]
    }
    mock_http.get.return_value = mock_resp

    results = await fetch_polygon_news(mock_http, api_key="test_key", limit=5)
    assert len(results) == 1
    assert results[0]["url"] == "https://polygon.io/news/amzn"
    assert results[0]["tickers"] == ["AMZN", "SPY"]


@pytest.mark.asyncio
async def test_fetch_fmp_news_includes_url_and_tickers():
    mock_http = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {
            "title": "Tesla Robotaxi Fleet Begins Texas Deployment",
            "publishedDate": "2026-11-01 19:30:00",
            "publisher": "Seeking Alpha",
            "text": "Regulatory clearance achieved in Austin.",
            "url": "https://seekingalpha.com/article/tsla",
        }
    ]
    mock_http.get.return_value = mock_resp

    results = await fetch_fmp_news(mock_http, api_key="test_key", symbols="TSLA", limit=5)
    assert len(results) == 1
    assert results[0]["url"] == "https://seekingalpha.com/article/tsla"
    assert results[0]["tickers"] == ["TSLA"]
    assert "T" in results[0]["published_at"]  # Normalized to ISO


@pytest.mark.asyncio
async def test_fetch_fmp_news_multi_symbol_does_not_broadcast_all_tickers():
    mock_http = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {
            "symbol": "NVDA",
            "title": "Nvidia Launches Next-Gen Vera Rubin AI Rack Architecture",
            "publishedDate": "2026-11-13 15:00:00",
            "publisher": "Reuters",
            "text": "Data center demand accelerates for Nvidia.",
            "url": "https://example.com/nvda",
        }
    ]
    mock_http.get.return_value = mock_resp

    results = await fetch_fmp_news(mock_http, api_key="test_key", symbols="SPY,QQQ,NVDA,TSLA", limit=5)
    assert len(results) == 1
    assert results[0]["tickers"] == ["NVDA"]


@pytest.mark.parametrize(
    "headline",
    [
        "Kaplan Fox Reminds AppLovin Corporation (NASDAQ: APP) Investors of an Approaching Securities Class Action Deadline",
        "Bronstein, Gewirtz & Grossman LLC Urges AppLovin Corporation Investors to Act: Class Action Filed",
        "Data Center Fire Suppression Systems Market Size, Share & Trends Analysis - Global Industry Forecast, 2026-2033",
        "Compute Express Link (CXL) Memory Market Size, Share, Trends and Global Forecast 2026-2036",
    ],
)
def test_is_noise_headline_flags_solicitations_and_market_reports(headline):
    from analysis.intraday_news_aggregator import is_noise_headline

    assert is_noise_headline(headline) is True


@pytest.mark.parametrize(
    "headline",
    [
        "Fed's Daly Says Inflation Is More Stubborn Than Would Like",
        "U.S. Baker Hughes Oil Rig Count +1 To 463",
        "Not Oklo. Not X-Energy. This SMR Stock Just Signed a Contract",
    ],
)
def test_is_noise_headline_keeps_real_news(headline):
    from analysis.intraday_news_aggregator import is_noise_headline

    assert is_noise_headline(headline) is False


@pytest.mark.asyncio
async def test_aggregate_drops_noise_headlines():
    from analysis.intraday_news_aggregator import aggregate_intraday_news

    alpaca = MagicMock()
    alpaca.get_news.return_value = MagicMock(data={"news": []})
    http = AsyncMock()
    resp = MagicMock(status_code=200)
    resp.json.return_value = {
        "results": [
            {"title": "Securities Class Action Filed Against ACME Investors", "published_utc": "2026-11-06T18:00:00Z"},
            {"title": "Treasury Secretary Bessent Meets China Vice Premier", "published_utc": "2026-11-06T18:01:00Z"},
        ]
    }
    http.get.return_value = resp

    out = await aggregate_intraday_news(alpaca_client=alpaca, http_client=http, massive_api_key="k")

    assert [i["headline"] for i in out] == ["Treasury Secretary Bessent Meets China Vice Premier"]
