"""
Tests for scripts.update_prices.py script, specifically the benchmark history fetching functionality.
"""

from unittest.mock import AsyncMock, patch

import pytest

from scripts.update_prices import (
    BENCHMARK_HISTORY_DAYS,
    BENCHMARK_TICKERS,
    fetch_benchmark_history,
    initialize_with_retry,
    update_prices,
)


class TestAsyncSleepOptimization:
    """Tests to ensure we are using non-blocking asyncio.sleep for retries."""

    @pytest.mark.asyncio
    @patch("scripts.update_prices.asyncio.sleep", new_callable=AsyncMock)
    @patch("scripts.update_prices.is_transient_supabase_error", return_value=True)
    async def test_initialize_with_retry_uses_async_sleep(self, mock_is_transient, mock_sleep):
        """Should await asyncio.sleep on failure before retrying."""
        from execution.portfolio import Portfolio

        with patch.object(Portfolio, "initialize", new_callable=AsyncMock) as mock_init:
            # First attempt fails, second succeeds
            mock_init.side_effect = [Exception("Transient error"), None]

            portfolio = await initialize_with_retry("test_user")

            assert mock_sleep.call_count == 1
            mock_sleep.assert_called_with(1)  # wait_time = 2 ** (1 - 1) = 1
            assert portfolio.owner_id == "test_user"

    @pytest.mark.asyncio
    @patch("scripts.update_prices.asyncio.sleep", new_callable=AsyncMock)
    @patch("scripts.update_prices.is_transient_supabase_error", return_value=True)
    async def test_update_prices_fetch_portfolios_uses_async_sleep(self, mock_is_transient, mock_sleep):
        """Should await asyncio.sleep if fetching portfolios fails."""
        with (
            patch("scripts.update_prices.get_supabase_client") as mock_get_client,
            patch("scripts.update_prices.MarketDataManager") as mock_mdm_cls,
        ):
            mock_mdm = mock_mdm_cls.return_value
            mock_mdm.is_market_open = AsyncMock(return_value=True)

            mock_client = mock_get_client.return_value
            mock_execute = mock_client.table.return_value.select.return_value.execute

            # First attempt fails, second returns empty data
            mock_execute.side_effect = [Exception("Transient DB error"), AsyncMock(data=[])]

            await update_prices()

            assert mock_sleep.call_count == 1
            mock_sleep.assert_called_with(1)  # wait_time = 2 ** (1 - 1) = 1


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
        expected = [
            "SPY",
            "QQQ",
            "GLD",
            "VGK",
            "EWJ",
            "EEM",
            "IWM",
            "DIA",
            "URTH",
            "TLT",
            "TIP",
            "UNG",
            "BTCUSD",
            "EWU",
            "EWC",
            "CPER",
        ]
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
        from core.macro_tracker import MACRO_TICKERS

        macro_tickers = set()
        for _category, items in MACRO_TICKERS.items():
            macro_tickers.update(items.keys())
        expected_tickers = sorted(list(set(BENCHMARK_TICKERS).union(macro_tickers)))

        mock_mdm = AsyncMock()
        mock_mdm.get_history = AsyncMock(
            return_value=[
                {"price": 450.00, "fetched_at": "2026-04-15"},
                {"price": 448.50, "fetched_at": "2026-04-14"},
                {"price": 447.00, "fetched_at": "2026-04-11"},
            ]
        )

        await fetch_benchmark_history(mock_mdm)

        assert mock_mdm.get_history.call_count == len(expected_tickers)

        for ticker in expected_tickers:
            mock_mdm.get_history.assert_any_call(ticker, days=BENCHMARK_HISTORY_DAYS, force_refresh=True)

    @pytest.mark.asyncio
    async def test_fetch_benchmark_history_partial_failure_continues(self):
        """Should continue fetching other tickers even if one fails."""
        from core.macro_tracker import MACRO_TICKERS

        macro_tickers = set()
        for _category, items in MACRO_TICKERS.items():
            macro_tickers.update(items.keys())
        expected_tickers = sorted(list(set(BENCHMARK_TICKERS).union(macro_tickers)))

        call_count = 0

        async def mock_get_history(ticker, days, force_refresh=False):
            nonlocal call_count
            call_count += 1
            if ticker == "QQQ":
                raise Exception("FMP API error")
            return [{"price": 450.00, "fetched_at": "2026-04-15"}] * 30

        mock_mdm = AsyncMock()
        mock_mdm.get_history = mock_get_history

        await fetch_benchmark_history(mock_mdm)

        assert call_count == len(expected_tickers)

    @pytest.mark.asyncio
    async def test_fetch_benchmark_history_insufficient_data_warning(self):
        """Should log warning when ticker has insufficient data points."""
        mock_mdm = AsyncMock()
        mock_mdm.get_history = AsyncMock(
            return_value=[
                {"price": 450.00, "fetched_at": "2026-04-15"},
                {"price": 448.50, "fetched_at": "2026-04-14"},
            ]
        )

        with patch("scripts.update_prices.logger") as mock_logger:
            await fetch_benchmark_history(mock_mdm)
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_fetch_benchmark_history_success_log(self):
        """Should log success message when benchmark data is stored."""
        mock_mdm = AsyncMock()
        mock_mdm.get_history = AsyncMock(
            return_value=[
                {"price": 450.00, "fetched_at": "2026-04-15"},
            ]
            * 30
        )

        with patch("scripts.update_prices.logger") as mock_logger:
            await fetch_benchmark_history(mock_mdm)
            mock_logger.info.assert_called()


class TestBenchmarkTickerConsistency:
    """Tests to ensure benchmark tickers match the frontend selector."""

    def test_tickers_match_frontend_benchmark_selector(self):
        """BENCHMARK_TICKERS should match the frontend BENCHMARK_OPTIONS ticker list.

        Frontend selector is defined in:
        apps/web/src/features/portfolios/components/BenchmarkSelector.tsx
        """
        frontend_tickers = [
            "SPY",
            "QQQ",
            "URTH",
            "GLD",
            "CPER",
            "UNG",
            "TLT",
            "TIP",
            "BTCUSD",
            "VGK",
            "EWJ",
            "EWU",
            "EWC",
            "EEM",
            "IWM",
            "DIA",
        ]

        assert set(BENCHMARK_TICKERS) == set(frontend_tickers), (
            f"BENCHMARK_TICKERS {BENCHMARK_TICKERS} does not match frontend tickers {frontend_tickers}"
        )
