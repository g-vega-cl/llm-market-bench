"""Tests for volume context functionality in tools."""

from unittest.mock import AsyncMock, patch

import pytest

from core.llm.tools import (
    compute_volume_context,
    execute_stock_screener_tool,
    execute_volatility_metrics_tool,
)


class TestComputeVolumeContext:
    """Tests for the compute_volume_context helper function."""

    def test_compute_volume_context_normal_volume(self):
        """Test with typical volume pattern."""
        history = [
            {"price": 150.0, "volume": 10000000, "fetched_at": "2024-01-02"},
            {"price": 151.0, "volume": 10000000, "fetched_at": "2024-01-01"},
            {"price": 152.0, "volume": 10000000, "fetched_at": "2024-01-03"},
        ] * 7  # 21 entries to test 20-day lookback
        
        result = compute_volume_context(history)
        
        assert "1.0x" in result
        assert "20-day average" in result
        assert "th percentile" in result

    def test_compute_volume_context_elevated_volume(self):
        """Test with elevated latest volume."""
        # First entry is 50000000, remaining 20 entries are 10000000 each
        # Code uses first 20 for lookback: (50000000 + 19*10000000) / 20 = 12000000
        # Ratio = 50000000 / 12000000 ≈ 4.17x
        # For percentile: 20 out of 21 values are below 50000000, so (20/21)*100 ≈ 95th
        history = [
            {"price": 150.0, "volume": 50000000, "fetched_at": "2024-01-02"},  # highest
            {"price": 151.0, "volume": 10000000, "fetched_at": "2024-01-01"},
        ] + [
            {"price": 152.0, "volume": 10000000, "fetched_at": f"2024-01-{i:02d}"}
            for i in range(3, 22)
        ]
        
        result = compute_volume_context(history)
        
        assert "4." in result  # Approximately 4.2x
        assert "20-day average" in result  # Capped at 20
        assert "95th percentile" in result

    def test_compute_volume_context_low_volume(self):
        """Test with low latest volume."""
        history = [
            {"price": 150.0, "volume": 1000000, "fetched_at": "2024-01-02"},  # 0.1x average
            {"price": 151.0, "volume": 10000000, "fetched_at": "2024-01-01"},
            {"price": 152.0, "volume": 10000000, "fetched_at": "2024-01-03"},
        ] * 7
        
        result = compute_volume_context(history)
        
        assert "0.1x" in result
        assert "0th percentile" in result

    def test_compute_volume_context_insufficient_data(self):
        """Test with less than 5 volume entries."""
        history = [
            {"price": 150.0, "volume": 10000000, "fetched_at": "2024-01-02"},
            {"price": 151.0, "volume": 10000000, "fetched_at": "2024-01-01"},
        ]
        
        result = compute_volume_context(history)
        
        assert result == "insufficient volume data"

    def test_compute_volume_context_missing_volume(self):
        """Test with missing volume values."""
        history = [
            {"price": 150.0, "fetched_at": "2024-01-02"},  # No volume
            {"price": 151.0, "volume": 10000000, "fetched_at": "2024-01-01"},
        ]
        
        result = compute_volume_context(history)
        
        assert result == "insufficient volume data"

    def test_compute_volume_context_dynamic_lookback(self):
        """Test that lookback days is dynamic (uses all days if fewer than 20)."""
        # 5 entries - enough for minimum but fewer than 20
        # Latest is 20000000, other 4 are 10000000 each
        # Average = (20000000 + 4*10000000) / 5 = 60000000 / 5 = 12000000
        # Ratio = 20000000 / 12000000 = 1.67x
        history = [
            {"price": 150.0, "volume": 20000000, "fetched_at": "2024-01-02"},  # latest
            {"price": 151.0, "volume": 10000000, "fetched_at": "2024-01-01"},
            {"price": 152.0, "volume": 10000000, "fetched_at": "2024-01-03"},
            {"price": 153.0, "volume": 10000000, "fetched_at": "2024-01-04"},
            {"price": 154.0, "volume": 10000000, "fetched_at": "2024-01-05"},
        ]
        
        result = compute_volume_context(history)
        
        assert "1.7x" in result
        assert "5-day average" in result

    def test_compute_volume_context_empty_history(self):
        """Test with empty history."""
        result = compute_volume_context([])
        
        assert result == "insufficient volume data"

    def test_compute_volume_context_none_values_filtered(self):
        """Test that None volume values are filtered out."""
        # Build 21 entries where the latest is 50000000 and rest are 10000000
        # None values are filtered out, so they don't affect the average
        history = [
            {"price": 150.0, "volume": 50000000, "fetched_at": "2024-01-02"},
        ] + [
            {"price": 151.0, "volume": 10000000, "fetched_at": f"2024-01-{i:02d}"}
            for i in range(3, 22)
        ]
        # Add some None values interspersed
        history_with_none = []
        for i, entry in enumerate(history):
            history_with_none.append(entry)
            if i > 0 and i < 20:
                history_with_none.append({"price": 999.0, "volume": None, "fetched_at": "2024-01-00"})
        
        result = compute_volume_context(history_with_none)
        
        # Should still be around 4.2x (same as elevated test) since None values are filtered
        assert "4." in result


class TestExecuteVolatilityMetricsTool:
    """Tests for execute_volatility_metrics_tool with volume context."""

    @pytest.mark.asyncio
    async def test_volatility_metrics_includes_volume_context(self):
        """Test that volatility metrics output includes volume context."""
        # Build 20 entries: latest is 50000000, others are 10000000
        mock_history = [
            {"price": 150.0, "volume": 50000000, "fetched_at": "2024-01-02"},  # latest
        ] + [
            {"price": 151.0 + i * 0.1, "volume": 10000000, "fetched_at": f"2024-01-{i+3:02d}"}
            for i in range(19)
        ]
        
        with patch("core.llm.tools.MarketDataManager") as mock_manager_cls:
            mock_manager = mock_manager_cls.return_value
            mock_manager.get_history = AsyncMock(return_value=mock_history)
            
            result = await execute_volatility_metrics_tool("AAPL", days=20)
            
            assert "Volume Context:" in result
            assert "4." in result  # Approximately 4.2x
            assert "20-day average" in result

    @pytest.mark.asyncio
    async def test_volatility_metrics_insufficient_data(self):
        """Test with insufficient historical data."""
        with patch("core.llm.tools.MarketDataManager") as mock_manager_cls:
            mock_manager = mock_manager_cls.return_value
            mock_manager.get_history = AsyncMock(return_value=[])
            
            result = await execute_volatility_metrics_tool("AAPL")
            
            assert "Insufficient historical data" in result


class TestExecuteStockScreenerTool:
    """Tests for execute_stock_screener_tool with N+1 volume context calls."""

    @pytest.mark.asyncio
    async def test_screener_enriches_results_with_volume_context(self):
        """Test that screener results include volume context per stock."""
        mock_screener_results = [
            {"symbol": "AAPL", "companyName": "Apple Inc", "price": 150.0, "marketCap": 2500000000000},
            {"symbol": "MSFT", "companyName": "Microsoft Corp", "price": 350.0, "marketCap": 2800000000000},
        ]
        
        # AAPL: latest is 50000000, others 10000000 -> ~4.2x
        mock_history_aapl = [
            {"price": 150.0, "volume": 50000000, "fetched_at": "2024-01-02"},
        ] + [
            {"price": 151.0 + i * 0.1, "volume": 10000000, "fetched_at": f"2024-01-{i+3:02d}"}
            for i in range(19)
        ]
        
        # MSFT: all volumes are 10000000 -> 1.0x
        mock_history_msft = [
            {"price": 350.0, "volume": 10000000, "fetched_at": "2024-01-02"},
        ] + [
            {"price": 351.0 + i * 0.1, "volume": 10000000, "fetched_at": f"2024-01-{i+3:02d}"}
            for i in range(19)
        ]

        async def mock_get_history(ticker, days=20):
            if ticker == "AAPL":
                return mock_history_aapl
            elif ticker == "MSFT":
                return mock_history_msft
            return []

        with patch("core.llm.tools.MarketDataManager") as mock_manager_cls:
            mock_manager = mock_manager_cls.return_value
            mock_manager.screen_stocks = AsyncMock(return_value=mock_screener_results)
            mock_manager.get_history = mock_get_history
            
            result = await execute_stock_screener_tool(sector="Technology", limit=2)
            
            assert "AAPL" in result
            assert "MSFT" in result
            assert "Volume Context:" in result
            assert "4." in result  # AAPL has ~4.2x volume
            assert "1.0x" in result  # MSFT has 1.0x volume

    @pytest.mark.asyncio
    async def test_screener_no_results(self):
        """Test screener with no matching results."""
        with patch("core.llm.tools.MarketDataManager") as mock_manager_cls:
            mock_manager = mock_manager_cls.return_value
            mock_manager.screen_stocks = AsyncMock(return_value=[])
            
            result = await execute_stock_screener_tool(sector="Nonexistent")
            
            assert "No stocks found" in result

    @pytest.mark.asyncio
    async def test_screener_handles_missing_ticker(self):
        """Test screener handles results with missing ticker symbols."""
        mock_screener_results = [
            {"symbol": None, "companyName": "Unknown", "price": 0, "marketCap": 0},
            {"symbol": "AAPL", "companyName": "Apple Inc", "price": 150.0, "marketCap": 2500000000000},
        ]
        
        mock_history = [
            {"price": 150.0, "volume": 10000000, "fetched_at": "2024-01-02"},
        ] + [
            {"price": 151.0 + i * 0.1, "volume": 10000000, "fetched_at": f"2024-01-{i+3:02d}"}
            for i in range(19)
        ]

        async def mock_get_history(ticker, days=20):
            if ticker == "AAPL":
                return mock_history
            return []

        with patch("core.llm.tools.MarketDataManager") as mock_manager_cls:
            mock_manager = mock_manager_cls.return_value
            mock_manager.screen_stocks = AsyncMock(return_value=mock_screener_results)
            mock_manager.get_history = mock_get_history
            
            result = await execute_stock_screener_tool(sector="Technology", limit=2)
            
            assert "AAPL" in result
            assert "Volume Context:" in result
