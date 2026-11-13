"""Hermetic unit tests for the Recipe Studio Unified News Corpus."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from recipes.news_corpus import (
    derive_article_buckets,
    import_stock_news_corpus,
    parse_and_normalize_article,
    sync_live_news_to_corpus,
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
    raw = {"article_id": "bad_id"}
    assert parse_and_normalize_article(raw) is None

    raw_bad_date = {
        "article_id": "art_2",
        "title": "Test Title",
        "url": "https://example.com",
        "date_published": "invalid-date-format",
    }
    assert parse_and_normalize_article(raw_bad_date) is None


def test_import_stock_news_corpus(tmp_path):
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


@pytest.mark.asyncio
async def test_sync_live_news_to_corpus_hermetic():
    mock_sb = MagicMock()
    news_tbl = MagicMock()
    snap_tbl = MagicMock()

    def _router(name: str):
        if name == "recipe_news_corpus":
            return news_tbl
        if name == "newsletter_snapshots":
            return snap_tbl
        return MagicMock()

    mock_sb.table.side_effect = _router
    snap_chain = snap_tbl.select.return_value
    snap_chain.gte.return_value = snap_chain
    snap_chain.order.return_value = snap_chain
    snap_chain.limit.return_value = snap_chain
    snap_chain.execute.return_value.data = [
        {
            "source_id": "nl_123",
            "sender": "Daily Market Brief",
            "subject": "Fed signals cautious rate path as NVDA rallies",
            "content": "Jerome Powell noted inflation progress while semiconductor stocks surged.",
            "date": "2026-11-13T12:00:00+00:00",
        }
    ]

    news_tbl.upsert.return_value.execute.return_value.data = [{"article_id": "a1"}, {"article_id": "nl_123"}]

    wire_items = [
        {
            "source": "FMP (Reuters)",
            "headline": "TSMC expands AI chip packaging capacity",
            "published_at": "2026-11-13T13:30:00Z",
            "summary": "Foundry demand remains elevated for GPUs.",
            "url": "https://example.com/tsmc",
            "tickers": ["TSM", "NVDA"],
            "source_id_hash": "wire_hash_1",
        }
    ]

    with patch("recipes.news_corpus.aggregate_intraday_news", new=AsyncMock(return_value=wire_items)):
        stats = await sync_live_news_to_corpus(
            mock_sb,
            as_of_utc=datetime(2026, 11, 13, 14, 0, tzinfo=UTC),
        )

    assert stats["inserted"] == 2
    assert news_tbl.upsert.called
    upserted_rows = news_tbl.upsert.call_args[0][0]
    ids = {r["article_id"] for r in upserted_rows}
    assert "wire_hash_1" in ids
    assert "nl_123_2026-11-13" in ids
