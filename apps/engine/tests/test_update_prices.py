"""
Tests for scripts.update_prices.py script, specifically the benchmark history fetching functionality.
"""
from unittest.mock import AsyncMock, patch

import pytest

from scripts.update_prices import (
    BENCHMARK_HISTORY_DAYS,
    BENCHMARK_TICKERS,
    fetch_benchmark_history,
)


class TestBenchmarkConstants:
    """Tests that benchmark ticker constants are properly defined."""

    def test_benchmark_tickers_defined(self):
        """Benchmark tickers list should be defined."""
        assert BENCHMARK_TICKERS is not None
        assert len(BENCHMARK_TICKERS) > 0

    def test_benchmark_tickers_are_strings(self):
        """All benchmark tickers should be string ticker symbols."""
        assert all(isinstance(t, str) for t in BENCHMARK_TICKERS)

    def test_benchmark_tickers_uppercase(self):
        """All benchmark tickers should be uppercase."""
        assert all(t.isupper() for t in BENCHMARK_TICKERS)

    def test_expected_benchmark_tickers_present(self):
        """Common benchmark tickers should be present in the list."""
        expected = ['SPY', 'QQQ', 'GLD', 'VGK', 'EWJ', 'EEM', 'IWM', 'DIA', 'URTH',
                     'TLT', 'TIP', 'UNG', 'BTCUSD', 'EWU', 'EWC', 'CPER']
        for ticker in expected:
            assert ticker in BENCHMARK_TICKERS, f"Expected benchmark {ticker} not found"

    def test_benchmark_history_days_defined(self):
        """Benchmark history days should be defined and positive."""
        assert BENCHMARK_HISTORY_DAYS is not None
        assert BENCHMARK_HISTORY_DAYS > 0
        assert BENCHMARK_HISTORY_DAYS == 90


class TestFetchBenchmarkHistory:
    """Tests for the fetch_benchmark_history function."""

    @pytest.mark.asyncio
    async def test_fetch_benchmark_history_success(self):
        """Should fetch and store history for all benchmark tickers successfully."""
        mock_mdm = AsyncMock()
        mock_mdm.get_history = AsyncMock(return_value=[
            {"price": 450.00, "fetched_at": "2026-04-15"},
            {"price": 448.50, "fetched_at": "2026-04-14"},
            {"price": 447.00, "fetched_at": "2026-04-11"},
        ])

        await fetch_benchmark_history(mock_mdm)

        assert mock_mdm.get_history.call_count == len(BENCHMARK_TICKERS)

        for ticker in BENCHMARK_TICKERS:
            mock_mdm.get_history.assert_any_call(ticker, days=BENCHMARK_HISTORY_DAYS)

    @pytest.mark.asyncio
    async def test_fetch_benchmark_history_partial_failure_continues(self):
        """Should continue fetching other tickers even if one fails."""
        call_count = 0

        async def mock_get_history(ticker, days):
            nonlocal call_count
            call_count += 1
            if ticker == 'QQQ':
                raise Exception("FMP API error")
            return [{"price": 450.00, "fetched_at": "2026-04-15"}] * 30

        mock_mdm = AsyncMock()
        mock_mdm.get_history = mock_get_history

        await fetch_benchmark_history(mock_mdm)

        assert call_count == len(BENCHMARK_TICKERS)

    @pytest.mark.asyncio
    async def test_fetch_benchmark_history_insufficient_data_warning(self):
        """Should log warning when ticker has insufficient data points."""
        mock_mdm = AsyncMock()
        mock_mdm.get_history = AsyncMock(return_value=[
            {"price": 450.00, "fetched_at": "2026-04-15"},
            {"price": 448.50, "fetched_at": "2026-04-14"},
        ])

        with patch('scripts.update_prices.logger') as mock_logger:
            await fetch_benchmark_history(mock_mdm)
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_fetch_benchmark_history_success_log(self):
        """Should log success message when benchmark data is stored."""
        mock_mdm = AsyncMock()
        mock_mdm.get_history = AsyncMock(return_value=[
            {"price": 450.00, "fetched_at": "2026-04-15"},
        ] * 30)

        with patch('scripts.update_prices.logger') as mock_logger:
            await fetch_benchmark_history(mock_mdm)
            mock_logger.info.assert_called()


class TestBenchmarkTickerConsistency:
    """Tests to ensure benchmark tickers match the frontend selector."""

    def test_tickers_match_frontend_benchmark_selector(self):
        """BENCHMARK_TICKERS should match the frontend BENCHMARK_OPTIONS ticker list.

        Frontend selector is defined in:
        apps/web/src/features/portfolios/components/BenchmarkSelector.tsx
        """
        frontend_tickers = ['SPY', 'QQQ', 'URTH', 'GLD', 'CPER', 'UNG', 'TLT', 'TIP',
                            'BTCUSD', 'VGK', 'EWJ', 'EWU', 'EWC', 'EEM', 'IWM', 'DIA']

        assert set(BENCHMARK_TICKERS) == set(frontend_tickers), (
            f"BENCHMARK_TICKERS {BENCHMARK_TICKERS} does not match "
            f"frontend tickers {frontend_tickers}"
        )
