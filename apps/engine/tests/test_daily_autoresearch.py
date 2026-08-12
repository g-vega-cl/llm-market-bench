from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tasks.daily_autoresearch import (
    calculate_daily_ratchet_score,
    generate_new_daily_prompt,
    run_daily_autoresearch,
)


def test_calculate_daily_ratchet_score():
    predictions = [
        {"is_correct": True, "intraday_hit": True, "brier_score": 0.04},
        {"is_correct": True, "intraday_hit": True, "brier_score": 0.09},
        {"is_correct": False, "intraday_hit": True, "brier_score": 0.64},
        {"is_correct": True, "intraday_hit": True, "brier_score": 0.04},
    ]
    # EOD Accuracy = 3/4 = 75.0% -> 0.60 * 75.0 = 45.0
    # Intraday Hit = 4/4 = 100.0% -> 0.40 * 100.0 = 40.0
    # Mean Brier = 0.2025 -> 0.2025 * 50 = 10.125
    # Combined Score = 45.0 + 40.0 - 10.125 = 74.875
    score = calculate_daily_ratchet_score(predictions)
    assert pytest.approx(score, 0.01) == 74.875


@pytest.mark.asyncio
async def test_generate_new_daily_prompt_success():
    mock_llm = MagicMock()
    mock_response = MagicMock(new_prompt="New strategy instructions for intraday SPY momentum.")
    mock_llm.chat.completions.create.return_value = mock_response

    old_prompt = "Header\nInstructions\nFooter"
    new_prompt = await generate_new_daily_prompt(
        old_prompt=old_prompt,
        baseline_score=70.0,
        meta_researcher=mock_llm,
    )

    assert "New strategy instructions" in new_prompt


@pytest.mark.asyncio
async def test_run_daily_autoresearch_ratchet():
    mock_supabase = MagicMock()

    eval_predictions = [
        {"is_correct": True, "brier_score": 0.04},
        {"is_correct": True, "brier_score": 0.04},
        {"is_correct": True, "brier_score": 0.04},
    ]

    active_prompt = [
        {
            "variant_tag": "daily-active-1",
            "prompt_name": "DAILY_PREDICTOR_PROMPT",
            "prompt_content": "Active prompt content",
            "status": "active",
        }
    ]

    all_variants = [
        {
            "variant_tag": "daily-baseline-1",
            "prompt_name": "DAILY_PREDICTOR_PROMPT",
            "prompt_content": "Baseline content",
            "metrics": {"score": 60.0},
        }
    ]

    mock_table = MagicMock()

    def mock_table_select(table_name):
        mock_chain = MagicMock()
        if table_name == "daily_predictions":
            mock_chain.select.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value.data = eval_predictions
        elif table_name == "prompt_experiments":
            select_mock = MagicMock()
            eq_name = MagicMock()
            eq_status = MagicMock()
            eq_status.order.return_value.limit.return_value.execute.return_value.data = active_prompt
            eq_name.eq.return_value = eq_status
            eq_name.execute.return_value.data = all_variants
            select_mock.eq.return_value = eq_name
            mock_chain.select.return_value = select_mock

            # Expose insert on prompt_experiments chain
            mock_chain.insert = mock_table.insert
            mock_chain.update = mock_table.update
        return mock_chain

    mock_supabase.table.side_effect = mock_table_select

    mock_llm = MagicMock()
    mock_llm.chat.completions.create.return_value = MagicMock(new_prompt="Mutated intraday strategy instructions")

    with (
        patch("tasks.daily_autoresearch.get_supabase_client", return_value=mock_supabase),
        patch("tasks.daily_autoresearch.get_deepseek_client", return_value=mock_llm),
        patch("tasks.daily_autoresearch.close_client", new_callable=AsyncMock),
    ):
        await run_daily_autoresearch()
        assert mock_table.insert.called
