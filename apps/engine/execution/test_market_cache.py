"""Unit tests for market_cache module."""

import datetime
from unittest.mock import MagicMock

from execution.market_cache import MarketDataCache
from execution.providers.base import TickerData


def test_market_cache_get_quote_hit():
    mock_client = MagicMock()
    now_iso = datetime.datetime.now(datetime.UTC).isoformat()
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"ticker": "AAPL", "price": 150.0, "market_cap": 2.5e12, "fetched_at": now_iso}
    ]

    cache = MarketDataCache(client=mock_client, cache_ttl_seconds=300)
    data = cache.get_quote("AAPL")

    assert data is not None
    assert data.ticker == "AAPL"
    assert data.price == 150.0
    assert data.market_cap == 2.5e12


def test_market_cache_get_quote_stale():
    mock_client = MagicMock()
    stale_iso = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(seconds=400)).isoformat()
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"ticker": "AAPL", "price": 150.0, "market_cap": 2.5e12, "fetched_at": stale_iso}
    ]

    cache = MarketDataCache(client=mock_client, cache_ttl_seconds=300)
    data = cache.get_quote("AAPL")
    assert data is None


def test_market_cache_get_quote_miss():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

    cache = MarketDataCache(client=mock_client, cache_ttl_seconds=300)
    data = cache.get_quote("AAPL")
    assert data is None


def test_market_cache_get_quotes_batch():
    mock_client = MagicMock()
    now_iso = datetime.datetime.now(datetime.UTC).isoformat()
    stale_iso = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(seconds=500)).isoformat()
    mock_client.table.return_value.select.return_value.in_.return_value.execute.return_value.data = [
        {"ticker": "AAPL", "price": 150.0, "market_cap": 2e12, "fetched_at": now_iso},
        {"ticker": "MSFT", "price": 400.0, "market_cap": 3e12, "fetched_at": stale_iso},
    ]

    cache = MarketDataCache(client=mock_client, cache_ttl_seconds=300)
    results, missing = cache.get_quotes_batch(["AAPL", "MSFT", "NVDA"])

    assert "AAPL" in results
    assert results["AAPL"].price == 150.0
    assert "MSFT" in missing
    assert "NVDA" in missing


def test_market_cache_save_quotes_batch_skips_nan():
    mock_client = MagicMock()
    cache = MarketDataCache(client=mock_client)

    nan_data = TickerData(ticker="BAD", price=float("nan"), market_cap=1e9, exists=True)
    valid_data = TickerData(ticker="GOOD", price=100.0, market_cap=1e9, exists=True, change_pct=1.5)

    cache.save_quotes_batch([nan_data, valid_data])

    mock_client.table.assert_called_once_with("market_data_cache")
    upsert_args = mock_client.table.return_value.upsert.call_args[0][0]
    assert len(upsert_args) == 1
    assert upsert_args[0]["ticker"] == "GOOD"
    assert upsert_args[0]["price"] == 100.0
    assert upsert_args[0]["today_pct_change"] == 1.5


def test_market_cache_get_last_known_price_stale():
    mock_client = MagicMock()
    stale_time = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=25)).isoformat()
    mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
        {"ticker": "AAPL", "price": 150.0, "market_cap": 2e12, "fetched_at": stale_time}
    ]

    cache = MarketDataCache(client=mock_client)
    assert cache.get_last_known_price("AAPL") is None


def test_market_cache_get_last_known_price_fresh():
    mock_client = MagicMock()
    fresh_time = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=5)).isoformat()
    mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
        {"ticker": "AAPL", "price": 150.0, "market_cap": 2e12, "fetched_at": fresh_time}
    ]

    cache = MarketDataCache(client=mock_client)
    data = cache.get_last_known_price("AAPL")
    assert data is not None
    assert data.price == 150.0


def test_market_cache_save_history():
    mock_client = MagicMock()
    cache = MarketDataCache(client=mock_client)

    history = [
        {
            "price": 100.0,
            "open": 98.0,
            "high": 101.0,
            "low": 97.0,
            "close": 100.0,
            "volume": 50000,
            "fetched_at": "2026-09-01",
        },
    ]
    cache.save_history("TEST", history)

    mock_client.table.assert_called_once_with("price_history")
    upsert_call = mock_client.table.return_value.upsert
    payloads = upsert_call.call_args[0][0]
    assert len(payloads) == 1
    assert payloads[0]["ticker"] == "TEST"
    assert payloads[0]["price"] == 100.0
    assert payloads[0]["volume"] == 50000
