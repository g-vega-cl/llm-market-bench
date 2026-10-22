"""Hermetic tests for the Alpaca open-interest max pain provider."""

import datetime
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from execution.providers import alpaca_max_pain as amp

EXP = "2026-10-22"


def _contract(strike: float, ctype: str, oi: int | None, exp: str = EXP) -> dict:
    row = {
        "symbol": f"SPY{exp}{ctype[0]}{strike}",
        "expiration_date": exp,
        "type": ctype,
        "strike_price": str(strike),
        "open_interest": None if oi is None else str(oi),
        "open_interest_date": "2026-10-21",
    }
    return row


def _brute_force_max_pain(contracts: list[dict]) -> float:
    strikes = sorted({float(c["strike_price"]) for c in contracts})
    best, best_pay = None, float("inf")
    for s in strikes:
        pay = 0.0
        for c in contracts:
            k, oi = float(c["strike_price"]), int(c["open_interest"] or 0)
            pay += max(0.0, s - k) * oi if c["type"] == "call" else max(0.0, k - s) * oi
        if pay < best_pay:
            best, best_pay = s, pay
    return best


def _chain() -> list[dict]:
    """Asymmetric 15-strike chain: heavy put OI below spot pulls max pain downward from the ATM strike."""
    rows = []
    for i, k in enumerate(range(750, 780)):
        rows.append(_contract(float(k), "call", 100 + 40 * i))
        rows.append(_contract(float(k), "put", 4000 - 120 * i))
    return rows


def _mock_client(rows_by_page: list[list[dict]], seen: list[httpx.Request] | None = None) -> httpx.AsyncClient:
    state = {"i": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        i = state["i"]
        state["i"] += 1
        page = rows_by_page[min(i, len(rows_by_page) - 1)]
        body = {"option_contracts": page, "next_page_token": f"tok{i + 1}" if i + 1 < len(rows_by_page) else None}
        return httpx.Response(200, json=body)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_max_pain_matches_brute_force_and_is_not_atm():
    chain = _chain()
    expected = _brute_force_max_pain(chain)
    seen: list[httpx.Request] = []
    async with _mock_client([chain[:20], chain[20:]], seen) as client:
        with patch.object(amp, "ALPACA_API_KEY", "k"), patch.object(amp, "ALPACA_SECRET_KEY", "s"):
            res = await amp.get_verified_max_pain("SPY", expiration_date=EXP, client=client)
    assert res is not None
    assert res["max_pain"] == expected
    assert res["expiration"] == EXP
    assert res["n_strikes"] == 30
    assert res["source"] == "alpaca_open_interest"
    assert res["open_interest_date"] == "2026-10-21"
    assert res["put_call_oi_ratio"] == pytest.approx(res["total_put_oi"] / res["total_call_oi"], rel=1e-3)
    # pagination followed and auth headers sent
    assert len(seen) == 2
    assert seen[0].headers["APCA-API-KEY-ID"] == "k"
    assert seen[0].headers["APCA-API-SECRET-KEY"] == "s"
    assert seen[1].url.params["page_token"] == "tok1"
    assert seen[0].url.params["expiration_date"] == EXP
    assert seen[0].url.params["underlying_symbols"] == "SPY"


@pytest.mark.asyncio
async def test_insufficient_strikes_returns_none():
    rows = [_contract(763.0, "call", 233), _contract(763.0, "put", 11416)]
    async with _mock_client([rows]) as client:
        with patch.object(amp, "ALPACA_API_KEY", "k"), patch.object(amp, "ALPACA_SECRET_KEY", "s"):
            assert await amp.get_verified_max_pain("SPY", expiration_date=EXP, client=client) is None


@pytest.mark.asyncio
async def test_missing_open_interest_returns_none():
    rows = [_contract(float(k), t, None) for k in range(750, 770) for t in ("call", "put")]
    async with _mock_client([rows]) as client:
        with patch.object(amp, "ALPACA_API_KEY", "k"), patch.object(amp, "ALPACA_SECRET_KEY", "s"):
            assert await amp.get_verified_max_pain("SPY", expiration_date=EXP, client=client) is None


@pytest.mark.asyncio
async def test_missing_credentials_returns_none_without_http():
    with patch.object(amp, "ALPACA_API_KEY", None), patch.object(amp, "ALPACA_SECRET_KEY", None):
        assert await amp.get_verified_max_pain("SPY", expiration_date=EXP) is None


@pytest.mark.asyncio
async def test_http_error_returns_none():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"message": "forbidden"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with patch.object(amp, "ALPACA_API_KEY", "k"), patch.object(amp, "ALPACA_SECRET_KEY", "s"):
            assert await amp.get_verified_max_pain("SPY", expiration_date=EXP, client=client) is None


@pytest.mark.asyncio
async def test_resolves_nearest_expiration_when_none_given():
    today = datetime.date(2026, 10, 22)
    near, far = "2026-10-23", "2026-10-30"
    probe = [_contract(750.0, "call", 1, far), _contract(750.0, "call", 1, near)]
    chain = [_contract(float(k), t, 100 + k % 7, near) for k in range(750, 770) for t in ("call", "put")]
    seen: list[httpx.Request] = []
    async with _mock_client([probe, chain], seen) as client:
        with patch.object(amp, "ALPACA_API_KEY", "k"), patch.object(amp, "ALPACA_SECRET_KEY", "s"):
            res = await amp.get_verified_max_pain("SPY", min_dte=1, today=today, client=client)
    assert res is not None
    assert res["expiration"] == near
    assert seen[0].url.params["expiration_date_gte"] == "2026-10-23"
    assert seen[1].url.params["expiration_date"] == near


@pytest.mark.asyncio
async def test_no_expiration_found_returns_none():
    async with _mock_client([[]]) as client:
        with patch.object(amp, "ALPACA_API_KEY", "k"), patch.object(amp, "ALPACA_SECRET_KEY", "s"):
            assert await amp.get_verified_max_pain("SPY", min_dte=0, client=client) is None


@pytest.mark.asyncio
async def test_massive_free_tier_max_pain_is_replaced_by_verified_value():
    """Free-tier Massive snapshots (4 contracts) must not publish a bogus max pain."""
    from execution.providers.massive import MassiveOptionsClient

    free_tier_contracts = [
        {
            "details": {"ticker": "x", "contract_type": ct, "strike_price": k, "expiration_date": EXP},
            "day": {"volume": v},
            "open_interest": v,
            "implied_volatility": 0.2,
            "greeks": {},
        }
        for ct, k, v in (("call", 763.0, 233), ("put", 763.0, 11416), ("call", 768.0, 3685), ("put", 758.0, 4631))
    ]
    verified = {"max_pain": 755.0, "expiration": EXP, "n_strikes": 30, "source": "alpaca_open_interest"}

    client = MassiveOptionsClient(api_key="x")
    client._get_supabase = lambda: None
    with (
        patch.object(MassiveOptionsClient, "_snapshot_supported", False),
        patch.object(client, "_fetch_free_tier_contracts", AsyncMock(return_value=free_tier_contracts)),
        patch("execution.providers.alpaca_max_pain.get_verified_max_pain", AsyncMock(return_value=verified)) as gv,
    ):
        snap = await client.get_options_snapshot("SPY", current_price=763.35, force_refresh=True, min_dte=0)
    assert snap["metrics"]["max_pain"] == 755.0
    assert snap["metrics"]["max_pain_source"] == "alpaca_open_interest"
    assert gv.await_args.kwargs["expiration_date"] == EXP

    client2 = MassiveOptionsClient(api_key="x")
    client2._get_supabase = lambda: None
    with (
        patch.object(MassiveOptionsClient, "_snapshot_supported", False),
        patch.object(client2, "_fetch_free_tier_contracts", AsyncMock(return_value=free_tier_contracts)),
        patch("execution.providers.alpaca_max_pain.get_verified_max_pain", AsyncMock(return_value=None)),
    ):
        snap2 = await client2.get_options_snapshot("SPY", current_price=763.35, force_refresh=True, min_dte=0)
    assert snap2["metrics"]["max_pain"] is None


@pytest.mark.asyncio
async def test_stale_open_interest_returns_none():
    """Open interest older than the OCC publication lag allows must not be treated as current."""
    chain = _chain()
    for row in chain:
        row["open_interest_date"] = "2026-10-01"
    async with _mock_client([chain]) as client:
        with patch.object(amp, "ALPACA_API_KEY", "k"), patch.object(amp, "ALPACA_SECRET_KEY", "s"):
            res = await amp.get_verified_max_pain(
                "SPY", expiration_date=EXP, today=datetime.date(2026, 10, 22), client=client
            )
    assert res is None


@pytest.mark.asyncio
async def test_recent_open_interest_with_lag_is_accepted():
    """A 2-day OCC lag (typical) is accepted and reported with its age."""
    chain = _chain()
    for row in chain:
        row["open_interest_date"] = "2026-10-20"
    async with _mock_client([chain]) as client:
        with patch.object(amp, "ALPACA_API_KEY", "k"), patch.object(amp, "ALPACA_SECRET_KEY", "s"):
            res = await amp.get_verified_max_pain(
                "SPY", expiration_date=EXP, today=datetime.date(2026, 10, 22), client=client
            )
    assert res is not None
    assert res["open_interest_age_days"] == 2
