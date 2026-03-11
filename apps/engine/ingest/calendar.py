"""Economic calendar ingestion pipeline.

This module fetches economic data from Trading Economics, parses it,
and uses DeepSeek to identify high-importance events for Horizon Watch.
"""

import subprocess
import logging
from datetime import datetime, timezone
from typing import List, Optional
from bs4 import BeautifulSoup

from core.db import get_supabase_client
from core.llm.clients import get_deepseek_client
from core.config import DEEPSEEK_MODEL, logger
from core.models import MacroEvent, DecisionsResponse
from memory.store import add_memory

class CalendarPipeline:
    """Pipeline for fetching and processing economic calendar data."""

    def __init__(self):
        self.client = get_deepseek_client()
        self.sb_client = get_supabase_client()
        self.url = "https://tradingeconomics.com/calendar"

    def fetch_html(self) -> str:
        """Fetches HTML from Trading Economics using curl."""
        logger.info(f"Fetching calendar data from {self.url} using curl...")
        try:
            result = subprocess.run(
                ["curl", "-L", self.url],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to fetch calendar HTML: {e}")
            return ""

    def parse_events(self, html: str) -> List[dict]:
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
            if header and any(day in header.get_text() for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]):
                date_text = header.get_text(strip=True)
                # Remove any extra text like "Actual Previous Consensus Forecast" if it's in the same header
                # We only want the date part which is usually at the start.
                # Trading Economics usually has just the date in that specific <th>.
                try:
                    # Clean up date text (sometimes it has extra whitespace or text)
                    if " " in date_text:
                        # Extract the first 4 parts: "Wednesday March 11 2026"
                        parts = date_text.split()
                        if len(parts) >= 4:
                            date_text = " ".join(parts[:4])
                    
                    current_date = datetime.strptime(date_text, "%A %B %d %Y").date().isoformat()
                except (ValueError, IndexError):
                    continue
                continue

            # Event rows have 'data-event' attributes
            event_name = row.get("data-event")
            if event_name:
                cells = row.find_all("td")
                if len(cells) < 6:
                    continue

                event_data = {
                    "date": current_date,
                    "time": cells[0].get_text(strip=True),
                    "country": row.get("data-country", cells[1].get_text(strip=True)).title(),
                    "event": event_name.strip(),
                    "actual": cells[3].get_text(strip=True),
                    "previous": cells[4].get_text(strip=True),
                    "forecast": cells[5].get_text(strip=True),
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
        # We'll batch the events to stay within context limits if needed, 
        # but for a weekly calendar it should fit.
        events_text = "\n".join([
            f"- [{e['date']} {e['time']}] {e['country']}: {e['event']} (Forecast: {e['forecast']}, Previous: {e['previous']})"
            for e in events
        ])

        prompt = f"""Analyze the following economic calendar events and identify the most RELEVANT ones 
        (Importance Score >= 8) that could significantly impact global financial markets.
        
        Focus on:
        1. Central Bank decisions (Fed, ECB, BoJ, etc.)
        2. Key inflation data (CPI, PCE)
        3. Employment reports (NFP)
        4. GDP releases
        5. Geopolitical summits or major policy shifts.

        For each relevant event, provide a structured MacroEvent entry.
        IMPORTANT: Set 'is_future_catalyst' to true and 'target_date' to the event's date (YYYY-MM-DD).

        EVENTS:
        {events_text}
        """

        try:
            res = await self.client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                response_model=DecisionsResponse,
                messages=[
                    {"role": "system", "content": "You are a macro-economic analyst for a hedge fund. Return structured JSON."},
                    {"role": "user", "content": prompt}
                ]
            )

            count = 0
            for event in res.macro_events:
                if event.importance_score < 8:
                    continue

                # Map relevant date back - DeepSeek should have put it in target_date or similar
                # We'll use event.expiry_date as a proxy if it's set, or the date we parsed
                target_date = event.expiry_date if event.expiry_date else None

                # Content for memory
                event_time = getattr(event, "time", "N/A") # DeepSeek might have it or we follow the text
                
                # Check if we can find the original time from our parsed events
                # Matches by fuzzy event name and date
                original_time = "N/A"
                for e in events:
                    if e["date"] == target_date:
                        # Fuzzy match: one is contained in the other
                        if (e["event"].lower() in event.event_name.lower() or 
                            event.event_name.lower() in e["event"].lower()):
                            original_time = e["time"]
                            break
                
                if original_time == "N/A":
                    # Fallback to source_id if it looks like a time or just use what we have
                    original_time = event.source_id if ":" in event.source_id else "N/A"

                memory_content = (
                    f"[CALENDAR EVENT] ({original_time}) {event.event_name}: {event.reasoning} | "
                    f"Impact: {event.impact} | Date: {event.expiry_date or event.source_id}"
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
                        "country": getattr(event, "country", "Global"),
                        "reach": "Global" if event.importance_score > 8 else "Regional",
                        "impact": event.impact
                    },
                    check_similarity=True # Prevents semantic duplicates
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
