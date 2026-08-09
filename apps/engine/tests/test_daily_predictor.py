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
async def test_run_daily_prediction_success():
    mock_supabase = MagicMock()

    # Mock active prompt DB query
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
        {
            "variant_tag": "daily-pred-tag1",
            "prompt_content": DAILY_PREDICTOR_PROMPT,
        }
    ]

    # Mock insert
    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{"id": "test-uuid"}]

    mock_llm = MagicMock()
    mock_prediction = DailyPredictionOutput(
        predicted_direction="UP",
        confidence=75.0,
        expected_return_pct=0.42,
        rationale="Overnight futures up and strong tech momentum.",
        catalysts=["Tech earnings", "Fed stance"],
    )
    mock_llm.chat.completions.create.return_value = mock_prediction

    with (
        patch("tasks.daily_predictor.get_supabase_client", return_value=mock_supabase),
        patch("tasks.daily_predictor.get_deepseek_client", return_value=mock_llm),
        patch("tasks.daily_predictor.close_client", new_callable=AsyncMock),
    ):
        result = await run_daily_prediction(ticker="SPY")
        assert result is not None
        assert result["predicted_direction"] == "UP"
        assert result["confidence"] == 75.0
        assert result["ticker"] == "SPY"


@pytest.mark.asyncio
async def test_get_daily_market_context_technicals():
    from tasks.daily_predictor import get_daily_market_context

    mock_history = [{"price": 700.0 + i, "fetched_at": f"2026-07-{i + 1:02d}T00:00:00Z"} for i in range(25)]
    mock_mdm = MagicMock()
    mock_mdm.get_history = AsyncMock(return_value=mock_history)

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
        assert "Global Macro Baseline" in ctx
        assert "Volatility Index Details" in ctx
        assert "Market Health Barometer" in ctx
        assert "Recent Market Feeling" in ctx
