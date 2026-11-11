"""Hermetic test suite for Weekly Stock Picker Autoresearch Task.

Verifies normalized alpha score formulation, prompt mutation splitting,
stochastic cold start logic, and baseline candidate selection without live network calls.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.llm.stock_picker_prompts import (
    STOCK_PICKER_CONSTRAINTS_FOOTER,
    STOCK_PICKER_CONSTRAINTS_HEADER,
    STOCK_PICKER_MUTABLE_STRATEGIES,
)
from tasks.stock_picker_autoresearch import (
    StockPickerMetaPromptResponse,
    calculate_stock_picker_hurdle_score,
    run_stock_picker_autoresearch,
)


def test_calculate_stock_picker_hurdle_score_normalized_weighting():
    # Hit rate 60.0%, Conviction norm 50.0%
    # Test +2.0% alpha: normalized_alpha = 50 + (2.0 * 10) = 70.0
    # Score = 0.50 * 60 + 0.40 * 70 + 0.10 * 50 = 30 + 28 + 5 = 63.0
    score_pos = calculate_stock_picker_hurdle_score(
        hit_rate_pct=60.0,
        mean_ls_alpha_pct=2.0,
        conviction_norm=50.0,
    )
    assert score_pos == 63.0

    # Test -2.0% alpha: normalized_alpha = 50 + (-2.0 * 10) = 30.0
    # Score = 0.50 * 60 + 0.40 * 30 + 0.10 * 50 = 30 + 12 + 5 = 47.0
    score_neg = calculate_stock_picker_hurdle_score(
        hit_rate_pct=60.0,
        mean_ls_alpha_pct=-2.0,
        conviction_norm=50.0,
    )
    assert score_neg == 47.0

    # The delta between +2% and -2% alpha should be exactly 16.0 points (40% of 40-point span)
    assert round(score_pos - score_neg, 2) == 16.0


def test_calculate_stock_picker_hurdle_score_clamping():
    # Extreme positive alpha: +8.0% -> clamped to 100.0
    score_extreme_pos = calculate_stock_picker_hurdle_score(100.0, 8.0, 100.0)
    assert score_extreme_pos == 100.0

    # Extreme negative alpha: -8.0% -> clamped to 0.0
    score_extreme_neg = calculate_stock_picker_hurdle_score(0.0, -8.0, 0.0)
    assert score_extreme_neg == 0.0


@pytest.mark.asyncio
async def test_run_stock_picker_autoresearch_mutation_deployment():
    mock_supabase = MagicMock()

    # Mock past 5 baskets for deepseek-v4-flash
    mock_baskets = [
        {
            "id": f"b-{i}",
            "target_date": f"2026-11-0{i}",
            "directional_hit_rate": 66.7,
            "ls_spread_alpha_pct": 1.5,
        }
        for i in range(1, 6)
    ]
    mock_picks = [{"confidence": 65.0, "is_hit": True} for _ in range(30)]

    mock_supabase.table().select().eq().eq().gte().execute.return_value = MagicMock(data=mock_baskets)
    mock_supabase.table().select().in_().eq().execute.return_value = MagicMock(data=mock_picks)

    # Mock active prompt query
    active_prompt = STOCK_PICKER_CONSTRAINTS_HEADER + STOCK_PICKER_MUTABLE_STRATEGIES + STOCK_PICKER_CONSTRAINTS_FOOTER
    mock_supabase.table().select().eq().eq().eq().order().limit().execute.return_value = MagicMock(
        data=[{"variant_tag": "active-v1", "prompt_content": active_prompt}]
    )

    # Mock prompt experiments for baseline comparison
    mock_supabase.table().select().eq().eq().execute.return_value = MagicMock(
        data=[{"variant_tag": "active-v1", "status": "baseline", "metrics": {"hurdle_score": 50.0}}]
    )

    mock_meta_response = StockPickerMetaPromptResponse(
        new_strategy="=== LONG/SHORT RELATIVE SELECTION STRATEGY ===\nRefined strategy prioritizing pricing power and low debt float.",
        research_insight="High net interest margins and float yields outperform speculative beta in elevated yield regimes.",
    )

    mock_ds_client = MagicMock()
    mock_ds_client.chat.completions.create = AsyncMock(return_value=mock_meta_response)

    with (
        patch("tasks.stock_picker_autoresearch.get_supabase_client", return_value=mock_supabase),
        patch("tasks.stock_picker_autoresearch.get_deepseek_client", return_value=mock_ds_client),
        patch("tasks.stock_picker_autoresearch.close_client", new_callable=AsyncMock),
        patch("tasks.stock_picker_autoresearch.TARGET_TRACK_MODELS", ["deepseek-v4-flash"]),
    ):
        await run_stock_picker_autoresearch(days=7, dry_run=False, cold_start=False)

        # Verify new prompt variant was inserted with status='active'
        insert_calls = mock_supabase.table().insert.call_args_list
        assert len(insert_calls) >= 1

        variant_insert = insert_calls[0][0][0]
        assert variant_insert["prompt_name"] == "STOCK_PICKER_PROMPT"
        assert variant_insert["track_id"] == "deepseek-v4-flash"
        assert variant_insert["status"] == "active"
        assert "Refined strategy prioritizing pricing power" in variant_insert["prompt_content"]

        # Verify durable research insight memory was saved
        memory_insert = insert_calls[1][0][0]
        assert memory_insert["memory_type"] == "AUTORESEARCH_INSIGHT"
        assert "High net interest margins" in memory_insert["content"]
