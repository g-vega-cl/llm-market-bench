"""Hermetic tests for HistoricalDownloader and rate-limited ingestion."""

from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from local_autoresearch.historical_downloader import (
    HistoricalDownloader,
    TokenBucketLimiter,
    init_raw_db,
)


def test_token_bucket_limiter():
    """Test token bucket limiter consumes and refills correctly."""
    limiter = TokenBucketLimiter(max_tokens=2.0, refill_period_seconds=1.0)
    assert limiter.consume() is True
    assert limiter.consume() is True
    assert limiter.consume() is False


def test_init_raw_db(tmp_path):
    """Test raw SQLite database tables and indexes initialization."""
    db_file = str(tmp_path / "test_raw.db")
    init_raw_db(db_file)

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {r[0] for r in cursor.fetchall()}
    conn.close()

    expected_tables = {
        "eod_bars",
        "premarket_bars",
        "raw_newsletters",
        "market_news",
        "macro_series",
    }
    assert expected_tables.issubset(tables)


@pytest.mark.asyncio
async def test_download_fmp_eod_saves_to_db(tmp_path):
    """Test downloading FMP EOD bars parses data and inserts into SQLite."""
    db_file = str(tmp_path / "test_raw.db")
    downloader = HistoricalDownloader(db_path=db_file, fmp_api_key="mock_key")

    mock_fmp_response = [
        {
            "symbol": "SPY",
            "date": "2023-05-10",
            "open": 414.52,
            "high": 415.08,
            "low": 411.45,
            "close": 413.44,
            "volume": 78601800,
            "vwap": 413.32,
        },
        {
            "symbol": "SPY",
            "date": "2023-05-09",
            "open": 411.53,
            "high": 412.31,
            "low": 410.58,
            "close": 411.95,
            "volume": 53139300,
            "vwap": 411.61,
        },
    ]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_fmp_response

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.get.return_value = mock_resp

    with patch("httpx.Client", return_value=mock_client):
        count = downloader.download_fmp_eod(["SPY"], "2023-05-08", "2023-05-11")

    assert count == 2

    # Verify rows in DB
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT ticker, date, close, vwap FROM eod_bars ORDER BY date ASC")
    rows = cursor.fetchall()
    conn.close()

    assert len(rows) == 2
    assert rows[0] == ("SPY", "2023-05-09", 411.95, 411.61)
    assert rows[1] == ("SPY", "2023-05-10", 413.44, 413.32)


@pytest.mark.asyncio
async def test_download_polygon_premarket_bars_saves_to_db(tmp_path):
    """Test downloading Polygon 5-min bars persists with UTC ISO timestamp."""
    db_file = str(tmp_path / "test_raw.db")
    downloader = HistoricalDownloader(db_path=db_file, massive_api_key="mock_key")

    mock_poly_response = {
        "status": "OK",
        "results": [
            {
                "t": 1746777600000,  # 2025-05-09 08:00:00 UTC (04:00 ET)
                "o": 565.38,
                "h": 565.60,
                "l": 565.36,
                "c": 565.54,
                "v": 7219,
                "vw": 565.45,
            },
            {
                "t": 1746796500000,  # 2025-05-09 13:15:00 UTC (09:15 ET)
                "o": 566.90,
                "h": 567.15,
                "l": 566.85,
                "c": 567.08,
                "v": 15420,
                "vw": 567.02,
            },
        ],
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_poly_response

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.get.return_value = mock_resp

    with patch("httpx.Client", return_value=mock_client):
        count = downloader.download_polygon_bars("SPY", "2025-05-09", "2025-05-09")

    assert count == 2

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT ticker, bar_time_utc, close, vwap FROM premarket_bars ORDER BY bar_time_utc ASC")
    rows = cursor.fetchall()
    conn.close()

    assert len(rows) == 2
    assert rows[0][0] == "SPY"
    assert rows[0][1] == "2025-05-09T08:00:00Z"
    assert rows[0][2] == 565.54
    assert rows[1][1] == "2025-05-09T13:15:00Z"
    assert rows[1][2] == 567.08


@pytest.mark.asyncio
async def test_download_polygon_news_saves_to_db(tmp_path):
    """Test downloading Polygon reference news stores articles in SQLite."""
    db_file = str(tmp_path / "test_raw.db")
    downloader = HistoricalDownloader(db_path=db_file, massive_api_key="mock_key")

    mock_news_response = {
        "status": "OK",
        "results": [
            {
                "id": "news_123",
                "title": "Fed rate expectations shift pre-market",
                "published_utc": "2023-05-10T12:30:00Z",
                "article_url": "https://example.com/news123",
                "description": "Inflation prints show cooling consumer prices.",
                "publisher": {"name": "Benzinga"},
                "keywords": ["macro", "cpi"],
            }
        ],
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_news_response

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.get.return_value = mock_resp

    with patch("httpx.Client", return_value=mock_client):
        count = downloader.download_polygon_news("2023-05-10T00:00:00Z", "2023-05-10T13:15:00Z", ticker="SPY")

    assert count == 1

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT id, published_utc, title, publisher FROM market_news")
    rows = cursor.fetchall()
    conn.close()

    assert len(rows) == 1
    assert rows[0] == ("news_123", "2023-05-10T12:30:00Z", "Fed rate expectations shift pre-market", "Benzinga")


@pytest.mark.asyncio
async def test_download_fred_series_saves_to_db(tmp_path):
    """Test downloading FRED CSV macroeconomic series saves observation dates."""
    db_file = str(tmp_path / "test_raw.db")
    downloader = HistoricalDownloader(db_path=db_file)

    mock_csv = "observation_date,DGS10\n2023-05-09,3.52\n2023-05-10,3.43\n"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = mock_csv

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.get.return_value = mock_resp

    with patch("httpx.Client", return_value=mock_client):
        count = downloader.download_fred_series(["DGS10"])

    assert count == 2

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT series_id, date, value FROM macro_series ORDER BY date ASC")
    rows = cursor.fetchall()
    conn.close()

    assert len(rows) == 2
    assert rows[0] == ("DGS10", "2023-05-09", 3.52)
    assert rows[1] == ("DGS10", "2023-05-10", 3.43)
