"""Yield Curve Macro Regime Classifier.

Analyzes US Treasury term structure (3M, 2Y, 5Y, 10Y, 30Y) using FMP /stable/treasury-rates
(with FRED fallback) to classify the macroeconomic monetary flow regime into:
- BULL_STEEPENER (Rate cuts / Easing -> Small-Caps, Banks)
- BULL_FLATTENER (Disinflation rally -> Mega-Cap Growth, Duration)
- BEAR_STEEPENER (Inflation / Supply shock -> Energy, Commodities, Value)
- BEAR_FLATTENER (Hawkish Fed / Tightening -> Defensive, Cash)
"""

from enum import StrEnum
from typing import Any

import httpx

from core.config import FMP_API_KEY, logger


class YieldCurveRegime(StrEnum):
    BULL_STEEPENER = "BULL_STEEPENER"
    BULL_FLATTENER = "BULL_FLATTENER"
    BEAR_STEEPENER = "BEAR_STEEPENER"
    BEAR_FLATTENER = "BEAR_FLATTENER"


FACTOR_TAILWINDS: dict[YieldCurveRegime, list[str]] = {
    YieldCurveRegime.BULL_STEEPENER: [
        "Small-Caps (IWM)",
        "Regional Banks (KRE)",
        "High-Beta Equities",
    ],
    YieldCurveRegime.BULL_FLATTENER: [
        "Mega-Cap Tech (QQQ)",
        "Quality Growth",
        "Long-Duration Treasuries (TLT)",
    ],
    YieldCurveRegime.BEAR_STEEPENER: [
        "Energy (XLE)",
        "Commodities (GLD/USO)",
        "Cyclical Value",
        "Inflation Hedges",
    ],
    YieldCurveRegime.BEAR_FLATTENER: [
        "Defensive Staples (XLP)",
        "Health Care (XLV)",
        "Short-Duration Treasuries / Cash (SHV)",
    ],
}

FACTOR_HEADWINDS: dict[YieldCurveRegime, list[str]] = {
    YieldCurveRegime.BULL_STEEPENER: [
        "Defensive Utilities (XLU)",
        "Cash / Money Markets",
    ],
    YieldCurveRegime.BULL_FLATTENER: [
        "Commodities (DBC)",
        "Cyclical Value",
    ],
    YieldCurveRegime.BEAR_STEEPENER: [
        "High-Multiple Software",
        "Long-Duration Bonds (TLT)",
    ],
    YieldCurveRegime.BEAR_FLATTENER: [
        "Equities Broadly (SPY/QQQ)",
        "Real Estate (XLRE)",
        "High-Leverage Balance Sheets",
    ],
}


def classify_yield_curve_regime(history: list[dict[str, Any]]) -> dict[str, Any]:
    """Classify the yield curve macro regime from daily Treasury rates history."""
    if not history:
        return {
            "regime": YieldCurveRegime.BULL_FLATTENER.value,
            "spread_10y_2y_bps": 0.0,
            "spread_10y_3m_bps": 0.0,
            "spread_10y_2y_5d_delta_bps": 0.0,
            "yield_level_direction": "NEUTRAL",
            "historical_factor_tailwinds": FACTOR_TAILWINDS[YieldCurveRegime.BULL_FLATTENER],
            "historical_factor_headwinds": FACTOR_HEADWINDS[YieldCurveRegime.BULL_FLATTENER],
        }

    # Sort history by date ascending
    sorted_history = sorted(history, key=lambda x: str(x.get("date", "")))
    latest = sorted_history[-1]
    prior = sorted_history[-2] if len(sorted_history) > 1 else latest

    # Extract rates safely
    y10_latest = float(latest.get("year10") or 0.0)
    y2_latest = float(latest.get("year2") or 0.0)
    m3_latest = float(latest.get("month3") or 0.0)
    y5_latest = float(latest.get("year5") or 0.0)
    y30_latest = float(latest.get("year30") or 0.0)

    y10_prior = float(prior.get("year10") or y10_latest)
    y2_prior = float(prior.get("year2") or y2_latest)

    spread_10y_2y = round((y10_latest - y2_latest) * 100, 1)
    spread_10y_3m = round((y10_latest - m3_latest) * 100, 1)
    spread_30y_5y = round((y30_latest - y5_latest) * 100, 1)

    spread_10y_2y_prior = (y10_prior - y2_prior) * 100
    spread_delta = round(spread_10y_2y - spread_10y_2y_prior, 1)

    # 10Y yield level delta
    yield_delta = y10_latest - y10_prior
    is_yield_falling = yield_delta < 0 or (yield_delta == 0 and (y2_latest - y2_prior) < 0)
    is_steepening = spread_delta > 0

    if is_yield_falling:
        yield_level_direction = "FALLING"
        regime = YieldCurveRegime.BULL_STEEPENER if is_steepening else YieldCurveRegime.BULL_FLATTENER
    else:
        yield_level_direction = "RISING"
        regime = YieldCurveRegime.BEAR_STEEPENER if is_steepening else YieldCurveRegime.BEAR_FLATTENER

    return {
        "date": latest.get("date", ""),
        "regime": regime.value,
        "spread_10y_2y_bps": spread_10y_2y,
        "spread_10y_3m_bps": spread_10y_3m,
        "spread_30y_5y_bps": spread_30y_5y,
        "spread_10y_2y_5d_delta_bps": spread_delta,
        "yield_level_direction": yield_level_direction,
        "historical_factor_tailwinds": FACTOR_TAILWINDS[regime],
        "historical_factor_headwinds": FACTOR_HEADWINDS[regime],
    }


def format_yield_curve_regime_markdown(data: dict[str, Any]) -> str:
    """Formats the yield curve classification into a clean markdown block."""
    regime = data.get("regime", "UNKNOWN")
    date_str = data.get("date", "Latest")
    spread_2y = data.get("spread_10y_2y_bps", 0.0)
    spread_3m = data.get("spread_10y_3m_bps", 0.0)
    delta_5d = data.get("spread_10y_2y_5d_delta_bps", 0.0)
    yield_dir = data.get("yield_level_direction", "NEUTRAL")

    tailwinds = ", ".join(data.get("historical_factor_tailwinds", []))
    headwinds = ", ".join(data.get("historical_factor_headwinds", []))

    return (
        f"### 📊 Yield Curve & Macro Regime\n\n"
        f"- **As of**: `{date_str}`\n"
        f"- **10Y-2Y Spread**: `{spread_2y:+.1f} bps` (5-Day $\\Delta$: `{delta_5d:+.1f} bps`)\n"
        f"- **10Y-3M Spread**: `{spread_3m:+.1f} bps`\n"
        f"- **Yield Level Direction**: `{yield_dir}`\n"
        f"- **Active Monetary Regime**: **`{regime}`**\n\n"
        f"**Factor Tailwinds**: {tailwinds}\n\n"
        f"**Factor Headwinds**: {headwinds}\n"
    )


async def get_yield_curve_regime_report() -> dict[str, Any]:
    """Fetch Treasury rates from FMP, classify regime, and return data + markdown."""
    if not FMP_API_KEY:
        logger.warning("FMP_API_KEY missing. Yield curve regime returning neutral default.")
        default_data = classify_yield_curve_regime([])
        default_data["markdown"] = format_yield_curve_regime_markdown(default_data)
        return default_data

    url = "https://financialmodelingprep.com/stable/treasury-rates"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params={"apikey": FMP_API_KEY})
            if resp.status_code == 200:
                history = resp.json()
                if isinstance(history, list) and history:
                    report_data = classify_yield_curve_regime(history)
                    report_data["markdown"] = format_yield_curve_regime_markdown(report_data)
                    return report_data
            logger.error(f"FMP treasury-rates error: {resp.status_code} - {resp.text[:300]}")
    except Exception as e:
        logger.error(f"Exception fetching treasury rates from FMP: {e}")

    fallback_data = classify_yield_curve_regime([])
    fallback_data["markdown"] = format_yield_curve_regime_markdown(fallback_data)
    return fallback_data
