"""Deterministic Intraday Movement Profile and Hourly Tape Matrix.

Decomposes regular trading hours (09:30 to 16:00 ET) price action into
quantitative market profile metrics, Close Location Value (CLV), Initial Balance (IB),
session archetypes, and an ultra-dense hourly tape matrix without consuming LLM tokens.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from core.config import logger


def filter_regular_trading_hours(bars: list[dict]) -> list[dict]:
    """Filter hourly/intraday bars strictly to Regular Trading Hours (09:30:00 to 16:00:00 ET)."""
    if not bars:
        return []

    rth_bars = []
    for b in bars:
        bar_date = b.get("date", "") if isinstance(b, dict) else getattr(b, "date", "")
        time_part = bar_date.split(" ")[1] if " " in bar_date else ""
        if "09:30:00" <= time_part <= "16:00:00":
            rth_bars.append(b)

    def _get_dt(b):
        return b.get("date", "") if isinstance(b, dict) else getattr(b, "date", "")

    return sorted(rth_bars, key=_get_dt)


def _get_float(bar: dict, key: str) -> float:
    return float(bar[key]) if isinstance(bar, dict) else float(getattr(bar, key))


def _get_int(bar: dict, key: str) -> int:
    val = bar.get(key, 0) if isinstance(bar, dict) else getattr(bar, key, 0)
    return int(val) if val is not None else 0


def calculate_intraday_metrics(rth_bars: list[dict]) -> dict[str, Any] | None:
    """Calculate quantitative session profile metrics and classify session archetype.

    Archetypes:
    - TREND_DAY_UP: Sustained bull momentum, high IB extension, close near session high (CLV > 0.6).
    - TREND_DAY_DOWN: Sustained bear momentum, low IB extension, close near session low (CLV < -0.6).
    - MORNING_DIP_AND_RIP: Early selloff below open/IB low, followed by strong reclaim closing green.
    - GAP_AND_CRAP: Early surge above open/IB high, followed by rollover closing red.
    - RANGE_BOUND_CHURN: Tight range within or near Initial Balance, close near midpoint.
    """
    if not rth_bars:
        return None

    open_p = _get_float(rth_bars[0], "open")
    close_p = _get_float(rth_bars[-1], "close")
    high_p = max(_get_float(b, "high") for b in rth_bars)
    low_p = min(_get_float(b, "low") for b in rth_bars)
    session_range = high_p - low_p

    intraday_return_pct = ((close_p - open_p) / open_p) * 100.0 if open_p > 0 else 0.0
    range_pct = (session_range / open_p) * 100.0 if open_p > 0 else 0.0

    # Close Location Value (CLV) in [-1.0, +1.0]
    clv = round(((close_p - low_p) - (high_p - close_p)) / session_range, 3) if session_range > 0 else 0.0

    # Volume-Weighted Average Price (VWAP)
    total_vol = sum(_get_int(b, "volume") for b in rth_bars)
    if total_vol > 0:
        sum_pv = sum(
            ((_get_float(b, "high") + _get_float(b, "low") + _get_float(b, "close")) / 3.0) * _get_int(b, "volume")
            for b in rth_bars
        )
        vwap = round(sum_pv / total_vol, 2)
    else:
        vwap = round(
            sum((_get_float(b, "high") + _get_float(b, "low") + _get_float(b, "close")) / 3.0 for b in rth_bars)
            / len(rth_bars),
            2,
        )

    # Initial Balance (IB: first 60 mins of regular trading hours, 09:30:00 to 10:30:00 ET)
    ib_bars = []
    for b in rth_bars:
        d_str = str(b.get("date", ""))
        t_part = d_str.split(" ")[1] if " " in d_str else ""
        if "09:30:00" <= t_part < "10:30:00":
            ib_bars.append(b)

    if not ib_bars:
        ib_bars = rth_bars[:1]

    ib_high = max(_get_float(b, "high") for b in ib_bars)
    ib_low = min(_get_float(b, "low") for b in ib_bars)

    broke_high = high_p > ib_high + 0.01
    broke_low = low_p < ib_low - 0.01

    if broke_high and broke_low:
        ib_broken = "BOTH"
    elif broke_high:
        ib_broken = "HIGH"
    elif broke_low:
        ib_broken = "LOW"
    else:
        ib_broken = "NONE"

    # Identify morning excursion vs afternoon direction
    morning_low_flush = (open_p - low_p) / open_p > 0.003
    morning_high_pop = (high_p - open_p) / open_p > 0.003

    # Archetype Classification
    if close_p > open_p and clv >= 0.5:
        if morning_low_flush and (ib_broken in ("BOTH", "HIGH") or low_p == _get_float(rth_bars[0], "low")):
            archetype = "MORNING_DIP_AND_RIP"
        elif broke_high:
            archetype = "TREND_DAY_UP"
        else:
            archetype = "TREND_DAY_UP"
    elif close_p < open_p and clv <= -0.5:
        if morning_high_pop and (ib_broken in ("BOTH", "LOW") or high_p == _get_float(rth_bars[0], "high")):
            archetype = "GAP_AND_CRAP"
        elif broke_low:
            archetype = "TREND_DAY_DOWN"
        else:
            archetype = "TREND_DAY_DOWN"
    elif ib_broken == "NONE" or (abs(intraday_return_pct) < 0.25 and abs(clv) < 0.4):
        archetype = "RANGE_BOUND_CHURN"
    elif close_p >= open_p:
        archetype = "MORNING_DIP_AND_RIP" if morning_low_flush else "RANGE_BOUND_CHURN"
    else:
        archetype = "GAP_AND_CRAP" if morning_high_pop else "RANGE_BOUND_CHURN"

    return {
        "open": round(open_p, 2),
        "high": round(high_p, 2),
        "low": round(low_p, 2),
        "close": round(close_p, 2),
        "range": round(session_range, 2),
        "range_pct": round(range_pct, 2),
        "intraday_return_pct": round(intraday_return_pct, 2),
        "clv": clv,
        "vwap": vwap,
        "ib_high": round(ib_high, 2),
        "ib_low": round(ib_low, 2),
        "ib_broken": ib_broken,
        "archetype": archetype,
        "bar_count": len(rth_bars),
    }


def _render_ascii_range_map(open_p: float, high_p: float, low_p: float, close_p: float) -> str:
    """Render a 10-slot visual ASCII bracket [L...O...C...H]."""
    rng = high_p - low_p
    if rng <= 0:
        return "[L====C====H]"

    slots = ["-"] * 8
    o_idx = min(7, max(0, int(((open_p - low_p) / rng) * 7.99)))
    c_idx = min(7, max(0, int(((close_p - low_p) / rng) * 7.99)))

    if o_idx == c_idx:
        slots[o_idx] = "="
    else:
        slots[o_idx] = "O"
        slots[c_idx] = "C"

    return f"[L{''.join(slots)}H]"


def build_hourly_tape_matrix(rth_bars: list[dict]) -> str:
    """Build a synchronized hourly progression table with ASCII range brackets."""
    if not rth_bars:
        return "No regular trading hours bar data available."

    lines = [
        "Time (ET) | Open -> Close       | Hourly Chg | Volume (M) | Range Map",
        "----------|---------------------|------------|------------|-----------",
    ]

    for b in rth_bars:
        date_str = str(b.get("date", ""))
        time_part = date_str.split(" ")[1][:5] if " " in date_str else date_str[:5]
        op = _get_float(b, "open")
        hp = _get_float(b, "high")
        lp = _get_float(b, "low")
        cp = _get_float(b, "close")
        vol = _get_int(b, "volume")

        chg_pct = ((cp - op) / op) * 100.0 if op > 0 else 0.0
        vol_m = vol / 1_000_000.0
        ascii_map = _render_ascii_range_map(op, hp, lp, cp)

        lines.append(f"{time_part:<9} | ${op:6.2f} -> ${cp:6.2f} | {chg_pct:+9.2f}% | {vol_m:9.1f}M | {ascii_map}")

    return "\n".join(lines)


def format_intraday_movement_markdown(
    ticker: str,
    date_str: str,
    metrics: dict[str, Any],
    rth_bars: list[dict],
    include_hourly_tape: bool = True,
) -> str:
    """Format the quant session profile and hourly matrix into clean Markdown."""
    if not metrics:
        return f"No intraday price data available for {ticker} on {date_str}."

    dir_tag = "UP Day: Close > Open" if metrics["intraday_return_pct"] >= 0 else "DOWN Day: Close < Open"
    vwap_diff = ((metrics["close"] - metrics["vwap"]) / metrics["vwap"]) * 100.0 if metrics["vwap"] > 0 else 0.0

    lines = [
        f"=== {ticker.upper()} INTRADAY MOVEMENT PROFILE ({date_str}) ===",
        f"- Regular Trading Hours: Open ${metrics['open']:.2f} | High ${metrics['high']:.2f} | Low ${metrics['low']:.2f} | Close ${metrics['close']:.2f}",
        f"- True Intraday Return: {metrics['intraday_return_pct']:+.2f}% ({dir_tag})",
        f"- Session Range: ${metrics['range']:.2f} ({metrics['range_pct']:.2f}% of Open) | VWAP: ${metrics['vwap']:.2f} (Closed {vwap_diff:+.2f}% vs VWAP)",
        f"- Close Location Value (CLV): {metrics['clv']:+.2f} ({'Upper quartile close' if metrics['clv'] > 0.5 else 'Lower quartile close' if metrics['clv'] < -0.5 else 'Mid-range close'})",
        f"- Initial Balance (09:30-10:30 ET): ${metrics['ib_high']:.2f} - ${metrics['ib_low']:.2f} (IB Broken: {metrics['ib_broken']})",
        f"- Session Archetype: {metrics['archetype']}",
    ]

    if include_hourly_tape and rth_bars:
        lines.append("\n--- HOURLY TAPE MATRIX ---")
        lines.append(build_hourly_tape_matrix(rth_bars))

    return "\n".join(lines)


async def get_intraday_movement_report(
    ticker: str = "SPY",
    date_str: str = "latest_completed",
    include_hourly_tape: bool = True,
) -> dict[str, Any]:
    """Retrieve hourly bars, calculate session profile, and format markdown report."""
    from execution.market_data import MarketDataManager

    mdm = MarketDataManager()
    resolved_date = date_str

    if date_str in ("latest_completed", "yesterday", "today") or not date_str:
        today_date = datetime.now(UTC).date()
        resolved_date = (today_date - timedelta(days=1)).isoformat()
        try:
            history = await mdm.get_history(ticker, days=5)
            if history:
                sorted_hist = sorted(history, key=lambda x: str(x.get("fetched_at", "")))
                for entry in reversed(sorted_hist):
                    entry_date = str(entry.get("fetched_at", ""))[:10]
                    if entry_date <= today_date.isoformat():
                        resolved_date = entry_date
                        break
        except Exception as e:
            logger.debug(f"Could not resolve latest completed date from history for {ticker}: {e}")

    try:
        provider = mdm.provider
        bars = []
        if provider and hasattr(provider, "get_hourly_history"):
            bars = await provider.get_hourly_history(ticker, resolved_date, resolved_date)

        rth_bars = filter_regular_trading_hours(bars)
        metrics = calculate_intraday_metrics(rth_bars)

        if not metrics:
            return {
                "ticker": ticker.upper(),
                "date": resolved_date,
                "metrics": None,
                "markdown": f"No intraday hourly bar data available for {ticker} on {resolved_date}.",
            }

        md = format_intraday_movement_markdown(
            ticker=ticker,
            date_str=resolved_date,
            metrics=metrics,
            rth_bars=rth_bars,
            include_hourly_tape=include_hourly_tape,
        )

        return {
            "ticker": ticker.upper(),
            "date": resolved_date,
            "metrics": metrics,
            "markdown": md,
        }
    except Exception as e:
        logger.exception(f"Error generating intraday movement report for {ticker} on {resolved_date}: {e}")
        return {
            "ticker": ticker.upper(),
            "date": resolved_date,
            "metrics": None,
            "markdown": f"Error retrieving intraday movement for {ticker}: {str(e)}",
        }
