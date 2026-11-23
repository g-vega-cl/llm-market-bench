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
    sanitize_mutated_stock_strategy,
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

    # Mock past 5 baskets for deepseek-flash
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
        patch("tasks.stock_picker_autoresearch.TARGET_TRACK_MODELS", ["deepseek-flash"]),
    ):
        await run_stock_picker_autoresearch(days=7, dry_run=False, cold_start=False)

        # Verify new prompt variant was inserted with status='active'
        insert_calls = mock_supabase.table().insert.call_args_list
        assert len(insert_calls) >= 1

        variant_insert = insert_calls[0][0][0]
        assert variant_insert["prompt_name"] == "STOCK_PICKER_PROMPT"
        assert variant_insert["track_id"] == "deepseek-flash"
        assert variant_insert["status"] == "active"
        assert variant_insert["parent_tag"] == "active-v1"
        assert variant_insert["experiment_type"] == "incremental"
        assert "week_start" in variant_insert and variant_insert["week_start"]
        assert "week_end" in variant_insert and variant_insert["week_end"]
        assert "change_description" in variant_insert
        assert "description" not in variant_insert
        assert variant_insert["research_output"]["research_insight"].startswith("High net interest margins")
        assert variant_insert["research_output"]["is_cold_start"] is False
        assert "Refined strategy prioritizing pricing power" in variant_insert["prompt_content"]

        # Verify durable research insight memory was saved
        memory_insert = insert_calls[1][0][0]
        assert memory_insert["memory_type"] == "AUTORESEARCH_INSIGHT"
        assert "High net interest margins" in memory_insert["content"]


def test_sanitize_mutated_stock_strategy_strips_fences_and_preserves_header():
    raw_fenced = "```markdown\n1. UP PICKS: Focus on margin expansion.\n2. DOWN PICKS: Short overleveraged beta.\n```"
    cleaned = sanitize_mutated_stock_strategy(raw_fenced)
    assert cleaned.startswith("=== LONG/SHORT RELATIVE SELECTION STRATEGY ===")
    assert "```" not in cleaned
    assert "Focus on margin expansion" in cleaned


@pytest.mark.asyncio
async def test_run_stock_picker_autoresearch_ratchet_reversion_on_baseline_miss():
    mock_supabase = MagicMock()

    # Low-performing week (hit rate 20%, alpha -2%) -> score ~ 27.0
    mock_baskets = [
        {
            "id": f"b-{i}",
            "target_date": f"2026-11-0{i}",
            "directional_hit_rate": 20.0,
            "ls_spread_alpha_pct": -2.0,
        }
        for i in range(1, 6)
    ]
    mock_picks = [{"confidence": 80.0, "is_hit": False} for _ in range(30)]

    mock_supabase.table().select().eq().eq().gte().execute.return_value = MagicMock(data=mock_baskets)
    mock_supabase.table().select().in_().eq().execute.return_value = MagicMock(data=mock_picks)

    active_prompt = STOCK_PICKER_CONSTRAINTS_HEADER + STOCK_PICKER_MUTABLE_STRATEGIES + STOCK_PICKER_CONSTRAINTS_FOOTER
    baseline_prompt = (
        STOCK_PICKER_CONSTRAINTS_HEADER
        + "=== LONG/SHORT RELATIVE SELECTION STRATEGY ===\nProven baseline strategy."
        + STOCK_PICKER_CONSTRAINTS_FOOTER
    )
    mock_supabase.table().select().eq().eq().eq().order().limit().execute.return_value = MagicMock(
        data=[{"variant_tag": "active-losing-v2", "prompt_content": active_prompt}]
    )

    # Distinct prior baseline with high hurdle_score (80.0) so select_baseline_candidate returns a (ceiling, variant) tuple
    mock_supabase.table().select().eq().eq().execute.return_value = MagicMock(
        data=[
            {
                "variant_tag": "base-winner-v1",
                "status": "baseline",
                "prompt_content": baseline_prompt,
                "metrics": {"hurdle_score": 80.0, "sample_baskets": 5},
            },
            {
                "variant_tag": "active-losing-v2",
                "status": "active",
                "prompt_content": active_prompt,
                "metrics": {},
            },
        ]
    )

    mock_meta_response = StockPickerMetaPromptResponse(
        new_strategy="Refined strategy without header.",
        research_insight="Revert from high-beta traps.",
    )
    mock_ds_client = MagicMock()
    mock_ds_client.chat.completions.create = AsyncMock(return_value=mock_meta_response)

    with (
        patch("tasks.stock_picker_autoresearch.get_supabase_client", return_value=mock_supabase),
        patch("tasks.stock_picker_autoresearch.get_deepseek_client", return_value=mock_ds_client),
        patch("tasks.stock_picker_autoresearch.close_client", new_callable=AsyncMock),
        patch("tasks.stock_picker_autoresearch.TARGET_TRACK_MODELS", ["deepseek-flash"]),
    ):
        await run_stock_picker_autoresearch(days=7, dry_run=False, cold_start=False)

        insert_calls = mock_supabase.table().insert.call_args_list
        variant_insert = insert_calls[0][0][0]
        # Reverted parent_tag to the winning baseline instead of chaining off the losing variant
        assert variant_insert["parent_tag"] == "base-winner-v1"
        assert "=== LONG/SHORT RELATIVE SELECTION STRATEGY ===" in variant_insert["prompt_content"]
        assert variant_insert["research_output"]["hypothesis"] is None


@pytest.mark.asyncio
async def test_stock_picker_autoresearch_closes_client_with_provider():
    """The mutation client must be closed with its provider name.

    A missing provider raises TypeError inside the finally block, after the
    mutation was generated and before the insert, so the variant is silently
    discarded every run.
    """
    mock_supabase = MagicMock()

    mock_baskets = [
        {"id": "b-1", "target_date": "2026-11-20", "directional_hit_rate": 50.0, "ls_spread_alpha_pct": 0.5}
    ]
    mock_picks = [{"confidence": 60.0, "is_hit": True}]

    mock_supabase.table().select().eq().eq().gte().execute.return_value = MagicMock(data=mock_baskets)
    mock_supabase.table().select().in_().eq().execute.return_value = MagicMock(data=mock_picks)

    active_prompt = STOCK_PICKER_CONSTRAINTS_HEADER + STOCK_PICKER_MUTABLE_STRATEGIES + STOCK_PICKER_CONSTRAINTS_FOOTER
    mock_supabase.table().select().eq().eq().eq().order().limit().execute.return_value = MagicMock(
        data=[{"variant_tag": "active-v1", "prompt_content": active_prompt}]
    )
    mock_supabase.table().select().eq().eq().execute.return_value = MagicMock(
        data=[{"variant_tag": "active-v1", "status": "baseline", "metrics": {"hurdle_score": 40.0}}]
    )

    mock_meta_response = StockPickerMetaPromptResponse(
        new_strategy="Refined strategy.",
        research_insight="Durable insight.",
    )
    mock_ds_client = MagicMock()
    mock_ds_client.chat.completions.create = AsyncMock(return_value=mock_meta_response)
    mock_close = AsyncMock()

    with (
        patch("tasks.stock_picker_autoresearch.get_supabase_client", return_value=mock_supabase),
        patch("tasks.stock_picker_autoresearch.get_deepseek_client", return_value=mock_ds_client),
        patch("tasks.stock_picker_autoresearch.close_client", mock_close),
        patch("tasks.stock_picker_autoresearch.TARGET_TRACK_MODELS", ["deepseek-flash"]),
    ):
        await run_stock_picker_autoresearch(days=7, dry_run=False, cold_start=False)

    mock_close.assert_awaited_once_with(mock_ds_client, "deepseek")


@pytest.mark.asyncio
async def test_stock_picker_autoresearch_raises_when_every_track_fails():
    """A loop where every track fails must exit non-zero, not log-and-continue."""

    async def _boom(*args, **kwargs):
        raise RuntimeError("deepseek unavailable")

    with (
        patch("tasks.stock_picker_autoresearch.get_supabase_client", return_value=MagicMock()),
        patch("tasks.stock_picker_autoresearch._optimize_stock_track", _boom),
        patch("tasks.stock_picker_autoresearch.TARGET_TRACK_MODELS", ["a", "b"]),
    ):
        with pytest.raises(RuntimeError):
            await run_stock_picker_autoresearch(days=7, dry_run=False, cold_start=False)
