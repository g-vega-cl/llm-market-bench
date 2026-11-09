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
    "treasury_3m": {
        "series_id": "DGS3MO",
        "title": "3-Month Treasury Constant Maturity Rate",
        "default_units": "lin",
        "category": "Bond Yields",
    },
    "treasury_2y": {
        "series_id": "DGS2",
        "title": "2-Year Treasury Constant Maturity Rate",
        "default_units": "lin",
        "category": "Bond Yields",
    },
    "treasury_5y": {
        "series_id": "DGS5",
        "title": "5-Year Treasury Constant Maturity Rate",
        "default_units": "lin",
        "category": "Bond Yields",
    },
    "treasury_10y": {
        "series_id": "DGS10",
        "title": "10-Year Treasury Constant Maturity Rate",
        "default_units": "lin",
        "category": "Bond Yields",
    },
    "treasury_30y": {
        "series_id": "DGS30",
        "title": "30-Year Treasury Constant Maturity Rate",
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
    "tga_weekly": {
        "series_id": "WTREGEN",
        "title": "Liabilities and Capital: U.S. Treasury, General Account: Week Average",
        "default_units": "lin",
        "category": "Liquidity",
    },
    "federal_deficit_monthly": {
        "series_id": "MTSDS133FMS",
        "title": "Federal Surplus or Deficit [-] as of Monthly Treasury Statement",
        "default_units": "lin",
        "category": "Fiscal Policy & Debt",
    },
    "federal_deficit_annual": {
        "series_id": "FYFSD",
        "title": "Federal Surplus or Deficit [-] (Annual)",
        "default_units": "lin",
        "category": "Fiscal Policy & Debt",
    },
    "federal_debt_to_gdp": {
        "series_id": "GFDEGDQ188S",
        "title": "Federal Debt: Total Public Debt as Percent of Gross Domestic Product",
        "default_units": "lin",
        "category": "Fiscal Policy & Debt",
    },
    "federal_interest_outlays": {
        "series_id": "A091RC1Q027SBEA",
        "title": "Federal Government Current Expenditures: Interest Payments",
        "default_units": "lin",
        "category": "Fiscal Policy & Debt",
    },
    "federal_expenditures": {
        "series_id": "FGEXPND",
        "title": "Federal Government: Current Expenditures",
        "default_units": "lin",
        "category": "Fiscal Policy & Debt",
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
    # Foreign Exchange
    "dollar_index": {
        "series_id": "DTWEXBGS",
        "title": "Nominal Broad U.S. Dollar Index",
        "default_units": "lin",
        "category": "Foreign Exchange",
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


def _format_cached_fred_result(
    cached_record: dict[str, Any],
    resolved_id: str,
    title: str,
    units: str,
    lookback_periods: int,
) -> dict[str, Any]:
    """Formats a cached Supabase record into the standard FRED observation dict."""
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


async def _fetch_cached_fred_record(resolved_id: str) -> dict[str, Any] | None:
    """Queries fred_series_cache in Supabase for a series_id."""
    try:
        sb = await get_async_supabase_client()
        res = (
            await sb.table("fred_series_cache")
            .select("series_id, title, units, frequency, latest_date, latest_value, observations, fetched_at")
            .eq("series_id", resolved_id)
            .execute()
        )
        if res and res.data and len(res.data) > 0:
            return res.data[0]
    except Exception as e:
        logger.warning(f"Error querying fred_series_cache in Supabase: {e}")
    return None


def _is_cache_fresh(cached_record: dict[str, Any], force_refresh: bool) -> bool:
    """Checks whether a cached FRED record is still within TTL."""
    if force_refresh:
        return False
    fetched_at_str = cached_record.get("fetched_at")
    if not fetched_at_str:
        return False
    fetched_at = datetime.fromisoformat(fetched_at_str.replace("Z", "+00:00"))
    return datetime.now(UTC) - fetched_at < timedelta(hours=FRED_CACHE_TTL_HOURS)


def _parse_fred_observations(obs_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parses raw FRED observation items into chronological date/float dicts."""
    parsed_obs = []
    for item in reversed(obs_data):
        raw_val = item.get("value")
        val = None
        if raw_val not in (None, ".", ""):
            try:
                val = float(raw_val)
            except ValueError:
                val = None
        parsed_obs.append({"date": item.get("date"), "value": val})
    return parsed_obs


async def _upsert_fred_cache(
    resolved_id: str,
    meta_title: str,
    meta_units: str,
    meta_frequency: str,
    latest_date: str,
    latest_value: float | None,
    parsed_obs: list[dict[str, Any]],
) -> None:
    """Upserts fetched FRED series observations into Supabase cache."""
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


async def _fetch_fred_metadata(
    client: httpx.AsyncClient,
    resolved_id: str,
    default_title: str,
    default_units: str,
    default_frequency: str,
) -> tuple[str, str, str]:
    """Fetches series title, units, and frequency from FRED /series endpoint."""
    meta_params = {
        "series_id": resolved_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
    }
    meta_resp = await client.get(f"{FRED_BASE_URL}/series", params=meta_params)
    meta_data = meta_resp.json() if meta_resp.status_code == 200 else {}
    seriess = meta_data.get("seriess", [{}])
    if seriess:
        return (
            seriess[0].get("title", default_title),
            seriess[0].get("units_short", default_units),
            seriess[0].get("frequency", "N/A"),
        )
    return default_title, default_units, default_frequency


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
    cached_record = await _fetch_cached_fred_record(resolved_id)
    if cached_record and _is_cache_fresh(cached_record, force_refresh):
        return _format_cached_fred_result(cached_record, resolved_id, title, units, lookback_periods)

    # 2. Fetch from FRED API
    if not FRED_API_KEY:
        logger.warning("FRED_API_KEY is not configured; using cached data or fallback.")
        if cached_record:
            return _format_cached_fred_result(cached_record, resolved_id, title, units, lookback_periods)
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
            meta_title, meta_units, meta_frequency = await _fetch_fred_metadata(
                client, resolved_id, title, units, frequency or "N/A"
            )

            obs_params: dict[str, Any] = {
                "series_id": resolved_id,
                "api_key": FRED_API_KEY,
                "file_type": "json",
                "sort_order": "desc",
                "limit": lookback_periods,
            }
            if units:
                obs_params["units"] = units
            if frequency and len(frequency) <= 3:
                obs_params["frequency"] = frequency.lower()

            obs_resp = await client.get(f"{FRED_BASE_URL}/series/observations", params=obs_params)
            if obs_resp.status_code != 200:
                logger.error(f"FRED API observations error for {resolved_id}: {obs_resp.status_code} {obs_resp.text}")
                if cached_record:
                    return _format_cached_fred_result(cached_record, resolved_id, title, units, lookback_periods)
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

            parsed_obs = _parse_fred_observations(obs_resp.json().get("observations", []))
            latest_date = parsed_obs[-1]["date"] if parsed_obs else ""
            latest_value = parsed_obs[-1]["value"] if parsed_obs else None

            await _upsert_fred_cache(
                resolved_id, meta_title, meta_units, meta_frequency, latest_date, latest_value, parsed_obs
            )

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
            return _format_cached_fred_result(cached_record, resolved_id, title, units, lookback_periods)
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
            "fed_balance_sheet",
            "federal_deficit_monthly",
            "pce",
            "dollar_index",
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
