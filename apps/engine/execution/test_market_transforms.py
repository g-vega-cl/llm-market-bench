"""Unit tests for market_transforms module."""

import datetime

from execution.market_transforms import (
    compute_premarket_quote,
    compute_reference_quote,
    validate_date_coverage,
)
from execution.providers.base import TickerData


def test_validate_date_coverage_empty():
    valid, reason = validate_date_coverage([], 10)
    assert not valid
    assert reason == "no data"


def test_validate_date_coverage_today_only():
    today = datetime.datetime.now(datetime.UTC).date().isoformat()
    rows = [
        {"price": 100.0, "fetched_at": f"{today}T10:00:00Z"},
        {"price": 101.0, "fetched_at": f"{today}T11:00:00Z"},
    ]
    valid, reason = validate_date_coverage(rows, 5)
    assert not valid
    assert "all 1 rows from today" in reason


def test_validate_date_coverage_min_dates_threshold():
    today = datetime.datetime.now(datetime.UTC).date().isoformat()
    yesterday = (datetime.datetime.now(datetime.UTC).date() - datetime.timedelta(days=1)).isoformat()
    # 2 distinct dates, but requested 10 days (requires ceil(10/2) = 5)
    rows = [
        {"price": 100.0, "fetched_at": f"{yesterday}T10:00:00Z"},
        {"price": 101.0, "fetched_at": f"{today}T10:00:00Z"},
    ]
    valid, reason = validate_date_coverage(rows, 10)
    assert not valid
    assert "only 2 distinct dates, need 5" in reason


def test_validate_date_coverage_stale():
    # Dates older than 4 days
    today = datetime.datetime.now(datetime.UTC).date()
    rows = [
        {"price": 100.0, "fetched_at": f"{(today - datetime.timedelta(days=10)).isoformat()}T10:00:00Z"},
        {"price": 101.0, "fetched_at": f"{(today - datetime.timedelta(days=9)).isoformat()}T10:00:00Z"},
        {"price": 102.0, "fetched_at": f"{(today - datetime.timedelta(days=8)).isoformat()}T10:00:00Z"},
    ]
    valid, reason = validate_date_coverage(rows, 4)
    assert not valid
    assert "cache is stale" in reason


def test_validate_date_coverage_valid_multi_day():
    today = datetime.datetime.now(datetime.UTC).date()
    rows = [
        {"price": 100.0, "fetched_at": f"{(today - datetime.timedelta(days=1)).isoformat()}T10:00:00Z"},
        {"price": 101.0, "fetched_at": f"{(today - datetime.timedelta(days=2)).isoformat()}T10:00:00Z"},
        {"price": 102.0, "fetched_at": f"{(today - datetime.timedelta(days=3)).isoformat()}T10:00:00Z"},
    ]
    valid, reason = validate_date_coverage(rows, 5)
    assert valid
    assert "valid cache with 3 distinct dates" in reason


def test_compute_premarket_quote_aftermarket_preferred():
    quote = TickerData(ticker="SPY", price=592.0, market_cap=800e9, exists=True, previous_close=590.0)
    aftermarket = {"symbol": "SPY", "price": 596.5, "volume": 50000}
    res = compute_premarket_quote(quote=quote, aftermarket_quote=aftermarket)
    assert res is not None
    assert res["price"] == 596.5
    assert res["previous_close"] == 592.0
    assert res["change"] == 4.5
    assert abs(res["change_pct"] - (4.5 / 592.0 * 100.0)) < 0.001
    assert res["volume"] == 50000


def test_compute_premarket_quote_standard_quote_fallback():
    quote = TickerData(
        ticker="AAPL",
        price=230.0,
        market_cap=3e12,
        exists=True,
        previous_close=225.0,
        change=5.0,
        change_pct=2.22,
        volume=1000000,
    )
    res = compute_premarket_quote(quote=quote)
    assert res is not None
    assert res["price"] == 230.0
    assert res["previous_close"] == 225.0
    assert res["change"] == 5.0
    assert res["change_pct"] == 2.22
    assert res["volume"] == 1000000


def test_compute_premarket_quote_history_fallback_for_prev_close():
    quote = TickerData(ticker="NVDA", price=120.0, market_cap=2e12, exists=True)
    history = [
        {"price": 115.0, "close": 115.0, "fetched_at": "2026-09-01T00:00:00Z"},
        {"price": 118.0, "close": 118.0, "fetched_at": "2026-09-02T00:00:00Z"},
    ]
    res = compute_premarket_quote(quote=quote, history=history)
    assert res is not None
    assert res["price"] == 120.0
    assert res["previous_close"] == 118.0
    assert res["change"] == 2.0
    assert abs(res["change_pct"] - (2.0 / 118.0 * 100.0)) < 0.001


def test_compute_premarket_quote_no_data():
    assert compute_premarket_quote(quote=None, aftermarket_quote=None) is None


def test_compute_reference_quote_complete_quote():
    """Verify quote with full price, previous_close, and change_pct is returned directly."""
    quote = TickerData(
        ticker="SPY",
        price=752.69,
        market_cap=800e9,
        exists=True,
        previous_close=735.29,
        change=17.40,
        change_pct=2.3664,
        volume=50000000,
    )
    res = compute_reference_quote(quote=quote)
    assert res is not None
    assert res["price"] == 752.69
    assert res["previous_close"] == 735.29
    assert abs(res["change"] - 17.40) < 0.01
    assert abs(res["change_pct"] - 2.3664) < 0.001
    assert res["volume"] == 50000000


def test_compute_reference_quote_missing_prev_close_resolves_descending_history():
    """Verify descending history is chronologically ordered so penultimate or prior bar is resolved."""
    quote = TickerData(ticker="DIA", price=450.0, market_cap=50e9, exists=True)
    # Descending bars as returned by cache/DB
    history = [
        {"close": 450.0, "date": "2026-11-09"},
        {"close": 442.0, "date": "2026-11-06"},
        {"close": 440.0, "date": "2026-11-05"},
    ]
    res = compute_reference_quote(quote=quote, history=history, target_date="2026-11-09")
    assert res is not None
    assert res["price"] == 450.0
    assert res["previous_close"] == 442.0
    assert abs(res["change"] - 8.0) < 0.001
    assert abs(res["change_pct"] - (8.0 / 442.0 * 100.0)) < 0.01


def test_compute_reference_quote_same_day_filtering():
    """Verify if history already has today's bar, prior close strictly filters to date < target_date."""
    quote = TickerData(ticker="QQQ", price=500.0, market_cap=1e12, exists=True)
    history = [
        {"close": 485.0, "fetched_at": "2026-11-06T20:00:00Z"},
        {"close": 500.0, "fetched_at": "2026-11-09T20:00:00Z"},
    ]
    res = compute_reference_quote(quote=quote, history=history, target_date="2026-11-09")
    assert res is not None
    assert res["price"] == 500.0
    assert res["previous_close"] == 485.0
    assert abs(res["change_pct"] - ((500.0 - 485.0) / 485.0 * 100.0)) < 0.01


def test_compute_reference_quote_historical_target_date_derives_from_history():
    """Verify historical backdate run ignores future live quote and uses historical bars."""
    live_future_quote = TickerData(ticker="SPY", price=999.0, market_cap=1e12, exists=True, previous_close=990.0)
    history = [
        {"close": 700.0, "date": "2026-10-01"},
        {"close": 710.0, "date": "2026-10-02"},
        {"close": 720.0, "date": "2026-10-03"},
    ]
    res = compute_reference_quote(quote=live_future_quote, history=history, target_date="2026-10-02")
    assert res is not None
    assert res["price"] == 710.0
    assert res["previous_close"] == 700.0
    assert abs(res["change"] - 10.0) < 0.01


def test_compute_reference_quote_null_quote_fallback():
    """Verify quote=None derives price and prior close from history."""
    history = [
        {"close": 1.0800, "date": "2026-11-06"},
        {"close": 1.0850, "date": "2026-11-09"},
    ]
    res = compute_reference_quote(quote=None, history=history, target_date="2026-11-09")
    assert res is not None
    assert res["price"] == 1.0850
    assert res["previous_close"] == 1.0800
    assert abs(res["change_pct"] - ((1.0850 - 1.0800) / 1.0800 * 100.0)) < 0.01


def test_compute_reference_quote_invalid_and_empty():
    """Verify compute_reference_quote gracefully returns None on missing or invalid data."""
    assert compute_reference_quote(quote=None, history=None) is None
    assert compute_reference_quote(quote=None, history=[]) is None
    bad_quote = TickerData(ticker="BAD", price=0.0, market_cap=0, exists=False)
    assert compute_reference_quote(quote=bad_quote, history=[]) is None
