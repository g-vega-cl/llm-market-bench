"""Shared evaluation-window helper.

The auto-research loop evaluates the most recent complete Mon–Sun week. We
extract this here so the runner and the evaluator can't drift.
"""

from datetime import date, timedelta


def get_week_window(today: date | None = None) -> tuple[date, date]:
    """Return (week_start, week_end) for the most recent complete Mon–Sun week.

    If `today` is Sunday, that Sunday is the end of the window (the trading
    week just closed). Otherwise, walk back to the prior Sunday.
    """
    today = today or date.today()
    if today.weekday() == 6:  # Sunday
        week_end = today
    else:
        week_end = today - timedelta(days=today.weekday() + 1)
    week_start = week_end - timedelta(days=6)
    return week_start, week_end
