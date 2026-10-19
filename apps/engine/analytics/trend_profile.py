"""Point-in-Time Trend & Multi-Day Momentum Profile Module.

Calculates multi-day technical trend features (5-day return, 20-day SMA, 3-day direction sequence)
strictly from verified historical prices with zero lookahead and zero hallucination.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TrendProfile:
    is_available: bool = False
    prior_date: str | None = None
    prior_close: float | None = None
    return_5d_pct: float | None = None
    sma_20: float | None = None
    sma_20_dist_pct: float | None = None
    sequence_3d: str | None = None
    bars_used: int = 0
    summary_lines: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        return "\n".join(self.summary_lines)

    def as_dict(self) -> dict[str, Any]:
        return {
            "is_available": self.is_available,
            "prior_date": self.prior_date,
            "prior_close": self.prior_close,
            "return_5d_pct": self.return_5d_pct,
            "sma_20": self.sma_20,
            "sma_20_dist_pct": self.sma_20_dist_pct,
            "sequence_3d": self.sequence_3d,
            "bars_used": self.bars_used,
            "summary": self.summary,
        }


def compute_trend_profile(
    history: list[dict[str, Any]] | None,
    target_date: str | None = None,
) -> TrendProfile:
    """Compute point-in-time trend indicators strictly prior to target_date (zero lookahead).

    Guarantees:
    - Zero lookahead: Excludes any bar with date >= target_date.
    - Zero hallucination: If fewer than 20 bars exist, sma_20 is strictly None.
      If fewer than 5 bars exist, return_5d_pct is strictly None.
    """
    if not history:
        return TrendProfile(is_available=False)

    valid_bars: list[dict[str, Any]] = []
    for row in history:
        try:
            price_val = row.get("price")
            if price_val is None:
                continue
            price = float(price_val)
            fetched_at = str(row.get("fetched_at", ""))
            if not fetched_at:
                continue

            # Zero lookahead filter: strictly prior to target_date
            bar_date = fetched_at[:10]
            if target_date and bar_date >= target_date[:10]:
                continue

            valid_bars.append(
                {
                    "price": price,
                    "open": float(row.get("open", price)) if row.get("open") is not None else price,
                    "close": float(row.get("close", price)) if row.get("close") is not None else price,
                    "date": bar_date,
                    "fetched_at": fetched_at,
                }
            )
        except (ValueError, TypeError):
            continue

    if len(valid_bars) < 2:
        return TrendProfile(is_available=False)

    # Sort chronologically (oldest to newest)
    sorted_hist = sorted(valid_bars, key=lambda x: str(x.get("fetched_at", "")))

    prior_row = sorted_hist[-1]
    prior_date = str(prior_row["date"])
    prior_close = float(prior_row["price"])
    close_prices = [float(r["price"]) for r in sorted_hist]

    summary_lines: list[str] = [f"Previous Trading Session ({prior_date}) Close: ${prior_close:.2f}"]

    # 1. 5-Day Return %
    return_5d_pct: float | None = None
    if len(close_prices) >= 6:
        base_5d = close_prices[-6]
        if base_5d > 0:
            return_5d_pct = ((prior_close - base_5d) / base_5d) * 100.0
    elif len(close_prices) >= 5:
        base_5d = close_prices[-5]
        if base_5d > 0:
            return_5d_pct = ((prior_close - base_5d) / base_5d) * 100.0

    if return_5d_pct is not None:
        summary_lines.append(f"5-Day Return: {return_5d_pct:+.2f}%")

    # 2. 20-Day SMA & Distance % (Strictly requires >= 20 bars, NO hallucination)
    sma_20: float | None = None
    sma_20_dist_pct: float | None = None
    if len(close_prices) >= 20:
        recent_20 = close_prices[-20:]
        sma_20 = sum(recent_20) / 20.0
        if sma_20 > 0:
            sma_20_dist_pct = ((prior_close - sma_20) / sma_20) * 100.0
            summary_lines.append(
                f"20-Day Simple Moving Average (SMA20): ${sma_20:.2f} (Distance: {sma_20_dist_pct:+.2f}%)"
            )
        else:
            summary_lines.append(f"20-Day Simple Moving Average (SMA20): ${sma_20:.2f}")

    # 3. 3-Day Direction Sequence
    sequence_3d: str | None = None
    if len(sorted_hist) >= 3:
        recent_3 = sorted_hist[-3:]
        seq_parts: list[str] = []
        for r in recent_3:
            d_date = r["date"]
            d_open = float(r.get("open", r["price"]))
            d_close = float(r.get("close", r["price"]))
            chg = ((d_close - d_open) / d_open * 100.0) if d_open > 0 else 0.0
            direction = "UP" if d_close >= d_open else "DOWN"
            seq_parts.append(f"{d_date}: {direction} ({chg:+.2f}%)")
        sequence_3d = " -> ".join(seq_parts)
        summary_lines.append(f"3-Day Direction Sequence: {sequence_3d}")

    return TrendProfile(
        is_available=True,
        prior_date=prior_date,
        prior_close=prior_close,
        return_5d_pct=return_5d_pct,
        sma_20=sma_20,
        sma_20_dist_pct=sma_20_dist_pct,
        sequence_3d=sequence_3d,
        bars_used=len(sorted_hist),
        summary_lines=summary_lines,
    )
