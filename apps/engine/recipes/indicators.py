"""Technical indicators and condition evaluation for Strategy Recipes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from recipes.schema import ConditionRule


@dataclass
class Bar:
    time_utc: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    ticker: str = "SPY"
    vwap: float | None = None
    rsi_14: float | None = None
    sma_20: float | None = None
    sma_50: float | None = None
    rvol: float | None = None


def compute_bar_indicators(bars: list[Bar]) -> list[Bar]:
    """Compute moving averages, RSI-14, intraday VWAP, and RVOL on a list of sorted bars."""
    if not bars:
        return []

    # Sort chronologically
    sorted_bars = sorted(bars, key=lambda b: b.time_utc)
    closes = [b.close for b in sorted_bars]
    volumes = [b.volume for b in sorted_bars]
    n = len(sorted_bars)

    # 1. SMAs
    for i in range(n):
        if i >= 19:
            sorted_bars[i].sma_20 = round(sum(closes[i - 19 : i + 1]) / 20.0, 4)
        if i >= 49:
            sorted_bars[i].sma_50 = round(sum(closes[i - 49 : i + 1]) / 50.0, 4)
        if i >= 19:
            avg_vol = sum(volumes[i - 19 : i + 1]) / 20.0
            sorted_bars[i].rvol = round(sorted_bars[i].volume / avg_vol, 2) if avg_vol > 0 else 1.0
        else:
            sorted_bars[i].rvol = 1.0

    # 2. RSI-14 (standard Wilder's smoothing)
    if n >= 15:
        deltas = [closes[i] - closes[i - 1] for i in range(1, n)]
        gains = [max(d, 0.0) for d in deltas]
        losses = [max(-d, 0.0) for d in deltas]

        # First average gain/loss over 14 bars
        avg_gain = sum(gains[:14]) / 14.0
        avg_loss = sum(losses[:14]) / 14.0

        if avg_loss == 0:
            sorted_bars[14].rsi_14 = 100.0
        else:
            rs = avg_gain / avg_loss
            sorted_bars[14].rsi_14 = round(100.0 - (100.0 / (1.0 + rs)), 2)

        for i in range(15, n):
            gain = gains[i - 1]
            loss = losses[i - 1]
            avg_gain = (avg_gain * 13.0 + gain) / 14.0
            avg_loss = (avg_loss * 13.0 + loss) / 14.0
            if avg_loss == 0:
                sorted_bars[i].rsi_14 = 100.0
            else:
                rs = avg_gain / avg_loss
                sorted_bars[i].rsi_14 = round(100.0 - (100.0 / (1.0 + rs)), 2)

    # 3. Cumulative VWAP (reset per trading day)
    current_day = None
    cum_vol_price = 0.0
    cum_vol = 0
    for b in sorted_bars:
        bar_day = b.time_utc.date()
        if bar_day != current_day:
            current_day = bar_day
            cum_vol_price = 0.0
            cum_vol = 0
        typ_price = (b.high + b.low + b.close) / 3.0
        cum_vol_price += typ_price * b.volume
        cum_vol += b.volume
        b.vwap = round(cum_vol_price / cum_vol, 4) if cum_vol > 0 else b.close

    return sorted_bars


def get_bar_metric(bar: Bar, metric_name: str) -> float | None:
    """Extract named metric from bar."""
    name = metric_name.lower().strip()
    if name in ("price", "close"):
        return bar.close
    if name == "open":
        return bar.open
    if name == "high":
        return bar.high
    if name == "low":
        return bar.low
    if name == "volume":
        return float(bar.volume)
    if name in ("rsi", "rsi_14"):
        return bar.rsi_14
    if name in ("vwap", "bar_vwap"):
        return bar.vwap
    if name in ("sma_20", "sma20"):
        return bar.sma_20
    if name in ("sma_50", "sma50"):
        return bar.sma_50
    if name in ("rvol", "relative_volume"):
        return bar.rvol
    return None


def evaluate_condition(rule: ConditionRule, bar: Bar) -> tuple[bool, str]:
    """Evaluate a single ConditionRule against a bar.

    Returns (passed, explanation).
    """
    val = get_bar_metric(bar, rule.metric)
    if val is None:
        return False, f"Metric '{rule.metric}' not available yet on bar at {bar.time_utc.isoformat()}"

    target_val: float | None = None
    if isinstance(rule.target, (int, float)):
        target_val = float(rule.target)
    else:
        # Check if target is a metric name (e.g. 'vwap', 'sma_20')
        target_metric_val = get_bar_metric(bar, str(rule.target))
        if target_metric_val is not None:
            target_val = target_metric_val
        else:
            try:
                target_val = float(str(rule.target).strip())
            except ValueError:
                return False, f"Invalid condition target '{rule.target}'"

    op = rule.operator
    passed = False
    if op == ">":
        passed = val > target_val
    elif op == "<":
        passed = val < target_val
    elif op == ">=":
        passed = val >= target_val
    elif op == "<=":
        passed = val <= target_val
    elif op == "==":
        passed = abs(val - target_val) < 1e-6

    explanation = f"{rule.metric} ({val}) {op} {rule.target} ({target_val}) -> {'PASS' if passed else 'FAIL'}"
    return passed, explanation


def evaluate_technical_gate(conditions: list[ConditionRule], bar: Bar) -> tuple[bool, list[str]]:
    """Evaluate all conditions in a technical gate. Must pass all conditions (AND)."""
    if not conditions:
        return True, ["No conditions specified (PASS)"]

    reasons: list[str] = []
    for cond in conditions:
        passed, explanation = evaluate_condition(cond, bar)
        reasons.append(explanation)
        if not passed:
            return False, reasons

    return True, reasons
