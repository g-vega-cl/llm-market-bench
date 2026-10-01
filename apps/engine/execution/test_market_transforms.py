"""Unit tests for market_transforms module."""

import datetime

from execution.market_transforms import compute_premarket_quote, validate_date_coverage
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
