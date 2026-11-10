"""High IV to Historical IV (HistIV) Ratio Watchlist Analytics Engine.

Calculates:
- Ratio: ATM Implied Volatility (30d) / 20-Day Close-to-Close Realized Volatility (HV/HistIV)
- Volatility Pricing Regime:
  - COILED_SPRING_EXTREME (Ratio >= 1.8): Imminent binary event risk or massive unannounced catalyst
  - VOL_RICH (1.3 <= Ratio < 1.8): Elevated uncertainty or rich options premium
  - FAIR_VOL (0.8 <= Ratio < 1.3): Options pricing aligned with historical baseline
  - VOL_CHEAP (Ratio < 0.8): Complacent options, low implied vol
- Universal Scopes: 'mega_mid', 'portfolio', 'custom', or 'all'
"""

import asyncio
from typing import Any

from analytics.options_surface import get_options_vol_surface_report
from core.config import logger
from core.db import get_supabase_client

# Default liquid mega-cap and high-beta market movers (top 10 bellwethers)
DEFAULT_MEGA_MID_TICKERS: tuple[str, ...] = (
    "SPY",
    "QQQ",
    "NVDA",
    "AAPL",
    "MSFT",
    "AMZN",
    "GOOGL",
    "META",
    "TSLA",
    "AMD",
)


def calculate_iv_hist_iv_ratio(atm_iv: float | None, hist_iv: float | None) -> float | None:
    """Calculate ratio of ATM Implied Volatility to Historical Realized Volatility."""
    if atm_iv is None or hist_iv is None:
        return None
    try:
        iv = float(atm_iv)
        hv = float(hist_iv)
        if iv <= 0 or hv <= 0:
            return None
        return round(iv / hv, 4)
    except (ValueError, ZeroDivisionError):
        return None


def classify_vol_ratio_regime(ratio: float | None) -> str:
    """Classify volatility dislocation regime based on IV / HistIV ratio."""
    if ratio is None or ratio <= 0:
        return "UNKNOWN"
    if ratio >= 1.8:
        return "COILED_SPRING_EXTREME"
    elif ratio >= 1.3:
        return "VOL_RICH"
    elif ratio >= 0.8:
        return "FAIR_VOL"
    return "VOL_CHEAP"


async def resolve_watchlist_universe(universe: str = "mega_mid", custom_tickers: str | None = None) -> list[str]:
    """Resolve target tickers based on universe selection."""
    scope = (universe or "mega_mid").strip().lower()

    if scope == "custom" and custom_tickers:
        raw_list = [t.strip().upper() for t in custom_tickers.split(",") if t.strip()]
        return list(dict.fromkeys(raw_list))

    resolved: list[str] = []

    if scope in ("portfolio", "all"):
        try:
            sb = get_supabase_client()
            if sb:
                pos_res = sb.table("position_pnl").select("ticker, quantity").execute()
                if pos_res.data:
                    port_tickers = [
                        p["ticker"].strip().upper()
                        for p in pos_res.data
                        if p.get("ticker") and abs(float(p.get("quantity", 0))) > 0
                    ]
                    resolved.extend(port_tickers)
        except Exception as e:
            logger.warning("Error fetching portfolio positions for IV watchlist: %s", e, exc_info=True)

    if scope in ("mega_mid", "all"):
        resolved.extend(DEFAULT_MEGA_MID_TICKERS)

    if not resolved and custom_tickers:
        resolved = [t.strip().upper() for t in custom_tickers.split(",") if t.strip()]

    if not resolved:
        resolved = list(DEFAULT_MEGA_MID_TICKERS)

    # Return deduplicated list preserving order
    return list(dict.fromkeys(resolved))


def format_high_iv_ratio_watchlist_markdown(items: list[dict[str, Any]], universe: str, min_ratio: float) -> str:
    """Format high IV / HistIV watchlist into clean Markdown table."""
    if not items:
        return (
            f"### ⚡ High IV / HistIV Watchlist (Scope: `{universe}`)\n\n"
            f"*(No tickers found with IV/HistIV ratio >= {min_ratio:.2f})*"
        )

    lines = [
        f"### ⚡ High IV / HistIV Watchlist (Scope: `{universe}`, Min Ratio: `{min_ratio:.2f}`)\n",
        "| Ticker | Spot Price | ATM IV (30d) | HistIV (20d RV) | IV / HistIV | IV Premium | Regime |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for it in items:
        ticker = it.get("ticker", "N/A")
        spot = f"${it.get('spot_price', 0.0):.2f}"
        iv = f"{it.get('atm_iv', 0.0) * 100:.1f}%"
        hv = f"{it.get('realized_vol_20d', 0.0) * 100:.1f}%"
        ratio = f"**{it.get('ratio', 0.0):.2f}x**"
        prem = f"{it.get('iv_premium_pct', 0.0):+.1f}%"
        regime = it.get("regime", "UNKNOWN")
        lines.append(f"| **{ticker}** | {spot} | {iv} | {hv} | {ratio} | {prem} | `{regime}` |")

    lines.append(
        "\n*Key: `COILED_SPRING_EXTREME` (>=1.8x) marks imminent binary catalyst risk or massive unpriced event fear. "
        "`VOL_RICH` (1.3-1.8x) signals elevated options pricing. `VOL_CHEAP` (<0.8x) marks complacency.*"
    )

    return "\n".join(lines)


async def get_high_iv_ratio_watchlist_report(
    universe: str = "mega_mid",
    custom_tickers: str | None = None,
    min_ratio: float = 1.0,
    limit: int = 10,
) -> dict[str, Any]:
    """Scan the selected universe for highest IV / HistIV ratios."""
    try:
        min_ratio = float(min_ratio) if min_ratio is not None else 1.0
    except (ValueError, TypeError):
        min_ratio = 1.0

    try:
        limit = int(limit) if limit is not None else 10
    except (ValueError, TypeError):
        limit = 10

    tickers = await resolve_watchlist_universe(universe=universe, custom_tickers=custom_tickers)

    # Process tickers concurrently (bounded to avoid rate spikes)
    sem = asyncio.Semaphore(5)

    async def _inspect_ticker(t: str) -> dict[str, Any] | None:
        async with sem:
            try:
                rep = await asyncio.wait_for(get_options_vol_surface_report(ticker=t), timeout=8.0)
                if rep.get("status") == "NO_DATA":
                    return None
                atm_iv = rep.get("atm_iv")
                rv_20d = rep.get("realized_vol_20d")
                ratio = calculate_iv_hist_iv_ratio(atm_iv, rv_20d)
                if ratio is None or ratio < min_ratio:
                    return None
                return {
                    "ticker": t,
                    "spot_price": rep.get("spot_price", 0.0),
                    "atm_iv": atm_iv,
                    "realized_vol_20d": rv_20d,
                    "ratio": ratio,
                    "iv_premium_pct": rep.get("iv_premium_pct", 0.0),
                    "regime": classify_vol_ratio_regime(ratio),
                }
            except TimeoutError:
                logger.warning("Options vol surface calculation timed out for %s", t)
                return None
            except Exception as e:
                logger.warning("Error checking IV ratio for %s: %s", t, e, exc_info=True)
                return None

    tasks = [_inspect_ticker(t) for t in tickers]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    valid_items = [r for r in results if isinstance(r, dict) and r is not None]
    valid_items.sort(key=lambda x: x["ratio"], reverse=True)
    capped_items = valid_items[:limit]

    markdown = format_high_iv_ratio_watchlist_markdown(capped_items, universe=universe, min_ratio=min_ratio)

    return {
        "status": "OK",
        "universe": universe,
        "total_screened": len(tickers),
        "items": capped_items,
        "markdown": markdown,
    }
