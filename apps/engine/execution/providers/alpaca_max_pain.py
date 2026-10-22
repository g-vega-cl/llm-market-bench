"""Verified Max Pain from Alpaca's OCC-sourced option contract open interest.

`GET /v2/options/contracts` returns every listed strike for an expiration with its
`open_interest` (end-of-previous-day, OCC). Max Pain is only meaningful over the *full*
chain, so this module refuses to answer (returns None) when the chain is thin or has no OI.
"""

import datetime
from typing import Any

import httpx

from core.config import ALPACA_API_KEY, ALPACA_PAPER_ENDPOINT, ALPACA_SECRET_KEY, logger
from execution.providers.massive import calculate_max_pain

MIN_STRIKES_WITH_OI = 10
PAGE_LIMIT = 1000
MAX_PAGES = 15
PROBE_WINDOW_DAYS = 10
MAX_OI_AGE_DAYS = 5  # OCC publishes with a 2-3 day lag; weekends add more
SOURCE_NAME = "alpaca_open_interest"


def _headers() -> dict[str, str]:
    return {"APCA-API-KEY-ID": ALPACA_API_KEY or "", "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY or ""}


async def _get_contracts(
    client: httpx.AsyncClient, params: dict[str, Any], max_pages: int = MAX_PAGES
) -> list[dict[str, Any]]:
    """Fetch (and paginate) option contracts. Raises on HTTP errors."""
    rows: list[dict[str, Any]] = []
    page_token: str | None = None
    for _ in range(max_pages):
        q = dict(params)
        if page_token:
            q["page_token"] = page_token
        resp = await client.get(f"{ALPACA_PAPER_ENDPOINT}/v2/options/contracts", params=q, headers=_headers())
        resp.raise_for_status()
        body = resp.json()
        rows.extend(body.get("option_contracts") or [])
        page_token = body.get("next_page_token")
        if not page_token:
            break
    return rows


async def _resolve_expiration(
    client: httpx.AsyncClient, underlying: str, min_dte: int, today: datetime.date
) -> str | None:
    """Find the nearest listed expiration at or after today + min_dte."""
    start = today + datetime.timedelta(days=min_dte)
    rows = await _get_contracts(
        client,
        {
            "underlying_symbols": underlying,
            "status": "active",
            "expiration_date_gte": start.isoformat(),
            "expiration_date_lte": (start + datetime.timedelta(days=PROBE_WINDOW_DAYS)).isoformat(),
            "limit": 100,
        },
        max_pages=1,
    )
    exps = sorted({r["expiration_date"] for r in rows if r.get("expiration_date")})
    return exps[0] if exps else None


def _to_massive_shape(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert Alpaca contract rows into the shape `calculate_max_pain` expects (skip rows without OI)."""
    out = []
    for r in rows:
        try:
            oi = int(float(r.get("open_interest") or 0))
            strike = float(r["strike_price"])
        except (KeyError, TypeError, ValueError):
            continue
        ctype = str(r.get("type", "")).lower()
        if oi <= 0 or ctype not in ("call", "put"):
            continue
        out.append(
            {
                "details": {
                    "contract_type": ctype,
                    "strike_price": strike,
                    "expiration_date": r.get("expiration_date"),
                },
                "open_interest": oi,
                "open_interest_date": r.get("open_interest_date"),
            }
        )
    return out


async def get_verified_max_pain(
    underlying: str,
    expiration_date: str | None = None,
    min_dte: int = 0,
    today: datetime.date | None = None,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any] | None:
    """Max Pain strike for one expiration from the full Alpaca open-interest chain, or None if unreliable."""
    if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
        logger.warning("Alpaca credentials missing; cannot compute verified Max Pain.")
        return None

    sym = underlying.upper().strip()
    today = today or datetime.datetime.now(datetime.UTC).date()
    owns_client = client is None
    http = client or httpx.AsyncClient(timeout=20.0)
    try:
        exp = expiration_date or await _resolve_expiration(http, sym, min_dte, today)
        if not exp:
            logger.warning(f"Alpaca: no active expiration found for {sym} (min_dte={min_dte}).")
            return None

        rows = await _get_contracts(
            http,
            {"underlying_symbols": sym, "status": "active", "expiration_date": exp, "limit": PAGE_LIMIT},
        )
    except Exception:
        logger.exception(f"Alpaca option contracts fetch failed for {sym}")
        return None
    finally:
        if owns_client:
            await http.aclose()

    contracts = _to_massive_shape(rows)
    strikes = {c["details"]["strike_price"] for c in contracts}
    if len(strikes) < MIN_STRIKES_WITH_OI:
        logger.warning(
            f"Alpaca chain for {sym} {exp} too thin for Max Pain ({len(strikes)} strikes with OI < {MIN_STRIKES_WITH_OI})."
        )
        return None

    oi_dates = [c["open_interest_date"] for c in contracts if c.get("open_interest_date")]
    oi_date = max(oi_dates) if oi_dates else None
    oi_age_days: int | None = None
    if oi_date:
        try:
            oi_age_days = (today - datetime.date.fromisoformat(str(oi_date)[:10])).days
        except ValueError:
            oi_age_days = None
    if oi_age_days is not None and oi_age_days > MAX_OI_AGE_DAYS:
        logger.warning(f"Alpaca open interest for {sym} {exp} is stale ({oi_date}, {oi_age_days}d old); no Max Pain.")
        return None

    max_pain = calculate_max_pain(contracts)
    if max_pain is None:
        return None

    call_oi = sum(c["open_interest"] for c in contracts if c["details"]["contract_type"] == "call")
    put_oi = sum(c["open_interest"] for c in contracts if c["details"]["contract_type"] == "put")
    return {
        "max_pain": max_pain,
        "expiration": exp,
        "n_strikes": len(strikes),
        "n_contracts": len(contracts),
        "total_call_oi": call_oi,
        "total_put_oi": put_oi,
        "put_call_oi_ratio": round(put_oi / call_oi, 4) if call_oi else None,
        "open_interest_date": oi_date,
        "open_interest_age_days": oi_age_days,
        "source": SOURCE_NAME,
    }
