"""Triple Barrier Method and regime-conditional touch probabilities.

Based on:
- Marcos Lopez de Prado (2018): Advances in Financial Machine Learning (Triple Barrier Method)
- James D. Hamilton (1989): Markov-Switching models and regime conditioning
- Mark Kritzman et al. (2012): Regime shifts in asset allocation
"""

from typing import Any

from core.config import logger


def calculate_atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> list[float | None]:
    """Calculate Average True Range (ATR) chronologically."""
    n = len(closes)
    if n < period or len(highs) != n or len(lows) != n:
        return [None] * n

    true_ranges: list[float] = []
    for i in range(n):
        if i == 0:
            tr = highs[i] - lows[i]
        else:
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
        true_ranges.append(tr)

    atrs: list[float | None] = [None] * (period - 1)
    # First ATR is simple average
    first_atr = sum(true_ranges[:period]) / period
    atrs.append(first_atr)

    for i in range(period, n):
        prior = atrs[-1]
        if prior is None:
            atrs.append(first_atr)
        else:
            current_atr = (prior * (period - 1) + true_ranges[i]) / period
            atrs.append(current_atr)

    return atrs


def calculate_sma(values: list[float], period: int = 20) -> list[float | None]:
    """Calculate Simple Moving Average (SMA) chronologically."""
    n = len(values)
    smas: list[float | None] = [None] * (period - 1) if period > 1 else []
    for i in range(period - 1, n):
        window = values[i - period + 1 : i + 1]
        smas.append(sum(window) / period)
    return smas


def classify_market_regime(
    current_close: float,
    current_sma: float | None,
    prev_sma: float | None,
    current_atr_pct: float,
    historical_atr_pcts: list[float],
) -> dict[str, str]:
    """Classify current market state into trend and volatility regimes."""
    # Volatility classification
    if not historical_atr_pcts:
        vol_regime = "NORMAL_VOLATILITY"
    else:
        sorted_vols = sorted(historical_atr_pcts)
        n = len(sorted_vols)
        p33 = sorted_vols[max(0, int(n * 0.33))]
        p67 = sorted_vols[min(n - 1, int(n * 0.67))]

        if current_atr_pct >= p67:
            vol_regime = "HIGH_VOLATILITY"
        elif current_atr_pct <= p33:
            vol_regime = "LOW_VOLATILITY"
        else:
            vol_regime = "NORMAL_VOLATILITY"

    # Trend classification
    if current_sma is not None and prev_sma is not None:
        if current_close > current_sma and current_sma >= prev_sma:
            trend_regime = "BULLISH_TREND"
        elif current_close < current_sma and current_sma <= prev_sma:
            trend_regime = "BEARISH_TREND"
        else:
            trend_regime = "SIDEWAYS_CONSOLIDATION"
    else:
        trend_regime = "NEUTRAL"

    return {
        "trend": trend_regime,
        "volatility": vol_regime,
        "combined": f"{trend_regime} + {vol_regime}",
    }


def calculate_barrier_probabilities(
    bars: list[dict],
    target_pct: float | None = None,
    stop_pct: float | None = None,
    horizon_bars: int = 5,
    lookback_days: int = 252,
    friction_bps: float = 10.0,
) -> dict[str, Any]:
    """Simulate Triple Barrier hitting frequencies conditional on the prevailing regime."""
    if not bars or len(bars) < 30:
        return {"error": "Insufficient historical bar data for barrier calculation"}

    # Take lookback slice
    window_bars = bars[-lookback_days:] if len(bars) > lookback_days else bars
    n = len(window_bars)

    closes = [float(b.get("close") or b.get("price") or 0.0) for b in window_bars]
    highs = [float(b.get("high") or b.get("close") or b.get("price") or 0.0) for b in window_bars]
    lows = [float(b.get("low") or b.get("close") or b.get("price") or 0.0) for b in window_bars]

    atrs = calculate_atr(highs, lows, closes, period=14)
    smas = calculate_sma(closes, period=20)

    # Calculate historical ATR percentages for volatility regime terciles
    atr_pcts: list[float] = []
    for i in range(n):
        atr_val = atrs[i]
        if atr_val is not None and closes[i] > 0:
            atr_pcts.append((atr_val / closes[i]) * 100.0)

    current_atr_pct = atr_pcts[-1] if atr_pcts else 1.5
    current_close = closes[-1]
    current_sma = smas[-1]
    prev_sma = smas[-2] if len(smas) >= 2 else current_sma

    current_regime = classify_market_regime(
        current_close=current_close,
        current_sma=current_sma,
        prev_sma=prev_sma,
        current_atr_pct=current_atr_pct,
        historical_atr_pcts=atr_pcts,
    )

    # Dynamic scaling if parameters omitted
    if target_pct is None or target_pct <= 0:
        target_pct = round(max(0.5, 1.5 * current_atr_pct), 2)
    if stop_pct is None or stop_pct <= 0:
        stop_pct = round(max(0.4, 1.0 * current_atr_pct), 2)

    upper_multiplier = 1.0 + (target_pct / 100.0)
    lower_multiplier = 1.0 - (stop_pct / 100.0)

    sample_count = 0
    upper_hit_count = 0
    lower_hit_count = 0
    vertical_exit_count = 0

    bars_to_upper: list[int] = []
    bars_to_lower: list[int] = []
    vertical_returns: list[float] = []

    # Evaluate paths across historical days
    eval_limit = n - horizon_bars
    for i in range(20, eval_limit):
        hist_atr_pct = atr_pcts[i] if i < len(atr_pcts) else current_atr_pct
        hist_regime = classify_market_regime(
            current_close=closes[i],
            current_sma=smas[i],
            prev_sma=smas[i - 1] if i > 0 else smas[i],
            current_atr_pct=hist_atr_pct,
            historical_atr_pcts=atr_pcts[: i + 1],
        )

        # Match regime
        if hist_regime["trend"] != current_regime["trend"]:
            continue

        sample_count += 1
        entry_price = closes[i]
        upper_barrier = entry_price * upper_multiplier
        lower_barrier = entry_price * lower_multiplier

        barrier_hit = None
        for step in range(1, horizon_bars + 1):
            bar_idx = i + step
            h = highs[bar_idx]
            low_val = lows[bar_idx]

            hit_upper = h >= upper_barrier
            hit_lower = low_val <= lower_barrier

            if hit_upper and hit_lower:
                # Conservative quant convention: count as stop loss hit
                barrier_hit = "LOWER"
                bars_to_lower.append(step)
                break
            elif hit_upper:
                barrier_hit = "UPPER"
                bars_to_upper.append(step)
                break
            elif hit_lower:
                barrier_hit = "LOWER"
                bars_to_lower.append(step)
                break

        if barrier_hit == "UPPER":
            upper_hit_count += 1
        elif barrier_hit == "LOWER":
            lower_hit_count += 1
        else:
            vertical_exit_count += 1
            exit_price = closes[i + horizon_bars]
            ret = ((exit_price - entry_price) / entry_price) * 100.0
            vertical_returns.append(ret)

    # Fallback to entire sample if regime matches were scarce
    if sample_count < 5:
        sample_count = 0
        upper_hit_count = 0
        lower_hit_count = 0
        vertical_exit_count = 0
        bars_to_upper.clear()
        bars_to_lower.clear()
        vertical_returns.clear()

        for i in range(20, eval_limit):
            sample_count += 1
            entry_price = closes[i]
            upper_barrier = entry_price * upper_multiplier
            lower_barrier = entry_price * lower_multiplier

            barrier_hit = None
            for step in range(1, horizon_bars + 1):
                bar_idx = i + step
                h = highs[bar_idx]
                low_val = lows[bar_idx]

                hit_upper = h >= upper_barrier
                hit_lower = low_val <= lower_barrier

                if hit_upper and hit_lower:
                    barrier_hit = "LOWER"
                    bars_to_lower.append(step)
                    break
                elif hit_upper:
                    barrier_hit = "UPPER"
                    bars_to_upper.append(step)
                    break
                elif hit_lower:
                    barrier_hit = "LOWER"
                    bars_to_lower.append(step)
                    break

            if barrier_hit == "UPPER":
                upper_hit_count += 1
            elif barrier_hit == "LOWER":
                lower_hit_count += 1
            else:
                vertical_exit_count += 1
                exit_price = closes[i + horizon_bars]
                ret = ((exit_price - entry_price) / entry_price) * 100.0
                vertical_returns.append(ret)

    upper_pct = round((upper_hit_count / sample_count) * 100.0, 1) if sample_count > 0 else 0.0
    lower_pct = round((lower_hit_count / sample_count) * 100.0, 1) if sample_count > 0 else 0.0
    vertical_pct = round((vertical_exit_count / sample_count) * 100.0, 1) if sample_count > 0 else 0.0

    avg_bars_upper = round(sum(bars_to_upper) / len(bars_to_upper), 1) if bars_to_upper else 0.0
    avg_bars_lower = round(sum(bars_to_lower) / len(bars_to_lower), 1) if bars_to_lower else 0.0
    avg_vertical_ret = round(sum(vertical_returns) / len(vertical_returns), 2) if vertical_returns else 0.0

    friction_pct = friction_bps / 100.0
    expected_value = (
        (upper_pct / 100.0) * target_pct
        - (lower_pct / 100.0) * stop_pct
        + (vertical_pct / 100.0) * avg_vertical_ret
        - friction_pct
    )
    expected_value_pct = round(expected_value, 2)

    # Strategy verdict
    if expected_value_pct > 0.25 and upper_pct >= 48.0:
        verdict = "FAVORABLE_LONG"
    elif expected_value_pct < -0.25 and lower_pct >= 48.0:
        verdict = "FAVORABLE_SHORT"
    elif vertical_pct >= 50.0:
        verdict = "RANGE_BOUND_NO_TOUCH"
    else:
        verdict = "UNFAVORABLE_ASYMMETRY"

    return {
        "current_price": round(current_close, 2),
        "current_atr_pct": round(current_atr_pct, 2),
        "current_regime": current_regime,
        "target_pct": target_pct,
        "stop_pct": stop_pct,
        "horizon_bars": horizon_bars,
        "sample_count": sample_count,
        "upper_hit_count": upper_hit_count,
        "upper_hit_pct": upper_pct,
        "lower_hit_count": lower_hit_count,
        "lower_hit_pct": lower_pct,
        "vertical_exit_count": vertical_exit_count,
        "vertical_exit_pct": vertical_pct,
        "avg_bars_to_upper": avg_bars_upper,
        "avg_bars_to_lower": avg_bars_lower,
        "avg_return_on_vertical_pct": avg_vertical_ret,
        "friction_bps": friction_bps,
        "expected_value_pct": expected_value_pct,
        "verdict": verdict,
    }


def format_barrier_report_markdown(data: dict[str, Any]) -> str:
    """Format barrier analysis into structured Markdown."""
    ticker = data.get("ticker", "ASSET")
    price = data.get("current_price", 0.0)
    regime = data.get("current_regime", {})
    target = data.get("target_pct", 0.0)
    stop = data.get("stop_pct", 0.0)
    horizon = data.get("horizon_bars", 5)
    samples = data.get("sample_count", 0)
    upper_pct = data.get("upper_hit_pct", 0.0)
    lower_pct = data.get("lower_hit_pct", 0.0)
    vert_pct = data.get("vertical_exit_pct", 0.0)
    ev = data.get("expected_value_pct", 0.0)
    verdict = data.get("verdict", "UNKNOWN")
    avg_vert = data.get("avg_return_on_vertical_pct", 0.0)

    return (
        f"### Triple Barrier Touch Probabilities: {ticker}\n\n"
        f"- **Current Price**: `${price:.2f}`\n"
        f"- **Current Regime**: `{regime.get('combined', 'UNKNOWN')}`\n"
        f"- **Barriers Tested**: Target `+{target:.1f}%`, Stop `-{stop:.1f}%`, Time Horizon `{horizon}` candles\n"
        f"- **Matched Samples**: `{samples}` regime occurrences\n\n"
        f"| Barrier Type | Outcome | Frequency | Percent | Avg Bars to Touch |\n"
        f"| :--- | :--- | :--- | :--- | :--- |\n"
        f"| Upper Barrier | Take Profit (+{target:.1f}%) | {data.get('upper_hit_count', 0)} | **{upper_pct:.1f}%** | {data.get('avg_bars_to_upper', 0.0)} |\n"
        f"| Lower Barrier | Stop Loss (-{stop:.1f}%) | {data.get('lower_hit_count', 0)} | **{lower_pct:.1f}%** | {data.get('avg_bars_to_lower', 0.0)} |\n"
        f"| Vertical Barrier | Time Stop (Expiry) | {data.get('vertical_exit_count', 0)} | **{vert_pct:.1f}%** | Avg return: {avg_vert:+.2f}% |\n\n"
        f"- **Expected Value (after 10 bps friction)**: `{ev:+.2f}%`\n"
        f"- **Statistical Strategy Verdict**: **`{verdict}`**\n\n"
        f"*Reference: López de Prado (2018) Triple Barrier Method, Hamilton (1989) Regime Shifts.*"
    )


async def get_barrier_touch_probabilities_report(
    ticker: str,
    target_pct: float | None = None,
    stop_pct: float | None = None,
    horizon_bars: int = 5,
    lookback_days: int = 252,
) -> dict[str, Any]:
    """Pull historical price data and compute empirical regime barrier touch probabilities."""
    from execution.market_data import MarketDataManager

    ticker = ticker.upper().strip()
    mdm = MarketDataManager()

    try:
        # Pull extra days to allow moving averages and ATR warm-up
        fetch_days = min(1000, max(120, lookback_days + 60))
        bars = await mdm.get_history(ticker, days=fetch_days)
        if not bars:
            return {"error": f"No historical price data available for {ticker}"}

        # Providers return newest first, reverse to chronological
        chronological_bars = list(reversed(bars))
        report = calculate_barrier_probabilities(
            chronological_bars,
            target_pct=target_pct,
            stop_pct=stop_pct,
            horizon_bars=horizon_bars,
            lookback_days=lookback_days,
        )
        if "error" in report:
            return report

        report["ticker"] = ticker
        report["markdown"] = format_barrier_report_markdown(report)
        return report
    except Exception as e:
        logger.exception("Error calculating barrier touch probabilities for %s: %s", ticker, e)
        return {"error": f"Failed calculating barrier touch probabilities: {e}"}
