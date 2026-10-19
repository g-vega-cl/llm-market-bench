"""Hermetic unit tests for local_autoresearch.document_builder."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from local_autoresearch.document_builder import (
    DEFAULT_INGESTION_SYSTEM_PROMPT,
    format_raw_point_in_time_inputs,
    generate_daily_document,
)


@pytest.fixture
def sample_day_record() -> dict:
    return {
        "target_date": "2026-10-12",
        "ticker": "SPY",
        "open_price": 575.20,
        "close_price": 578.40,
        "actual_direction": "UP",
        "economic_calendar": "8:30 AM CPI: Core CPI +0.2% MoM (Consensus +0.3%)",
        "proxies": {
            "SPY": {"price": 575.20, "change_pct": 0.35},
            "QQQ": {"price": 490.10, "change_pct": 0.50},
            "TLT": {"price": 94.20, "change_pct": -0.15},
        },
        "options_sentiment": "Put/Call Ratio: 0.85, Max Pain: $574.00",
        "intraday_profile": "Prior session closed above VWAP with positive CLV (+0.62).",
        "newsletters": [
            {
                "sender": "The Kobeissi Letter",
                "subject": "Morning Brief",
                "content": "S&P futures point higher as tech leads ahead of CPI data.",
            }
        ],
    }


def test_format_raw_point_in_time_inputs(sample_day_record: dict):
    raw_text = format_raw_point_in_time_inputs(sample_day_record)

    assert "POINT-IN-TIME MARKET INPUTS: SPY (2026-10-12)" in raw_text
    assert "8:30 AM CPI" in raw_text
    assert "QQQ: $490.10 (+0.50%)" in raw_text
    assert "The Kobeissi Letter" in raw_text
    assert "Max Pain: $574.00" in raw_text


@pytest.mark.asyncio
async def test_generate_daily_document_with_strata(sample_day_record: dict):
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "## 1. Macro & Yield Trajectory\nCPI cooler than expected...\n## 2. Overnight Tape\nSPY +0.35%..."
                }
            }
        ]
    }

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        doc = await generate_daily_document(
            day_record=sample_day_record,
            ingestion_prompt=DEFAULT_INGESTION_SYSTEM_PROMPT,
            base_url="http://localhost:8080/v1",
        )

    assert "## 1. Macro & Yield Trajectory" in doc
    assert "CPI cooler than expected" in doc


@pytest.mark.asyncio
async def test_generate_daily_document_local_retry_success(sample_day_record: dict):
    # Strata fails on attempt 1, succeeds on attempt 2
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "## Recovered Briefing\nLocal retry succeeded."}}]
    }

    call_count = 0

    async def mock_post(url, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("Strata engine reloading...")
        return mock_resp

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        doc = await generate_daily_document(
            day_record=sample_day_record,
            ingestion_prompt=DEFAULT_INGESTION_SYSTEM_PROMPT,
            base_url="http://localhost:8080/v1",
            max_retries=2,
            retry_delay_seconds=0.01,
        )

    assert "Recovered Briefing" in doc
    assert call_count == 2


@pytest.mark.asyncio
async def test_generate_daily_document_fails_without_cloud_fallback(sample_day_record: dict):
    # Strata fails all retries, raises RuntimeError, NEVER calls external API
    with (
        patch("httpx.AsyncClient.post", side_effect=Exception("Strata engine offline")),
        pytest.raises(RuntimeError, match="Strata document generation failed after 2 attempts"),
    ):
        await generate_daily_document(
            day_record=sample_day_record,
            ingestion_prompt=DEFAULT_INGESTION_SYSTEM_PROMPT,
            base_url="http://localhost:8080/v1",
            max_retries=2,
            retry_delay_seconds=0.01,
        )


def test_default_ingestion_prompt_word_ceiling():
    assert "200 to 240 words" not in DEFAULT_INGESTION_SYSTEM_PROMPT
    assert "under 300 tokens" not in DEFAULT_INGESTION_SYSTEM_PROMPT
    assert "1,000 to 1,500 words" in DEFAULT_INGESTION_SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_generate_daily_document_payload_tokens(sample_day_record: dict):
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"choices": [{"message": {"content": "Sample Briefing"}}]}

    with patch("httpx.AsyncClient.post", return_value=mock_resp) as mock_post:
        await generate_daily_document(
            day_record=sample_day_record,
            ingestion_prompt=DEFAULT_INGESTION_SYSTEM_PROMPT,
            base_url="http://localhost:8080/v1",
        )
        called_json = mock_post.call_args[1]["json"]
        assert called_json["max_tokens"] >= 4096
        assert called_json["reasoning_budget_tokens"] == -1


def test_clean_newsletter_text_locally():
    from local_autoresearch.document_builder import clean_newsletter_text_locally

    raw = """
    View Online | Sign Up | Shop
    Presented By Sponsor Logo: Autocamp
    <a href="http://example.com"><img src="logo.png" /></a>
    Micron posted record $54.2 billion revenue and guided higher for Q1.
    PCE inflation undershoots forecasts, easing rate-hike fears.
    ADVERTISE//CAREERS//SHOP//FAQ
    Update your email preferences or unsubscribe here. Copyright 2026.
    """
    cleaned = clean_newsletter_text_locally(raw)

    assert "Micron posted record $54.2 billion revenue" in cleaned
    assert "PCE inflation undershoots forecasts" in cleaned
    assert "View Online" not in cleaned
    assert "Sponsor Logo" not in cleaned
    assert "Unsubscribe" not in cleaned
    assert "<img" not in cleaned


def test_decode_mime_header():
    from local_autoresearch.document_builder import decode_mime_header

    assert decode_mime_header("Plain Subject") == "Plain Subject"
    encoded = "=?utf-8?B?4piV77iPIEdpbW1lIHRoZSBiZWVm?="
    decoded = decode_mime_header(encoded)
    assert "Gimme the beef" in decoded


def test_format_raw_point_in_time_inputs_full_clean_content(sample_day_record: dict):
    sample_day_record["newsletters"] = [
        {
            "sender": "Morning Brew",
            "subject": "=?utf-8?B?4piV77iPIEdpbW1lIHRoZSBiZWVm?=",
            "content": "View Online\nTesla reported Q3 delivery beat of 462,000 vehicles.\nUnsubscribe here.",
        }
    ]
    formatted = format_raw_point_in_time_inputs(sample_day_record)

    assert "Gimme the beef" in formatted
    assert "Tesla reported Q3 delivery beat of 462,000 vehicles." in formatted
    assert "View Online" not in formatted
    assert "Unsubscribe" not in formatted


def test_clean_newsletter_text_strips_markdown_urls_and_tracking():
    from local_autoresearch.document_builder import clean_newsletter_text_locally

    raw = (
        "Check [The Morning Report](https://example.com/click?token=eyJhbGciOiJIUzI1NiJ9.abc.xyz&utm_source=email) "
        "and read more at https://finance.yahoo.com/news/123.\n"
        "S&P 500 pushed to record highs led by semiconductors.\n"
        "Unsubscribe from this list. All rights reserved."
    )
    cleaned = clean_newsletter_text_locally(raw)

    # Markdown link URLs stripped, anchor text preserved
    assert "The Morning Report" in cleaned
    assert "https://example.com" not in cleaned
    assert "eyJhbGciOiJIUzI1NiJ9" not in cleaned
    assert "https://finance.yahoo.com" not in cleaned
    assert "S&P 500 pushed to record highs led by semiconductors." in cleaned
    assert "Unsubscribe" not in cleaned


def test_get_rolling_trend_vector_zero_lookahead(tmp_path):
    import sqlite3
    from contextlib import closing

    from local_autoresearch.document_builder import get_rolling_trend_vector

    db_path = str(tmp_path / "test_trend.db")
    with closing(sqlite3.connect(db_path)) as conn:
        with conn:
            conn.execute(
                """
            CREATE TABLE cached_days (
                target_date TEXT PRIMARY KEY,
                open_price REAL,
                close_price REAL,
                actual_direction TEXT
            )
            """
            )
        # Insert 10 days of prices: 500 to 509
        for i in range(1, 11):
            d_str = f"2026-09-{i:02d}"
            conn.execute(
                "INSERT INTO cached_days VALUES (?, ?, ?, ?)",
                (d_str, 500.0 + i, 502.0 + i, "UP"),
            )
        # Insert target date (Day 11) with a huge jump to test that target date is NOT included
        conn.execute("INSERT INTO cached_days VALUES ('2026-09-11', 600.0, 650.0, 'UP')")
        conn.commit()

    trend = get_rolling_trend_vector("2026-09-11", db_path=db_path)

    # Prior day must be 2026-09-10 (close 512.0), NEVER 2026-09-11 (close 650.0)
    assert trend["prior_date"] == "2026-09-10"
    assert trend["prior_close"] == 512.0
    assert trend["days_available"] == 10
    assert "650.0" not in trend["summary"]
    assert "2026-09-10" in trend["summary"]


def test_get_point_in_time_memories_filtering(tmp_path):
    import sqlite3
    from contextlib import closing

    from local_autoresearch.document_builder import get_point_in_time_memories

    db_path = str(tmp_path / "test_memories.db")
    with closing(sqlite3.connect(db_path)) as conn:
        with conn:
            conn.execute(
                """
            CREATE TABLE cached_memories (
                id INTEGER PRIMARY KEY,
                content TEXT,
                memory_type TEXT,
                importance_score REAL,
                created_at TEXT
            )
            """
            )
        # Memory 1: created prior to target date
        conn.execute(
            "INSERT INTO cached_memories VALUES (1, 'Prior lesson: watch yields', 'LESSON_LEARNED', 0.9, '2026-09-10T12:00:00Z')"
        )
        # Memory 2: created ON target date evening (LOOKAHEAD - MUST BE EXCLUDED)
        conn.execute(
            "INSERT INTO cached_memories VALUES (2, 'Future lesson: market crashed today', 'LESSON_LEARNED', 0.95, '2026-09-11T18:00:00Z')"
        )
        # Memory 3: created weeks later
        conn.execute(
            "INSERT INTO cached_memories VALUES (3, 'Far future lesson', 'LESSON_LEARNED', 0.8, '2026-10-01T00:00:00Z')"
        )
        conn.commit()

    memories = get_point_in_time_memories("2026-09-11", db_path=db_path)

    assert len(memories) == 1
    assert memories[0]["content"] == "Prior lesson: watch yields"
    assert not any("Future lesson" in m["content"] for m in memories)


def test_format_raw_point_in_time_inputs_with_safety_ceiling(sample_day_record: dict):
    # Enormous newsletter content exceeding 180,000 characters
    huge_text = "Macro commentary. " * 15000  # ~270,000 chars
    sample_day_record["newsletters"] = [{"sender": "Heavy Newsletter", "subject": "Long Report", "content": huge_text}]

    formatted = format_raw_point_in_time_inputs(sample_day_record)
    assert len(formatted) <= 180500
    assert "[INPUT EXCEEDED 180,000 CHAR SAFETY BUFFER" in formatted


def test_format_raw_point_in_time_inputs_trend_fallback_when_cache_absent(tmp_path):
    """Verify that format_raw_point_in_time_inputs falls back to day_record['trend_vector'] when cache DB is absent."""
    non_existent_db = str(tmp_path / "absent.db")
    day_record = {
        "target_date": "2026-10-15",
        "ticker": "SPY",
        "trend_vector": {
            "summary": "5-Day Return: +1.45%\n20-Day Simple Moving Average (SMA20): $578.00 (Distance: +0.42%)",
        },
    }

    raw_text = format_raw_point_in_time_inputs(day_record, db_path=non_existent_db)

    assert "--- Multi-Day Momentum & Trend Vector ---" in raw_text
    assert "5-Day Return: +1.45%" in raw_text
    assert "20-Day Simple Moving Average (SMA20): $578.00" in raw_text
