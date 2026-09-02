"""Backfill missing target_date fields for CALENDAR_EVENT memories."""

import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from supabase import create_client

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

url = os.environ.get("SUPABASE_PROJECT_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    print("Error: SUPABASE_PROJECT_URL and SUPABASE_SERVICE_ROLE_KEY are required.")
    sys.exit(1)

supabase = create_client(url, key)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("backfill_calendar")


def extract_iso_date(text: str, default_year: int = 2026) -> str | None:
    """Extracts the first valid YYYY-MM-DD date or Month Day date from text."""
    if not text:
        return None

    # 1. ISO format: YYYY-MM-DD
    matches = re.findall(r"\b(202\d-[01]\d-[0-3]\d)\b", text)
    for date_str in matches:
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return date_str
        except ValueError:
            continue

    # 2. Textual format: (Aug 25), Aug 28, September 11, etc.
    month_day_match = re.search(
        r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{1,2})\b",
        text,
        re.IGNORECASE,
    )
    if month_day_match:
        month_str = month_day_match.group(1).title()[:3]
        day_str = month_day_match.group(2).zfill(2)
        try:
            dt = datetime.strptime(f"{default_year} {month_str} {day_str}", "%Y %b %d")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    return None


def backfill_calendar_events():
    """Queries all calendar events missing target_date and backfills them."""
    logger.info("Querying CALENDAR_EVENT memories with missing target_date...")
    res = (
        supabase.table("memories")
        .select("id, content, target_date, importance_score, metadata")
        .eq("memory_type", "CALENDAR_EVENT")
        .is_("target_date", "null")
        .execute()
    )

    rows = res.data or []
    logger.info(f"Found {len(rows)} CALENDAR_EVENT records missing target_date.")

    today_str = datetime.now().strftime("%Y-%m-%d")
    updated_count = 0

    for row in rows:
        row_id = row["id"]
        content = row.get("content", "")
        meta = row.get("metadata") or {}
        importance = row.get("importance_score") or 5

        date_found = extract_iso_date(content) or extract_iso_date(str(meta))

        if not date_found:
            logger.warning(f"Could not extract date for Memory {row_id}: {content[:60]}...")
            continue

        new_meta = dict(meta)
        is_future = date_found >= today_str and importance >= 8
        new_meta["is_future_catalyst"] = is_future

        # If content has "(N/A) unknown:", clean it up with the real date
        new_content = content
        if "unknown:" in new_content:
            new_content = new_content.replace("unknown:", f"{date_found}:")

        update_payload = {
            "target_date": date_found,
            "metadata": new_meta,
            "content": new_content,
        }

        supabase.table("memories").update(update_payload).eq("id", row_id).execute()
        updated_count += 1
        logger.info(f"Updated Memory {row_id} -> target_date: {date_found}, is_future_catalyst: {is_future}")

    logger.info(f"Backfill complete. Updated {updated_count}/{len(rows)} records.")


if __name__ == "__main__":
    backfill_calendar_events()
