"""Federal Reserve Economic Data (FRED) API client and Supabase caching layer.

Provides on-demand macroeconomic time series data with alias shortcuts,
Supabase database caching, and markdown formatting for LLM tool calling
and daily market newsletter generation.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from core.config import FRED_API_KEY, FRED_CACHE_TTL_HOURS
from core.db import get_async_supabase_client

logger = logging.getLogger("engine")

FRED_BASE_URL = "https://api.stlouisfed.org/fred"

# Pre-defined curated alias map for top-tier macroeconomic indicators
FRED_SERIES_ALIASES: dict[str, dict[str, Any]] = {
    # Core Benchmark Pack
    "fed_funds": {
        "series_id": "FEDFUNDS",
        "title": "Federal Funds Effective Rate",
        "default_units": "lin",
        "category": "Interest Rates",
    },
    "treasury_10y": {
        "series_id": "DGS10",
        "title": "10-Year Treasury Constant Maturity Rate",
        "default_units": "lin",
        "category": "Bond Yields",
    },
    "treasury_2y": {
        "series_id": "DGS2",
        "title": "2-Year Treasury Constant Maturity Rate",
        "default_units": "lin",
        "category": "Bond Yields",
    },
    "yield_curve_10y2y": {
        "series_id": "T10Y2Y",
        "title": "10-Year Treasury Constant Maturity Minus 2-Year Treasury (Yield Curve)",
        "default_units": "lin",
        "category": "Yield Curve",
    },
    "cpi": {
        "series_id": "CPIAUCSL",
        "title": "Consumer Price Index for All Urban Consumers: All Items",
        "default_units": "pc1",  # Percent change from 1 year ago (YoY)
        "category": "Inflation",
    },
    "core_cpi": {
        "series_id": "CPILFESL",
        "title": "Core CPI (All Items Less Food and Energy)",
        "default_units": "pc1",
        "category": "Inflation",
    },
    "unemployment": {
        "series_id": "UNRATE",
        "title": "Civilian Unemployment Rate",
        "default_units": "lin",
        "category": "Labor Market",
    },
    "high_yield_spread": {
        "series_id": "BAMLH0A0HYM2",
        "title": "ICE BofA US High Yield Index Option-Adjusted Spread",
        "default_units": "lin",
        "category": "Credit Spreads",
    },
    # Liquidity & Monetary Pack
    "m2": {
        "series_id": "M2SL",
        "title": "M2 Money Supply",
        "default_units": "pc1",  # YoY growth
        "category": "Liquidity",
    },
    "fed_balance_sheet": {
        "series_id": "WALCL",
        "title": "Federal Reserve Total Assets (Balance Sheet)",
        "default_units": "lin",
        "category": "Liquidity",
    },
    "reverse_repo": {
        "series_id": "RRPONTSYD",
        "title": "Overnight Reverse Repurchase Agreements (ON RRP)",
        "default_units": "lin",
        "category": "Liquidity",
    },
    # Growth & Labor Pulse
    "nonfarm_payrolls": {
        "series_id": "PAYEMS",
        "title": "All Employees, Total Nonfarm Payrolls",
        "default_units": "chg",  # Monthly change in thousands
        "category": "Labor Market",
    },
    "initial_claims": {
        "series_id": "ICSA",
        "title": "Initial Jobless Claims",
        "default_units": "lin",
        "category": "Labor Market",
    },
    "real_gdp": {
        "series_id": "GDPC1",
        "title": "Real Gross Domestic Product",
        "default_units": "pc1",  # YoY growth
        "category": "Economic Growth",
    },
    "retail_sales": {
        "series_id": "RSAFS",
        "title": "Advance Retail Sales: Retail and Food Services",
        "default_units": "pc1",
        "category": "Consumer & Retail",
    },
    # Inflation & Sentiment
    "pce": {
        "series_id": "PCEPI",
        "title": "Personal Consumption Expenditures: Chain-type Price Index",
        "default_units": "pc1",
        "category": "Inflation",
    },
    "consumer_sentiment": {
        "series_id": "UMCSENT",
        "title": "University of Michigan: Consumer Sentiment",
        "default_units": "lin",
        "category": "Consumer Sentiment",
    },
    "breakeven_5y": {
        "series_id": "T5YIE",
        "title": "5-Year Breakeven Inflation Rate",
        "default_units": "lin",
        "category": "Inflation Expectations",
    },
    "breakeven_10y": {
        "series_id": "T10YIE",
        "title": "10-Year Breakeven Inflation Rate",
        "default_units": "lin",
        "category": "Inflation Expectations",
    },
    "vix": {
        "series_id": "VIXCLS",
        "title": "CBOE Volatility Index (VIX)",
        "default_units": "lin",
        "category": "Volatility",
    },
}


def resolve_series_alias(alias_or_series_id: str) -> str:
    """Resolves a human-friendly alias key or normalizes a raw FRED series ID."""
    clean_key = (alias_or_series_id or "").strip().lower()
    if clean_key in FRED_SERIES_ALIASES:
        return FRED_SERIES_ALIASES[clean_key]["series_id"]
    return (alias_or_series_id or "").strip().upper()


def format_fred_observations_markdown(
    series_id: str,
    title: str,
    units: str,
    frequency: str,
    observations: list[dict[str, Any]],
) -> str:
    """Formats series observations into a clean, scannable Markdown summary table."""
    if not observations:
        return f"No observations found for FRED series `{series_id}` ({title})."

    lines = [
        f"### 📊 FRED Macro Series: {title} (`{series_id}`)",
        f"- **Units**: {units} | **Frequency**: {frequency}",
        "",
        "| Date | Value | Change vs Prev |",
        "| :--- | :---: | :---: |",
    ]

    prev_val = None
    for obs in observations:
        date_str = obs.get("date", "N/A")
        val = obs.get("value")
        if val is None:
            change_str = "-"
            val_str = "N/A"
        else:
            val_str = f"{val:,.2f}" if isinstance(val, (int, float)) else str(val)
            if prev_val is not None and isinstance(val, (int, float)) and isinstance(prev_val, (int, float)):
                diff = val - prev_val
                sign = "+" if diff > 0 else ""
                change_str = f"{sign}{diff:,.2f}"
            else:
                change_str = "-"
            prev_val = val
        lines.append(f"| {date_str} | {val_str} | {change_str} |")

    return "\n".join(lines)


async def fetch_fred_series_observations(
    series_id_or_alias: str,
    lookback_periods: int = 12,
    units: str = "lin",
    frequency: str | None = None,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Fetches observations for a FRED series with Supabase caching and graceful fallbacks.

    Args:
        series_id_or_alias: Alias name (e.g. 'fed_funds', 'yield_curve_10y2y') or raw ID (e.g. 'FEDFUNDS').
        lookback_periods: Max observations to retrieve (default: 12).
        units: Transformation unit ('lin'=Levels, 'chg'=Change, 'ch1'=Change from 1 year ago, 'pch'=Percent Change, 'pc1'=Percent Change from 1 year ago).
        frequency: Optional aggregation frequency ('d'=Daily, 'w'=Weekly, 'm'=Monthly, 'q'=Quarterly, 'a'=Annual).
        force_refresh: If True, bypass cache and fetch directly from FRED API.

    Returns:
        Dict containing series metadata and list of observation dictionaries.
    """
    resolved_id = resolve_series_alias(series_id_or_alias)
    alias_meta = FRED_SERIES_ALIASES.get(series_id_or_alias.strip().lower(), {})
    title = alias_meta.get("title", resolved_id)

    # 1. Check Supabase cache
    cached_record = None
    try:
        sb = await get_async_supabase_client()
        res = (
            await sb.table("fred_series_cache")
            .select("series_id, title, units, frequency, latest_date, latest_value, observations, fetched_at")
            .eq("series_id", resolved_id)
            .execute()
        )
        if res and res.data and len(res.data) > 0:
            cached_record = res.data[0]
            fetched_at_str = cached_record.get("fetched_at")
            if fetched_at_str and not force_refresh:
                # Check TTL
                fetched_at = datetime.fromisoformat(fetched_at_str.replace("Z", "+00:00"))
                if datetime.now(UTC) - fetched_at < timedelta(hours=FRED_CACHE_TTL_HOURS):
                    cached_obs = cached_record.get("observations") or []
                    return {
                        "series_id": resolved_id,
                        "title": cached_record.get("title") or title,
                        "units": cached_record.get("units") or units,
                        "frequency": cached_record.get("frequency") or "N/A",
                        "latest_date": cached_record.get("latest_date") or "",
                        "latest_value": cached_record.get("latest_value"),
                        "observations": cached_obs[-lookback_periods:] if cached_obs else [],
                    }
    except Exception as e:
        logger.warning(f"Error querying fred_series_cache in Supabase: {e}")

    # 2. Fetch from FRED API
    if not FRED_API_KEY:
        logger.warning("FRED_API_KEY is not configured; using cached data or fallback.")
        if cached_record:
            cached_obs = cached_record.get("observations") or []
            return {
                "series_id": resolved_id,
                "title": cached_record.get("title") or title,
                "units": cached_record.get("units") or units,
                "frequency": cached_record.get("frequency") or "N/A",
                "latest_date": cached_record.get("latest_date") or "",
                "latest_value": cached_record.get("latest_value"),
                "observations": cached_obs[-lookback_periods:] if cached_obs else [],
            }
        return {
            "series_id": resolved_id,
            "title": title,
            "units": units,
            "frequency": frequency or "N/A",
            "latest_date": "",
            "latest_value": None,
            "observations": [],
            "error": "FRED_API_KEY is not set and no cached data is available.",
        }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            meta_title = title
            meta_units = units
            meta_frequency = frequency or "N/A"

            # Fetch metadata
            meta_params = {
                "series_id": resolved_id,
                "api_key": FRED_API_KEY,
                "file_type": "json",
            }
            meta_resp = await client.get(f"{FRED_BASE_URL}/series", params=meta_params)
            meta_data = meta_resp.json() if meta_resp.status_code == 200 else {}
            seriess = meta_data.get("seriess", [{}])
            if seriess:
                meta_title = seriess[0].get("title", title)
                meta_units = seriess[0].get("units_short", units)
                meta_frequency = seriess[0].get("frequency", "N/A")

            # Fetch observations
            obs_params: dict[str, Any] = {
                "series_id": resolved_id,
                "api_key": FRED_API_KEY,
                "file_type": "json",
                "sort_order": "desc",
                "limit": lookback_periods,
            }
            if units:
                obs_params["units"] = units
            # Only include frequency in observations query if explicitly passed as a short code (e.g. 'd', 'w', 'm', 'q', 'a')
            if frequency and len(frequency) <= 3:
                obs_params["frequency"] = frequency.lower()

            obs_resp = await client.get(f"{FRED_BASE_URL}/series/observations", params=obs_params)
            if obs_resp.status_code != 200:
                logger.error(f"FRED API observations error for {resolved_id}: {obs_resp.status_code} {obs_resp.text}")
                if cached_record:
                    cached_obs = cached_record.get("observations") or []
                    return {
                        "series_id": resolved_id,
                        "title": cached_record.get("title") or title,
                        "units": cached_record.get("units") or units,
                        "frequency": cached_record.get("frequency") or "N/A",
                        "latest_date": cached_record.get("latest_date") or "",
                        "latest_value": cached_record.get("latest_value"),
                        "observations": cached_obs[-lookback_periods:] if cached_obs else [],
                    }
                return {
                    "series_id": resolved_id,
                    "title": title,
                    "units": units,
                    "frequency": frequency or "N/A",
                    "latest_date": "",
                    "latest_value": None,
                    "observations": [],
                    "error": f"FRED API error: HTTP {obs_resp.status_code}",
                }

            obs_data = obs_resp.json().get("observations", [])
            parsed_obs = []
            for item in reversed(obs_data):  # Put in chronological order
                raw_val = item.get("value")
                val = None
                if raw_val not in (None, ".", ""):
                    try:
                        val = float(raw_val)
                    except ValueError:
                        val = None
                parsed_obs.append({"date": item.get("date"), "value": val})

            latest_date = parsed_obs[-1]["date"] if parsed_obs else ""
            latest_value = parsed_obs[-1]["value"] if parsed_obs else None

            # Upsert into Supabase cache
            try:
                sb = await get_async_supabase_client()
                await (
                    sb.table("fred_series_cache")
                    .upsert(
                        {
                            "series_id": resolved_id,
                            "title": meta_title,
                            "units": meta_units,
                            "frequency": meta_frequency,
                            "latest_date": latest_date,
                            "latest_value": latest_value,
                            "observations": parsed_obs,
                            "fetched_at": datetime.now(UTC).isoformat(),
                        }
                    )
                    .execute()
                )
            except Exception as e:
                logger.warning(f"Failed to upsert series {resolved_id} to fred_series_cache: {e}")

            return {
                "series_id": resolved_id,
                "title": meta_title,
                "units": meta_units,
                "frequency": meta_frequency,
                "latest_date": latest_date,
                "latest_value": latest_value,
                "observations": parsed_obs,
            }

    except Exception as e:
        logger.exception(f"Exception fetching FRED series {resolved_id}: {e}")
        if cached_record:
            cached_obs = cached_record.get("observations") or []
            return {
                "series_id": resolved_id,
                "title": cached_record.get("title") or title,
                "units": cached_record.get("units") or units,
                "frequency": cached_record.get("frequency") or "N/A",
                "latest_date": cached_record.get("latest_date") or "",
                "latest_value": cached_record.get("latest_value"),
                "observations": cached_obs[-lookback_periods:] if cached_obs else [],
            }
        return {
            "series_id": resolved_id,
            "title": title,
            "units": units,
            "frequency": frequency or "N/A",
            "latest_date": "",
            "latest_value": None,
            "observations": [],
            "error": str(e),
        }


async def get_curated_macro_dashboard(indicators: list[str] | None = None) -> str:
    """Fetches a snapshot of key macroeconomic indicators to inject as structured context.

    Args:
        indicators: Optional list of indicator aliases or series IDs (defaults to core macro benchmark pack).

    Returns:
        Formatted summary string describing current macro conditions.
    """
    if not indicators:
        indicators = [
            "fed_funds",
            "treasury_10y",
            "treasury_2y",
            "yield_curve_10y2y",
            "cpi",
            "core_cpi",
            "unemployment",
            "high_yield_spread",
            "m2",
            "pce",
        ]

    lines = ["=== Macro & Economic Context (FRED) ==="]
    for key in indicators:
        try:
            data = await fetch_fred_series_observations(key, lookback_periods=3)
            title = data.get("title", key)
            latest_val = data.get("latest_value")
            latest_date = data.get("latest_date", "N/A")
            units = data.get("units", "")
            val_str = f"{latest_val:,.2f}" if isinstance(latest_val, (int, float)) else "N/A"
            lines.append(f"- **{title}** (`{data.get('series_id')}`): {val_str} {units} (as of {latest_date})")
        except Exception as e:
            logger.warning(f"Error compiling macro dashboard item {key}: {e}")

    return "\n".join(lines)
