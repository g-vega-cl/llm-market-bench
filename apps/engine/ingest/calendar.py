"""Economic calendar ingestion pipeline.

This module fetches economic data from Trading Economics, parses it,
and uses DeepSeek to identify high-importance events for Horizon Watch.
"""

import re
import subprocess
from datetime import datetime

from bs4 import BeautifulSoup

from core.config import DEEPSEEK_FLASH_MODEL, logger
from core.db import get_supabase_client
from core.llm.clients import get_deepseek_client
from core.models import DecisionsResponse
from memory.store import add_memory


class CalendarPipeline:
    """Pipeline for fetching and processing economic calendar data."""

    def __init__(self):
        self.client = get_deepseek_client()
        self.sb_client = get_supabase_client()
        self.url = "https://tradingeconomics.com/calendar"

    def fetch_html(self) -> str:
        """Fetches HTML from Trading Economics using curl with a 60s timeout."""
        logger.info(f"Fetching calendar data from {self.url} using curl...")
        try:
            result = subprocess.run(
                ["curl", "-L", self.url],
                capture_output=True,
                text=True,
                check=True,
                timeout=60,
            )
            return result.stdout
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            logger.error(f"Failed to fetch calendar HTML: {e}")
            return ""

    def parse_events(self, html: str) -> list[dict]:
        """Parses event rows from the Trading Economics HTML."""
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        # The main calendar table has id="calendar"
        table = soup.find("table", {"id": "calendar"})
        if not table:
            logger.warning("Could not find table with id='calendar' in HTML.")
            return []

        events = []
        current_date = None

        # Iterate through all rows (including those in thead/tbody)
        rows = table.find_all("tr")
        for row in rows:
            # Check for date header - usually in a parent thead or a tr with a th
            header = row.find("th")
            if header and any(
                day in header.get_text()
                for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            ):
                date_text = header.get_text(strip=True)
                try:
                    # Clean up date text (extract the first 4 parts: "Wednesday September 02 2026")
                    if " " in date_text:
                        parts = date_text.split()
                        if len(parts) >= 4:
                            date_text = " ".join(parts[:4])

                    current_date = datetime.strptime(date_text, "%A %B %d %Y").date().isoformat()
                except (ValueError, IndexError):
                    continue
                continue

            # Event rows have 'data-event' attributes
            event_name_attr = row.get("data-event")
            if event_name_attr:
                # Critical: recursive=False avoids grabbing nested <td> inside the country table
                cells = row.find_all("td", recursive=False)
                if len(cells) < 6:
                    continue

                # Country extraction: check data attribute first, then fallback to cell text
                country = (row.get("data-country") or cells[1].get_text(strip=True)).title()

                # Event title: prefer cell text with reference period if present, fallback to attribute
                cell_event_text = cells[2].get_text(" ", strip=True) if len(cells) > 2 else ""
                event_title = cell_event_text if cell_event_text else event_name_attr.strip()

                if len(cells) >= 7:
                    actual = cells[3].get_text(strip=True)
                    previous = cells[4].get_text(strip=True)
                    consensus = cells[5].get_text(strip=True)
                    forecast = cells[6].get_text(strip=True)
                else:
                    # 6-cell fallback
                    actual = cells[3].get_text(strip=True)
                    previous = cells[4].get_text(strip=True)
                    consensus = ""
                    forecast = cells[5].get_text(strip=True)

                event_data = {
                    "date": current_date,
                    "time": cells[0].get_text(strip=True),
                    "country": country,
                    "event": event_title,
                    "actual": actual,
                    "previous": previous,
                    "consensus": consensus,
                    "forecast": forecast,
                }
                # Only add if we have a valid date
                if current_date:
                    events.append(event_data)

        return events

    async def run(self):
        """Executes the calendar ingestion pipeline."""
        logger.info("Starting Economic Calendar Ingestion...")

        html = self.fetch_html()
        events = self.parse_events(html)

        if not events:
            logger.warning("No events parsed from calendar.")
            return 0

        logger.info(f"Parsed {len(events)} events. Sending to DeepSeek for relevance analysis...")

        # DeepSeek to identify high-importance events
        events_text = "\n".join(
            [
                f"- [#{idx}] [{e.get('date', '')} {e.get('time', '')}] {e.get('country', 'Global')}: {e.get('event', '')} "
                f"(Actual: {e.get('actual', '')}, Forecast: {e.get('forecast', '')}, Previous: {e.get('previous', '')}, Consensus: {e.get('consensus', '')})"
                for idx, e in enumerate(events)
            ]
        )

        prompt = f"""Analyze the following economic calendar events and identify the most RELEVANT ones 
        (Importance Score >= 8) or those that match specific CALENDAR STRATEGIES.
        
        Focus on:
        1. Central Bank decisions (Fed, ECB, BoJ, etc.) - LABEL THESE AS "CENTRAL_BANK"
        2. Key inflation data (CPI, PCE) - LABEL THESE AS "INFLATION"
        3. Employment reports (NFP)
        4. GDP releases
        5. Geopolitical summits or major policy shifts.
        6. Major Market Holidays - LABEL THESE AS "HOLIDAY"

        STRATEGY MATCHING:
        - If an event is a Central Bank meeting, it aligns with 'Pre-ECB/Fed Drift'.
        - If an event is a major market holiday, it aligns with 'Pre-Holiday Effect'.
        - If an event occurs on the 1st, 15th, or last day of the month, highlight its 'Payday' or 'ToM' relevance.

        For each relevant event, provide a structured MacroEvent entry:
        - Set 'source_id' to the event ID tag (e.g., '[#12]' or '12').
        - Set 'is_future_catalyst' to true.
        - Set 'target_date' to the event's date (YYYY-MM-DD).
        - In the reasoning, explicitly mention if it aligns with a known calendar strategy.

        EVENTS:
        {events_text}
        """

        try:
            res = await self.client.chat.completions.create(
                model=DEEPSEEK_FLASH_MODEL,
                response_model=DecisionsResponse,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a macro-economic analyst for a hedge fund. Return structured JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
            )

            count = 0
            for event in res.macro_events:
                if event.importance_score < 8:
                    continue

                # 1. Deterministic Index Lookup via source_id
                source_event = None
                if event.source_id:
                    match = re.search(r"\d+", event.source_id)
                    if match:
                        idx = int(match.group(0))
                        if 0 <= idx < len(events):
                            source_event = events[idx]

                # 2. Fallback to fuzzy substring search if index lookup fails
                if not source_event:
                    for e in events:
                        if (
                            e["event"].lower() in event.event_name.lower()
                            or event.event_name.lower() in e["event"].lower()
                        ):
                            source_event = e
                            break

                # Resolve target_date deterministically
                target_date = event.target_date or (source_event["date"] if source_event else None) or event.expiry_date
                if target_date == "unknown" or not target_date:
                    target_date = source_event["date"] if source_event else None

                original_time = source_event["time"] if source_event and source_event.get("time") else "N/A"
                if original_time == "N/A" and event.source_id and ":" in event.source_id:
                    original_time = event.source_id

                country = getattr(event, "country", None) or (source_event["country"] if source_event else "Global")

                display_date = target_date if target_date else "unknown"
                memory_content = (
                    f"[CALENDAR EVENT] ({original_time}) {display_date}: {event.event_name}: {event.reasoning} | "
                    f"Impact: {event.impact} | Date: {display_date}"
                )

                success = add_memory(
                    content=memory_content,
                    memory_type="CALENDAR_EVENT",
                    target_date=target_date,
                    importance_score=event.importance_score,
                    metadata={
                        "is_calendar_event": True,
                        "is_future_catalyst": True,
                        "event_time": original_time,
                        "country": country,
                        "reach": "Global" if event.importance_score > 8 else "Regional",
                        "impact": event.impact,
                    },
                    check_similarity=True,  # Prevents semantic duplicates
                )
                if success:
                    count += 1

            logger.info(f"Calendar pipeline complete. Added {count} high-importance memories.")
            return count

        except Exception as e:
            logger.error(f"Calendar pipeline failed: {e}")
            return 0


async def run_calendar_pipeline():
    """Entry point for the calendar pipeline."""
    pipeline = CalendarPipeline()
    await pipeline.run()
