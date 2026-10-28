"""Multi-Horizon Historical Reference & Statistical Regime Module.

Provides comprehensive point-in-time reference metrics across 20-day (tactical),
60-day (intermediate), and 252-day/52-week (structural) horizons, alongside
realized volatility regime classification and moving average anchors.
"""

from __future__ import annotations

import asyncio
import logging
import math
import re
import statistics
from collections import Counter
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("engine")

# Exclude macro benchmarks and common acronyms when scanning for single stocks
_MACRO_AND_BENCHMARK_TICKERS = frozenset(
    {
        "SPY",
        "QQQ",
        "DIA",
        "IWM",
        "TLT",
        "IEF",
        "TIP",
        "GLD",
        "SLV",
        "CPER",
        "USO",
        "UNG",
        "UUP",
        "EURUSD",
        "USDJPY",
        "BTC",
        "BTCUSD",
        "ETH",
        "ETHUSD",
        "VIX",
        "VIXY",
        "VIXM",
        "^VIX",
        "DXY",
    }
)

_COMMON_WORD_COLLISIONS = frozenset(
    [
        "THE",
        "AND",
        "CEO",
        "CFO",
        "ETF",
        "IPO",
        "FOR",
        "ARE",
        "NEW",
        "YEAR",
        "MARKET",
        "STOCK",
        "TRADE",
        "FUND",
        "DOWN",
        "OVER",
        "FROM",
        "THAT",
        "THIS",
        "WITH",
        "WILL",
        "HAVE",
        "MORE",
        "LESS",
        "WHEN",
        "THAN",
        "ALSO",
        "INTO",
        "JUST",
        "LIKE",
        "SOME",
        "MUCH",
        "SUCH",
        "ONLY",
        "VERY",
        "MAKE",
        "HUGE",
        "BULL",
        "BEAR",
        "SELL",
        "BUY",
        "HOLD",
        "CALL",
        "PUT",
        "NOTE",
        "HERE",
        "MUST",
        "NEED",
        "WELL",
        "HIGH",
        "LOW",
        "LONG",
        "SHORT",
        "BIG",
        "SEE",
        "USE",
        "US",
        "TOP",
        "OUT",
        "END",
        "TRUMP",
        "BIDEN",
        "HARRIS",
        "USA",
        "FED",
        "FOMC",
        "CPI",
        "PPI",
        "GDP",
        "PCE",
        "PMI",
        "WACC",
        "DCF",
        "MBA",
        "EIA",
        "FRN",
        "ARM",
        "AI",
        "FX",
    ]
)


@dataclass
class MultiHorizonReferenceProfile:
    """Historical context metrics across multiple horizons with volatility regime."""

    ticker: str
    current_price: float
    today_change_pct: float | None = None
    prior_close: float | None = None

    # Tactical (20 Days)
    min_20: float | None = None
    max_20: float | None = None
    pct_20: float | None = None
    ret_20: float | None = None
    sma_20: float | None = None
    dist_sma_20: float | None = None

    # Intermediate (60 Days)
    min_60: float | None = None
    max_60: float | None = None
    pct_60: float | None = None
    ret_60: float | None = None
    sma_50: float | None = None
    dist_sma_50: float | None = None

    # Structural (252 Days / 52 Weeks)
    min_52w: float | None = None
    max_52w: float | None = None
    pct_52w: float | None = None
    ret_52w: float | None = None
    sma_200: float | None = None
    dist_sma_200: float | None = None
    z_score_52w: float | None = None

    # Volatility & Regime Classification
    vol_20d: float | None = None
    vol_1y: float | None = None
    vol_regime: str = "Normal"
    regime_tag: str = "Mid-Range Consolidation"
    bars_used: int = 0

    def to_inline_summary(self) -> str:
        """Compact dense string for prose injection or narrative bullet."""
        parts = [f"**{self.ticker}**: ${self.current_price:,.2f}"]
        if self.today_change_pct is not None:
            parts.append(f"({self.today_change_pct:+.2f}% today)")

        if self.min_52w is not None and self.max_52w is not None and self.pct_52w is not None:
            z_str = f", {self.z_score_52w:+.1f}σ" if self.z_score_52w is not None else ""
            parts.append(
                f"| 52W: [${self.min_52w:,.2f} – ${self.max_52w:,.2f}] ({self.pct_52w:.0f}%-tile{z_str}, {self.regime_tag})"
            )

        if self.ret_20 is not None and self.dist_sma_20 is not None:
            parts.append(f"| 20D: {self.ret_20:+.1f}% ({self.dist_sma_20:+.1f}% vs 20-DMA)")

        if self.vol_regime:
            parts.append(f"| Vol: {self.vol_regime}")

        return " ".join(parts)


def compute_multi_horizon_reference(
    ticker: str,
    history: list[dict[str, Any]] | None,
    live_price: float | None = None,
    target_date: str | None = None,
    today_change_pct: float | None = None,
) -> MultiHorizonReferenceProfile | None:
    """Calculates multi-horizon reference anchors from historical EOD price bars.

    Zero-Lookahead Guarantee:
    If target_date is provided, excludes any bar with date >= target_date.
    """
    if not history:
        return None

    valid_bars: list[dict[str, Any]] = []
    for row in history:
        try:
            p_val = row.get("price")
            if p_val is None:
                continue
            p = float(p_val)
            if math.isnan(p) or p <= 0:
                continue

            fetched_at = str(row.get("fetched_at", ""))
            bar_date = fetched_at[:10]
            if target_date and bar_date and bar_date >= target_date[:10]:
                continue

            valid_bars.append({"price": p, "date": bar_date, "fetched_at": fetched_at})
        except (ValueError, TypeError):
            continue

    if len(valid_bars) < 3:
        return None

    # Sort descending (newest first, matching standard MarketDataManager)
    sorted_bars = sorted(valid_bars, key=lambda x: str(x.get("fetched_at", "")), reverse=True)
    prices = [b["price"] for b in sorted_bars]

    curr = live_price if live_price is not None and live_price > 0 else prices[0]
    prior_close = prices[1] if len(prices) > 1 else prices[0]

    if today_change_pct is None and prior_close > 0:
        chg_pct = ((curr - prior_close) / prior_close) * 100.0
    else:
        chg_pct = today_change_pct

    def _calc_range_and_rank(sub_prices: list[float]) -> tuple[float, float, float]:
        min_p = min(sub_prices)
        max_p = max(sub_prices)
        rank = (sum(1 for p in sub_prices if p <= curr) / len(sub_prices)) * 100.0
        return min_p, max_p, rank

    # 1. Tactical (20 Days)
    p_20 = prices[:20]
    min_20, max_20, pct_20 = _calc_range_and_rank(p_20)
    ret_20 = ((curr - p_20[-1]) / p_20[-1] * 100.0) if p_20[-1] > 0 else 0.0
    sma_20 = sum(p_20) / len(p_20)
    dist_sma_20 = ((curr - sma_20) / sma_20 * 100.0) if sma_20 > 0 else 0.0

    # 2. Intermediate (60 Days)
    p_60 = prices[:60]
    min_60, max_60, pct_60 = _calc_range_and_rank(p_60)
    ret_60 = ((curr - p_60[-1]) / p_60[-1] * 100.0) if p_60[-1] > 0 else 0.0
    p_50 = prices[:50]
    sma_50 = (sum(p_50) / len(p_50)) if len(p_50) >= 30 else None
    dist_sma_50 = (((curr - sma_50) / sma_50) * 100.0) if sma_50 and sma_50 > 0 else None

    # 3. Structural (252 Days / 52 Weeks)
    p_252 = prices[:252]
    min_52w, max_52w, pct_52w = _calc_range_and_rank(p_252)
    ret_52w = ((curr - p_252[-1]) / p_252[-1] * 100.0) if p_252[-1] > 0 else 0.0
    p_200 = prices[:200]
    sma_200 = (sum(p_200) / len(p_200)) if len(p_200) >= 120 else None
    dist_sma_200 = (((curr - sma_200) / sma_200) * 100.0) if sma_200 and sma_200 > 0 else None

    # Z-Score over available long-term history
    mean_52w = statistics.mean(p_252)
    stdev_52w = statistics.stdev(p_252) if len(p_252) > 1 else 0.0
    z_score_52w = ((curr - mean_52w) / stdev_52w) if stdev_52w > 0 else 0.0

    # Realized Volatility: 20d vs 1Y
    chrono_prices = list(reversed(p_252))
    returns = [
        (chrono_prices[i] - chrono_prices[i - 1]) / chrono_prices[i - 1]
        for i in range(1, len(chrono_prices))
        if chrono_prices[i - 1] > 0
    ]
    vol_20d = (statistics.stdev(returns[-20:]) * math.sqrt(252) * 100.0) if len(returns) >= 20 else None
    vol_1y = (statistics.stdev(returns) * math.sqrt(252) * 100.0) if len(returns) >= 30 else None

    vol_regime = "Normal"
    if vol_20d is not None and vol_1y is not None and vol_1y > 0:
        ratio = vol_20d / vol_1y
        if ratio > 1.3:
            vol_regime = f"Expanding ({vol_20d:.1f}% vs 1Y {vol_1y:.1f}%)"
        elif ratio < 0.75:
            vol_regime = f"Compressed ({vol_20d:.1f}% vs 1Y {vol_1y:.1f}%)"
        else:
            vol_regime = f"Normal ({vol_20d:.1f}% vs 1Y {vol_1y:.1f}%)"
    elif vol_20d is not None:
        vol_regime = f"{vol_20d:.1f}%"

    # Qualitative Range Tag
    if pct_52w >= 90.0:
        regime_tag = "Near 52W High (Top Decile)"
    elif pct_52w <= 10.0:
        regime_tag = "Near 52W Low (Bottom Decile)"
    elif pct_52w >= 75.0:
        regime_tag = "Elevated (Upper Quartile)"
    elif pct_52w <= 25.0:
        regime_tag = "Depressed (Lower Quartile)"
    else:
        regime_tag = "Mid-Range Consolidation"

    return MultiHorizonReferenceProfile(
        ticker=ticker.upper().strip(),
        current_price=curr,
        today_change_pct=chg_pct,
        prior_close=prior_close,
        min_20=min_20,
        max_20=max_20,
        pct_20=pct_20,
        ret_20=ret_20,
        sma_20=sma_20,
        dist_sma_20=dist_sma_20,
        min_60=min_60,
        max_60=max_60,
        pct_60=pct_60,
        ret_60=ret_60,
        sma_50=sma_50,
        dist_sma_50=dist_sma_50,
        min_52w=min_52w,
        max_52w=max_52w,
        pct_52w=pct_52w,
        ret_52w=ret_52w,
        sma_200=sma_200,
        dist_sma_200=dist_sma_200,
        z_score_52w=z_score_52w,
        vol_20d=vol_20d,
        vol_1y=vol_1y,
        vol_regime=vol_regime,
        regime_tag=regime_tag,
        bars_used=len(prices),
    )


def format_reference_table(profiles: list[MultiHorizonReferenceProfile]) -> str:
    """Formats a clean Markdown table summarizing multi-horizon positioning for all profiles."""
    if not profiles:
        return ""

    headers = [
        "| Asset | Price | 1D Move | 52W Range (%-tile) | 60D Move | 20D Move (vs 20-DMA) | Vol Regime | Regime Tag |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    rows = []
    for p in profiles:
        chg_str = f"{p.today_change_pct:+.2f}%" if p.today_change_pct is not None else "N/A"
        range_52w_str = (
            f"[${p.min_52w:,.2f} – ${p.max_52w:,.2f}] ({p.pct_52w:.0f}%)"
            if p.min_52w is not None and p.max_52w is not None and p.pct_52w is not None
            else "N/A"
        )
        ret_60_str = f"{p.ret_60:+.1f}%" if p.ret_60 is not None else "N/A"
        ret_20_str = (
            f"{p.ret_20:+.1f}% ({p.dist_sma_20:+.1f}% vs 20d)"
            if p.ret_20 is not None and p.dist_sma_20 is not None
            else "N/A"
        )
        rows.append(
            f"| **{p.ticker}** | ${p.current_price:,.2f} | {chg_str} | {range_52w_str} | {ret_60_str} | {ret_20_str} | {p.vol_regime} | {p.regime_tag} |"
        )

    return "\n".join(headers + rows)


def extract_mentioned_single_stocks(chunks: list[dict[str, Any]], max_tickers: int = 6) -> list[str]:
    """Extracts top mentioned single stock equity tickers from newsletter chunk subjects and contents."""
    ticker_counts: Counter[str] = Counter()

    for chunk in chunks:
        text = f"{chunk.get('subject', '')} {chunk.get('content', '')}"
        for m in re.finditer(r"\$([A-Z]{1,5})\b", text):
            sym = m.group(1).upper()
            if sym not in _MACRO_AND_BENCHMARK_TICKERS and sym not in _COMMON_WORD_COLLISIONS:
                ticker_counts[sym] += 1

        for m in re.finditer(r"\(([A-Z]{1,5})\)", text):
            sym = m.group(1).upper()
            if sym not in _MACRO_AND_BENCHMARK_TICKERS and sym not in _COMMON_WORD_COLLISIONS:
                ticker_counts[sym] += 1

    return [t for t, _ in ticker_counts.most_common(max_tickers)]


async def get_newsletter_reference_context(
    chunks: list[dict[str, Any]] | None = None,
    mdm=None,
    target_date: str | None = None,
    macro_tickers: list[str] | None = None,
    max_single_stocks: int = 5,
) -> str:
    """Fetch multi-horizon positioning, percentiles, and volatility regimes for macro core and mentioned stocks.

    Queries 252-day history from MarketDataManager for core macro proxies
    plus top single stocks extracted from newsletter chunks.
    """
    from execution.market_data import MarketDataManager

    manager = mdm or MarketDataManager()
    macro_core = macro_tickers or ["UUP", "EURUSD", "USDJPY", "SPY", "QQQ", "TLT", "GLD", "USO"]
    single_stocks = extract_mentioned_single_stocks(chunks or [], max_tickers=max_single_stocks)

    all_targets = list(macro_core) + [s for s in single_stocks if s not in macro_core]

    try:
        quote_tasks = [manager.get_premarket_quote(ticker) for ticker in all_targets]
        hist_tasks = [manager.get_history(ticker, days=252) for ticker in all_targets]

        quotes, histories = await asyncio.gather(
            asyncio.gather(*quote_tasks, return_exceptions=True),
            asyncio.gather(*hist_tasks, return_exceptions=True),
        )
    except Exception as e:
        logger.warning(f"Error gathering market reference data for newsletter: {e}")
        return ""

    profiles: list[MultiHorizonReferenceProfile] = []
    for ticker, q, h in zip(all_targets, quotes, histories, strict=False):
        if isinstance(h, Exception) or not h:
            continue
        price = q.get("price") if isinstance(q, dict) else None
        chg = q.get("change_pct") if isinstance(q, dict) else None
        prof = compute_multi_horizon_reference(
            ticker=ticker,
            history=h,
            live_price=price,
            target_date=target_date,
            today_change_pct=chg,
        )
        if prof:
            profiles.append(prof)

    if not profiles:
        return ""

    table_md = format_reference_table(profiles)
    highlights = [f"- {p.to_inline_summary()}" for p in profiles]

    header = "### 📊 Multi-Horizon Reference & Statistical Regime Matrix\n\n"
    return f"{header}{table_md}\n\n**Key Reference & Statistical Highlights (Multi-Horizon):**\n" + "\n".join(
        highlights
    )
