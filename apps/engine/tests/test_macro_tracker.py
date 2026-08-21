"""Unit tests for Global Macro Tracker module."""

from unittest.mock import MagicMock

import pytest

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
        """Verify we have exactly 24 macro tickers (5+8+5+3+2+1)."""
        all_tickers = []
        for category_dict in MACRO_TICKERS.values():
            all_tickers.extend(category_dict.keys())
        assert len(all_tickers) == 24


class TestGetGlobalMacroContext:
    """Tests for get_global_macro_context function."""

    @pytest.mark.asyncio
    async def test_returns_formatted_context(self):
        """Test that function returns a formatted string with macro environment."""
        mock_mdm = MagicMock()
        mock_data = [
            {
                "ticker": "SPY",
                "price": 450.0,
                "today_pct_change": 1.25,
                "stdev_pct": 0.85,
                "regime_flag": "Normal",
            },
            {
                "ticker": "IEF",
                "price": 95.0,
                "today_pct_change": -0.45,
                "stdev_pct": 0.35,
                "regime_flag": "Normal",
            },
        ]
        mock_execute = MagicMock(return_value=MagicMock(data=mock_data))
        mock_in = MagicMock(return_value=MagicMock(execute=mock_execute))
        mock_select = MagicMock(return_value=MagicMock(in_=mock_in))
        mock_table = MagicMock(return_value=MagicMock(select=mock_select))
        mock_mdm.client = MagicMock(table=mock_table)

        result = await get_global_macro_context(mock_mdm)

        assert isinstance(result, str)
        assert "GLOBAL MACRO ENVIRONMENT (PRIOR SESSION CLOSE)" in result
        assert "S&P 500" in result
        assert "prior close" in result
        assert "Instruction" not in result

    @pytest.mark.asyncio
    async def test_skips_missing_quotes(self):
        """Test that function handles missing cache data cleanly."""
        mock_mdm = MagicMock()
        mock_execute = MagicMock(return_value=MagicMock(data=[]))
        mock_in = MagicMock(return_value=MagicMock(execute=mock_execute))
        mock_select = MagicMock(return_value=MagicMock(in_=mock_in))
        mock_table = MagicMock(return_value=MagicMock(select=mock_select))
        mock_mdm.client = MagicMock(table=mock_table)

        result = await get_global_macro_context(mock_mdm)

        assert isinstance(result, str)
        assert "GLOBAL MACRO ENVIRONMENT" in result

    @pytest.mark.asyncio
    async def test_calculates_regime_flags_correctly(self):
        """Test that regime flags are fetched correctly from pre-calculated stats."""
        mock_mdm = MagicMock()
        mock_data = [
            {
                "ticker": "SPY",
                "price": 450.0,
                "today_pct_change": 3.5,
                "stdev_pct": 0.85,
                "regime_flag": "⚠️ HIGHLY UNUSUAL",
            },
        ]
        mock_execute = MagicMock(return_value=MagicMock(data=mock_data))
        mock_in = MagicMock(return_value=MagicMock(execute=mock_execute))
        mock_select = MagicMock(return_value=MagicMock(in_=mock_in))
        mock_table = MagicMock(return_value=MagicMock(select=mock_select))
        mock_mdm.client = MagicMock(table=mock_table)

        result = await get_global_macro_context(mock_mdm)

        assert isinstance(result, str)
        assert "⚠️ HIGHLY UNUSUAL (Regime Shift)" in result

    @pytest.mark.asyncio
    async def test_batch_quotes_called_with_all_tickers(self):
        """Test that client queries the cache with the expected list."""
        mock_mdm = MagicMock()
        mock_execute = MagicMock(return_value=MagicMock(data=[]))
        mock_in = MagicMock(return_value=MagicMock(execute=mock_execute))
        mock_select = MagicMock(return_value=MagicMock(in_=mock_in))
        mock_table = MagicMock(return_value=MagicMock(select=mock_select))
        mock_mdm.client = MagicMock(table=mock_table)

        await get_global_macro_context(mock_mdm)

        mock_in.assert_called_once()
        tickers_passed = mock_in.call_args[0][1]
        assert len(tickers_passed) == 24
        assert "SPY" in tickers_passed
        assert "IEF" in tickers_passed
        assert "UUP" in tickers_passed
        assert "VIXY" in tickers_passed

    @pytest.mark.asyncio
    async def test_instruction_appears_at_end(self):
        """Test that the instruction text is not present in the output."""
        mock_mdm = MagicMock()
        mock_execute = MagicMock(return_value=MagicMock(data=[]))
        mock_in = MagicMock(return_value=MagicMock(execute=mock_execute))
        mock_select = MagicMock(return_value=MagicMock(in_=mock_in))
        mock_table = MagicMock(return_value=MagicMock(select=mock_select))
        mock_mdm.client = MagicMock(table=mock_table)

        result = await get_global_macro_context(mock_mdm)

        assert "Instruction" not in result

    @pytest.mark.asyncio
    async def test_positive_percentage_change_format(self):
        """Test that positive changes show + sign in output."""
        mock_mdm = MagicMock()
        mock_data = [
            {
                "ticker": "GLD",
                "price": 100.0,
                "today_pct_change": 1.25,
                "stdev_pct": 0.85,
                "regime_flag": "Normal",
            },
        ]
        mock_execute = MagicMock(return_value=MagicMock(data=mock_data))
        mock_in = MagicMock(return_value=MagicMock(execute=mock_execute))
        mock_select = MagicMock(return_value=MagicMock(in_=mock_in))
        mock_table = MagicMock(return_value=MagicMock(select=mock_select))
        mock_mdm.client = MagicMock(table=mock_table)

        result = await get_global_macro_context(mock_mdm)

        assert "+1.25%" in result, "Expected + sign for positive price change"

    @pytest.mark.asyncio
    async def test_negative_percentage_change_format(self):
        """Test that negative changes show - sign in output."""
        mock_mdm = MagicMock()
        mock_data = [
            {
                "ticker": "GLD",
                "price": 90.0,
                "today_pct_change": -1.25,
                "stdev_pct": 0.85,
                "regime_flag": "Normal",
            },
        ]
        mock_execute = MagicMock(return_value=MagicMock(data=mock_data))
        mock_in = MagicMock(return_value=MagicMock(execute=mock_execute))
        mock_select = MagicMock(return_value=MagicMock(in_=mock_in))
        mock_table = MagicMock(return_value=MagicMock(select=mock_select))
        mock_mdm.client = MagicMock(table=mock_table)

        result = await get_global_macro_context(mock_mdm)

        assert "-1.25%" in result, "Expected - sign for negative price change"

    @pytest.mark.asyncio
    async def test_all_six_categories_present(self):
        """Test that all six ticker categories are present in output."""
        mock_mdm = MagicMock()
        mock_data = [
            {"ticker": "SPY", "price": 450.0, "today_pct_change": 1.0, "stdev_pct": 0.5, "regime_flag": "Normal"},
            {"ticker": "EWJ", "price": 80.0, "today_pct_change": 1.0, "stdev_pct": 0.5, "regime_flag": "Normal"},
            {"ticker": "GLD", "price": 180.0, "today_pct_change": 1.0, "stdev_pct": 0.5, "regime_flag": "Normal"},
            {"ticker": "IEF", "price": 95.0, "today_pct_change": 1.0, "stdev_pct": 0.5, "regime_flag": "Normal"},
            {"ticker": "UUP", "price": 28.0, "today_pct_change": 1.0, "stdev_pct": 0.5, "regime_flag": "Normal"},
            {"ticker": "BTCUSD", "price": 87000.0, "today_pct_change": 1.0, "stdev_pct": 0.5, "regime_flag": "Normal"},
        ]
        mock_execute = MagicMock(return_value=MagicMock(data=mock_data))
        mock_in = MagicMock(return_value=MagicMock(execute=mock_execute))
        mock_select = MagicMock(return_value=MagicMock(in_=mock_in))
        mock_table = MagicMock(return_value=MagicMock(select=mock_select))
        mock_mdm.client = MagicMock(table=mock_table)

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
