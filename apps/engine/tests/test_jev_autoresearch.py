from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.config import JEV_MODEL, OPENAI_MODEL
from core.llm.daily_predictor_prompts import (
    JEV_DEFAULT_CRITERIA,
    format_jev_prompt_content,
    parse_jev_prompt_content,
)


@pytest.mark.asyncio
async def test_generate_new_jev_criteria_with_luna():
    """Verify generate_new_jev_criteria calls OpenAI Luna (gpt-5.6-luna) and preserves frozen structure."""
    from tasks.daily_autoresearch import JevMetaCriteriaResponse, generate_new_jev_criteria

    mock_openai = MagicMock()
    mock_luna_resp = JevMetaCriteriaResponse(
        criteria_up="Close >= Open. Evolved UP rule: momentum continuation on positive gap with high tech breadth.",
        criteria_down="Close < Open. Evolved DOWN rule: reversal on gap exhaustion and rising 10Y yield.",
        research_insight="Jev was overconfident on high VIX days; tightened criteria for gap continuations.",
    )
    mock_openai.chat.completions.create = AsyncMock(return_value=mock_luna_resp)

    old_criteria_content = format_jev_prompt_content(JEV_DEFAULT_CRITERIA)
    mock_predictions = [
        {
            "target_date": "2026-09-21",
            "predicted_direction": "UP",
            "confidence": 75.0,
            "is_correct": False,
            "brier_score": 0.5625,
            "open_price": 590.0,
            "close_price": 588.0,
            "high_price": 591.0,
            "low_price": 587.0,
        }
    ]

    new_content, insight = await generate_new_jev_criteria(
        old_prompt_content=old_criteria_content,
        predictions=mock_predictions,
        macro_context={},
        baseline_score=45.0,
        openai_meta=mock_openai,
        cold_start=False,
    )

    # Verify Luna was called with OPENAI_MODEL
    mock_openai.chat.completions.create.assert_called_once()
    call_kwargs = mock_openai.chat.completions.create.call_args[1]
    assert call_kwargs["model"] == OPENAI_MODEL
    assert call_kwargs["response_model"] == JevMetaCriteriaResponse

    # Verify returned content is valid criteria JSON
    parsed = parse_jev_prompt_content(new_content)
    assert "Evolved UP rule" in parsed["UP"]
    assert "Evolved DOWN rule" in parsed["DOWN"]
    assert insight == "Jev was overconfident on high VIX days; tightened criteria for gap continuations."


@pytest.mark.asyncio
async def test_run_daily_autoresearch_includes_jev_track():
    """Verify run_daily_autoresearch processes Jev track with OpenAI Luna client."""
    from tasks.daily_autoresearch import run_daily_autoresearch

    mock_supabase = MagicMock()
    # Mock predictions returned for models
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value.data = [
        {
            "target_date": "2026-09-22",
            "predicted_direction": "UP",
            "confidence": 80.0,
            "is_correct": True,
            "brier_score": 0.04,
            "open_price": 590.0,
            "close_price": 593.0,
            "high_price": 594.0,
            "low_price": 589.5,
            "prompt_variant_tag": "jev-variant-v1",
        }
    ]

    mock_deepseek = MagicMock()
    mock_openai = MagicMock()

    with (
        patch("tasks.daily_autoresearch.get_supabase_client", return_value=mock_supabase),
        patch("tasks.daily_autoresearch.get_deepseek_client", return_value=mock_deepseek),
        patch("tasks.daily_autoresearch.get_openai_client", return_value=mock_openai),
        patch("tasks.daily_autoresearch.close_client", new_callable=AsyncMock),
        patch("tasks.daily_autoresearch.run_daily_autoresearch_for_model", new_callable=AsyncMock) as mock_run_model,
    ):
        await run_daily_autoresearch(dry_run=True, cold_start=False)

        # Verify all 3 model tracks are evaluated: DeepSeek, MiniMax, Jev
        called_models = [call.kwargs["model_name"] for call in mock_run_model.call_args_list]
        assert JEV_MODEL in called_models
        assert len(called_models) == 3
