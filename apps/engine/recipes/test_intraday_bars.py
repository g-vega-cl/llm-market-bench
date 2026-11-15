"""Hermetic tests for 3x/day ET slot expansion, intraday bar resolution, and Postgres caching."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _mock_sb_with_bars(rows: list[dict] | None = None) -> MagicMock:
    sb = MagicMock()
    table_mock = MagicMock()
    sb.table.return_value = table_mock
    for method in ("select", "eq", "gte", "lte", "order", "limit", "upsert"):
        getattr(table_mock, method).return_value = table_mock
    table_mock.execute.return_value = MagicMock(data=rows or [])
    return sb


def test_expand_dates_to_et_slots_respects_dst_and_order():
    from recipes.intraday_bars import TRADING_SLOTS_ET, expand_dates_to_et_slots

    assert TRADING_SLOTS_ET == ((9, 30), (12, 30), (15, 30))
    # 2026-03-06 is EST (-05:00); 2026-06-15 is EDT (-04:00)
    slots = expand_dates_to_et_slots(["2026-03-06", "2026-06-15"])
    assert len(slots) == 6
    assert slots[0]["slot_label"] == "2026-03-06 09:30 ET"
    assert slots[0]["timestamp_utc"] == datetime(2026, 3, 6, 14, 30, tzinfo=UTC)
    assert slots[1]["slot_label"] == "2026-03-06 12:30 ET"
    assert slots[2]["slot_label"] == "2026-03-06 15:30 ET"
    assert slots[3]["slot_label"] == "2026-06-15 09:30 ET"
    assert slots[3]["timestamp_utc"] == datetime(2026, 6, 15, 13, 30, tzinfo=UTC)


def test_resolve_slot_price_uses_exact_bar_open_and_avoids_future_lookahead():
    from recipes.intraday_bars import resolve_slot_price

    # 2026-06-15 is EDT (-04:00): 09:30 ET = 13:30Z, 12:30 ET = 16:30Z, 15:30 ET = 19:30Z
    bars = [
        {
            "bar_time_utc": "2026-06-15T13:30:00+00:00",
            "open": 100.0,
            "high": 102.0,
            "low": 99.5,
            "close": 101.8,
        },
        {
            "bar_time_utc": "2026-06-15T16:00:00+00:00",
            "open": 103.0,
            "high": 104.5,
            "low": 102.5,
            "close": 104.2,
        },
        {
            "bar_time_utc": "2026-06-15T20:00:00+00:00",  # Future relative to 15:30 ET (19:30Z)!
            "open": 108.0,
            "high": 109.0,
            "low": 107.0,
            "close": 108.5,
        },
    ]

    # Exact bar timestamp match uses bar.open (price at 09:30 ET, before 10:30 close of 101.8)
    p_open = resolve_slot_price(bars, {}, "NVDA", datetime(2026, 6, 15, 13, 30, tzinfo=UTC))
    assert p_open == 100.0

    # Prior bar <= slot uses bar.close (16:00Z bar closes just before 16:30Z)
    p_mid = resolve_slot_price(bars, {}, "NVDA", datetime(2026, 6, 15, 16, 30, tzinfo=UTC))
    assert p_mid == 104.2

    # 15:30 ET (19:30Z) must NOT use 20:00Z future bar OR same-day EOD close (lookahead!)
    p_late = resolve_slot_price(
        bars, {"NVDA": {"2026-06-15": 105.0}}, "NVDA", datetime(2026, 6, 15, 19, 30, tzinfo=UTC)
    )
    assert p_late is None

    # Falls back only to strictly prior trading days (< day_et)
    p_prior = resolve_slot_price(
        bars,
        {"NVDA": {"2026-06-14": 102.0, "2026-06-15": 105.0}},
        "NVDA",
        datetime(2026, 6, 15, 19, 30, tzinfo=UTC),
    )
    assert p_prior == 102.0

    # A bar timestamped even 60s AFTER slot_dt_utc must never match (no future leakage)
    p_future = resolve_slot_price(
        bars,
        {},
        "NVDA",
        datetime(2026, 6, 15, 19, 59, tzinfo=UTC),
    )
    assert p_future is None


def test_has_slot_coverage_requires_three_bars_per_day():
    from recipes.intraday_bars import _has_slot_coverage

    one_bar = [{"bar_time_utc": "2026-06-15T13:30:00+00:00"}]
    three_bars = [
        {"bar_time_utc": "2026-06-15T13:30:00+00:00"},
        {"bar_time_utc": "2026-06-15T16:30:00+00:00"},
        {"bar_time_utc": "2026-06-15T19:30:00+00:00"},
    ]
    assert _has_slot_coverage(one_bar, "2026-06-15", "2026-06-15") is False
    assert _has_slot_coverage(three_bars, "2026-06-15", "2026-06-15") is True


@pytest.mark.asyncio
async def test_snapshot_live_intraday_bars_fetches_parallel_and_upserts_in_one_batch():
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock, patch

    from recipes.intraday_bars import snapshot_live_intraday_bars

    sb = MagicMock()
    bars_tbl = MagicMock()
    sb.table.return_value = bars_tbl

    mock_mgr = MagicMock()
    mock_mgr.get_quote = AsyncMock(
        side_effect=[
            SimpleNamespace(exists=True, price=125.0, open=124.0, high=126.0, low=123.5, volume=1000),
            SimpleNamespace(exists=True, price=510.0, open=508.0, high=511.0, low=507.0, volume=2000),
        ]
    )
    with patch("tools._compat.MarketDataManager", return_value=mock_mgr):
        count = await snapshot_live_intraday_bars(sb, ["nvda", "spy"], datetime(2026, 6, 15, 13, 30, tzinfo=UTC))

    assert count == 2
    bars_tbl.upsert.assert_called_once()
    payload = bars_tbl.upsert.call_args[0][0]
    assert {r["ticker"] for r in payload} == {"NVDA", "SPY"}
    assert bars_tbl.upsert.call_args.kwargs.get("on_conflict") == "ticker,bar_time_utc"


@pytest.mark.asyncio
async def test_fetch_intraday_bars_reads_postgres_first_then_fmp_and_upserts():
    from recipes.intraday_bars import fetch_intraday_bars_for_ticker

    sb = _mock_sb_with_bars(rows=[])
    fmp_bars = [
        {"date": "2026-04-06 09:30:00", "open": 110.0, "high": 112.0, "low": 109.5, "close": 111.5, "volume": 1000},
        {"date": "2026-04-06 12:30:00", "open": 112.0, "high": 113.0, "low": 111.5, "close": 112.8, "volume": 900},
        {"date": "2026-04-06 15:30:00", "open": 113.0, "high": 114.0, "low": 112.5, "close": 113.9, "volume": 1200},
    ]

    with patch("recipes.intraday_bars._fetch_fmp_hourly", new=AsyncMock(return_value=fmp_bars)):
        bars = await fetch_intraday_bars_for_ticker(sb, "nvda", "2026-04-06", "2026-04-06")

    assert len(bars) == 3
    assert bars[0]["bar_time_utc"] == "2026-04-06T13:30:00+00:00"
    assert bars[0]["source"] == "fmp"
    sb.table.assert_any_call("recipe_intraday_bars")
    assert sb.table.return_value.upsert.called


@pytest.mark.asyncio
async def test_fetch_intraday_bars_falls_back_to_alpaca_when_fmp_empty():
    from recipes.intraday_bars import fetch_intraday_bars_for_ticker

    sb = _mock_sb_with_bars(rows=[])
    alpaca_bars = [
        {
            "bar_time_utc": "2026-04-06T13:30:00+00:00",
            "open": 200.0,
            "high": 201.0,
            "low": 199.0,
            "close": 200.5,
            "volume": 500,
            "source": "alpaca",
        }
    ]

    with (
        patch("recipes.intraday_bars._fetch_fmp_hourly", new=AsyncMock(return_value=[])),
        patch("recipes.intraday_bars._fetch_alpaca_hourly", new=AsyncMock(return_value=alpaca_bars)),
    ):
        bars = await fetch_intraday_bars_for_ticker(sb, "AAPL", "2026-04-06", "2026-04-06")

    assert len(bars) == 1
    assert bars[0]["source"] == "alpaca"
    assert bars[0]["open"] == 200.0


@pytest.mark.asyncio
async def test_fetch_intraday_bars_uses_postgres_cache_without_api_calls():
    from recipes.intraday_bars import fetch_intraday_bars_for_ticker

    cached_rows = [
        {
            "ticker": "SPY",
            "bar_time_utc": "2026-04-06T13:30:00+00:00",
            "open": 510.0,
            "high": 512.0,
            "low": 509.0,
            "close": 511.0,
            "volume": 10,
            "source": "fmp",
        },
        {
            "ticker": "SPY",
            "bar_time_utc": "2026-04-06T16:30:00+00:00",
            "open": 511.0,
            "high": 513.0,
            "low": 510.0,
            "close": 512.0,
            "volume": 10,
            "source": "fmp",
        },
        {
            "ticker": "SPY",
            "bar_time_utc": "2026-04-06T19:30:00+00:00",
            "open": 512.0,
            "high": 514.0,
            "low": 511.0,
            "close": 513.0,
            "volume": 10,
            "source": "fmp",
        },
    ]
    sb = _mock_sb_with_bars(rows=cached_rows)

    with patch("recipes.intraday_bars._fetch_fmp_hourly", new=AsyncMock()) as mock_fmp:
        bars = await fetch_intraday_bars_for_ticker(sb, "SPY", "2026-04-06", "2026-04-06")

    assert len(bars) == 3
    mock_fmp.assert_not_called()
