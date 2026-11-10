"""Tests for audit_price_overreaction and get_high_iv_ratio_watchlist tools.

Hermetic test suite with zero outbound network calls, mocking MarketDataManager,
MassiveOptionsClient, and Supabase database calls.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from analytics.overreaction import audit_price_overreaction_report
from analytics.volatility_ratio import (
    calculate_iv_hist_iv_ratio,
    classify_vol_ratio_regime,
    get_high_iv_ratio_watchlist_report,
    resolve_watchlist_universe,
)
from core.llm.tools import execute_tool

# =============================================================================
# VOLATILITY RATIO UNIT TESTS
# =============================================================================


def test_classify_vol_ratio_regime():
    """Verify IV/HistIV regime classification boundaries."""
    assert classify_vol_ratio_regime(2.1) == "COILED_SPRING_EXTREME"
    assert classify_vol_ratio_regime(1.8) == "COILED_SPRING_EXTREME"
    assert classify_vol_ratio_regime(1.5) == "VOL_RICH"
    assert classify_vol_ratio_regime(1.3) == "VOL_RICH"
    assert classify_vol_ratio_regime(1.0) == "FAIR_VOL"
    assert classify_vol_ratio_regime(0.8) == "FAIR_VOL"
    assert classify_vol_ratio_regime(0.6) == "VOL_CHEAP"


def test_calculate_iv_hist_iv_ratio_math():
    """Verify precision math of IV / HistIV ratio."""
    # ATM IV 45%, HistIV 25% -> 1.80x
    ratio = calculate_iv_hist_iv_ratio(0.45, 0.25)
    assert ratio == 1.8

    # HistIV 0 or invalid returns None
    assert calculate_iv_hist_iv_ratio(0.45, 0.0) is None
    assert calculate_iv_hist_iv_ratio(0.0, 0.25) is None


@pytest.mark.asyncio
async def test_resolve_watchlist_universe_mega_mid():
    """Verify mega_mid returns liquid basket."""
    tickers = await resolve_watchlist_universe("mega_mid")
    assert "SPY" in tickers
    assert "NVDA" in tickers
    assert "AAPL" in tickers


@pytest.mark.asyncio
async def test_resolve_watchlist_universe_custom():
    """Verify custom ticker string splitting."""
    tickers = await resolve_watchlist_universe("custom", custom_tickers="pltr, coin,  mara ")
    assert tickers == ["PLTR", "COIN", "MARA"]


@pytest.mark.asyncio
async def test_resolve_watchlist_universe_portfolio():
    """Verify portfolio universe retrieves active tickers from position_pnl."""
    mock_sb = MagicMock()
    mock_pos_res = MagicMock()
    mock_pos_res.data = [
        {"ticker": "MSFT", "quantity": 10},
        {"ticker": "GOOGL", "quantity": 5},
        {"ticker": "NVDA_SHORT", "quantity": -8},
        {"ticker": "CASH", "quantity": 0},
    ]
    mock_sb.table.return_value.select.return_value.execute.return_value = mock_pos_res

    with patch("analytics.volatility_ratio.get_supabase_client", return_value=mock_sb):
        tickers = await resolve_watchlist_universe("portfolio")
        assert "MSFT" in tickers
        assert "GOOGL" in tickers
        assert "NVDA_SHORT" in tickers
        assert "CASH" not in tickers


@pytest.mark.asyncio
async def test_get_high_iv_ratio_watchlist_report_sorting():
    """Verify watchlist computes ratios and sorts descending by IV/HistIV ratio."""
    mock_vol_surface = AsyncMock()

    async def mock_vol_report(ticker="SPY", **kwargs):
        t = ticker
        if t == "HIGH_VOL":
            return {
                "status": "OK",
                "ticker": "HIGH_VOL",
                "spot_price": 100.0,
                "atm_iv": 0.60,
                "realized_vol_20d": 0.20,  # 3.0x ratio
                "iv_premium_pct": 40.0,
            }
        elif t == "MID_VOL":
            return {
                "status": "OK",
                "ticker": "MID_VOL",
                "spot_price": 50.0,
                "atm_iv": 0.30,
                "realized_vol_20d": 0.20,  # 1.5x ratio
                "iv_premium_pct": 10.0,
            }
        else:
            return {
                "status": "OK",
                "ticker": "LOW_VOL",
                "spot_price": 20.0,
                "atm_iv": 0.15,
                "realized_vol_20d": 0.25,  # 0.6x ratio
                "iv_premium_pct": -10.0,
            }

    mock_vol_surface.side_effect = mock_vol_report

    with patch("analytics.volatility_ratio.get_options_vol_surface_report", mock_vol_surface):
        report = await get_high_iv_ratio_watchlist_report(
            universe="custom", custom_tickers="LOW_VOL,HIGH_VOL,MID_VOL", min_ratio="0.5", limit="5"
        )

        assert report["status"] == "OK"
        items = report["items"]
        assert len(items) == 3
        # Sorted descending by ratio
        assert items[0]["ticker"] == "HIGH_VOL"
        assert items[0]["ratio"] == 3.0
        assert items[0]["regime"] == "COILED_SPRING_EXTREME"
        assert items[1]["ticker"] == "MID_VOL"
        assert items[1]["ratio"] == 1.5
        assert items[2]["ticker"] == "LOW_VOL"
        assert items[2]["ratio"] == 0.6
        assert "⚡ High IV / HistIV Watchlist" in report["markdown"]


# =============================================================================
# OVERREACTION AUDIT TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_audit_price_overreaction_identifies_statistical_overreaction():
    """Verify statistical overreaction when price plunges > 2.5 sigma on high volume but revisions are intact."""
    mock_mdm = MagicMock()
    # 20 days of prices: dropped from 100 to 85 today (-15%), historical daily std is ~1.5%
    historical_bars = []
    # 20 steady days around 100
    for i in range(20):
        historical_bars.append({"price": 100.0 + (i % 3) * 0.5, "volume": 1000000})
    # Today bar: sharp drop to 85, massive volume 4,000,000 (RVOL 4.0)
    mock_mdm.get_history = AsyncMock(return_value=historical_bars)
    mock_mdm.get_quote = AsyncMock(
        return_value=MagicMock(price=85.0, change_percent=-15.0, volume=4000000, avg_volume=1000000)
    )

    mock_vol_report = AsyncMock(
        return_value={
            "status": "OK",
            "ticker": "PANIC_STOCK",
            "spot_price": 85.0,
            "atm_iv": 0.40,
            "implied_daily_move_pct": 2.52,  # 1-sigma move is ~2.5%
            "implied_daily_move_pts": 2.14,
        }
    )

    # Analyst consensus revisions intact (no downgrades)
    mock_fmp = AsyncMock(return_value=[{"consensusTarget": 110.0, "strongBuy": 10, "buy": 15, "hold": 2, "sell": 0}])

    with (
        patch("analytics.overreaction.MarketDataManager", return_value=mock_mdm),
        patch("analytics.overreaction.get_options_vol_surface_report", mock_vol_report),
        patch("analytics.overreaction.fetch_analyst_targets", mock_fmp),
    ):
        report = await audit_price_overreaction_report(ticker="PANIC_STOCK", lookback_days="20")

        assert report["status"] == "OK"
        assert report["verdict"] == "STATISTICAL_OVERREACTION"
        assert report["rvol"] >= 2.5
        assert report["cone_multiplier"] >= 2.0
        assert "STATISTICAL_OVERREACTION" in report["markdown"]


@pytest.mark.asyncio
async def test_audit_price_overreaction_low_rvol_prevents_statistical_overreaction():
    """Verify that an illiquid low-volume drift does NOT trigger statistical overreaction."""
    mock_mdm = MagicMock()
    historical_bars = [{"price": 100.0 + (i % 3) * 0.5, "volume": 1000000} for i in range(20)]
    mock_mdm.get_history = AsyncMock(return_value=historical_bars)
    # RVOL is only 0.2 (low volume)
    mock_mdm.get_quote = AsyncMock(
        return_value=MagicMock(price=85.0, change_percent=-15.0, volume=200000, avg_volume=1000000)
    )

    mock_vol_report = AsyncMock(
        return_value={
            "status": "OK",
            "ticker": "ILLIQUID_STOCK",
            "spot_price": 85.0,
            "atm_iv": 0.40,
            "implied_daily_move_pct": 2.52,
            "implied_daily_move_pts": 2.14,
        }
    )

    mock_fmp = AsyncMock(return_value=[{"consensusTarget": 110.0}])

    with (
        patch("analytics.overreaction.MarketDataManager", return_value=mock_mdm),
        patch("analytics.overreaction.get_options_vol_surface_report", mock_vol_report),
        patch("analytics.overreaction.fetch_analyst_targets", mock_fmp),
    ):
        report = await audit_price_overreaction_report(ticker="ILLIQUID_STOCK")

        assert report["status"] == "OK"
        # Low volume prevents overreaction classification
        assert report["verdict"] == "NORMAL_VOLATILITY"


@pytest.mark.asyncio
async def test_audit_price_overreaction_identifies_justified_repricing():
    """Verify justified repricing when price drops but analyst targets slashed severely."""
    mock_mdm = MagicMock()
    historical_bars = [{"price": 100.0 + (i % 3) * 0.5, "volume": 1000000} for i in range(20)]
    mock_mdm.get_history = AsyncMock(return_value=historical_bars)
    mock_mdm.get_quote = AsyncMock(
        return_value=MagicMock(price=70.0, change_percent=-30.0, volume=5000000, avg_volume=1000000)
    )

    mock_vol_report = AsyncMock(
        return_value={
            "status": "OK",
            "ticker": "FRAUD_CORP",
            "spot_price": 70.0,
            "atm_iv": 0.80,
            "implied_daily_move_pct": 5.0,
            "implied_daily_move_pts": 3.5,
        }
    )

    # Slashing revisions (target cut from 120 to 65, sells increased)
    mock_fmp = AsyncMock(
        return_value=[
            {
                "consensusTarget": 65.0,
                "targetPrior": 120.0,
                "strongBuy": 0,
                "buy": 1,
                "hold": 5,
                "sell": 12,
            }
        ]
    )

    with (
        patch("analytics.overreaction.MarketDataManager", return_value=mock_mdm),
        patch("analytics.overreaction.get_options_vol_surface_report", mock_vol_report),
        patch("analytics.overreaction.fetch_analyst_targets", mock_fmp),
    ):
        report = await audit_price_overreaction_report(ticker="FRAUD_CORP")

        assert report["status"] == "OK"
        assert report["verdict"] == "JUSTIFIED_REPRICING"
        assert "JUSTIFIED_REPRICING" in report["markdown"]


@pytest.mark.asyncio
async def test_tools_execution_via_dispatcher():
    """Verify tool execution via execute_tool convenience dispatcher."""
    with (
        patch("core.llm.tools.execute_high_iv_ratio_watchlist_tool", new_callable=AsyncMock) as mock_ratio,
        patch("core.llm.tools.execute_audit_price_overreaction_tool", new_callable=AsyncMock) as mock_audit,
    ):
        mock_ratio.return_value = "### Watchlist Test"
        mock_audit.return_value = "### Overreaction Test"

        res_ratio = await execute_tool("get_high_iv_ratio_watchlist", {"universe": "mega_mid"})
        assert "Watchlist Test" in res_ratio

        res_audit = await execute_tool("audit_price_overreaction", {"ticker": "AAPL"})
        assert "Overreaction Test" in res_audit


@pytest.mark.asyncio
async def test_tool_execution_wrappers_direct():
    """Verify tool wrappers directly execute and format gracefully on errors."""
    from tools.overreaction import execute_audit_price_overreaction_tool
    from tools.technicals_options import execute_high_iv_ratio_watchlist_tool

    with patch("tools.overreaction.audit_price_overreaction_report", new_callable=AsyncMock) as mock_audit:
        mock_audit.return_value = {"markdown": "### Direct Audit Markdown"}
        out = await execute_audit_price_overreaction_tool(ticker="TSLA")
        assert "Direct Audit Markdown" in out

        mock_audit.side_effect = RuntimeError("Service down")
        err_out = await execute_audit_price_overreaction_tool(ticker="TSLA")
        assert "Error executing audit_price_overreaction" in err_out

    with patch("analytics.volatility_ratio.get_high_iv_ratio_watchlist_report", new_callable=AsyncMock) as mock_wl:
        mock_wl.return_value = {"markdown": "### Direct Watchlist Markdown"}
        out_wl = await execute_high_iv_ratio_watchlist_tool(universe="mega_mid")
        assert "Direct Watchlist Markdown" in out_wl

        mock_wl.side_effect = RuntimeError("Database timeout")
        err_wl = await execute_high_iv_ratio_watchlist_tool(universe="mega_mid")
        assert "Error executing get_high_iv_ratio_watchlist" in err_wl
