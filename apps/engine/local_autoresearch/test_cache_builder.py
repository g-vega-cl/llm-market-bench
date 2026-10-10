"""Unit tests for local_autoresearch.cache_builder."""

import os
import tempfile
from unittest.mock import MagicMock

import pytest
from apps.engine.local_autoresearch.cache_builder import (
    build_cache_from_supabase,
    extract_features_from_prediction_record,
    get_iso_week_key,
    init_cache_db,
    load_cached_weeks,
    save_cached_day,
)


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
