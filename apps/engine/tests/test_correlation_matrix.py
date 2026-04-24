"""Tests for correlation_matrix.py module.

This module tests:
1. Ticker universe validation
2. Returns calculation
3. Pearson and Spearman correlation computation
4. 90-day returns calculation
5. Ticker verification logic
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch

import correlation_matrix


class TestTickerUniverse:
    """Tests for the ticker universe configuration."""

    def test_ticker_universe_is_defined(self):
        """Verify ticker universe is defined."""
        assert hasattr(correlation_matrix, "TICKER_UNIVERSE")
        assert isinstance(correlation_matrix.TICKER_UNIVERSE, list)
        assert len(correlation_matrix.TICKER_UNIVERSE) > 0

    def test_ticker_universe_contains_expected_sectors(self):
        """Verify ticker universe contains expected sector ETFs."""
        tickers = correlation_matrix.TICKER_UNIVERSE

        # US Sectors
        assert "XLK" in tickers  # Technology
        assert "SMH" in tickers  # Semiconductors (VanEck)
        assert "XLE" in tickers  # Energy
        assert "XLF" in tickers  # Financials
        assert "XLV" in tickers  # Healthcare

    def test_ticker_universe_contains_broad_market(self):
        """Verify ticker universe contains broad market ETFs."""
        tickers = correlation_matrix.TICKER_UNIVERSE

        assert "SPY" in tickers
        assert "QQQ" in tickers
        assert "IWM" in tickers

    def test_ticker_universe_contains_international(self):
        """Verify ticker universe contains international ETFs."""
        tickers = correlation_matrix.TICKER_UNIVERSE

        assert "EFA" in tickers  # Developed markets
        assert "EEM" in tickers  # Emerging markets
        assert "EWJ" in tickers  # Japan

    def test_ticker_universe_contains_commodities(self):
        """Verify ticker universe contains commodity ETFs."""
        tickers = correlation_matrix.TICKER_UNIVERSE

        assert "GLD" in tickers  # Gold
        assert "USO" in tickers  # Oil

    def test_ticker_universe_contains_crypto(self):
        """Verify ticker universe contains crypto."""
        tickers = correlation_matrix.TICKER_UNIVERSE

        assert "BTCUSD" in tickers
        assert "ETHUSD" in tickers

    def test_ticker_universe_contains_volatility(self):
        """Verify ticker universe contains volatility ETFs."""
        tickers = correlation_matrix.TICKER_UNIVERSE

        assert "VIXY" in tickers
        assert "VIXM" in tickers

    def test_window_days_is_90(self):
        """Verify rolling window is set to 90 days."""
        assert correlation_matrix.WINDOW_DAYS == 90


class TestComputeReturns:
    """Tests for daily returns calculation."""

    def test_compute_returns_basic(self):
        """Test basic returns calculation."""
        prices = [100.0, 105.0, 102.0, 110.0]
        returns = correlation_matrix.compute_returns(prices)

        # Expected returns: (105-100)/100=0.05, (102-105)/105=-0.0286, (110-102)/102=0.0784
        assert len(returns) == 3
        assert returns[0] == pytest.approx(0.05)
        assert returns[1] == pytest.approx(-0.02857, abs=0.001)
        assert returns[2] == pytest.approx(0.0784, abs=0.001)

    def test_compute_returns_single_price(self):
        """Test returns with single price returns empty array."""
        prices = [100.0]
        returns = correlation_matrix.compute_returns(prices)
        assert len(returns) == 0

    def test_compute_returns_two_prices(self):
        """Test returns with two prices returns single return."""
        prices = [100.0, 110.0]
        returns = correlation_matrix.compute_returns(prices)
        assert len(returns) == 1
        assert returns[0] == pytest.approx(0.10)

    def test_compute_returns_negative_returns(self):
        """Test negative returns calculation."""
        prices = [100.0, 90.0, 85.0]
        returns = correlation_matrix.compute_returns(prices)

        assert len(returns) == 2
        assert returns[0] == pytest.approx(-0.10)
        assert returns[1] == pytest.approx(-0.0556, abs=0.001)

    def test_compute_returns_zero_change(self):
        """Test returns with no price change."""
        prices = [100.0, 100.0, 100.0]
        returns = correlation_matrix.compute_returns(prices)

        assert len(returns) == 2
        assert returns[0] == pytest.approx(0.0)
        assert returns[1] == pytest.approx(0.0)

    def test_compute_returns_returns_numpy_array(self):
        """Test that returns is a numpy array."""
        prices = [100.0, 105.0, 110.0]
        returns = correlation_matrix.compute_returns(prices)
        assert isinstance(returns, np.ndarray)


class TestComputeCorrelationMatrices:
    """Tests for Pearson and Spearman correlation computation."""

    def test_identical_returns_perfect_correlation(self):
        """Test that identical returns produce correlation of 1."""
        # Need at least 30 observations and varying data (constant returns = NaN correlation)
        np.random.seed(42)
        base = np.random.randn(50) * 0.01 + 0.01  # Small random variation around 1%
        returns_dict = {
            "A": list(base),
            "B": list(base),  # Identical with small variation
        }

        pearson_corrs, spearman_corrs = correlation_matrix.compute_correlation_matrices(returns_dict)

        key = ("A", "B")
        assert key in pearson_corrs
        assert pearson_corrs[key] == pytest.approx(1.0, abs=0.01)
        assert spearman_corrs[key] == pytest.approx(1.0, abs=0.01)

    def test_opposite_returns_perfect_negative_correlation(self):
        """Test that opposite returns produce correlation of -1."""
        # Need at least 30 observations and varying data
        np.random.seed(42)
        base = np.random.randn(50) * 0.01 + 0.01
        returns_dict = {
            "A": list(base),
            "B": list(-base),  # Negated
        }

        pearson_corrs, spearman_corrs = correlation_matrix.compute_correlation_matrices(returns_dict)

        key = ("A", "B")
        assert pearson_corrs[key] == pytest.approx(-1.0, abs=0.01)
        assert spearman_corrs[key] == pytest.approx(-1.0, abs=0.01)

    def test_uncorrelated_returns_near_zero(self):
        """Test that random returns produce near-zero correlation."""
        np.random.seed(42)
        returns_dict = {
            "A": list(np.random.randn(100) * 0.01),
            "B": list(np.random.randn(100) * 0.01),
        }

        pearson_corrs, spearman_corrs = correlation_matrix.compute_correlation_matrices(returns_dict)

        key = ("A", "B")
        assert abs(pearson_corrs[key]) < 0.3  # Should be relatively uncorrelated

    def test_known_correlation_xlk_xle(self):
        """Test correlation between Technology and Energy sectors."""
        # Need at least 30 observations - use larger arrays
        np.random.seed(42)
        returns_dict = {
            "XLK": list(np.random.randn(50) * 0.015),
            "XLE": list(np.random.randn(50) * 0.02),
        }

        pearson_corrs, spearman_corrs = correlation_matrix.compute_correlation_matrices(returns_dict)

        key = ("XLK", "XLE")
        assert key in pearson_corrs
        # Correlation should be between -1 and 1
        assert -1.0 <= pearson_corrs[key] <= 1.0
        assert -1.0 <= spearman_corrs[key] <= 1.0

    def test_all_tickers_same_returns_perfect_correlation(self):
        """Test that all identical tickers produce perfect correlations."""
        np.random.seed(42)
        base = np.random.randn(50) * 0.01 + 0.01  # Small variation
        returns = list(base)
        returns_dict = {f"TICKER_{i}": returns for i in range(5)}

        pearson_corrs, _ = correlation_matrix.compute_correlation_matrices(returns_dict)

        # All pairs should have correlation of 1
        for (a, b), corr in pearson_corrs.items():
            assert corr == pytest.approx(1.0, abs=0.01)

    def test_mismatched_lengths_uses_minimum(self):
        """Test that mismatched return lengths are handled correctly."""
        np.random.seed(42)
        base_a = np.random.randn(60) * 0.01 + 0.01
        base_b = np.random.randn(50) * 0.01 + 0.01
        returns_dict = {
            "A": list(base_a),  # 60 points
            "B": list(base_b),  # 50 points
        }

        pearson_corrs, spearman_corrs = correlation_matrix.compute_correlation_matrices(returns_dict)

        key = ("A", "B")
        assert key in pearson_corrs
        # Should use only first 50 points (minimum length)
        assert -1.0 <= pearson_corrs[key] <= 1.0


class TestCompute90dReturns:
    """Tests for 90-day returns calculation."""

    def test_positive_return(self):
        """Test positive 90-day return calculation."""
        prices = {
            "A": [100.0, 105.0, 110.0],  # 10% total return
        }

        returns = correlation_matrix.compute_90d_returns(prices)

        assert "A" in returns
        assert returns["A"] == pytest.approx(10.0, abs=0.1)

    def test_negative_return(self):
        """Test negative 90-day return calculation."""
        prices = {
            "A": [100.0, 95.0, 90.0],  # -10% total return
        }

        returns = correlation_matrix.compute_90d_returns(prices)

        assert "A" in returns
        assert returns["A"] == pytest.approx(-10.0, abs=0.1)

    def test_zero_return(self):
        """Test zero 90-day return calculation."""
        prices = {
            "A": [100.0, 100.0, 100.0],  # 0% total return
        }

        returns = correlation_matrix.compute_90d_returns(prices)

        assert "A" in returns
        assert returns["A"] == pytest.approx(0.0, abs=0.001)

    def test_multiple_tickers(self):
        """Test 90-day returns for multiple tickers."""
        prices = {
            "SPY": [400.0, 410.0, 420.0],  # +5%
            "QQQ": [300.0, 290.0, 280.0],  # -6.67%
            "TLT": [100.0, 95.0, 90.0],  # -10%
        }

        returns = correlation_matrix.compute_90d_returns(prices)

        assert len(returns) == 3
        assert returns["SPY"] == pytest.approx(5.0, abs=0.1)
        assert returns["QQQ"] == pytest.approx(-6.67, abs=0.1)
        assert returns["TLT"] == pytest.approx(-10.0, abs=0.1)

    def test_large_return(self):
        """Test large 90-day return (like XLE recently)."""
        prices = {
            "XLE": [80.0, 100.0, 120.0, 150.0, 185.0],  # +131.25%
        }

        returns = correlation_matrix.compute_90d_returns(prices)

        assert returns["XLE"] == pytest.approx(131.25, abs=0.1)


class TestTickerVerification:
    """Tests for ticker verification logic."""

    @pytest.mark.asyncio
    async def test_verify_tickers_success(self):
        """Test successful ticker verification."""
        mock_provider = MagicMock()

        # Create async mock for get_history
        async def mock_history(ticker, days=5):
            return [
                {"price": 100.0, "fetched_at": "2026-04-10"},
                {"price": 105.0, "fetched_at": "2026-04-11"},
            ]

        mock_provider.get_history = mock_history

        tickers = ["XLK", "XLE"]
        valid, failed = await correlation_matrix.verify_tickers(mock_provider, tickers)

        assert len(valid) == 2
        assert len(failed) == 0
        assert "XLK" in valid
        assert "XLE" in valid

    @pytest.mark.asyncio
    async def test_verify_tickers_failure(self):
        """Test failed ticker verification."""
        mock_provider = MagicMock()

        async def mock_history(ticker, days=5):
            return []  # Empty = failure

        mock_provider.get_history = mock_history

        tickers = ["INVALID"]
        valid, failed = await correlation_matrix.verify_tickers(mock_provider, tickers)

        assert len(valid) == 0
        assert len(failed) == 1
        assert "INVALID" in failed

    @pytest.mark.asyncio
    async def test_verify_tickers_partial_failure(self):
        """Test partial ticker verification failure."""
        mock_provider = MagicMock()

        async def mock_history(ticker, days=5):
            if ticker == "XLK":
                return [
                    {"price": 100.0, "fetched_at": "2026-04-10"},
                    {"price": 105.0, "fetched_at": "2026-04-11"},
                ]
            return []

        mock_provider.get_history = mock_history

        tickers = ["XLK", "INVALID"]
        valid, failed = await correlation_matrix.verify_tickers(mock_provider, tickers)

        assert len(valid) == 1
        assert len(failed) == 1
        assert "XLK" in valid
        assert "INVALID" in failed


class TestIntegration:
    """Integration tests for the full correlation pipeline logic."""

    def test_full_pipeline_logic_xlk_xle(self):
        """Test the full pipeline logic for XLK/XLE pair."""
        # Simulate returns for uncorrelated assets
        np.random.seed(123)
        xlk_returns = np.random.randn(90) * 0.015  # ~1.5% daily vol
        xle_returns = np.random.randn(90) * 0.02   # ~2% daily vol

        returns_dict = {
            "XLK": list(xlk_returns),
            "XLE": list(xle_returns),
        }

        pearson_corrs, spearman_corrs = correlation_matrix.compute_correlation_matrices(returns_dict)

        key = ("XLK", "XLE")
        assert key in pearson_corrs
        # Correlation should be weak/near zero for random data
        assert abs(pearson_corrs[key]) < 0.5

    def test_90d_returns_calculation_realistic(self):
        """Test 90-day returns with realistic price data."""
        # Simulate 90 days of prices
        np.random.seed(42)
        initial_price = 100.0
        daily_returns = np.random.randn(90) * 0.01 + 0.0003  # Slight positive drift

        prices = [initial_price]
        for r in daily_returns[:-1]:
            prices.append(prices[-1] * (1 + r))

        prices_dict = {"TEST": prices}
        returns = correlation_matrix.compute_90d_returns(prices_dict)

        # Calculate expected return
        expected_return = ((prices[-1] / prices[0]) - 1) * 100

        assert "TEST" in returns
        assert returns["TEST"] == pytest.approx(expected_return, abs=0.01)


class TestMainErrorHandling:
    """Tests for main() error handling and exit codes."""

    @pytest.mark.asyncio
    async def test_main_exits_when_fmp_key_missing(self):
        """Test that main() exits with code 1 when FMP_API_KEY is missing."""
        with patch.object(correlation_matrix, 'FMP_API_KEY', None):
            with pytest.raises(SystemExit) as exc_info:
                await correlation_matrix.main()
            assert exc_info.value.code == 1

    @pytest.mark.asyncio
    async def test_main_exits_when_supabase_connection_fails(self):
        """Test that main() exits with code 1 when Supabase connection fails."""
        with patch.object(correlation_matrix, 'FMP_API_KEY', 'test-key'):
            with patch('correlation_matrix.get_supabase_client', side_effect=Exception("Connection failed")):
                with pytest.raises(SystemExit) as exc_info:
                    await correlation_matrix.main()
                assert exc_info.value.code == 1

    @pytest.mark.asyncio
    async def test_main_exits_when_no_valid_tickers(self):
        """Test that main() exits with code 1 when no tickers pass verification."""
        with patch.object(correlation_matrix, 'FMP_API_KEY', 'test-key'):
            mock_client = MagicMock()
            with patch('correlation_matrix.get_supabase_client', return_value=mock_client):
                async def empty_history(ticker, days=5):
                    return []

                mock_provider = MagicMock()
                mock_provider.get_history = empty_history
                with patch('correlation_matrix.FMPProvider', return_value=mock_provider):
                    with pytest.raises(SystemExit) as exc_info:
                        await correlation_matrix.main()
                    assert exc_info.value.code == 1

    @pytest.mark.asyncio
    async def test_main_exits_when_less_than_two_tickers_have_data(self):
        """Test that main() exits with code 1 when fewer than 2 tickers have sufficient data."""
        with patch.object(correlation_matrix, 'FMP_API_KEY', 'test-key'):
            mock_client = MagicMock()
            with patch('correlation_matrix.get_supabase_client', return_value=mock_client):
                # Mock provider to return valid history for one ticker only
                async def mock_history(ticker, days=5):
                    if ticker == "XLK":
                        return [{"price": 100.0, "fetched_at": "2026-04-01"}] * 35
                    return []

                mock_provider = MagicMock()
                mock_provider.get_history = mock_history
                with patch('correlation_matrix.FMPProvider', return_value=mock_provider):
                    with pytest.raises(SystemExit) as exc_info:
                        await correlation_matrix.main()
                    assert exc_info.value.code == 1


class TestStorageVerification:
    """Tests for post-storage verification logic."""

    def test_store_correlation_results_returns_run_id(self):
        """Test that store_correlation_results returns a valid run_id."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "test-run-id-123"}])

        pearson_corrs = {("A", "B"): 0.5}
        spearman_corrs = {("A", "B"): 0.4}
        returns_90d = {"A": 5.0, "B": 3.0}

        run_id = correlation_matrix.store_correlation_results(
            mock_client,
            ["A", "B"],
            pearson_corrs,
            spearman_corrs,
            returns_90d
        )

        assert run_id == "test-run-id-123"

    @pytest.mark.asyncio
    async def test_main_exits_when_storage_verification_fails(self):
        """Test that main() exits with code 1 when stored row count doesn't match expected."""
        with patch.object(correlation_matrix, 'FMP_API_KEY', 'test-key'):
            mock_client = MagicMock()
            with patch('correlation_matrix.get_supabase_client', return_value=mock_client):
                # Mock provider to return valid history for two tickers
                async def mock_history(ticker, days=5):
                    return [{"price": 100.0 + i, "fetched_at": f"2026-04-{i+1:02d}"} for i in range(35)]

                mock_provider = MagicMock()
                mock_provider.get_history = mock_history
                with patch('correlation_matrix.FMPProvider', return_value=mock_provider):
                    # Mock store_correlation_results to return a run_id
                    with patch('correlation_matrix.store_correlation_results', return_value="test-run-id"):
                        # Mock verification query to return mismatched count
                        mock_count_response = MagicMock()
                        mock_count_response.count = 0  # Mismatched: expected 1, got 0
                        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_count_response

                        with pytest.raises(SystemExit) as exc_info:
                            await correlation_matrix.main()
                        assert exc_info.value.code == 1

    @pytest.mark.asyncio
    async def test_main_passes_when_storage_verification_succeeds(self):
        """Test that main() completes successfully when verification passes."""
        with patch.object(correlation_matrix, 'FMP_API_KEY', 'test-key'):
            with patch.object(correlation_matrix, 'TICKER_UNIVERSE', ["XLK", "XLE"]):
                mock_client = MagicMock()
                with patch('correlation_matrix.get_supabase_client', return_value=mock_client):
                    async def mock_history(ticker, days=5):
                        return [{"price": 100.0 + i, "fetched_at": f"2026-04-{i+1:02d}"} for i in range(35)]

                    mock_provider = MagicMock()
                    mock_provider.get_history = mock_history
                    with patch('correlation_matrix.FMPProvider', return_value=mock_provider):
                        with patch('correlation_matrix.store_correlation_results', return_value="test-run-id"):
                            # Mock verification query to return matching count (1 pair for 2 tickers)
                            mock_count_response = MagicMock()
                            mock_count_response.count = 1
                            mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_count_response

                            # Should not raise SystemExit
                            await correlation_matrix.main()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
