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
        assert "EWU" in intl_tickers
        assert "EWC" in intl_tickers
        assert "INDA" in intl_tickers

    def test_commodity_tickers_exist(self):
        """Verify commodity tickers are defined."""
        assert "Commodities" in MACRO_TICKERS
        comm_tickers = MACRO_TICKERS["Commodities"]
        assert "GLD" in comm_tickers
        assert "SLV" in comm_tickers
        assert "CPER" in comm_tickers
        assert "USO" in comm_tickers
        assert "UNG" in comm_tickers

    def test_fixed_income_tickers_use_fmp_compatible_symbols(self):
        """Verify fixed income tickers are FMP-compatible ETFs, not Yahoo-style symbols."""
        assert "Fixed Income" in MACRO_TICKERS
        fi_tickers = MACRO_TICKERS["Fixed Income"]

        assert "IEF" in fi_tickers, "Expected IEF (Treasury ETF) instead of ^TNX"
        assert "TLT" in fi_tickers, "Expected TLT (Long Treasury ETF)"
        assert "TIP" in fi_tickers, "Expected TIP (TIPS ETF)"

    def test_fx_risk_tickers_use_fmp_compatible_symbols(self):
        """Verify FX & Risk tickers are FMP-compatible ETFs."""
        assert "FX & Risk" in MACRO_TICKERS
        fx_tickers = MACRO_TICKERS["FX & Risk"]

        assert "UUP" in fx_tickers, "Expected UUP (Dollar ETF)"
        assert "VIXY" in fx_tickers, "Expected VIXY (VIX ETF)"

    def test_crypto_tickers_exist(self):
        """Verify crypto tickers are defined."""
        assert "Crypto" in MACRO_TICKERS
        crypto_tickers = MACRO_TICKERS["Crypto"]
        assert "BTCUSD" in crypto_tickers

    def test_no_yahoo_style_tickers(self):
        """Verify no Yahoo Finance-style tickers (with ^ or -Y.) are present."""
        all_tickers = []
        for category_dict in MACRO_TICKERS.values():
            all_tickers.extend(category_dict.keys())
        
        for ticker in all_tickers:
            assert not ticker.startswith("^"), f"Yahoo-style ticker {ticker} found (starts with ^)"
            assert "-Y." not in ticker, f"Yahoo-style ticker {ticker} found (contains -Y.)"

    def test_total_ticker_count(self):
        """Verify we have exactly 23 macro tickers (4+8+5+3+2+1)."""
        all_tickers = []
        for category_dict in MACRO_TICKERS.values():
            all_tickers.extend(category_dict.keys())
        assert len(all_tickers) == 23


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
        """Test that get_quotes is called with all 23 macro tickers."""
        mock_mdm = MagicMock()
        mock_mdm.get_quotes = AsyncMock(return_value={})
        mock_mdm.get_history = AsyncMock(return_value=[])

        await get_global_macro_context(mock_mdm)

        call_args = mock_mdm.get_quotes.call_args
        tickers_passed = call_args[0][0]
        assert len(tickers_passed) == 23
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
    async def test_all_six_categories_present(self):
        """Test that all six ticker categories are present in output."""
        mock_mdm = MagicMock()
        mock_mdm.get_quotes = AsyncMock(return_value={
            "SPY": MagicMock(exists=True, price=450.0),
            "EWJ": MagicMock(exists=True, price=80.0),
            "GLD": MagicMock(exists=True, price=180.0),
            "IEF": MagicMock(exists=True, price=95.0),
            "UUP": MagicMock(exists=True, price=28.0),
            "BTCUSD": MagicMock(exists=True, price=87000.0),
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
        assert "[ FIXED INCOME ]" in result
        assert "[ FX & RISK ]" in result
        assert "[ CRYPTO ]" in result


class TestMacroTrackerFixedIncome:
    """Specific tests for Fixed Income category."""

    def test_fixed_income_ticker_names_are_descriptive(self):
        """Verify fixed income tickers have meaningful descriptions."""
        fi = MACRO_TICKERS["Fixed Income"]

        assert "Treasury" in fi["IEF"] or "7-10yr" in fi["IEF"]
        assert "Treasury" in fi["TLT"] or "20+yr" in fi["TLT"]
        assert "TIPS" in fi["TIP"] or "Inflation" in fi["TIP"]

    @pytest.mark.asyncio
    async def test_fmp_compatible_tickers_can_be_fetched(self):
        """Verify the FMP-compatible tickers can be passed to market data manager."""
        fi_tickers = list(MACRO_TICKERS["Fixed Income"].keys())
        fx_tickers = list(MACRO_TICKERS["FX & Risk"].keys())

        assert "IEF" in fi_tickers
        assert "TLT" in fi_tickers
        assert "TIP" in fi_tickers
        assert "UUP" in fx_tickers
        assert "VIXY" in fx_tickers

        all_tickers = []
        for category in MACRO_TICKERS.values():
            all_tickers.extend(category.keys())

        for ticker in all_tickers:
            # Allow alphanumeric tickers (BTCUSD) alongside alphabetic ones
            assert ticker.isalnum(), f"Ticker {ticker} should be alphanumeric"
