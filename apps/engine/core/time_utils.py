"""Centralized temporal and market session utilities.

Provides exact date, time, timezone, session phase, and forward horizon anchors
for trading analysis, predictors, and autonomous agents.
"""

import calendar
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

EASTERN_TZ = ZoneInfo("America/New_York")


def get_market_session_phase(dt: datetime) -> str:
    """Returns the US equity market session phase for a given datetime."""
    dt = dt.replace(tzinfo=EASTERN_TZ) if dt.tzinfo is None else dt.astimezone(EASTERN_TZ)

    # Check weekend
    if dt.weekday() >= 5:  # Saturday=5, Sunday=6
        return "Closed (Weekend)"

    t = dt.time()
    pre_market_start = time(4, 0)
    market_open = time(9, 30)
    market_close = time(16, 0)
    after_hours_end = time(20, 0)

    if pre_market_start <= t < market_open:
        return "Pre-Market (04:00 - 09:30 EDT)"
    elif market_open <= t < market_close:
        return "Regular Trading Hours (09:30 - 16:00 EDT)"
    elif market_close <= t < after_hours_end:
        return "Post-Market / After-Hours (16:00 - 20:00 EDT)"
    else:
        return "Closed (Overnight)"


def get_current_day_info(now: datetime | None = None) -> str:
    """Builds a rich, anchored date/time context string for LLM prompts."""
    if now is None:
        now = datetime.now(EASTERN_TZ)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=EASTERN_TZ)
    else:
        now = now.astimezone(EASTERN_TZ)

    now_utc = now.astimezone(UTC)
    session_phase = get_market_session_phase(now)

    date_str = now.strftime("%A, %B %d, %Y")
    time_str = now.strftime("%I:%M:%S %p")
    tz_str = now.strftime("%Z")
    utc_time_str = now_utc.strftime("%H:%M:%S")

    lines = [
        f"Today is {date_str}.",
        f"Exact Current Time: {time_str} {tz_str} ({utc_time_str} UTC).",
        f"Market Session: {session_phase}.",
    ]

    # Forward Horizon Anchors
    tomorrow = now + timedelta(days=1)
    lines.append(f"Tomorrow: {tomorrow.strftime('%A, %B %d, %Y')}.")

    # Next full business week (Monday to Friday)
    days_until_monday = (7 - now.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    next_monday = (now + timedelta(days=days_until_monday)).date()
    next_friday = next_monday + timedelta(days=4)
    lines.append(f"Next Week: {next_monday.strftime('%A, %B %d, %Y')} to {next_friday.strftime('%A, %B %d, %Y')}.")

    # Seasonal & Calendar Anomalies
    last_day = calendar.monthrange(now.year, now.month)[1]
    days_to_end = last_day - now.day
    if now.day in [1, 2, 3]:
        lines.append(f"Calendar Anomaly: Turn of the Month (ToM) window active (Day {now.day}).")
    elif days_to_end == 0:
        lines.append("Calendar Anomaly: Today is the LAST trading day of the month (ToM Start).")
    else:
        lines.append(f"Month-End Proximity: {days_to_end} calendar days until month-end.")

    if now.day == 15:
        lines.append("Calendar Anomaly: Today is mid-month payday anomaly (inflows expected).")
    elif now.day == 14:
        lines.append("Calendar Anomaly: Tomorrow is mid-month payday anomaly.")

    return "\n".join(lines)
