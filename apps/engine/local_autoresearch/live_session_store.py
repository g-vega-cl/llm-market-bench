"""Live Production Session Store for Ground-Truth Local Autoresearch.

Materializes and caches real live trading sessions from Supabase into a hermetic
local SQLite database, including real morning open newsletters, live market contexts,
and ground-truth intraday SPY price action.
"""

from __future__ import annotations

import os
import re
import sqlite3
import sys
import time
from typing import Any

# Ensure apps/engine root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import logger
from core.db import get_supabase_client

DEFAULT_LIVE_SESSIONS_DB = ".live_production_sessions.db"


def is_premarket_timestamp_clean(source_created_at: str | None, payload: str | None) -> bool:
    """Verify that session data was strictly produced before the 09:30 AM ET market open."""
    # 1. Check source creation timestamp in UTC (09:30 AM EDT is 13:30:00 UTC)
    if source_created_at:
        utc_time_match = re.search(r"T([0-9]{2}:[0-9]{2}:[0-9]{2})", source_created_at)
        if utc_time_match and utc_time_match.group(1) > "13:30:00":
            return False

    # 2. Check exact current time inside market context
    if payload:
        m = re.search(r"Exact Current Time:\s*([0-9]{2}):([0-9]{2}):[0-9]{2}\s*([AP]M)", payload)
        if m:
            hh, mm, ampm = int(m.group(1)), int(m.group(2)), m.group(3).upper()
            if ampm == "PM":
                return False
            if ampm == "AM":
                if hh > 9 or hh < 4:
                    return False
                if hh == 9 and mm >= 30:
                    return False

    return True


def init_live_sessions_db(db_path: str = DEFAULT_LIVE_SESSIONS_DB) -> None:
    """Initialize SQLite schema for live production sessions."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS live_sessions (
            target_date TEXT PRIMARY KEY,
            ticker TEXT NOT NULL,
            open_price REAL NOT NULL,
            close_price REAL NOT NULL,
            high_price REAL,
            low_price REAL,
            actual_direction TEXT NOT NULL,
            morning_newsletter TEXT,
            market_context TEXT,
            evaluation_payload TEXT NOT NULL,
            source_created_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def fetch_all_open_newsletters(page_size: int = 15) -> list[dict[str, Any]]:
    """Fetch all production morning newsletters (session='open') with pagination."""
    sb = get_supabase_client()
    news_items: list[dict[str, Any]] = []
    offset = 0

    while True:
        res = None
        for attempt in range(3):
            try:
                res = (
                    sb.table("generated_newsletters")
                    .select("id, title, content, created_at, session")
                    .eq("session", "open")
                    .order("created_at", desc=False)
                    .range(offset, offset + page_size - 1)
                    .execute()
                )
                break
            except Exception as e:
                logger.warning(
                    f"Error fetching generated_newsletters at offset {offset} (attempt {attempt + 1}/3): {e}"
                )
                time.sleep(1.0)

        if not res or not res.data:
            break

        news_items.extend(res.data)
        offset += len(res.data)
        if len(res.data) < page_size:
            break

    return news_items


def fetch_all_spy_predictions(page_size: int = 25) -> dict[str, dict[str, Any]]:
    """Fetch all historical SPY daily_predictions with ground-truth prices."""
    sb = get_supabase_client()
    preds_by_date: dict[str, dict[str, Any]] = {}
    offset = 0

    while True:
        res = None
        for attempt in range(3):
            try:
                res = (
                    sb.table("daily_predictions")
                    .select(
                        "target_date, open_price, close_price, high_price, low_price, actual_direction, market_context"
                    )
                    .eq("ticker", "SPY")
                    .order("target_date", desc=False)
                    .range(offset, offset + page_size - 1)
                    .execute()
                )
                break
            except Exception as e:
                logger.warning(f"Error fetching daily_predictions at offset {offset} (attempt {attempt + 1}/3): {e}")
                time.sleep(1.0)

        if not res or not res.data:
            break

        for p in res.data:
            d = p.get("target_date")
            if d and d not in preds_by_date:
                preds_by_date[d] = p

        offset += len(res.data)
        if len(res.data) < page_size:
            break

    return preds_by_date


def build_evaluation_payload(date_str: str, morning_newsletter: str, market_context: str | None) -> str:
    """Construct the exact single-pass user evaluation payload passed to the trading model."""
    if market_context and len(market_context.strip()) > 200:
        return market_context.strip()

    # Fallback to standard live context format when full market_context was not serialized
    header = (
        f"Asset: SPY (S&P 500 ETF)\n"
        f"=== EXACT TEMPORAL CONTEXT ===\n"
        f"Today is {date_str}.\n"
        f"Market Session: Pre-Market (04:00 - 09:30 EDT).\n"
        f"==============================\n\n"
        f"Morning Newsletter Briefing:\n{morning_newsletter.strip()}"
    )
    return header


def materialize_live_sessions(db_path: str = DEFAULT_LIVE_SESSIONS_DB) -> int:
    """Extract real live production sessions from Supabase and materialize them locally."""
    init_live_sessions_db(db_path)
    news_items = fetch_all_open_newsletters()
    preds_by_date = fetch_all_spy_predictions()

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    inserted = 0

    for item in news_items:
        date_str = item.get("created_at", "")[:10]
        pred = preds_by_date.get(date_str)
        if not pred:
            continue

        actual_dir = str(pred.get("actual_direction") or "").upper()
        if actual_dir not in ("UP", "DOWN"):
            continue

        open_p = float(pred.get("open_price") or 0.0)
        close_p = float(pred.get("close_price") or 0.0)
        if open_p <= 0 or close_p <= 0:
            continue

        high_p = float(pred.get("high_price") or open_p)
        low_p = float(pred.get("low_price") or open_p)
        newsletter_content = item.get("content") or ""
        market_ctx = pred.get("market_context") or ""
        payload = build_evaluation_payload(date_str, newsletter_content, market_ctx)

        # Enforce zero-leakage pre-market timestamp guard (< 09:30 AM EDT / 13:30:00 UTC)
        if not is_premarket_timestamp_clean(item.get("created_at"), payload):
            logger.warning(f"Purging session {date_str} due to post-open timestamp leakage.")
            continue

        c.execute(
            """
            INSERT OR REPLACE INTO live_sessions (
                target_date, ticker, open_price, close_price, high_price, low_price,
                actual_direction, morning_newsletter, market_context, evaluation_payload,
                source_created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                date_str,
                "SPY",
                open_p,
                close_p,
                high_p,
                low_p,
                actual_dir,
                newsletter_content,
                market_ctx,
                payload,
                item.get("created_at"),
            ),
        )
        inserted += 1

    conn.commit()
    conn.close()
    logger.info(f"Materialized {inserted} live production sessions into {db_path}.")
    return inserted


def load_live_sessions(db_path: str = DEFAULT_LIVE_SESSIONS_DB) -> list[dict[str, Any]]:
    """Hermetic loader retrieving live production sessions from local SQLite."""
    if not os.path.exists(db_path):
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    rows = c.execute("SELECT * FROM live_sessions ORDER BY target_date ASC").fetchall()
    sessions = [dict(r) for r in rows]
    conn.close()
    return sessions


if __name__ == "__main__":
    count = materialize_live_sessions()
    print(f"Successfully materialized {count} clean pre-market sessions.")
