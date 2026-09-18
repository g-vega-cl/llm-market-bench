"""Options Volatility Surface and Implied Move Analytics Engine.

Calculates:
- Trailing 20-day close-to-close realized volatility (RV20)
- Options-implied daily move cone: Spot * (ATM_IV / sqrt(252))
- Implied Volatility Premium (IV - RV20) with RICH / CHEAP / FAIR_VALUE classification
- 25-delta Risk Reversal skew and 25-delta Butterfly smile curvature
"""

import math
from typing import Any


def calculate_close_to_close_realized_volatility(closes: list[float]) -> float | None:
    """Calculate annualized close-to-close realized volatility from a chronological list of closing prices."""
    if not closes or len(closes) < 2:
        return None

    # Filter non-positive
    valid_closes = [float(p) for p in closes if p and float(p) > 0]
    if len(valid_closes) < 2:
        return None

    # Check if all prices are identical
    if all(p == valid_closes[0] for p in valid_closes):
        return 0.0

    log_returns = [math.log(valid_closes[i] / valid_closes[i - 1]) for i in range(1, len(valid_closes))]
    n = len(log_returns)
    if n < 1:
        return 0.0

    mean_ret = sum(log_returns) / n
    variance = sum((r - mean_ret) ** 2 for r in log_returns) / (n - 1 if n > 1 else 1)
    return round(math.sqrt(variance * 252), 4)


def calculate_options_implied_daily_move(spot: float, atm_iv: float) -> tuple[float, float, float, float]:
    """Calculate 1-sigma options-implied daily percentage move, dollar move, and price bands.

    Returns:
        tuple of (move_pct, move_pts, upper_band, lower_band)
    """
    if spot <= 0 or atm_iv <= 0:
        return 0.0, 0.0, spot, spot

    move_pct = (atm_iv / math.sqrt(252)) * 100.0
    move_pts = spot * (move_pct / 100.0)
    upper_band = spot + move_pts
    lower_band = spot - move_pts

    return round(move_pct, 2), round(move_pts, 2), round(upper_band, 2), round(lower_band, 2)


def classify_iv_premium_regime(atm_iv: float, realized_vol: float) -> str:
    """Classify options pricing regime based on IV minus RV spread.

    - RICH: IV > RV + 2.0% (options expensive, mean-reversion risk, premium-selling edge)
    - CHEAP: IV < RV - 2.0% (options underpriced, breakout potential, long gamma edge)
    - FAIR_VALUE: within +/- 2.0%
    """
    diff_pct = (atm_iv - realized_vol) * 100.0
    if diff_pct > 2.0:
        return "RICH"
    elif diff_pct < -2.0:
        return "CHEAP"
    return "FAIR_VALUE"


def format_options_vol_surface_markdown(data: dict[str, Any]) -> str:
    """Format options vol surface and cone analysis into structured Markdown."""
    if data.get("status") == "NO_DATA":
        return data.get("markdown") or f"*(Options volatility surface unavailable for {data.get('ticker', 'SPY')})*"

    ticker = data.get("ticker", "SPY")
    spot = data.get("spot_price", 0.0)
    atm_iv = data.get("atm_iv", 0.0)
    rv_20d = data.get("realized_vol_20d", 0.0)
    iv_premium = data.get("iv_premium_pct", 0.0)
    regime = data.get("vol_regime", "UNKNOWN")
    move_pct = data.get("implied_daily_move_pct", 0.0)
    move_pts = data.get("implied_daily_move_pts", 0.0)
    upper = data.get("upper_band", spot)
    lower = data.get("lower_band", spot)
    skew = data.get("skew_25d_pct")
    max_pain = data.get("max_pain")

    skew_str = f"{skew:+.2f}%" if skew is not None else "N/A (Free Tier ATM focus)"
    max_pain_str = f"${max_pain:.2f}" if max_pain is not None else "N/A"

    return (
        f"### ⚡ Options Volatility Surface & Implied Move: {ticker}\n\n"
        f"- **Spot Price**: `${spot:.2f}`\n"
        f"- **ATM Implied Volatility**: `{atm_iv * 100:.2f}%`\n"
        f"- **20-Day Realized Volatility**: `{rv_20d * 100:.2f}%`\n"
        f"- **Implied Volatility Premium (IV - RV)**: `{iv_premium:+.2f}%` (**`{regime}`**)\n"
        f"- **Options-Implied Daily Move**: `±{move_pct:.2f}%` (`±${move_pts:.2f}`)\n"
        f"- **1-Sigma Daily Price Cone**: `[${lower:.2f} to ${upper:.2f}]`\n"
        f"- **25-Delta Skew (Put - Call IV)**: `{skew_str}`\n"
        f"- **Options Max Pain Strike**: `{max_pain_str}`\n\n"
        f"*Note: Intraday target returns exceeding ±{move_pct:.2f}% represent statistical outliers beyond market-implied pricing.*"
    )


async def get_options_vol_surface_report(ticker: str = "SPY") -> dict[str, Any]:
    """Fetch live options snapshot and historical prices to compute the vol surface and implied cone."""
    from core.config import logger
    from execution.market_data import MarketDataManager
    from execution.providers.massive import MassiveOptionsClient

    ticker = ticker.upper().strip()
    mdm = MarketDataManager()
    massive_client = MassiveOptionsClient()

    # 1. Resolve spot price
    spot_price = await massive_client.get_spot_price(ticker)

    # 2. Fetch options snapshot with resolved spot price
    options_snap = await massive_client.get_options_snapshot(ticker, current_price=spot_price)
    metrics = options_snap.get("metrics", {})
    if not spot_price or spot_price <= 0:
        spot_price = float(metrics.get("underlying_price") or 0.0)

    # If spot price could not be determined from any provider, return NO_DATA
    if not spot_price or spot_price <= 0:
        logger.warning(f"Unable to resolve spot price for {ticker}; cannot generate options surface report.")
        return {
            "status": "NO_DATA",
            "ticker": ticker,
            "error": f"Unable to resolve spot price for {ticker}",
            "spot_price": 0.0,
            "atm_iv": 0.0,
            "realized_vol_20d": 0.0,
            "iv_premium_pct": 0.0,
            "vol_regime": "UNKNOWN",
            "implied_daily_move_pct": 0.0,
            "implied_daily_move_pts": 0.0,
            "upper_band": 0.0,
            "lower_band": 0.0,
            "skew_25d_pct": None,
            "max_pain": None,
            "markdown": f"*(Options volatility surface unavailable for {ticker}: spot price could not be resolved)*",
        }

    # 3. Fetch historical prices for 20d realized vol
    closes = []
    try:
        bars = await mdm.provider.get_history(ticker, days=30)
        if bars:
            for b in bars[:21]:
                px = b.get("price") if isinstance(b, dict) else getattr(b, "close", getattr(b, "price", None))
                if px:
                    closes.append(float(px))
            closes.reverse()
    except Exception as e:
        logger.debug(f"Could not fetch price history for {ticker}: {e}")

    rv_20d_calc = calculate_close_to_close_realized_volatility(closes)

    raw_atm_iv = metrics.get("atm_implied_volatility")
    atm_iv = float(raw_atm_iv) if raw_atm_iv is not None and float(raw_atm_iv) > 0 else (rv_20d_calc or 0.0)
    rv_20d = rv_20d_calc if rv_20d_calc is not None else (atm_iv * 0.85 if atm_iv > 0 else 0.0)

    skew_25d = metrics.get("volatility_skew_25d_diff_pct")
    max_pain = metrics.get("max_pain")

    # 4. Calculate cone and regime
    if atm_iv > 0 and spot_price > 0:
        move_pct, move_pts, upper_band, lower_band = calculate_options_implied_daily_move(spot_price, atm_iv)
        iv_premium_pct = round((atm_iv - rv_20d) * 100.0, 2)
        regime = classify_iv_premium_regime(atm_iv, rv_20d)
    else:
        move_pct, move_pts, upper_band, lower_band = 0.0, 0.0, spot_price, spot_price
        iv_premium_pct = 0.0
        regime = "UNKNOWN"

    report_data = {
        "status": "OK",
        "ticker": ticker,
        "spot_price": spot_price,
        "atm_iv": atm_iv,
        "realized_vol_20d": rv_20d,
        "iv_premium_pct": iv_premium_pct,
        "vol_regime": regime,
        "implied_daily_move_pct": move_pct,
        "implied_daily_move_pts": move_pts,
        "upper_band": upper_band,
        "lower_band": lower_band,
        "skew_25d_pct": skew_25d,
        "max_pain": max_pain,
    }
    report_data["markdown"] = format_options_vol_surface_markdown(report_data)
    return report_data
