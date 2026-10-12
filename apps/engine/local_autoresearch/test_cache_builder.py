"""Unit tests for local_autoresearch.cache_builder."""

import os
import sqlite3
import tempfile
from unittest.mock import MagicMock

import pytest

from local_autoresearch.cache_builder import (
    build_cache_from_raw_db,
    build_cache_from_supabase,
    extract_features_from_prediction_record,
    get_iso_week_key,
    init_cache_db,
    load_cached_weeks,
    save_cached_day,
)
from local_autoresearch.historical_downloader import init_raw_db


@pytest.fixture
def temp_cache_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_cache_db(path)
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_get_iso_week_key():
    # 2026-10-05 (Monday) and 2026-10-09 (Friday) share the same ISO week
    w1 = get_iso_week_key("2026-10-05")
    w2 = get_iso_week_key("2026-10-09")
    assert w1 == w2
    assert "2026-W" in w1


def test_save_and_load_cached_weeks(temp_cache_db):
    day1 = {
        "target_date": "2026-10-05",
        "ticker": "SPY",
        "open_price": 570.0,
        "close_price": 573.0,
        "actual_direction": "UP",
        "economic_calendar": "None",
        "newsletters": [{"sender": "Morning Brew", "subject": "Open", "content": "Rally"}],
    }
    day2 = {
        "target_date": "2026-10-06",
        "ticker": "SPY",
        "open_price": 573.0,
        "close_price": 571.0,
        "actual_direction": "DOWN",
        "economic_calendar": "None",
        "newsletters": [],
    }
    # Different week
    day3 = {
        "target_date": "2026-10-12",
        "ticker": "SPY",
        "open_price": 572.0,
        "close_price": 575.0,
        "actual_direction": "UP",
        "economic_calendar": "None",
        "newsletters": [],
    }

    save_cached_day(day1, db_path=temp_cache_db)
    save_cached_day(day2, db_path=temp_cache_db)
    save_cached_day(day3, db_path=temp_cache_db)

    weeks = load_cached_weeks(db_path=temp_cache_db)
    assert len(weeks) == 2

    w1_key = get_iso_week_key("2026-10-05")
    assert len(weeks[w1_key]) == 2
    assert weeks[w1_key][0]["target_date"] == "2026-10-05"
    assert weeks[w1_key][1]["target_date"] == "2026-10-06"


def test_extract_features_from_prediction_record():
    mock_pred = {
        "target_date": "2026-09-24",
        "ticker": "SPY",
        "actual_open_price": 568.5,
        "actual_close_price": 570.2,
        "actual_direction": "UP",
        "market_context": (
            "=== TODAY'S HIGH-IMPACT ECONOMIC RELEASES ===\nJobless Claims 218k\n"
            "=== LIVE PRE-MARKET ACTION ===\n- QQQ: $485.00 (+0.80%)\n- UUP: $28.00 (-0.10%)\n"
            "Morning Newsletter Briefing:\nTech leads opening bell.\n"
            "Options Derivatives Positioning (SPY):\nMax Pain 570 strike."
        ),
    }

    feat = extract_features_from_prediction_record(mock_pred)
    assert feat["target_date"] == "2026-09-24"
    assert feat["open_price"] == 568.5
    assert feat["close_price"] == 570.2
    assert feat["actual_direction"] == "UP"
    assert "Jobless Claims" in feat["economic_calendar"]
    assert "Tech leads" in feat["synthetic_newsletter"]
    assert "Max Pain" in feat["options_sentiment"]
    assert "QQQ" in feat["proxies"]
    assert feat["proxies"]["QQQ"]["price"] == 485.0


def test_extract_features_with_production_headers():
    mock_pred = {
        "target_date": "2026-10-09",
        "ticker": "SPY",
        "actual_open_price": 774.89,
        "actual_close_price": 773.83,
        "actual_direction": "DOWN",
        "market_context": (
            "=== TODAY'S ECONOMIC RELEASES & MACRO PRINTS (Live Actual vs Consensus) ===\n"
            "Jobless Claims: 197k vs 200k est\n"
            "=== AI WALL STREET SYNTHESIZED DAILY NEWSLETTER ===\n"
            "AI debt wave fuels market.\n"
            "=== LIVE PRE-MARKET ACTION & GAP ANALYSIS ===\n"
            "- QQQ: $500.00 (+0.40%)\n"
            "=== SPY INTRADAY MOVEMENT PROFILE (2026-10-08) ===\n"
            "- Regular Trading Hours: Open $774.89 | Close $773.83\n"
            "- Session Archetype: RANGE_BOUND_CHURN\n"
            "### 📊 Macro Options Sentiment (SPY)\n"
            "Max pain at 774 strike.\n"
        ),
    }
    feat = extract_features_from_prediction_record(mock_pred)
    assert "Jobless Claims" in feat["economic_calendar"]
    assert "AI debt wave" in feat["synthetic_newsletter"]
    assert "RANGE_BOUND_CHURN" in feat["intraday_profile"]
    assert "Max pain" in feat["options_sentiment"]


@pytest.mark.asyncio
async def test_build_cache_from_supabase_hermetic(temp_cache_db):
    mock_supabase = MagicMock()
    mock_pred_data = [
        {
            "target_date": "2026-10-01",
            "ticker": "SPY",
            "actual_open_price": 571.0,
            "actual_close_price": 573.5,
            "actual_direction": "UP",
            "status": "evaluated",
            "market_context": "Sample context",
        }
    ]
    mock_news_data = [
        {
            "sender": "The Kobeissi Letter",
            "subject": "Week Ahead",
            "content": "Macro rally",
            "date": "2026-10-01T08:00:00Z",
        }
    ]

    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = mock_pred_data
    mock_supabase.table.return_value.select.return_value.gte.return_value.lte.return_value.limit.return_value.execute.return_value.data = mock_news_data

    count = await build_cache_from_supabase(mock_supabase, limit_days=10, db_path=temp_cache_db)
    assert count == 1

    weeks = load_cached_weeks(db_path=temp_cache_db)
    assert len(weeks) == 1


def test_build_cache_from_raw_db_zero_lookahead(tmp_path):
    """Test build_cache_from_raw_db strictly respects 09:15 ET cutoff and avoids leaks."""
    import sqlite3

    from local_autoresearch.cache_builder import build_cache_from_raw_db
    from local_autoresearch.historical_downloader import init_raw_db

    raw_db = str(tmp_path / "raw.db")
    cache_db = str(tmp_path / "cache.db")
    init_raw_db(raw_db)

    conn = sqlite3.connect(raw_db)
    cursor = conn.cursor()

    # Prior day 2025-05-08 EOD
    cursor.execute("""
        INSERT INTO eod_bars (ticker, date, open, high, low, close, volume, vwap)
        VALUES ('SPY', '2025-05-08', 560.0, 565.0, 559.0, 564.0, 50000000, 562.5)
    """)
    # Target day 2025-05-09 EOD
    cursor.execute("""
        INSERT INTO eod_bars (ticker, date, open, high, low, close, volume, vwap)
        VALUES ('SPY', '2025-05-09', 565.0, 568.0, 563.0, 567.0, 60000000, 566.0)
    """)

    # Premarket bar at 09:15 ET (13:15 UTC) - ALLOWED
    cursor.execute("""
        INSERT INTO premarket_bars (ticker, bar_time_utc, open, high, low, close, volume, vwap)
        VALUES ('SPY', '2025-05-09T13:15:00Z', 566.0, 566.5, 565.8, 566.2, 5000, 566.1)
    """)
    # Regular session bar at 10:00 ET (14:00 UTC) - MUST BE IGNORED
    cursor.execute("""
        INSERT INTO premarket_bars (ticker, bar_time_utc, open, high, low, close, volume, vwap)
        VALUES ('SPY', '2025-05-09T14:00:00Z', 567.0, 568.0, 566.0, 567.5, 10000, 567.2)
    """)

    # News before 09:15 ET (08:30 ET / 12:30 UTC) - ALLOWED
    cursor.execute("""
        INSERT INTO market_news (id, published_utc, ticker, title, description, publisher, keywords)
        VALUES ('n1', '2025-05-09T12:30:00Z', 'SPY', 'Pre-market jobs print beats', 'Nonfarm payrolls rose', 'Bloomberg', 'jobs')
    """)
    # News after 09:15 ET (09:35 ET / 13:35 UTC) - LEAK! MUST BE EXCLUDED
    cursor.execute("""
        INSERT INTO market_news (id, published_utc, ticker, title, description, publisher, keywords)
        VALUES ('n2', '2025-05-09T13:35:00Z', 'SPY', 'Opening bell selloff begins', 'Markets slide', 'CNBC', 'market')
    """)

    # Newsletter before 09:15 ET (07:00 ET / 11:00 UTC) - ALLOWED
    cursor.execute("""
        INSERT INTO raw_newsletters (source_id, date_utc, sender, subject, content, ingested_at)
        VALUES ('g1', '2025-05-09T11:00:00Z', 'Chartr', 'Morning Visual', 'Macro visual breakdown', '2025-05-09T11:05:00Z')
    """)
    # Newsletter after 09:15 ET (09:45 ET / 13:45 UTC) - LEAK! MUST BE EXCLUDED
    cursor.execute("""
        INSERT INTO raw_newsletters (source_id, date_utc, sender, subject, content, ingested_at)
        VALUES ('g2', '2025-05-09T13:45:00Z', 'Morning Brew', 'Midday update', 'Stocks dropping fast', '2025-05-09T13:50:00Z')
    """)

    conn.commit()
    conn.close()

    # 1. Primary Arena Mode
    count = build_cache_from_raw_db(
        raw_db, cache_db, start_date="2025-05-09", end_date="2025-05-09", is_regime_vault=False
    )
    assert count == 1

    weeks = load_cached_weeks(cache_db)
    day_rec = list(weeks.values())[0][0]

    # Verify zero-lookahead on news
    news_titles = [item.get("title") for item in day_rec.get("market_news", [])]
    assert "Pre-market jobs print beats" in news_titles
    assert "Opening bell selloff begins" not in news_titles

    # Verify zero-lookahead on newsletters
    nl_subjects = [item.get("subject") for item in day_rec.get("newsletters", [])]
    assert "Morning Visual" in nl_subjects
    assert "Midday update" not in nl_subjects

    # Verify pre-market quote was as of 09:15 ET (566.2)
    assert "SPY" in day_rec.get("proxies", {})
    assert day_rec["proxies"]["SPY"]["price"] == 566.2

    # 2. Regime Vault Mode (Pre-market tape strictly omitted)
    cache_db_vault = str(tmp_path / "cache_vault.db")
    count_v = build_cache_from_raw_db(
        raw_db, cache_db_vault, start_date="2025-05-09", end_date="2025-05-09", is_regime_vault=True
    )
    assert count_v == 1

    weeks_v = load_cached_weeks(cache_db_vault)
    day_rec_v = list(weeks_v.values())[0][0]
    # Proxies must be empty in Regime Vault
    assert day_rec_v.get("proxies") == {}
    # Ground truth remains UP (Close 567.0 >= Open 565.0)
    assert day_rec_v["actual_direction"] == "UP"


def test_build_cache_from_raw_db_populates_macro_calendar_and_proxies(tmp_path):
    """Reproduction test: Verify raw DB compiler extracts FRED macro series and multi-proxy premarket bars."""
    raw_db = str(tmp_path / "raw_with_macro.db")
    cache_db = str(tmp_path / "cache_with_macro.db")
    init_raw_db(raw_db)

    conn = sqlite3.connect(raw_db)
    cursor = conn.cursor()

    # EOD bars for SPY and QQQ
    cursor.execute("""
        INSERT INTO eod_bars (ticker, date, open, high, low, close, volume, vwap)
        VALUES
            ('SPY', '2025-05-08', 560.0, 565.0, 559.0, 564.0, 100000, 562.5),
            ('SPY', '2025-05-09', 565.0, 568.0, 564.0, 567.0, 120000, 566.0),
            ('QQQ', '2025-05-08', 450.0, 455.0, 449.0, 454.0, 80000, 452.0),
            ('QQQ', '2025-05-09', 455.0, 460.0, 454.0, 458.0, 90000, 457.0)
    """)

    # Premarket bars for SPY and QQQ at 09:15 ET (13:15 UTC)
    cursor.execute("""
        INSERT INTO premarket_bars (ticker, bar_time_utc, open, high, low, close, volume, vwap)
        VALUES
            ('SPY', '2025-05-09T13:15:00Z', 566.0, 566.5, 565.8, 566.2, 5000, 566.1),
            ('QQQ', '2025-05-09T13:15:00Z', 456.0, 456.8, 455.9, 456.5, 4000, 456.3)
    """)

    # Macro series from FRED as of 2025-05-08 (T-1)
    cursor.execute("""
        INSERT INTO macro_series (series_id, date, value)
        VALUES
            ('DGS10', '2025-05-07', 4.30),
            ('DGS10', '2025-05-08', 4.35),
            ('DGS2', '2025-05-08', 4.15),
            ('T10Y2Y', '2025-05-08', 0.20),
            ('FEDFUNDS', '2025-05-01', 4.83),
            ('ICSA', '2025-05-03', 215000.0)
    """)

    conn.commit()
    conn.close()

    count = build_cache_from_raw_db(raw_db, cache_db, start_date="2025-05-09", end_date="2025-05-09")
    assert count == 1

    weeks = load_cached_weeks(cache_db)
    day_rec = list(weeks.values())[0][0]

    # Verify multi-proxy premarket tape includes QQQ
    proxies = day_rec.get("proxies", {})
    assert "SPY" in proxies
    assert "QQQ" in proxies
    assert proxies["QQQ"]["price"] == 456.5
    # Prior QQQ EOD was 454.0, premarket close was 456.5 -> +0.55%
    assert abs(proxies["QQQ"]["change_pct"] - 0.55) < 0.05

    # Verify economic_calendar contains formatted rates and claims from macro_series
    econ = day_rec.get("economic_calendar", "")
    assert "10-Year Treasury Yield: 4.35%" in econ
    assert "2-Year Treasury Yield: 4.15%" in econ
    assert "10Y-2Y Spread" in econ
    assert "215,000" in econ
