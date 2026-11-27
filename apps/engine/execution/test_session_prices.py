"""Hermetic tests for session-scoped entry prices.

A trade stamped with a past session must use that session's bar, never a live
quote from the day the backfill happens to run.
"""

import asyncio
from types import SimpleNamespace

from execution.picks_fakes import FakeSupabase
from execution.session_prices import resolve_entry_prices

SESSION = "2026-11-19"


def _bar(ticker, open_price=100.0):
    return {
        "ticker": ticker,
        "fetched_at": f"{SESSION}T14:30:00Z",
        "open": open_price,
        "price": 105.0,
        "high": 110.0,
        "low": 90.0,
        "close": 105.0,
    }


def _live_quotes(tickers):
    async def _fetch(_tickers):
        return {t: SimpleNamespace(open_price=None, price=83.0) for t in tickers}

    return _fetch


def test_historical_session_uses_bar_open_not_live_quote():
    store = FakeSupabase({"price_history": [_bar("ANT", 100.0)]})
    calls = []

    async def _forbidden(_tickers):
        calls.append("live")
        return {}

    prices, missing = asyncio.run(
        resolve_entry_prices(
            ["ANT"],
            SESSION,
            client=store,
            quote_fetcher=_forbidden,
            today="2026-11-27",
        )
    )

    assert prices == {"ANT": 100.0}
    assert missing == []
    assert calls == []


def test_historical_session_falls_back_to_bar_price_without_open():
    row = _bar("XLF")
    row["open"] = None
    store = FakeSupabase({"price_history": [row]})

    prices, missing = asyncio.run(resolve_entry_prices(["XLF"], SESSION, client=store, today="2026-11-27"))

    assert prices == {"XLF": 105.0}
    assert missing == []


def test_historical_session_without_bar_is_missing_not_live():
    store = FakeSupabase({"price_history": [_bar("AAA")]})

    prices, missing = asyncio.run(
        resolve_entry_prices(
            ["AAA", "BBB"],
            SESSION,
            client=store,
            quote_fetcher=_live_quotes(["BBB"]),
            today="2026-11-27",
        )
    )

    assert prices == {"AAA": 100.0}
    assert missing == ["BBB"]


def test_current_session_keeps_live_open_price():
    store = FakeSupabase({"price_history": [_bar("SPY")]})

    prices, missing = asyncio.run(
        resolve_entry_prices(
            ["SPY"],
            SESSION,
            client=store,
            quote_fetcher=_live_quotes(["SPY"]),
            today=SESSION,
        )
    )

    assert prices == {"SPY": 83.0}
    assert missing == []
