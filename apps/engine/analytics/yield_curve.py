"""Yield Curve Macro Regime Classifier.

Analyzes US Treasury term structure (3M, 2Y, 5Y, 10Y, 30Y) using FMP /stable/treasury-rates
(with FRED fallback) to classify the macroeconomic monetary flow regime into:
- BULL_STEEPENER (Rate cuts / Easing -> Small-Caps, Banks)
- BULL_FLATTENER (Disinflation rally -> Mega-Cap Growth, Duration)
- BEAR_STEEPENER (Inflation / Supply shock -> Energy, Commodities, Value)
- BEAR_FLATTENER (Hawkish Fed / Tightening -> Defensive, Cash)
"""

import asyncio
from enum import StrEnum
from typing import Any

import httpx

from core.config import FMP_API_KEY, logger


class YieldCurveRegime(StrEnum):
    BULL_STEEPENER = "BULL_STEEPENER"
    BULL_FLATTENER = "BULL_FLATTENER"
    BEAR_STEEPENER = "BEAR_STEEPENER"
    BEAR_FLATTENER = "BEAR_FLATTENER"
    UNAVAILABLE = "UNAVAILABLE"


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
    YieldCurveRegime.UNAVAILABLE: [],
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
    YieldCurveRegime.UNAVAILABLE: [],
}


def _opt_float(row: dict[str, Any], key: str) -> float | None:
    """Parse an optional numeric field without coercing missing values to zero."""
    val = row.get(key)
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _spread_bps(long_val: float | None, short_val: float | None) -> float | None:
    """Compute spread in basis points only when both tenors are present."""
    if long_val is None or short_val is None:
        return None
    return round((long_val - short_val) * 100, 1)


def _format_bps(val: float | None) -> str:
    """Render basis-point values cleanly without fabricating zeros for missing tenors."""
    return f"`{val:+.1f} bps`" if isinstance(val, (int, float)) else "`N/A`"


def classify_yield_curve_regime(history: list[dict[str, Any]]) -> dict[str, Any]:
    """Classify the yield curve macro regime from daily Treasury rates history."""
    valid_rows = [
        row for row in (history or []) if _opt_float(row, "year10") is not None and _opt_float(row, "year2") is not None
    ]
    if not valid_rows:
        return {
            "date": "",
            "regime": YieldCurveRegime.UNAVAILABLE.value,
            "spread_10y_2y_bps": None,
            "spread_10y_3m_bps": None,
            "spread_30y_5y_bps": None,
            "spread_10y_2y_5d_delta_bps": None,
            "yield_level_direction": "UNAVAILABLE",
            "historical_factor_tailwinds": [],
            "historical_factor_headwinds": [],
        }

    # Sort history by date ascending
    sorted_history = sorted(valid_rows, key=lambda x: str(x.get("date", "")))
    latest = sorted_history[-1]

    y10_latest = _opt_float(latest, "year10")
    y2_latest = _opt_float(latest, "year2")
    m3_latest = _opt_float(latest, "month3")
    y5_latest = _opt_float(latest, "year5")
    y30_latest = _opt_float(latest, "year30")

    spread_10y_2y = _spread_bps(y10_latest, y2_latest)
    spread_10y_3m = _spread_bps(y10_latest, m3_latest)
    spread_30y_5y = _spread_bps(y30_latest, y5_latest)

    if len(sorted_history) < 2:
        return {
            "date": latest.get("date", ""),
            "regime": YieldCurveRegime.UNAVAILABLE.value,
            "spread_10y_2y_bps": spread_10y_2y,
            "spread_10y_3m_bps": spread_10y_3m,
            "spread_30y_5y_bps": spread_30y_5y,
            "spread_10y_2y_5d_delta_bps": None,
            "yield_level_direction": "UNAVAILABLE",
            "historical_factor_tailwinds": [],
            "historical_factor_headwinds": [],
        }

    prior = sorted_history[-2]
    y10_prior = _opt_float(prior, "year10")
    y2_prior = _opt_float(prior, "year2")

    assert y10_latest is not None and y2_latest is not None
    assert y10_prior is not None and y2_prior is not None
    assert spread_10y_2y is not None

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
    regime = data.get("regime", YieldCurveRegime.UNAVAILABLE.value)
    date_str = data.get("date") or "N/A"
    spread_2y_str = _format_bps(data.get("spread_10y_2y_bps"))
    spread_3m_str = _format_bps(data.get("spread_10y_3m_bps"))
    delta_5d_str = _format_bps(data.get("spread_10y_2y_5d_delta_bps"))
    yield_dir = data.get("yield_level_direction", "UNAVAILABLE")

    tailwinds = ", ".join(data.get("historical_factor_tailwinds") or []) or "N/A (insufficient data)"
    headwinds = ", ".join(data.get("historical_factor_headwinds") or []) or "N/A (insufficient data)"

    return (
        f"### 📊 Yield Curve & Macro Regime\n\n"
        f"- **As of**: `{date_str}`\n"
        f"- **10Y-2Y Spread**: {spread_2y_str} (5-Day $\\Delta$: {delta_5d_str})\n"
        f"- **10Y-3M Spread**: {spread_3m_str}\n"
        f"- **Yield Level Direction**: `{yield_dir}`\n"
        f"- **Active Monetary Regime**: **`{regime}`**\n\n"
        f"**Factor Tailwinds**: {tailwinds}\n\n"
        f"**Factor Headwinds**: {headwinds}\n"
    )


_FRED_YIELD_TENORS: tuple[tuple[str, str], ...] = (
    ("treasury_3m", "month3"),
    ("treasury_2y", "year2"),
    ("treasury_5y", "year5"),
    ("treasury_10y", "year10"),
    ("treasury_30y", "year30"),
)


async def _fetch_fred_yield_history(lookback_periods: int = 10) -> list[dict[str, Any]]:
    """Build daily yield history dicts from FRED series when FMP treasury-rates is unavailable."""
    from core.fred import fetch_fred_series_observations

    results = await asyncio.gather(
        *(fetch_fred_series_observations(alias, lookback_periods=lookback_periods) for alias, _ in _FRED_YIELD_TENORS),
        return_exceptions=True,
    )

    by_date: dict[str, dict[str, Any]] = {}
    for (_, field_name), res in zip(_FRED_YIELD_TENORS, results, strict=True):
        if isinstance(res, Exception) or not isinstance(res, dict):
            continue
        for obs in res.get("observations") or []:
            obs_date = str(obs.get("date") or "")[:10]
            obs_val = obs.get("value")
            if not obs_date or obs_val is None:
                continue
            try:
                by_date.setdefault(obs_date, {"date": obs_date})[field_name] = float(obs_val)
            except (TypeError, ValueError):
                continue

    # Retain dates that have the core 2Y and 10Y benchmark yields needed for spread classification.
    aligned = [row for row in by_date.values() if "year10" in row and "year2" in row]
    aligned.sort(key=lambda r: r["date"])
    return aligned


async def get_yield_curve_regime_report() -> dict[str, Any]:
    """Fetch Treasury rates from FMP with FRED fallback, classify regime, and return data + markdown."""
    if FMP_API_KEY:
        url = "https://financialmodelingprep.com/stable/treasury-rates"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params={"apikey": FMP_API_KEY})
                if resp.status_code == 200:
                    history = resp.json()
                    if isinstance(history, list) and history:
                        report_data = classify_yield_curve_regime(history)
                        report_data["source"] = "FMP"
                        report_data["markdown"] = format_yield_curve_regime_markdown(report_data)
                        return report_data
                logger.warning(f"FMP treasury-rates error: {resp.status_code} - {resp.text[:300]}")
        except Exception:
            logger.exception("Exception fetching treasury rates from FMP")
    else:
        logger.info("FMP_API_KEY missing. Falling back to FRED Treasury curve series.")

    try:
        fred_history = await _fetch_fred_yield_history()
        if len(fred_history) >= 2:
            report_data = classify_yield_curve_regime(fred_history)
            report_data["source"] = "FRED"
            report_data["markdown"] = format_yield_curve_regime_markdown(report_data)
            return report_data
    except Exception:
        logger.exception("Exception fetching Treasury yield curve fallback from FRED")

    logger.warning("Both FMP and FRED Treasury curve feeds unavailable. Returning UNAVAILABLE state.")
    fallback_data = classify_yield_curve_regime([])
    fallback_data["source"] = "NONE"
    fallback_data["markdown"] = format_yield_curve_regime_markdown(fallback_data)
    return fallback_data
