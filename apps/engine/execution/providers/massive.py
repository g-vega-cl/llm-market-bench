"""Massive.com (Polygon.io) Options API provider with caching, rate-limiting, and analytics.

Supports both Paid Snapshot endpoints and Free Tier reference + EOD aggregate fallback
with local Black-Scholes Implied Volatility and Greeks computation.
"""

import asyncio
import datetime
import math
import time
from typing import Any

import httpx

from core.config import (
    MASSIVE_API_KEY,
    MASSIVE_BASE_URL,
    OPTIONS_CACHE_TTL_SECONDS,
    logger,
)
from core.db import get_supabase_client

# =============================================================================
# BLACK-SCHOLES ANALYTICAL ENGINE
# =============================================================================


def _std_norm_cdf(x: float) -> float:
    """Standard normal cumulative distribution function using math.erf."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _std_norm_pdf(x: float) -> float:
    """Standard normal probability density function."""
    return (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * x * x)


def black_scholes_price(
    s: float,
    k: float,
    t: float,
    r: float,
    sigma: float,
    contract_type: str = "call",
) -> float:
    """Calculate theoretical Black-Scholes price for European options."""
    if t <= 0 or sigma <= 0 or s <= 0 or k <= 0:
        return max(0.0, s - k) if contract_type == "call" else max(0.0, k - s)

    d1 = (math.log(s / k) + (r + 0.5 * sigma * sigma) * t) / (sigma * math.sqrt(t))
    d2 = d1 - sigma * math.sqrt(t)

    if contract_type.lower() == "call":
        return s * _std_norm_cdf(d1) - k * math.exp(-r * t) * _std_norm_cdf(d2)
    else:
        return k * math.exp(-r * t) * _std_norm_cdf(-d2) - s * _std_norm_cdf(-d1)


def black_scholes_implied_volatility(
    price: float,
    s: float,
    k: float,
    t: float,
    r: float = 0.045,
    contract_type: str = "call",
    max_iter: int = 50,
) -> float | None:
    """Compute implied volatility via bisection search matching the observed option premium."""
    if price <= 0 or s <= 0 or k <= 0 or t <= 0:
        return None

    intrinsic = max(0.0, s - k) if contract_type.lower() == "call" else max(0.0, k - s)
    if price < intrinsic:
        return None

    low_vol = 0.001
    high_vol = 5.0  # 500% vol upper bound

    for _ in range(max_iter):
        mid_vol = (low_vol + high_vol) / 2.0
        mid_price = black_scholes_price(s, k, t, r, mid_vol, contract_type)
        diff = mid_price - price

        if abs(diff) < 1e-4:
            return round(mid_vol, 4)

        if diff > 0:
            high_vol = mid_vol
        else:
            low_vol = mid_vol

    return round((low_vol + high_vol) / 2.0, 4)


def black_scholes_greeks(
    s: float,
    k: float,
    t: float,
    r: float = 0.045,
    sigma: float = 0.30,
    contract_type: str = "call",
) -> dict[str, float]:
    """Calculate Delta, Gamma, Theta, and Vega using Black-Scholes formula."""
    if t <= 0 or sigma <= 0 or s <= 0 or k <= 0:
        return {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0}

    d1 = (math.log(s / k) + (r + 0.5 * sigma * sigma) * t) / (sigma * math.sqrt(t))
    d2 = d1 - sigma * math.sqrt(t)

    pdf_d1 = _std_norm_pdf(d1)
    is_call = contract_type.lower() == "call"

    delta = _std_norm_cdf(d1) if is_call else _std_norm_cdf(d1) - 1.0
    gamma = pdf_d1 / (s * sigma * math.sqrt(t))
    vega = (s * pdf_d1 * math.sqrt(t)) / 100.0  # Per 1% vol change

    # 1-day theta
    if is_call:
        theta = (-s * pdf_d1 * sigma / (2.0 * math.sqrt(t)) - r * k * math.exp(-r * t) * _std_norm_cdf(d2)) / 365.0
    else:
        theta = (-s * pdf_d1 * sigma / (2.0 * math.sqrt(t)) + r * k * math.exp(-r * t) * _std_norm_cdf(-d2)) / 365.0

    return {
        "delta": round(delta, 3),
        "gamma": round(gamma, 4),
        "theta": round(theta, 3),
        "vega": round(vega, 3),
    }


# =============================================================================
# RATE LIMITER
# =============================================================================


class AsyncTokenBucketLimiter:
    """Async token bucket rate limiter for external APIs (e.g. 5 req/min on Massive free tier)."""

    def __init__(self, max_tokens: float = 5.0, refill_period_seconds: float = 60.0):
        self.capacity = max_tokens
        self.tokens = max_tokens
        self.refill_rate = max_tokens / refill_period_seconds  # tokens per second
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until a token is available before returning."""
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self.last_update
                self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
                self.last_update = now

                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return

                # Calculate sleep duration needed for at least 1 token
                needed = 1.0 - self.tokens
                wait_time = max(0.1, needed / self.refill_rate)
                await asyncio.sleep(wait_time)


# Global limiter singleton for Massive API (5 req/min)
_MASSIVE_LIMITER = AsyncTokenBucketLimiter(max_tokens=5.0, refill_period_seconds=60.0)


# =============================================================================
# ANALYTICS DERIVERS & FORMATTERS
# =============================================================================


def calculate_max_pain(contracts: list[dict]) -> float | None:
    """Calculate the Max Pain strike price where option writers face minimum payout."""
    if not contracts:
        return None

    strikes = set()
    for c in contracts:
        details = c.get("details", {})
        strike = details.get("strike_price")
        if strike is not None:
            strikes.add(float(strike))

    if not strikes:
        return None

    sorted_strikes = sorted(strikes)
    min_total_payout = float("inf")
    max_pain_strike = None

    for target_strike in sorted_strikes:
        total_payout = 0.0
        for c in contracts:
            details = c.get("details", {})
            k = details.get("strike_price")
            ctype = details.get("contract_type", "").lower()
            oi = c.get("open_interest") or c.get("day", {}).get("volume") or 0

            if k is None or oi <= 0:
                continue

            k = float(k)
            if ctype == "call":
                payout = max(0.0, target_strike - k) * oi * 100
            elif ctype == "put":
                payout = max(0.0, k - target_strike) * oi * 100
            else:
                payout = 0.0

            total_payout += payout

        if total_payout < min_total_payout:
            min_total_payout = total_payout
            max_pain_strike = target_strike

    return max_pain_strike


def get_options_market_session(dt_utc: datetime.datetime | None = None) -> tuple[str, str, str]:
    """Determine market session status and staleness note for US equity options.

    Returns:
        tuple: (session_status, staleness_note, as_of_iso)
    """
    now_utc = dt_utc or datetime.datetime.now(datetime.UTC)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=datetime.UTC)

    try:
        import zoneinfo

        et_zone = zoneinfo.ZoneInfo("America/New_York")
    except Exception:
        et_zone = datetime.timezone(datetime.timedelta(hours=-4))

    now_et = now_utc.astimezone(et_zone)
    as_of_iso = now_utc.isoformat()

    # Weekend check
    if now_et.weekday() >= 5:
        session_status = "WEEKEND"
        staleness_note = "Market Closed (Weekend). Data reflects prior Friday closing settlement."
    else:
        et_time = now_et.time()
        market_open = datetime.time(9, 30)
        market_close = datetime.time(16, 0)

        if et_time < market_open:
            session_status = "PRE_MARKET"
            staleness_note = (
                "Pre-Market Session. Data reflects prior trading day closing settlement & overnight open interest. "
                "Intraday 0DTE trading begins at 9:30 AM ET."
            )
        elif et_time <= market_close:
            session_status = "REGULAR_HOURS"
            staleness_note = "Regular Trading Hours (Live / 15-minute delayed options snapshot)."
        else:
            session_status = "POST_MARKET"
            staleness_note = "Post-Market Session. Data reflects today's final closing settlement."

    return session_status, staleness_note, as_of_iso


def calculate_options_sentiment(
    ticker: str,
    contracts: list[dict],
    current_price: float | None = None,
    as_of_timestamp: str | None = None,
) -> dict[str, Any]:
    """Calculate high-level options market sentiment, IV, skew, and unusual activity with explicit session timestamps."""
    call_volume = 0
    put_volume = 0
    call_oi = 0
    put_oi = 0

    atm_contracts: list[tuple[float, float]] = []  # (distance, iv)
    put_25d_ivs: list[float] = []
    call_25d_ivs: list[float] = []
    unusual_activity: list[dict] = []

    ref_price = current_price

    for c in contracts:
        details = c.get("details", {})
        ctype = details.get("contract_type", "").lower()
        strike = details.get("strike_price")
        exp = details.get("expiration_date")
        day = c.get("day", {}) or {}
        vol = day.get("volume") or 0
        oi = c.get("open_interest") or 0
        iv = c.get("implied_volatility")
        greeks = c.get("greeks", {}) or {}
        delta = greeks.get("delta")

        if ctype == "call":
            call_volume += vol
            call_oi += oi
        elif ctype == "put":
            put_volume += vol
            put_oi += oi

        # Unusual options activity: high volume relative to open interest
        if vol > 500 and oi > 0 and vol >= 3 * oi:
            unusual_activity.append(
                {
                    "ticker": details.get("ticker", ""),
                    "contract_type": ctype,
                    "strike": strike,
                    "expiration": exp,
                    "volume": vol,
                    "open_interest": oi,
                    "ratio": round(vol / oi, 1),
                    "iv": round(iv * 100, 1) if iv else None,
                }
            )

        # Collect ATM IV
        if ref_price and strike and iv is not None and iv > 0:
            dist = abs(float(strike) - ref_price)
            atm_contracts.append((dist, float(iv)))

        # 25-Delta Skew detection (|delta| ~ 0.15 - 0.35)
        if delta is not None and iv is not None and iv > 0:
            if ctype == "put" and -0.35 <= delta <= -0.15:
                put_25d_ivs.append(float(iv))
            elif ctype == "call" and 0.15 <= delta <= 0.35:
                call_25d_ivs.append(float(iv))

    pv_ratio = round(put_volume / call_volume, 3) if call_volume > 0 else (1.0 if put_volume == 0 else 999.0)
    poi_ratio = round(put_oi / call_oi, 3) if call_oi > 0 else (1.0 if put_oi == 0 else 999.0)

    # ATM IV (closest strike to reference price)
    atm_iv = None
    if atm_contracts:
        atm_contracts.sort(key=lambda x: x[0])
        atm_iv = round(atm_contracts[0][1], 4)

    # 25-Delta Skew
    avg_put_iv = sum(put_25d_ivs) / len(put_25d_ivs) if put_25d_ivs else None
    avg_call_iv = sum(call_25d_ivs) / len(call_25d_ivs) if call_25d_ivs else None
    skew_diff = None
    if avg_put_iv is not None and avg_call_iv is not None:
        skew_diff = round((avg_put_iv - avg_call_iv) * 100, 2)

    max_pain = calculate_max_pain(contracts)
    unusual_activity.sort(key=lambda x: x["volume"], reverse=True)

    dt_obj = None
    if as_of_timestamp:
        try:
            dt_obj = datetime.datetime.fromisoformat(as_of_timestamp.replace("Z", "+00:00"))
        except Exception:
            dt_obj = None
    session_status, staleness_note, as_of_iso = get_options_market_session(dt_obj)

    return {
        "ticker": ticker.upper(),
        "underlying_price": ref_price,
        "as_of_timestamp": as_of_iso,
        "session_status": session_status,
        "staleness_note": staleness_note,
        "total_contracts_analyzed": len(contracts),
        "total_call_volume": call_volume,
        "total_put_volume": put_volume,
        "put_call_volume_ratio": pv_ratio,
        "total_call_oi": call_oi,
        "total_put_oi": put_oi,
        "put_call_oi_ratio": poi_ratio,
        "atm_implied_volatility": atm_iv,
        "volatility_skew_25d_diff_pct": skew_diff,
        "max_pain": max_pain,
        "unusual_activity": unusual_activity[:5],
    }


def filter_option_chain(
    contracts: list[dict],
    current_price: float | None = None,
    expiration_date: str | None = None,
    contract_type: str = "all",
    strike_range_pct: float = 10.0,
    min_dte: int | None = None,
    max_dte: int | None = None,
) -> list[dict]:
    """Filter raw contract list to near-the-money strikes and specific expirations."""
    if not contracts:
        return []

    today = datetime.datetime.now(datetime.UTC).date()
    target_type = contract_type.lower()
    min_strike = current_price * (1.0 - strike_range_pct / 100.0) if current_price else 0.0
    max_strike = current_price * (1.0 + strike_range_pct / 100.0) if current_price else float("inf")

    filtered = []
    for c in contracts:
        details = c.get("details", {})
        ctype = details.get("contract_type", "").lower()
        strike = details.get("strike_price")
        exp_str = details.get("expiration_date")

        if target_type in ("call", "put") and ctype != target_type:
            continue

        if strike is not None and (strike < min_strike or strike > max_strike):
            continue

        if exp_str:
            if expiration_date and exp_str != expiration_date:
                continue
            if min_dte is not None or max_dte is not None:
                try:
                    exp_date = datetime.date.fromisoformat(exp_str)
                    dte = (exp_date - today).days
                    if min_dte is not None and dte < min_dte:
                        continue
                    if max_dte is not None and dte > max_dte:
                        continue
                except Exception:
                    pass

        day = c.get("day", {}) or {}
        quote = c.get("last_quote", {}) or {}
        greeks = c.get("greeks", {}) or {}
        iv = c.get("implied_volatility")

        filtered.append(
            {
                "ticker": details.get("ticker", ""),
                "contract_type": ctype,
                "strike": strike,
                "expiration": exp_str,
                "bid": quote.get("bid"),
                "ask": quote.get("ask"),
                "last": day.get("close"),
                "volume": day.get("volume", 0),
                "open_interest": c.get("open_interest", 0),
                "iv": round(iv * 100, 1) if iv is not None else None,
                "delta": greeks.get("delta"),
                "gamma": greeks.get("gamma"),
                "theta": greeks.get("theta"),
                "vega": greeks.get("vega"),
            }
        )

    filtered.sort(key=lambda x: (x.get("expiration") or "", x.get("strike") or 0.0, x.get("contract_type") or ""))
    return filtered


def format_options_sentiment_markdown(metrics: dict) -> str:
    """Formats options sentiment dictionary into a compact Markdown summary with explicit staleness and zero bias."""
    ticker = metrics.get("ticker", "UNKNOWN")
    px_str = f"${metrics['underlying_price']:.2f}" if metrics.get("underlying_price") else "N/A"
    as_of = metrics.get("as_of_timestamp", "N/A")
    session = metrics.get("session_status", "N/A")
    staleness = metrics.get("staleness_note", "N/A")
    pv_ratio = metrics.get("put_call_volume_ratio", "N/A")
    poi_ratio = metrics.get("put_call_oi_ratio", "N/A")
    atm_iv = f"{metrics['atm_implied_volatility'] * 100:.1f}%" if metrics.get("atm_implied_volatility") else "N/A"
    max_pain = f"${metrics['max_pain']:.2f}" if metrics.get("max_pain") else "N/A"
    skew = (
        f"{metrics['volatility_skew_25d_diff_pct']:+.2f}%"
        if metrics.get("volatility_skew_25d_diff_pct") is not None
        else "N/A"
    )

    lines = [
        f"### 📊 Options Derivatives Positioning: {ticker} (Ref Price: {px_str})",
        f"- **As-Of Timestamp**: {as_of}",
        f"- **Market Session**: {session}",
        f"- **Staleness Note**: {staleness}",
        f"- **Put/Call Volume Ratio**: {pv_ratio} (Calls: {metrics.get('total_call_volume', 0):,}, Puts: {metrics.get('total_put_volume', 0):,})",
        f"- **Put/Call Open Interest Ratio**: {poi_ratio} (Calls: {metrics.get('total_call_oi', 0):,}, Puts: {metrics.get('total_put_oi', 0):,})",
        f"- **ATM Implied Volatility**: {atm_iv}",
        f"- **25-Delta Skew (Put IV - Call IV)**: {skew}",
        f"- **Max Pain Strike**: {max_pain}",
    ]

    unusual = metrics.get("unusual_activity", [])
    if unusual:
        lines.append("\n**⚡ Notable Options Activity (Vol > 3x OI):**")
        for u in unusual:
            lines.append(
                f"  • `{u['expiration']}` ${u['strike']} {u['contract_type'].upper()}: "
                f"Vol {u['volume']:,} vs OI {u['open_interest']:,} ({u['ratio']}x) | IV {u['iv']}%"
            )

    return "\n".join(lines)


def format_option_chain_markdown(ticker: str, contracts: list[dict], current_price: float | None = None) -> str:
    """Formats filtered options chain into a clean markdown table."""
    if not contracts:
        return f"No option contracts found matching criteria for {ticker}."

    px_str = f" (Underlying: ${current_price:.2f})" if current_price else ""
    lines = [
        f"### 📋 Option Chain for {ticker}{px_str} (Top {min(len(contracts), 25)} Strikes)",
        "| Exp Date | Type | Strike | Bid | Ask | Last | Vol | OI | IV | Δ (Delta) | Γ (Gamma) |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for c in contracts[:25]:
        exp = c.get("expiration", "N/A")
        ctype = c.get("contract_type", "").upper()
        strike = f"${c.get('strike', 0):.2f}"
        bid = f"${c.get('bid', 0):.2f}" if c.get("bid") is not None else "-"
        ask = f"${c.get('ask', 0):.2f}" if c.get("ask") is not None else "-"
        last = f"${c.get('last', 0):.2f}" if c.get("last") is not None else "-"
        vol = f"{c.get('volume', 0):,}"
        oi = f"{c.get('open_interest', 0):,}"
        iv = f"{c.get('iv', 0):.1f}%" if c.get("iv") is not None else "-"
        delta = f"{c.get('delta', 0):.2f}" if c.get("delta") is not None else "-"
        gamma = f"{c.get('gamma', 0):.3f}" if c.get("gamma") is not None else "-"

        lines.append(
            f"| {exp} | {ctype} | {strike} | {bid} | {ask} | {last} | {vol} | {oi} | {iv} | {delta} | {gamma} |"
        )

    if len(contracts) > 25:
        lines.append(
            f"\n*(Showing 25 of {len(contracts)} matching contracts. Narrow strike_range_pct or expiration_date for more specific views)*"
        )

    return "\n".join(lines)


# =============================================================================
# MASSIVE CLIENT (SNAPSHOT + FREE TIER FALLBACK)
# =============================================================================


class MassiveOptionsClient:
    """Client for Massive / Polygon Options API with rate-limiting, local Black-Scholes engine, and cache."""

    _memory_cache: dict[str, tuple[float, dict[str, Any]]] = {}

    def __init__(self, api_key: str | None = None, base_url: str | None = None, cache_ttl_seconds: int | None = None):
        self.api_key = api_key or MASSIVE_API_KEY
        self.base_url = (base_url or MASSIVE_BASE_URL).rstrip("/")
        self.cache_ttl_seconds = cache_ttl_seconds or OPTIONS_CACHE_TTL_SECONDS
        self._limiter = _MASSIVE_LIMITER

    def _get_supabase(self):
        """Helper to get Supabase client."""
        return get_supabase_client()

    async def _fetch_free_tier_contracts(
        self,
        ticker: str,
        current_price: float | None = None,
    ) -> list[dict[str, Any]]:
        """Fallback for Free Tier accounts: fetches contracts reference for calls and puts near spot + EOD bars, then calculates IV & Greeks locally."""
        today = datetime.datetime.now(datetime.UTC).date()
        today_str = today.isoformat()

        ref_px = current_price
        if not ref_px or ref_px <= 0:
            try:
                from execution.market_data import MarketDataManager

                mdm = MarketDataManager()
                quote = await mdm.get_quote(ticker)
                if quote and quote.price:
                    ref_px = float(quote.price)
            except Exception as e:
                logger.debug(f"Could not resolve spot price for {ticker} in free tier fallback: {e}")

        # Step 1: Query contracts reference for CALLS and PUTS near spot
        min_strike = ref_px * 0.96 if ref_px else None
        max_strike = ref_px * 1.04 if ref_px else None

        ref_contracts = []
        async with httpx.AsyncClient(timeout=15.0) as client:
            for c_type in ("call", "put"):
                await self._limiter.acquire()
                url = f"{self.base_url}/v3/reference/options/contracts"
                params = {
                    "underlying_ticker": ticker.upper(),
                    "contract_type": c_type,
                    "expiration_date.gte": today_str,
                    "limit": 50,
                    "apiKey": self.api_key,
                }
                if min_strike is not None:
                    params["strike_price.gte"] = min_strike
                if max_strike is not None:
                    params["strike_price.lte"] = max_strike

                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    contracts_batch = data.get("results", [])
                    ref_contracts.extend(contracts_batch)
                elif resp.status_code == 429:
                    logger.warning(
                        f"Rate limit querying {c_type} reference contracts for {ticker}; retrying after wait..."
                    )
                    await asyncio.sleep(12.0)
                    await self._limiter.acquire()
                    resp = await client.get(url, params=params)
                    if resp.status_code == 200:
                        ref_contracts.extend(resp.json().get("results", []))

            if not ref_contracts:
                return []

            # Step 2: Target nearest 1-2 active expirations
            exp_dates = sorted({c["expiration_date"] for c in ref_contracts if "expiration_date" in c})
            target_exps = exp_dates[:1] if exp_dates else []

            active_refs = [c for c in ref_contracts if c.get("expiration_date") in target_exps]
            if not ref_px and active_refs:
                ref_px = sum(c["strike_price"] for c in active_refs) / len(active_refs)

            # Separate calls and puts, sort by distance to spot price
            calls = [c for c in active_refs if c.get("contract_type") == "call"]
            puts = [c for c in active_refs if c.get("contract_type") == "put"]
            calls.sort(key=lambda c: abs(c.get("strike_price", 0) - ref_px))
            puts.sort(key=lambda c: abs(c.get("strike_price", 0) - ref_px))

            # Pick top 2 closest calls and top 2 closest puts
            target_selection = calls[:2] + puts[:2]

            # Step 3: Fetch previous day bars for selected target contracts
            results = []
            for target in target_selection:
                sym = target["ticker"]
                await self._limiter.acquire()
                bar_resp = await client.get(
                    f"{self.base_url}/v2/aggs/ticker/{sym}/prev",
                    params={"apiKey": self.api_key},
                )
                if bar_resp.status_code == 429:
                    logger.warning(f"Rate limit fetching prev bar for {sym}; retrying after wait...")
                    await asyncio.sleep(12.0)
                    await self._limiter.acquire()
                    bar_resp = await client.get(
                        f"{self.base_url}/v2/aggs/ticker/{sym}/prev",
                        params={"apiKey": self.api_key},
                    )

                bar = {}
                if bar_resp.status_code == 200:
                    bar_data = bar_resp.json().get("results", [])
                    if bar_data:
                        bar = bar_data[0]

                close_px = bar.get("c")
                vol = bar.get("v", 0)
                strike = float(target.get("strike_price", 0.0))
                exp_date_str = target.get("expiration_date", today_str)
                ctype = target.get("contract_type", "call")

                # Step 4: Compute local Black-Scholes IV and Greeks
                exp_date = datetime.date.fromisoformat(exp_date_str)
                dte = max(1, (exp_date - today).days)
                t_years = dte / 365.0

                iv = None
                greeks = {"delta": None, "gamma": None, "theta": None, "vega": None}
                if close_px and ref_px and strike and t_years > 0:
                    iv = black_scholes_implied_volatility(
                        price=close_px,
                        s=ref_px,
                        k=strike,
                        t=t_years,
                        r=0.045,
                        contract_type=ctype,
                    )
                    if iv is not None:
                        greeks = black_scholes_greeks(
                            s=ref_px,
                            k=strike,
                            t=t_years,
                            r=0.045,
                            sigma=iv,
                            contract_type=ctype,
                        )

                results.append(
                    {
                        "details": {
                            "ticker": sym,
                            "contract_type": ctype,
                            "strike_price": strike,
                            "expiration_date": exp_date_str,
                            "shares_per_contract": target.get("shares_per_contract", 100),
                        },
                        "day": {
                            "close": close_px,
                            "open": bar.get("o"),
                            "high": bar.get("h"),
                            "low": bar.get("l"),
                            "volume": vol,
                            "vwap": bar.get("vw"),
                        },
                        "last_quote": {
                            "bid": close_px,
                            "ask": close_px,
                        },
                        "implied_volatility": iv,
                        "greeks": greeks,
                        "open_interest": vol,
                    }
                )

            return results

    async def _fetch_from_api(self, ticker: str, current_price: float | None = None) -> dict[str, Any]:
        """Fetch options data, gracefully falling back to Free Tier pipeline on 403 NOT_AUTHORIZED."""
        if not self.api_key:
            raise ValueError("Massive/Polygon API key is not configured. Set MASSIVE_API_KEY in .env.")

        # Attempt Snapshot endpoint
        await self._limiter.acquire()
        url = f"{self.base_url}/v3/snapshot/options/{ticker.upper()}"
        params = {
            "apiKey": self.api_key,
            "limit": 250,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                return resp.json()

            if resp.status_code == 403:
                logger.info(
                    f"Massive snapshot requires paid plan for {ticker}; activating Free Tier EOD + local Black-Scholes pipeline."
                )
                results = await self._fetch_free_tier_contracts(ticker, current_price=current_price)
                return {"status": "OK", "results": results}

            if resp.status_code == 429:
                logger.warning(f"Massive rate limit reached for {ticker} (429). Retrying after backoff...")
                await asyncio.sleep(12.0)
                await self._limiter.acquire()
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    return resp.json()

            logger.error(f"Massive API error for {ticker}: {resp.status_code} - {resp.text}")
            return {"status": "ERROR", "error": resp.text, "results": []}

    async def get_options_snapshot(
        self,
        ticker: str,
        current_price: float | None = None,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """Retrieve options snapshot from Supabase cache, in-memory cache, or Massive API, computing metrics."""
        ticker = ticker.upper().strip()
        now_ts = time.time()

        # 1. Check in-memory process cache
        if not force_refresh and ticker in self._memory_cache:
            cached_time, cached_data = self._memory_cache[ticker]
            if now_ts - cached_time < self.cache_ttl_seconds:
                return cached_data

        sb = self._get_supabase()

        # 2. Check database cache
        if not force_refresh and sb:
            try:
                res = sb.table("options_data_cache").select("*").eq("ticker", ticker).execute()
                if res.data:
                    row = res.data[0]
                    fetched_at_str = row.get("fetched_at")
                    if fetched_at_str:
                        fetched_at = datetime.datetime.fromisoformat(fetched_at_str.replace("Z", "+00:00"))
                        now = datetime.datetime.now(datetime.UTC)
                        if (now - fetched_at).total_seconds() < self.cache_ttl_seconds:
                            metrics = row.get("metrics", {})
                            if "as_of_timestamp" not in metrics or "staleness_note" not in metrics:
                                sess, note, as_of_iso = get_options_market_session(fetched_at)
                                metrics["as_of_timestamp"] = metrics.get("as_of_timestamp") or as_of_iso
                                metrics["session_status"] = metrics.get("session_status") or sess
                                metrics["staleness_note"] = metrics.get("staleness_note") or note
                            contracts = row.get("contracts", [])
                            res_payload = {
                                "status": "OK",
                                "ticker": ticker,
                                "source": "db_cache",
                                "metrics": metrics,
                                "contracts": contracts,
                            }
                            self._memory_cache[ticker] = (now_ts, res_payload)
                            return res_payload
            except Exception as e:
                logger.warning(f"Error checking options_data_cache table in Supabase: {e}")

        # Ensure spot price is resolved if missing
        if not current_price or current_price <= 0:
            try:
                from execution.market_data import MarketDataManager

                mdm = MarketDataManager()
                quote = await mdm.get_quote(ticker)
                if quote and quote.price:
                    current_price = float(quote.price)
            except Exception as e:
                logger.debug(f"Could not resolve market quote for {ticker}: {e}")

        # 3. Fetch fresh snapshot from API (with automatic Free Tier fallback)
        raw_data = await self._fetch_from_api(ticker, current_price=current_price)
        results = raw_data.get("results", [])
        if not results:
            return {
                "status": "NO_DATA",
                "ticker": ticker,
                "metrics": {},
                "contracts": [],
            }

        # 4. Compute derived metrics
        now_iso = datetime.datetime.now(datetime.UTC).isoformat()
        metrics = calculate_options_sentiment(ticker, results, current_price=current_price, as_of_timestamp=now_iso)

        payload = {
            "status": "OK",
            "ticker": ticker,
            "source": "api",
            "metrics": metrics,
            "contracts": results,
        }
        self._memory_cache[ticker] = (now_ts, payload)

        # 5. Save to database cache
        if sb:
            try:
                sb.table("options_data_cache").upsert(
                    {
                        "ticker": ticker,
                        "metrics": metrics,
                        "contracts": results,
                        "fetched_at": now_iso,
                    }
                ).execute()
            except Exception as e:
                logger.warning(f"Failed to upsert options_data_cache in Supabase: {e}")

        return payload
