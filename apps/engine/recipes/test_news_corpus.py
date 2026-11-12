"""Hermetic unit tests for the Recipe Studio Unified News Corpus."""

import json
from unittest.mock import MagicMock

from recipes.news_corpus import (
    derive_article_buckets,
    import_stock_news_corpus,
    parse_and_normalize_article,
    query_corpus_point_in_time,
)


def test_derive_article_buckets_semiconductors():
    buckets, tickers = derive_article_buckets(
        title="Nvidia Unveils Next-Gen Blackwell Ultra Chips for AI Data Centers",
        full_text="Nvidia announced massive GPU server shipments...",
        company="Nvidia",
        companies=["Nvidia"],
        tickers=["NVDA"],
    )
    assert "semiconductors" in buckets
    assert "ai_cloud" in buckets
    assert "NVDA" in tickers


def test_derive_article_buckets_macro_general():
    buckets, tickers = derive_article_buckets(
        title="Oil prices drop as global crude stockpiles surge",
        full_text="Crude oil inventories rose significantly...",
        company="general_market",
        companies=[],
        tickers=[],
    )
    assert "macro_general" in buckets
    assert "energy" in buckets
    assert "SPY" in tickers
    assert "QQQ" in tickers
    assert "TLT" in tickers


def test_derive_article_buckets_fed_and_earnings():
    buckets, tickers = derive_article_buckets(
        title="Powell Signals Rate Cut Consideration as Quarterly Inflation Eases",
        full_text="Federal reserve chairman jerome powell noted quarterly eps...",
        company="general_market",
        companies=[],
        tickers=[],
    )
    assert "fed_rates" in buckets
    assert "macro_inflation" in buckets
    assert "earnings" in buckets


def test_parse_and_normalize_article_valid():
    raw = {
        "article_id": "art_1234567890abcdef",
        "title": "AMD Reports Record Data Center Revenue Beat",
        "url": "https://example.com/amd-record-quarter",
        "date_published": "2026-11-10T14:30:00Z",
        "date_precision": "article_meta",
        "source": "example.com",
        "source_family": "example",
        "full_text": "AMD posted stellar quarterly earnings driven by server chip demand.",
        "word_count": 10,
        "company": "AMD",
        "companies": ["AMD"],
        "tickers": ["AMD"],
        "company_in_headline": True,
    }

    parsed = parse_and_normalize_article(raw)
    assert parsed is not None
    assert parsed["article_id"] == "art_1234567890abcdef"
    assert parsed["date_published"] == "2026-11-10T14:30:00+00:00"
    assert "semiconductors" in parsed["buckets"]
    assert "earnings" in parsed["buckets"]
    assert "AMD" in parsed["tickers"]
    assert parsed["company_in_headline"] is True


def test_parse_and_normalize_article_invalid():
    # Missing title and date
    raw = {"article_id": "bad_id"}
    assert parse_and_normalize_article(raw) is None

    # Invalid date string
    raw_bad_date = {
        "article_id": "art_2",
        "title": "Test Title",
        "url": "https://example.com",
        "date_published": "invalid-date-format",
    }
    assert parse_and_normalize_article(raw_bad_date) is None


def test_import_stock_news_corpus(tmp_path):
    # Create temporary JSONL file
    shard_file = tmp_path / "news_shard000.jsonl"
    records = [
        {
            "article_id": "art_1",
            "title": "Microsoft Invests $10B in AI Cloud Infrastructure",
            "url": "https://example.com/msft-ai",
            "date_published": "2026-10-01T09:00:00Z",
            "full_text": "Microsoft expands data center footprint for Azure AI.",
            "company": "Microsoft",
            "companies": ["Microsoft"],
            "tickers": ["MSFT"],
        },
        {
            "article_id": "art_2",
            "title": "Apple Prepares New M5 Silicon for Mac Lineup",
            "url": "https://example.com/aapl-m5",
            "date_published": "2026-10-02T10:00:00Z",
            "full_text": "Apple is gearing up production of M5 processors.",
            "company": "Apple",
            "companies": ["Apple"],
            "tickers": ["AAPL"],
        },
    ]

    with open(shard_file, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_sb.table.return_value = mock_table
    mock_table.upsert.return_value.execute.return_value.data = [{"article_id": "art_1"}, {"article_id": "art_2"}]

    stats = import_stock_news_corpus([shard_file], sb_client=mock_sb, batch_size=10)

    assert stats["total_read"] == 2
    assert stats["inserted"] == 2
    assert stats["skipped_or_invalid"] == 0
    mock_sb.table.assert_called_with("recipe_news_corpus")


def test_query_corpus_point_in_time():
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_sb.table.return_value = mock_table

    mock_query = MagicMock()
    mock_table.select.return_value = mock_query
    mock_query.lte.return_value = mock_query
    mock_query.gte.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.overlaps.return_value = mock_query
    mock_query.limit.return_value = mock_query

    mock_rows = [
        {
            "article_id": "art_1",
            "title": "Nvidia Earnings Surge Beyond Expectations",
            "url": "https://example.com/nvda",
            "date_published": "2026-11-10T09:15:00+00:00",
            "tickers": ["NVDA"],
            "buckets": ["semiconductors", "earnings"],
            "full_text": "Data center demand powers record beat.",
        },
        {
            "article_id": "art_2",
            "title": "Routine Corporate Update",
            "url": "https://example.com/corp",
            "date_published": "2026-11-10T08:00:00+00:00",
            "tickers": ["NVDA"],
            "buckets": ["semiconductors"],
            "full_text": "Company board meeting held.",
        },
    ]
    mock_query.execute.return_value.data = mock_rows

    results = query_corpus_point_in_time(
        sb_client=mock_sb,
        cutoff_timestamp="2026-11-10T09:30:00Z",
        tickers=["NVDA"],
        buckets=["semiconductors"],
        keywords=["earnings"],
        lookback_hours=24,
        limit=5,
    )

    # Keyword filter should keep only article 1
    assert len(results) == 1
    assert results[0]["article_id"] == "art_1"

    # Verify point in time parameters
    mock_query.lte.assert_called()
    mock_query.gte.assert_called()
