"""Unit tests for Global Macro Tracker module."""

import pytest
import math
from unittest.mock import AsyncMock, MagicMock
from core.macro_tracker import MACRO_TICKERS, get_global_macro_context


class TestMacroTickers:
    """Tests that MACRO_TICKERS uses FMP-compatible tickers."""

    def test_equity_tickers_exist(self):
        """Verify equity tickers are defined."""
        assert "Equities" in MACRO_TICKERS
        equity_tickers = MACRO_TICKERS["Equities"]
        assert "SPY" in equity_tickers
        assert "QQQ" in equity_tickers
        assert "DIA" in equity_tickers
        assert "IWM" in equity_tickers

    def test_international_tickers_exist(self):
        """Verify international tickers are defined."""
        assert "International" in MACRO_TICKERS
        intl_tickers = MACRO_TICKERS["International"]
        assert "EWJ" in intl_tickers
        assert "EWY" in intl_tickers
        assert "VGK" in intl_tickers
        assert "MCHI" in intl_tickers
        assert "EEM" in intl_tickers

    def test_commodity_tickers_exist(self):
        """Verify commodity tickers are defined."""
        assert "Commodities" in MACRO_TICKERS
        comm_tickers = MACRO_TICKERS["Commodities"]
        assert "GLD" in comm_tickers
        assert "SLV" in comm_tickers
        assert "CPER" in comm_tickers
        assert "USO" in comm_tickers

    def test_yields_indices_tickers_use_fmp_compatible_symbols(self):
        """Verify yields/indices tickers are FMP-compatible ETFs, not Yahoo-style symbols."""
        assert "Yields & Indices" in MACRO_TICKERS
        yields_tickers = MACRO_TICKERS["Yields & Indices"]
        
        assert "IEF" in yields_tickers, "Expected IEF (Treasury ETF) instead of ^TNX"
        assert "UUP" in yields_tickers, "Expected UUP (Dollar ETF) instead of DX-Y.NYB"
        assert "VIXY" in yields_tickers, "Expected VIXY (VIX ETF) instead of ^VIX"

    def test_no_yahoo_style_tickers(self):
        """Verify no Yahoo Finance-style tickers (with ^ or -Y.) are present."""
        all_tickers = []
        for category_dict in MACRO_TICKERS.values():
            all_tickers.extend(category_dict.keys())
        
        for ticker in all_tickers:
            assert not ticker.startswith("^"), f"Yahoo-style ticker {ticker} found (starts with ^)"
            assert "-Y." not in ticker, f"Yahoo-style ticker {ticker} found (contains -Y.)"

    def test_total_ticker_count(self):
        """Verify we have exactly 16 macro tickers (4+5+4+3)."""
        all_tickers = []
        for category_dict in MACRO_TICKERS.values():
            all_tickers.extend(category_dict.keys())
        assert len(all_tickers) == 16


class TestGetGlobalMacroContext:
    """Tests for get_global_macro_context function."""

    @pytest.mark.asyncio
    async def test_returns_formatted_context(self):
        """Test that function returns a formatted string with macro environment."""
        mock_mdm = MagicMock()
        mock_mdm.get_quotes = AsyncMock(return_value={
            "SPY": MagicMock(exists=True, price=450.0),
            "IEF": MagicMock(exists=True, price=95.0),
        })
        mock_mdm.get_history = AsyncMock(return_value=[
            {"price": 448.0, "fetched_at": "2024-01-02"},
            {"price": 445.0, "fetched_at": "2024-01-03"},
            {"price": 446.0, "fetched_at": "2024-01-04"},
        ])
        
        result = await get_global_macro_context(mock_mdm)
        
        assert isinstance(result, str)
        assert "GLOBAL MACRO ENVIRONMENT" in result
        assert "SPY" in result
        assert "Instruction" in result

    @pytest.mark.asyncio
    async def test_skips_missing_quotes(self):
        """Test that function skips tickers with missing quotes."""
        mock_mdm = MagicMock()
        mock_mdm.get_quotes = AsyncMock(return_value={})
        mock_mdm.get_history = AsyncMock(return_value=[])
        
        result = await get_global_macro_context(mock_mdm)
        
        assert isinstance(result, str)
        assert "GLOBAL MACRO ENVIRONMENT" in result

    @pytest.mark.asyncio
    async def test_skips_tickers_with_nan_price(self):
        """Test that function skips tickers where price is NaN."""
        mock_mdm = MagicMock()
        mock_mdm.get_quotes = AsyncMock(return_value={
            "SPY": MagicMock(exists=True, price=float('nan')),
        })
        mock_mdm.get_history = AsyncMock(return_value=[])
        
        result = await get_global_macro_context(mock_mdm)
        
        assert isinstance(result, str)
        assert "SPY" not in result

    @pytest.mark.asyncio
    async def test_handles_history_with_insufficient_data(self):
        """Test that function handles tickers with less than 2 history points."""
        mock_mdm = MagicMock()
        mock_mdm.get_quotes = AsyncMock(return_value={
            "SPY": MagicMock(exists=True, price=450.0),
        })
        mock_mdm.get_history = AsyncMock(return_value=[
            {"price": 448.0, "fetched_at": "2024-01-02"},
        ])
        
        result = await get_global_macro_context(mock_mdm)
        
        assert isinstance(result, str)
        assert "No history available" in result

    @pytest.mark.asyncio
    async def test_calculates_regime_flags_correctly(self):
        """Test that regime flags are calculated based on volatility thresholds."""
        mock_mdm = MagicMock()
        
        quote_price = 460.0
        history = [
            {"price": 450.0, "fetched_at": "2024-01-01"},
            {"price": 445.0, "fetched_at": "2024-01-02"},
            {"price": 440.0, "fetched_at": "2024-01-03"},
            {"price": 435.0, "fetched_at": "2024-01-04"},
            {"price": 430.0, "fetched_at": "2024-01-05"},
        ]
        
        mock_mdm.get_quotes = AsyncMock(return_value={
            "SPY": MagicMock(exists=True, price=quote_price),
        })
        mock_mdm.get_history = AsyncMock(return_value=history)
        
        result = await get_global_macro_context(mock_mdm)
        
        assert isinstance(result, str)
        assert "Normal" in result or "UNUSUAL" in result or "Regime Shift" in result

    @pytest.mark.asyncio
    async def test_batch_quotes_called_with_all_tickers(self):
        """Test that get_quotes is called with all 16 macro tickers."""
        mock_mdm = MagicMock()
        mock_mdm.get_quotes = AsyncMock(return_value={})
        mock_mdm.get_history = AsyncMock(return_value=[])
        
        await get_global_macro_context(mock_mdm)
        
        call_args = mock_mdm.get_quotes.call_args
        tickers_passed = call_args[0][0]
        assert len(tickers_passed) == 16
        assert "SPY" in tickers_passed
        assert "IEF" in tickers_passed
        assert "UUP" in tickers_passed
        assert "VIXY" in tickers_passed

    @pytest.mark.asyncio
    async def test_instruction_appears_at_end(self):
        """Test that the instruction text appears at the end of the output."""
        mock_mdm = MagicMock()
        mock_mdm.get_quotes = AsyncMock(return_value={})
        mock_mdm.get_history = AsyncMock(return_value=[])
        
        result = await get_global_macro_context(mock_mdm)
        
        assert result.endswith("catalyst.")

    @pytest.mark.asyncio
    async def test_positive_percentage_change_format(self):
        """Test that positive changes show + sign in output."""
        mock_mdm = MagicMock()
        history = [
            {"price": 100.0, "fetched_at": "2024-01-01"},
            {"price": 95.0, "fetched_at": "2024-01-02"},
            {"price": 96.0, "fetched_at": "2024-01-03"},
            {"price": 97.0, "fetched_at": "2024-01-04"},
            {"price": 98.0, "fetched_at": "2024-01-05"},
        ]
        mock_mdm.get_quotes = AsyncMock(return_value={
            "GLD": MagicMock(exists=True, price=100.0),
        })
        mock_mdm.get_history = AsyncMock(return_value=history)
        
        result = await get_global_macro_context(mock_mdm)
        
        assert "+" in result, "Expected + sign for positive price change"

    @pytest.mark.asyncio
    async def test_negative_percentage_change_format(self):
        """Test that negative changes show - sign in output."""
        mock_mdm = MagicMock()
        history = [
            {"price": 90.0, "fetched_at": "2024-01-01"},
            {"price": 95.0, "fetched_at": "2024-01-02"},
            {"price": 96.0, "fetched_at": "2024-01-03"},
            {"price": 97.0, "fetched_at": "2024-01-04"},
            {"price": 98.0, "fetched_at": "2024-01-05"},
        ]
        mock_mdm.get_quotes = AsyncMock(return_value={
            "GLD": MagicMock(exists=True, price=90.0),
        })
        mock_mdm.get_history = AsyncMock(return_value=history)
        
        result = await get_global_macro_context(mock_mdm)
        
        assert "-" in result, "Expected - sign for negative price change"

    @pytest.mark.asyncio
    async def test_get_history_called_for_each_valid_ticker(self):
        """Test that get_history is called for each ticker with a valid quote."""
        mock_mdm = MagicMock()
        mock_mdm.get_quotes = AsyncMock(return_value={
            "SPY": MagicMock(exists=True, price=450.0),
            "QQQ": MagicMock(exists=True, price=380.0),
            "GLD": MagicMock(exists=True, price=180.0),
        })
        mock_mdm.get_history = AsyncMock(return_value=[
            {"price": 445.0, "fetched_at": "2024-01-01"},
            {"price": 440.0, "fetched_at": "2024-01-02"},
        ])
        
        await get_global_macro_context(mock_mdm)
        
        assert mock_mdm.get_history.call_count == 3

    @pytest.mark.asyncio
    async def test_skips_ticker_when_quote_not_exists(self):
        """Test that tickers with exists=False are skipped."""
        mock_mdm = MagicMock()
        mock_mdm.get_quotes = AsyncMock(return_value={
            "SPY": MagicMock(exists=False, price=450.0),
            "QQQ": MagicMock(exists=True, price=380.0),
        })
        mock_mdm.get_history = AsyncMock(return_value=[])
        
        result = await get_global_macro_context(mock_mdm)
        
        assert "SPY" not in result
        assert "QQQ" in result

    @pytest.mark.asyncio
    async def test_zero_yesterday_close_handled(self):
        """Test that zero yesterday_close doesn't cause division by zero."""
        mock_mdm = MagicMock()
        history = [
            {"price": 100.0, "fetched_at": "2024-01-01"},
            {"price": 0.0, "fetched_at": "2024-01-02"},
            {"price": 50.0, "fetched_at": "2024-01-03"},
        ]
        mock_mdm.get_quotes = AsyncMock(return_value={
            "GLD": MagicMock(exists=True, price=100.0),
        })
        mock_mdm.get_history = AsyncMock(return_value=history)
        
        result = await get_global_macro_context(mock_mdm)
        
        assert isinstance(result, str)
        assert "GLD" in result

    @pytest.mark.asyncio
    async def test_all_four_categories_present(self):
        """Test that all four ticker categories are present in output."""
        mock_mdm = MagicMock()
        mock_mdm.get_quotes = AsyncMock(return_value={
            "SPY": MagicMock(exists=True, price=450.0),
            "EWJ": MagicMock(exists=True, price=80.0),
            "GLD": MagicMock(exists=True, price=180.0),
            "IEF": MagicMock(exists=True, price=95.0),
        })
        mock_mdm.get_history = AsyncMock(return_value=[
            {"price": 445.0, "fetched_at": "2024-01-01"},
            {"price": 440.0, "fetched_at": "2024-01-02"},
            {"price": 442.0, "fetched_at": "2024-01-03"},
        ])
        
        result = await get_global_macro_context(mock_mdm)
        
        assert "[ EQUITIES ]" in result
        assert "[ INTERNATIONAL ]" in result
        assert "[ COMMODITIES ]" in result
        assert "[ YIELDS & INDICES ]" in result


class TestMacroTrackerYieldIndices:
    """Specific tests for Yields & Indices category."""

    def test_yields_ticker_names_are_descriptive(self):
        """Verify yield/index tickers have meaningful descriptions."""
        yields = MACRO_TICKERS["Yields & Indices"]
        
        assert "10-Yr" in yields["IEF"] or "Treasury" in yields["IEF"]
        assert "Dollar" in yields["UUP"] or "DXY" in yields["UUP"]
        assert "Volatility" in yields["VIXY"] or "VIX" in yields["VIXY"]

    @pytest.mark.asyncio
    async def test_fmp_compatible_tickers_can_be_fetched(self):
        """Verify the FMP-compatible tickers can be passed to market data manager."""
        yield_tickers = list(MACRO_TICKERS["Yields & Indices"].keys())
        
        assert "IEF" in yield_tickers
        assert "UUP" in yield_tickers
        assert "VIXY" in yield_tickers
        
        all_tickers = []
        for category in MACRO_TICKERS.values():
            all_tickers.extend(category.keys())
        
        for ticker in all_tickers:
            assert ticker.isalpha() or ticker in ["IEF", "UUP", "VIXY"], f"Ticker {ticker} may not be FMP-compatible"

    def test_yields_indices_tickers_are_uppercase(self):
        """Verify all yield/index tickers are uppercase."""
        yields = MACRO_TICKERS["Yields & Indices"]
        for ticker in yields.keys():
            assert ticker.isupper(), f"Ticker {ticker} should be uppercase"
            assert ticker.isalpha(), f"Ticker {ticker} should be alphabetic"

    def test_yields_indices_tickers_match_fmp_etf_format(self):
        """Verify tickers follow FMP ETF ticker format (3-4 letters)."""
        yields = MACRO_TICKERS["Yields & Indices"]
        for ticker in yields.keys():
            assert 3 <= len(ticker) <= 4, f"Ticker {ticker} should be 3-4 characters"
            assert ticker.isalpha(), f"Ticker {ticker} should be alphabetic"
