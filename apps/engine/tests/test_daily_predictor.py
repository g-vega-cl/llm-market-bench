from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.llm.daily_predictor_prompts import (
    DAILY_PREDICTOR_CONSTRAINTS_FOOTER,
    DAILY_PREDICTOR_CONSTRAINTS_HEADER,
    DAILY_PREDICTOR_PROMPT,
    DailyPredictionOutput,
    split_daily_predictor_prompt,
)
from tasks.daily_predictor import run_daily_prediction


def test_split_daily_predictor_prompt():
    header, mutable, footer = split_daily_predictor_prompt(DAILY_PREDICTOR_PROMPT)
    assert header == DAILY_PREDICTOR_CONSTRAINTS_HEADER
    assert footer == DAILY_PREDICTOR_CONSTRAINTS_FOOTER
    assert "MACRO CATALYST EXTRACTION" in mutable

    # Test fallback
    custom_prompt = "Custom instructions text"
    h, m, f = split_daily_predictor_prompt(custom_prompt)
    assert h == DAILY_PREDICTOR_CONSTRAINTS_HEADER
    assert m == custom_prompt
    assert f == DAILY_PREDICTOR_CONSTRAINTS_FOOTER


def test_daily_predictor_prompt_symmetry():
    """Verify DAILY_PREDICTOR_PROMPT is strictly symmetric and counter-biases against always-UP predictions."""
    header, mutable, footer = split_daily_predictor_prompt(DAILY_PREDICTOR_PROMPT)

    # Must explicitly direct symmetric zero-mean base-rate evaluation in header or mutable
    assert "ZERO-MEAN BASE RATE" in header or "ZERO-MEAN BASE RATE" in mutable
    assert "SYMMETRIC" in mutable

    # Must contain explicit bearish directives alongside bullish directives
    full_prompt = DAILY_PREDICTOR_PROMPT.lower()
    assert "bearish catalyst" in full_prompt
    assert "bullish catalyst" in full_prompt
    assert "down" in full_prompt and "up" in full_prompt


@pytest.mark.asyncio
async def test_run_daily_prediction_arena_success():
    mock_supabase = MagicMock()

    # Mock active prompt DB query
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
        {
            "variant_tag": "daily-pred-tag1",
            "prompt_content": DAILY_PREDICTOR_PROMPT,
        }
    ]

    # Mock upsert
    mock_supabase.table.return_value.upsert.return_value.execute.return_value.data = [{"id": "test-uuid"}]

    mock_deepseek = MagicMock()
    mock_prediction = DailyPredictionOutput(
        predicted_direction="UP",
        confidence=75.0,
        expected_return_pct=0.42,
        rationale="Overnight futures up and strong tech momentum.",
        catalysts=["Tech earnings", "Fed stance"],
    )
    mock_deepseek.chat.completions.create.return_value = mock_prediction

    mock_minimax = AsyncMock()
    mock_minimax.chat_with_json_response = AsyncMock(
        return_value={
            "predicted_direction": "DOWN",
            "confidence": 60.0,
            "expected_return_pct": -0.30,
            "rationale": "Overextended RSI and pending macro risk.",
            "catalysts": ["CPI release"],
        }
    )
    mock_minimax.close = AsyncMock()

    with (
        patch("tasks.daily_predictor.get_supabase_client", return_value=mock_supabase),
        patch("tasks.daily_predictor.get_deepseek_client", return_value=mock_deepseek),
        patch("tasks.daily_predictor.MiniMaxClient", return_value=mock_minimax),
        patch("tasks.daily_predictor.close_client", new_callable=AsyncMock),
    ):
        results = await run_daily_prediction(ticker="SPY")
        assert isinstance(results, list)
        assert len(results) == 2

        deepseek_res = next((r for r in results if r["model_name"] == "deepseek-v4-flash"), None)
        assert deepseek_res is not None
        assert deepseek_res["predicted_direction"] == "UP"
        assert deepseek_res["confidence"] == 75.0

        minimax_res = next((r for r in results if r["model_name"] == "MiniMax-M3"), None)
        assert minimax_res is not None
        assert minimax_res["predicted_direction"] == "DOWN"
        assert minimax_res["confidence"] == 60.0


@pytest.mark.asyncio
async def test_run_daily_prediction_partial_failure():
    mock_supabase = MagicMock()

    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
        {
            "variant_tag": "daily-pred-tag1",
            "prompt_content": DAILY_PREDICTOR_PROMPT,
        }
    ]
    mock_supabase.table.return_value.upsert.return_value.execute.return_value.data = [{"id": "test-uuid"}]

    mock_deepseek = MagicMock()
    mock_prediction = DailyPredictionOutput(
        predicted_direction="UP",
        confidence=80.0,
        expected_return_pct=0.50,
        rationale="Strong pre-market breakout.",
        catalysts=["Earnings beat"],
    )
    mock_deepseek.chat.completions.create.return_value = mock_prediction

    # MiniMax fails on all attempts
    mock_minimax = AsyncMock()
    mock_minimax.chat_with_json_response = AsyncMock(side_effect=Exception("MiniMax API Timeout"))
    mock_minimax.close = AsyncMock()

    with (
        patch("tasks.daily_predictor.get_supabase_client", return_value=mock_supabase),
        patch("tasks.daily_predictor.get_deepseek_client", return_value=mock_deepseek),
        patch("tasks.daily_predictor.MiniMaxClient", return_value=mock_minimax),
        patch("tasks.daily_predictor.close_client", new_callable=AsyncMock),
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        results = await run_daily_prediction(ticker="SPY")
        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0]["model_name"] == "deepseek-v4-flash"
        assert results[0]["predicted_direction"] == "UP"


@pytest.mark.asyncio
async def test_get_daily_market_context_technicals():
    from tasks.daily_predictor import get_daily_market_context

    mock_history = [{"price": 700.0 + i, "fetched_at": f"2026-07-{i + 1:02d}T00:00:00Z"} for i in range(25)]
    mock_mdm = MagicMock()
    mock_mdm.get_history = AsyncMock(return_value=mock_history)
    mock_mdm.get_premarket_quote = AsyncMock(
        return_value={
            "price": 725.50,
            "previous_close": 724.00,
            "change": 1.50,
            "change_pct": 0.207,
        }
    )

    with (
        patch("execution.market_data.MarketDataManager", return_value=mock_mdm),
        patch(
            "core.llm.tools.execute_get_global_macro_context_tool", new_callable=AsyncMock, return_value="Macro test"
        ),
        patch(
            "core.llm.tools.execute_get_volatility_index_details_tool", new_callable=AsyncMock, return_value="VIX test"
        ),
        patch("core.llm.tools.execute_market_health_barometer_tool", new_callable=AsyncMock, return_value="Baro test"),
        patch("core.llm.tools.execute_get_market_feeling_tool", new_callable=AsyncMock, return_value="Feeling test"),
    ):
        ctx = await get_daily_market_context(ticker="SPY")
        assert "Previous Trading Session" in ctx
        assert "5-Day Return" in ctx
        assert "20-Day Simple Moving Average" in ctx
        assert "Live Pre-Market / Early Session Quote" in ctx
        assert "Overnight Gap: +1.50 (+0.21%)" in ctx
        assert "$725.50" in ctx
        assert "Global Macro Baseline" in ctx
        assert "Volatility Index Details" in ctx
        assert "Market Health Barometer" in ctx
        assert "Recent Market Feeling" in ctx

        # TDD Assertion: Pre-market quote section must appear BEFORE macro context blocks
        pm_idx = ctx.find("Live Pre-Market / Early Session Quote")
        macro_idx = ctx.find("Global Macro Baseline")
        assert pm_idx != -1 and macro_idx != -1
        assert pm_idx < macro_idx, "Pre-market quote block must appear before Global Macro Baseline context"
