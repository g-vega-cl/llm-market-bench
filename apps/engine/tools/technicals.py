"""Technical indicators tool (RSI, MACD, VWAP, SMA, RVOL, 52-week range %)."""

from __future__ import annotations

from typing import Any

from core.config import logger
from execution.market_data import MarketDataManager


def _ema_series(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    k = 2.0 / (period + 1)
    result = [values[0]]
    for val in values[1:]:
        result.append(val * k + result[-1] * (1.0 - k))
    return result


def _compute_rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    recent = deltas[-period:]
    gains = [d for d in recent if d > 0]
    losses = [-d for d in recent if d < 0]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 2)


def compute_technical_snapshot(
    history: list[dict[str, Any]],
    cutoff_date: str | None = None,
) -> dict[str, Any]:
    """Compute technical indicators from MarketDataManager history rows."""
    filtered = history
    if cutoff_date:
        cutoff_day = cutoff_date[:10]
        filtered = [h for h in history if str(h.get("fetched_at", ""))[:10] <= cutoff_day]

    ordered = [
        r for r in sorted(filtered, key=lambda r: str(r.get("fetched_at", ""))) if r.get("price") is not None
    ]
    if not ordered:
        return {}

    closes = [float(r["price"]) for r in ordered]
    volumes = [float(r.get("volume") or 0.0) for r in ordered]

    latest_price = closes[-1]
    latest_date = str(ordered[-1].get("fetched_at", ""))

    sma_20 = round(sum(closes[-20:]) / len(closes[-20:]), 2) if len(closes) >= 20 else None
    sma_50 = round(sum(closes[-50:]) / len(closes[-50:]), 2) if len(closes) >= 50 else None
    rsi_14 = _compute_rsi(closes, 14)

    macd = macd_signal = macd_hist = None
    if len(closes) >= 26:
        ema12 = _ema_series(closes, 12)
        ema26 = _ema_series(closes, 26)
        macd_line = [a - b for a, b in zip(ema12, ema26, strict=False)]
        signal_line = _ema_series(macd_line, 9)
        macd = round(macd_line[-1], 4)
        macd_signal = round(signal_line[-1], 4)
        macd_hist = round(macd_line[-1] - signal_line[-1], 4)

    recent_closes = closes[-20:]
    recent_vols = volumes[-20:]
    total_vol = sum(recent_vols)
    vwap_20d = (
        round(sum(p * v for p, v in zip(recent_closes, recent_vols, strict=False)) / total_vol, 2)
        if total_vol > 0
        else round(sum(recent_closes) / len(recent_closes), 2)
    )

    avg_vol_20 = (sum(recent_vols[:-1]) / len(recent_vols[:-1])) if len(recent_vols) > 1 else 0.0
    rvol_20d = round(recent_vols[-1] / avg_vol_20, 2) if avg_vol_20 > 0 and recent_vols[-1] > 0 else None

    window_52w = closes[-252:]
    high_52w = max(window_52w)
    low_52w = min(window_52w)
    span = high_52w - low_52w
    price_52w_pct = round(((latest_price - low_52w) / span) * 100.0, 2) if span > 0 else 50.0
    pct_from_high = round(((latest_price - high_52w) / high_52w) * 100.0, 2) if high_52w > 0 else 0.0

    return {
        "latest_price": round(latest_price, 2),
        "latest_date": latest_date,
        "rsi_14": rsi_14,
        "macd": macd,
        "macd_signal": macd_signal,
        "macd_histogram": macd_hist,
        "sma_20": sma_20,
        "sma_50": sma_50,
        "vwap_20d": vwap_20d,
        "rvol_20d": rvol_20d,
        "high_52w": round(high_52w, 2),
        "low_52w": round(low_52w, 2),
        "price_52w_pct": price_52w_pct,
        "pct_from_52w_high": pct_from_high,
    }


async def execute_technical_indicators_tool(ticker: str, cutoff_date: str | None = None) -> str:
    """Fetch price history and return RSI, MACD, VWAP, SMAs, RVOL, and 52W range %."""
    clean_ticker = ticker.upper().strip()
    manager = MarketDataManager()
    try:
        history = await manager.get_history(clean_ticker, days=365)
        if not history:
            return f"No price history available for {clean_ticker}."

        snap = compute_technical_snapshot(history, cutoff_date=cutoff_date)
        if not snap:
            return f"No price history available for {clean_ticker} up to {cutoff_date}."

        cutoff_note = f" (cutoff: {cutoff_date})" if cutoff_date else ""
        lines = [
            f"Technical Indicators for {clean_ticker}{cutoff_note} as of {snap['latest_date'][:10]}:",
            f"- Price: ${snap['latest_price']:.2f}",
            f"- RSI (14): {snap['rsi_14'] if snap['rsi_14'] is not None else 'N/A'}",
            f"- MACD: {snap['macd']} | Signal: {snap['macd_signal']} | Hist: {snap['macd_histogram']}",
            f"- VWAP (20D): ${snap['vwap_20d']:.2f}",
            f"- SMA 20: {snap['sma_20'] if snap['sma_20'] is not None else 'N/A'} | SMA 50: {snap['sma_50'] if snap['sma_50'] is not None else 'N/A'}",
            f"- RVOL (20D): {snap['rvol_20d'] if snap['rvol_20d'] is not None else 'N/A'}x",
            f"- 52W Range Position: {snap['price_52w_pct']:.1f}% (Low ${snap['low_52w']:.2f} - High ${snap['high_52w']:.2f}, {snap['pct_from_52w_high']:+.1f}% from 52W high)",
        ]
        return "\n".join(lines)
    except Exception as exc:
        logger.exception("Failed computing technical indicators for %s", clean_ticker)
        return f"Error computing technical indicators for {clean_ticker}: {exc}"
