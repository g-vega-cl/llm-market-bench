"""Tests for FSI Analytical Tools: Yield Curve Regimes, Options Vol Surface, and Thesis Ledger."""

from unittest.mock import AsyncMock, patch

import pytest

from analytics.options_surface import (
    calculate_close_to_close_realized_volatility,
    calculate_options_implied_daily_move,
    classify_iv_premium_regime,
)
from analytics.yield_curve import (
    YieldCurveRegime,
    classify_yield_curve_regime,
    format_yield_curve_regime_markdown,
)
from core.llm.tools import execute_tool

# =============================================================================
# 1. YIELD CURVE & MACRO REGIME CLASSIFICATION TESTS
# =============================================================================


def test_classify_yield_curve_regime_bull_steepener():
    """Falling yields + steepening slope (front end drops faster than long end)."""
    # 5 days ago: 2Y = 4.50%, 10Y = 4.50% (Spread = 0 bps)
    # Today:      2Y = 3.50%, 10Y = 4.20% (Spread = +70 bps, Yields fell)
    history = [
        {"date": "2026-08-25", "year2": 4.50, "year10": 4.50, "month3": 4.60, "year5": 4.50, "year30": 4.70},
        {"date": "2026-09-01", "year2": 3.50, "year10": 4.20, "month3": 3.80, "year5": 3.90, "year30": 4.60},
    ]
    result = classify_yield_curve_regime(history)
    assert result["regime"] == YieldCurveRegime.BULL_STEEPENER.value
    assert result["spread_10y_2y_bps"] == 70.0
    assert result["spread_10y_2y_5d_delta_bps"] == 70.0
    assert any("Small-Cap" in t for t in result["historical_factor_tailwinds"])


def test_classify_yield_curve_regime_bull_flattener():
    """Falling yields + flattening/inverting slope (long end rallies harder)."""
    # 5 days ago: 2Y = 4.40%, 10Y = 4.80% (Spread = +40 bps)
    # Today:      2Y = 4.30%, 10Y = 4.40% (Spread = +10 bps, Yields fell, spread narrowed)
    history = [
        {"date": "2026-08-25", "year2": 4.40, "year10": 4.80, "month3": 4.50, "year5": 4.70, "year30": 5.00},
        {"date": "2026-09-01", "year2": 4.30, "year10": 4.40, "month3": 4.40, "year5": 4.35, "year30": 4.60},
    ]
    result = classify_yield_curve_regime(history)
    assert result["regime"] == YieldCurveRegime.BULL_FLATTENER.value
    assert result["spread_10y_2y_bps"] == 10.0
    assert result["spread_10y_2y_5d_delta_bps"] == -30.0
    assert any("Mega-Cap" in t or "Growth" in t for t in result["historical_factor_tailwinds"])


def test_classify_yield_curve_regime_bear_steepener():
    """Rising yields + steepening slope (long end yields surge on inflation/supply)."""
    # 5 days ago: 2Y = 4.00%, 10Y = 4.10% (Spread = +10 bps)
    # Today:      2Y = 4.10%, 10Y = 4.70% (Spread = +60 bps, Yields rose)
    history = [
        {"date": "2026-08-25", "year2": 4.00, "year10": 4.10, "month3": 4.00, "year5": 4.05, "year30": 4.20},
        {"date": "2026-09-01", "year2": 4.10, "year10": 4.70, "month3": 4.05, "year5": 4.40, "year30": 5.10},
    ]
    result = classify_yield_curve_regime(history)
    assert result["regime"] == YieldCurveRegime.BEAR_STEEPENER.value
    assert result["spread_10y_2y_bps"] == 60.0
    assert any("Energy" in t or "Value" in t for t in result["historical_factor_tailwinds"])


def test_classify_yield_curve_regime_bear_flattener():
    """Rising yields + flattening/inverting slope (hawkish Fed hikes front end)."""
    # 5 days ago: 2Y = 3.80%, 10Y = 4.20% (Spread = +40 bps)
    # Today:      2Y = 4.60%, 10Y = 4.40% (Spread = -20 bps, Inverted, Yields rose)
    history = [
        {"date": "2026-08-25", "year2": 3.80, "year10": 4.20, "month3": 3.70, "year5": 4.00, "year30": 4.30},
        {"date": "2026-09-01", "year2": 4.60, "year10": 4.40, "month3": 4.50, "year5": 4.50, "year30": 4.55},
    ]
    result = classify_yield_curve_regime(history)
    assert result["regime"] == YieldCurveRegime.BEAR_FLATTENER.value
    assert result["spread_10y_2y_bps"] == -20.0
    assert any("Defensive" in t or "Cash" in t for t in result["historical_factor_tailwinds"])


def test_format_yield_curve_regime_markdown():
    """Verifies clean Markdown table output for tool consumers."""
    sample_data = {
        "date": "2026-09-01",
        "regime": "BULL_STEEPENER",
        "spread_10y_2y_bps": 40.0,
        "spread_10y_3m_bps": 87.0,
        "spread_10y_2y_5d_delta_bps": 12.0,
        "yield_level_direction": "FALLING",
        "historical_factor_tailwinds": ["Small-Caps (IWM)", "Regional Banks (KRE)"],
        "historical_factor_headwinds": ["Defensive Utilities (XLU)"],
    }
    md = format_yield_curve_regime_markdown(sample_data)
    assert "### 📊 Yield Curve & Macro Regime" in md
    assert "BULL_STEEPENER" in md
    assert "Small-Caps (IWM)" in md


# =============================================================================
# 2. OPTIONS VOLATILITY SURFACE & CONE TESTS
# =============================================================================


def test_realized_volatility_deterministic():
    """Verifies close-to-close realized volatility matches standard mathematical formula."""
    # 21 constant closing prices -> 0% volatility
    flat_closes = [100.0] * 21
    rv_flat = calculate_close_to_close_realized_volatility(flat_closes)
    assert rv_flat == 0.0

    # Deterministic alternating prices: 100, 102, 100, 102...
    alt_closes = [100.0 if i % 2 == 0 else 102.0 for i in range(21)]
    rv_alt = calculate_close_to_close_realized_volatility(alt_closes)
    assert rv_alt is not None
    assert 0.25 <= rv_alt <= 0.40  # Annualized volatility ~ 31%


def test_calculate_options_implied_daily_move():
    """Verifies options implied daily move cone calculation."""
    spot = 500.0
    atm_iv = 0.16  # 16% annualized IV
    move_pct, move_pts, upper_band, lower_band = calculate_options_implied_daily_move(spot, atm_iv)
    assert round(move_pct, 2) == 1.01
    assert round(move_pts, 2) == 5.04
    assert round(upper_band, 2) == 505.04
    assert round(lower_band, 2) == 494.96


def test_classify_iv_premium_regime():
    """Verifies Rich vs Cheap vs Fair classification based on IV - RV spread."""
    # IV = 20%, RV = 10% -> Premium = +10% (Rich)
    assert classify_iv_premium_regime(0.20, 0.10) == "RICH"
    # IV = 10%, RV = 18% -> Premium = -8% (Cheap)
    assert classify_iv_premium_regime(0.10, 0.18) == "CHEAP"
    # IV = 15%, RV = 14.5% -> Premium = +0.5% (Fair)
    assert classify_iv_premium_regime(0.15, 0.145) == "FAIR_VALUE"


# =============================================================================
# 3. FALSIFIABLE THESIS PILLARS & DISCONFIRMING LEDGER TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_track_thesis_pillars_disconfirming_evidence_workflow():
    """Verifies that registering disconfirming evidence transitions conviction state."""
    from unittest.mock import MagicMock

    from tools.thesis_tools import execute_track_thesis_pillars

    mock_supabase = MagicMock()
    mock_resp_empty = MagicMock(data=[])
    mock_resp_created = MagicMock(data=[{"id": "test-id"}])
    mock_resp_existing = MagicMock(
        data=[
            {
                "id": "test-id",
                "ticker": "NVDA",
                "thesis_statement": "Long NVDA on Blackwell hyperscaler demand.",
                "pillars": ["Blackwell cluster shipments accelerating", "Operating margins > 75%"],
                "risks": ["CoWoS packaging supply constraints"],
                "disconfirming_evidence": [],
                "conviction": "HIGH",
                "status": "ACTIVE",
            }
        ]
    )

    mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_resp_empty
    mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_resp_created

    with patch("tools.thesis_tools.get_supabase_client", return_value=mock_supabase):
        # 1. Create thesis
        created = await execute_track_thesis_pillars(
            ticker="NVDA",
            action="create",
            thesis_statement="Long NVDA on Blackwell hyperscaler demand.",
            pillars=["Blackwell cluster shipments accelerating", "Operating margins > 75%"],
            risks=["CoWoS packaging supply constraints"],
            price_target=160.0,
            stop_loss=115.0,
        )
        assert created["status"] == "CREATED"
        assert created["conviction"] == "HIGH"

        # Mock existing thesis for disconfirmation
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_resp_existing
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_resp_empty

        # 2. Add Disconfirming Signal -> Transitions conviction to WEAKENED
        updated = await execute_track_thesis_pillars(
            ticker="NVDA",
            action="disconfirm",
            disconfirming_factor="Hyperscaler capex guidance cut by major cloud customer",
            pillar_impacted="Blackwell cluster shipments accelerating",
        )
        assert updated["conviction"] == "WEAKENED"
        assert len(updated["disconfirming_evidence"]) >= 1


# =============================================================================
# 4. TOOL DISPATCH INTEGRATION TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_execute_tool_dispatch_new_fsi_tools():
    """Verify tool dispatcher in core/llm/tools.py resolves and runs new FSI tools."""
    with (
        patch(
            "analytics.yield_curve.get_yield_curve_regime_report",
            new_callable=AsyncMock,
            return_value={"regime": "BULL_STEEPENER", "markdown": "### 📊 Yield Curve & Macro Regime\nBULL_STEEPENER"},
        ),
        patch(
            "analytics.options_surface.get_options_vol_surface_report",
            new_callable=AsyncMock,
            return_value={"ticker": "SPY", "iv": 0.13, "markdown": "### ⚡ Options Volatility Surface: SPY"},
        ),
        patch(
            "tools.thesis_tools.execute_track_thesis_pillars",
            new_callable=AsyncMock,
            return_value={"status": "OK", "ticker": "SPY", "conviction": "HIGH"},
        ),
    ):
        curve_res = await execute_tool("get_yield_curve_regime", {})
        assert "BULL_STEEPENER" in str(curve_res)

        vol_res = await execute_tool("get_options_vol_surface", {"ticker": "SPY"})
        assert "SPY" in str(vol_res)

        thesis_res = await execute_tool("track_thesis_pillars", {"ticker": "SPY", "action": "get"})
        assert "SPY" in str(thesis_res)
