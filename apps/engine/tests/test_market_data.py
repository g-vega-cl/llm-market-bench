"""Unit tests for MarketDataManager caching logic."""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from execution.market_data import MarketDataManager
from execution.providers.base import TickerData


@pytest.mark.asyncio
async def test_market_data_manager_cache_hit():
    """Test that manager returns data from cache if available and fresh."""
    mock_data = {
        "ticker": "AAPL",
        "price": 150.0,
        "market_cap": 2.5e12,
        "fetched_at": datetime.datetime.now(datetime.UTC).isoformat(),
    }

    with patch("execution.market_data.get_supabase_client") as mock_db:
        mock_client = mock_db.return_value
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [mock_data]

        manager = MarketDataManager()
        # Mock provider to ensure it's NOT called
        manager.provider = AsyncMock()

        result = await manager.get_quote("AAPL")

        assert result is not None
        assert result.ticker == "AAPL"
        assert result.price == 150.0
        assert manager.provider.get_ticker_data.call_count == 0


@pytest.mark.asyncio
async def test_market_data_manager_cache_stale():
    """Test that manager fetches from provider if cache is stale."""
    # 310 seconds ago (default TTL is 300)
    stale_time = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(seconds=310)).isoformat()
    mock_cached_data = {"ticker": "TSLA", "price": 100.0, "market_cap": 500e9, "fetched_at": stale_time}

    mock_provider_data = TickerData(ticker="TSLA", price=200.0, market_cap=600e9, exists=True)

    with patch("execution.market_data.get_supabase_client") as mock_db:
        mock_client = mock_db.return_value
        # Cache returns stale data
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            mock_cached_data
        ]
        # Upsert mock
        mock_client.table.return_value.upsert.return_value.execute = MagicMock()

        manager = MarketDataManager()
        manager.provider.get_ticker_data = AsyncMock(return_value=mock_provider_data)

        result = await manager.get_quote("TSLA")

        assert result is not None
        assert result.price == 200.0  # Fresh data
        assert manager.provider.get_ticker_data.call_count == 1


@pytest.mark.asyncio
async def test_market_data_manager_cache_miss():
    """Test that manager fetches and saves if cache is empty."""
    mock_provider_data = TickerData(ticker="NVDA", price=500.0, market_cap=1.2e12, exists=True)

    with patch("execution.market_data.get_supabase_client") as mock_db:
        mock_client = mock_db.return_value
        # Cache returns empty
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        # Upsert mock
        mock_client.table.return_value.upsert.return_value.execute = MagicMock()

        manager = MarketDataManager()
        manager.provider.get_ticker_data = AsyncMock(return_value=mock_provider_data)

        result = await manager.get_quote("NVDA")

        assert result is not None
        assert result.ticker == "NVDA"
        assert manager.provider.get_ticker_data.call_count == 1
        assert mock_client.table.return_value.upsert.call_count == 1


class TestCacheTTL:
    """Tests for the cache TTL configuration."""

    def test_default_ttl_is_300_seconds(self):
        """Default cache TTL should be 300 seconds (5 minutes)."""
        manager = MarketDataManager()
        assert manager.cache_ttl_seconds == 300

    def test_explicit_ttl_override(self):
        """Explicit cache_ttl_seconds should override the default."""
        manager = MarketDataManager(cache_ttl_seconds=60)
        assert manager.cache_ttl_seconds == 60

    def test_ttl_from_env_var(self, monkeypatch):
        """MARKET_DATA_CACHE_TTL_SECONDS env var should set the default."""
        monkeypatch.setenv("MARKET_DATA_CACHE_TTL_SECONDS", "120")
        import importlib

        import core.config

        importlib.reload(core.config)
        try:
            manager = MarketDataManager()
            assert manager.cache_ttl_seconds == 120
        finally:
            monkeypatch.delenv("MARKET_DATA_CACHE_TTL_SECONDS", raising=False)
            importlib.reload(core.config)

    @pytest.mark.asyncio
    async def test_cache_fresh_within_ttl(self):
        """Data within the 300s TTL should be a cache hit (not stale)."""
        fresh_time = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(seconds=290)).isoformat()
        mock_cached = {"ticker": "AAPL", "price": 150.0, "market_cap": 2.5e12, "fetched_at": fresh_time}

        with patch("execution.market_data.get_supabase_client") as mock_db:
            mock_client = mock_db.return_value
            mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [mock_cached]

            manager = MarketDataManager()
            manager.provider = AsyncMock()

            result = await manager.get_quote("AAPL")

            assert result is not None
            assert result.price == 150.0
            manager.provider.get_ticker_data.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_stale_beyond_ttl(self):
        """Data beyond the 300s TTL should be fetched from provider."""
        stale_time = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(seconds=310)).isoformat()
        mock_cached = {"ticker": "META", "price": 400.0, "market_cap": 1e12, "fetched_at": stale_time}
        mock_fresh = TickerData(ticker="META", price=420.0, market_cap=1.1e12, exists=True)

        with patch("execution.market_data.get_supabase_client") as mock_db:
            mock_client = mock_db.return_value
            mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [mock_cached]
            mock_client.table.return_value.upsert.return_value.execute = MagicMock()

            manager = MarketDataManager()
            manager.provider.get_ticker_data = AsyncMock(return_value=mock_fresh)

            result = await manager.get_quote("META")

            assert result.price == 420.0
            manager.provider.get_ticker_data.assert_called_once()


@pytest.mark.asyncio
async def test_market_status_lock_prevents_thundering_herd():
    """Test that concurrent is_market_open calls are serialized and make only 1 request."""
    import asyncio

    from execution.market_data import MarketDataManager

    # Reset cache
    MarketDataManager._market_status_cache = {
        "is_open": None,
        "fetched_at": None,
        "ttl_seconds": 300,
    }
    MarketDataManager._market_status_lock = None

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{"isMarketOpen": True}]

    call_count = 0

    async def slow_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.1)
        return mock_resp

    with (
        patch("execution.market_data.FMP_API_KEY", "dummy_key"),
        patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=slow_get),
    ):
        manager = MarketDataManager()

        results = await asyncio.gather(manager.is_market_open(), manager.is_market_open(), manager.is_market_open())

        assert all(results)
        assert call_count == 1


@pytest.mark.asyncio
async def test_is_premarket():
    """Test is_premarket returns True between 4:00 and 9:30 AM ET on weekdays."""
    from zoneinfo import ZoneInfo

    manager = MarketDataManager()

    # Pre-market time: Wednesday 8:00 AM ET
    wed_8am = datetime.datetime(2026, 8, 19, 8, 0, 0, tzinfo=ZoneInfo("America/New_York"))
    with patch("datetime.datetime") as mock_dt:
        mock_dt.now.return_value = wed_8am
        mock_dt.side_effect = lambda *args, **kw: datetime.datetime(*args, **kw)
        assert await manager.is_premarket() is True

    # Market hours: Wednesday 10:30 AM ET
    wed_1030am = datetime.datetime(2026, 8, 19, 10, 30, 0, tzinfo=ZoneInfo("America/New_York"))
    with patch("datetime.datetime") as mock_dt:
        mock_dt.now.return_value = wed_1030am
        mock_dt.side_effect = lambda *args, **kw: datetime.datetime(*args, **kw)
        assert await manager.is_premarket() is False

    # Weekend: Saturday 8:00 AM ET
    sat_8am = datetime.datetime(2026, 8, 22, 8, 0, 0, tzinfo=ZoneInfo("America/New_York"))
    with patch("datetime.datetime") as mock_dt:
        mock_dt.now.return_value = sat_8am
        mock_dt.side_effect = lambda *args, **kw: datetime.datetime(*args, **kw)
        assert await manager.is_premarket() is False


@pytest.mark.asyncio
async def test_get_aftermarket_quote_fmp():
    """Test FMPProvider get_aftermarket_quote parsing with price or bid/ask."""
    from execution.providers.fmp import FMPProvider

    provider = FMPProvider()
    provider.api_key = "dummy_key"

    # Test with bidPrice / askPrice
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{"symbol": "SPY", "bidPrice": 595.40, "askPrice": 595.60, "volume": 120000}]

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        quote = await provider.get_aftermarket_quote("SPY")
        assert quote is not None
        assert quote["symbol"] == "SPY"
        assert quote["price"] == 595.50
        assert quote["volume"] == 120000


@pytest.mark.asyncio
async def test_get_ticker_data_fmp_extracts_previous_close_and_change():
    """Test that FMPProvider.get_ticker_data parses previousClose, change, changePercentage, and volume."""
    from execution.providers.fmp import FMPProvider

    provider = FMPProvider()
    provider.api_key = "dummy_key"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {
            "symbol": "SPY",
            "price": 770.20,
            "marketCap": 820000000000.0,
            "previousClose": 767.45,
            "change": 2.75,
            "changePercentage": 0.3583,
            "volume": 3500000,
            "currency": "USD",
            "exchange": "AMEX",
        }
    ]

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        data = await provider.get_ticker_data("SPY")
        assert data is not None
        assert data.ticker == "SPY"
        assert data.price == 770.20
        assert data.previous_close == 767.45
        assert data.change == 2.75
        assert data.change_pct == 0.3583
        assert data.volume == 3500000


@pytest.mark.asyncio
async def test_get_premarket_quote_using_quote_previous_close():
    """Test MarketDataManager.get_premarket_quote directly uses quote's previous_close and change_pct."""
    manager = MarketDataManager()
    manager.provider = MagicMock()
    manager.provider.get_aftermarket_quote = AsyncMock(return_value=None)
    manager.get_quote = AsyncMock(
        return_value=TickerData(
            ticker="SPY",
            price=770.20,
            market_cap=820e9,
            exists=True,
            previous_close=767.45,
            change=2.75,
            change_pct=0.3583,
            volume=3500000,
        )
    )

    result = await manager.get_premarket_quote("SPY")
    assert result is not None
    assert result["price"] == 770.20
    assert result["previous_close"] == 767.45
    assert result["change"] == 2.75
    assert result["change_pct"] == 0.3583
    assert result["volume"] == 3500000


@pytest.mark.asyncio
async def test_get_premarket_quote_fallback_to_history():
    """Test MarketDataManager.get_premarket_quote falls back to history if previous_close is missing on quote."""
    manager = MarketDataManager()
    manager.provider = MagicMock()
    manager.provider.get_aftermarket_quote = AsyncMock(return_value=None)
    manager.get_quote = AsyncMock(
        return_value=TickerData(
            ticker="AAPL",
            price=230.00,
            market_cap=3e12,
            exists=True,
        )
    )
    manager.get_history = AsyncMock(
        return_value=[{"price": 225.00, "close": 225.00, "fetched_at": "2026-08-17T00:00:00Z"}]
    )

    result = await manager.get_premarket_quote("AAPL")
    assert result is not None
    assert result["price"] == 230.00
    assert result["previous_close"] == 225.00
    assert result["change"] == 5.00
    assert abs(result["change_pct"] - 2.222) < 0.01


@pytest.mark.asyncio
async def test_get_premarket_quote_prefers_aftermarket_quote():
    """Test MarketDataManager.get_premarket_quote uses provider.get_aftermarket_quote if available."""
    manager = MarketDataManager()
    mock_provider = MagicMock()
    mock_provider.get_aftermarket_quote = AsyncMock(
        return_value={
            "symbol": "SPY",
            "price": 596.50,
            "bid": 596.40,
            "ask": 596.60,
            "volume": 120000,
        }
    )
    manager.provider = mock_provider
    manager.get_quote = AsyncMock(
        return_value=TickerData(
            ticker="SPY",
            price=592.00,
            market_cap=820e9,
            exists=True,
            previous_close=590.00,  # distinct two-day-old close
        )
    )

    result = await manager.get_premarket_quote("SPY")
    assert result is not None
    assert result["price"] == 596.50
    # Baseline for overnight gap should be yesterday's regular close (quote.price 592.00), not quote.previous_close (590.00)
    assert result["previous_close"] == 592.00
    assert result["change"] == 4.50
    assert abs(result["change_pct"] - (4.50 / 592.00 * 100.0)) < 0.001
    assert result["volume"] == 120000
