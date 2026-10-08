"""TDD Tests for Systematic Daily Bond Predictor."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from tasks.bond_predictor import (
    BOND_PREDICTOR_MODELS,
    BOND_TOOLBOX,
    compile_jev_bond_context,
    construct_lean_bond_prompt,
    run_daily_bond_prediction,
)


def test_bond_toolbox_contains_curated_tools():
    """Verify bond toolbox contains agreed curated tools."""
    assert "get_treasury_yield_curve" in BOND_TOOLBOX
    assert "get_today_economic_releases" in BOND_TOOLBOX
    assert "get_yield_curve_regime" in BOND_TOOLBOX
    assert "get_macro_options_sentiment" in BOND_TOOLBOX
    assert "get_calendar_scenario_analysis" in BOND_TOOLBOX


def test_bond_predictor_models_lineup():
    """Verify model lineup contains gpt-5.6-luna, deepseek-v4-flash, and jev."""
    model_names = [m["name"] for m in BOND_PREDICTOR_MODELS]
    assert any("luna" in name.lower() or "5.6" in name.lower() for name in model_names)
    assert any("deepseek" in name.lower() for name in model_names)
    assert any("jev" in name.lower() for name in model_names)


def test_construct_lean_bond_prompt():
    """Verify lean prompt has date, TLT ticker, quote, and no raw data dumps."""
    quote = {"price": 92.45, "change": -0.35, "change_pct": -0.38, "previous_close": 92.80}
    prompt = construct_lean_bond_prompt(ticker="TLT", quote=quote, date_str="2026-10-07")
    assert "TLT" in prompt
    assert "2026-10-07" in prompt
    assert "92.45" in prompt
    assert "-0.38%" in prompt
    # Strict Principle 8 check: prompt must NOT dump raw tables or pre-injected news
    assert "GLOBAL MACRO ENVIRONMENT:" not in prompt
    assert "=== YIELD CURVE REPORT ===" not in prompt


@pytest.mark.asyncio
async def test_compile_jev_bond_context():
    """Verify Jev automated tool bundle compiles yield curve and economic releases."""
    with (
        patch(
            "tasks.bond_predictor.execute_get_treasury_yield_curve_tool",
            new_callable=AsyncMock,
            return_value="### US Treasury Yield Curve Snapshot\n10Y: 4.10%",
        ),
        patch(
            "tasks.bond_predictor.execute_get_today_economic_releases_tool",
            new_callable=AsyncMock,
            return_value="Today's Releases: CPI YoY 2.4%",
        ),
    ):
        quote = {"price": 92.45, "change": -0.35, "change_pct": -0.38, "previous_close": 92.80}
        ctx = await compile_jev_bond_context(ticker="TLT", quote=quote, date_str="2026-10-07")
        assert "US Treasury Yield Curve" in ctx
        assert "CPI YoY 2.4%" in ctx
        assert "TLT" in ctx


@pytest.mark.asyncio
async def test_run_daily_bond_prediction_success():
    """Verify run_daily_bond_prediction executes across models and inserts into Supabase."""
    mock_supabase = MagicMock()
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table

    # Existing predictions check returns empty
    mock_select = MagicMock()
    mock_select.eq.return_value = mock_select
    mock_select.execute.return_value = MagicMock(data=[])
    mock_table.select.return_value = mock_select

    # Insert execution returns mock ID
    mock_insert = MagicMock()
    mock_insert.execute.return_value = MagicMock(data=[{"id": "pred-123"}])
    mock_table.insert.return_value = mock_insert

    mock_quote = {"price": 92.45, "change": -0.35, "change_pct": -0.38, "previous_close": 92.80}

    with (
        patch("tasks.bond_predictor.get_supabase_client", return_value=mock_supabase),
        patch(
            "execution.market_data.MarketDataManager.get_premarket_quote",
            new_callable=AsyncMock,
            return_value=mock_quote,
        ),
        patch("execution.market_data.MarketDataManager.is_trading_day", new_callable=AsyncMock, return_value=True),
        patch("tasks.bond_predictor.predict_bond_with_reasoning_model", new_callable=AsyncMock) as mock_reasoning,
        patch("tasks.bond_predictor.compile_jev_bond_context", new_callable=AsyncMock, return_value="Mock Jev Context"),
        patch("tasks.bond_predictor.predict_daily_with_jev", new_callable=AsyncMock) as mock_jev,
        patch(
            "tasks.bond_predictor.get_ny_now",
            return_value=datetime(2026, 10, 7, 8, 30, tzinfo=ZoneInfo("America/New_York")),
        ),
    ):
        mock_reasoning.return_value = {
            "predicted_direction": "UP",
            "confidence": 68.0,
            "expected_return_pct": 0.45,
            "rationale": "Yield curve steepening and soft PPI print favors duration.",
            "catalysts": ["PPI print", "10Y yield pullback"],
        }
        mock_jev.return_value = {
            "predicted_direction": "UP",
            "confidence": 72.0,
            "expected_return_pct": 0.0,
            "rationale": "Jev decisions classification: UP (P=0.72)",
            "catalysts": [],
        }

        results = await run_daily_bond_prediction(ticker="TLT", force=False)
        assert len(results) == 3
        assert all(r["status"] == "success" for r in results)
        assert mock_table.insert.call_count == 3
