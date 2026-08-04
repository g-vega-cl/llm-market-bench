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
    assert "Evaluate overnight news" in mutable

    # Test fallback
    custom_prompt = "Custom instructions text"
    h, m, f = split_daily_predictor_prompt(custom_prompt)
    assert h == DAILY_PREDICTOR_CONSTRAINTS_HEADER
    assert m == custom_prompt
    assert f == DAILY_PREDICTOR_CONSTRAINTS_FOOTER


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
