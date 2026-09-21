"""Tests for 1-in-6 stochastic cold start reset across autoresearch domains."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autoresearch import evaluator, runner
from core.llm import daily_predictor_prompts, predictor_prompts, prompts
from tasks import daily_autoresearch, predictor_autoresearch


def test_roll_cold_start_dice():
    """Verify roll_cold_start_dice returns True only when random roll is 1."""
    with patch("random.randint", return_value=1):
        assert runner.roll_cold_start_dice(sides=6) is True

    with patch("random.randint", return_value=2):
        assert runner.roll_cold_start_dice(sides=6) is False

    with patch("random.randint", return_value=6):
        assert runner.roll_cold_start_dice(sides=6) is False


@pytest.mark.asyncio
async def test_evaluate_week_cold_start_omits_prior_strategy_text():
    """Verify evaluate_week with cold_start=True strips baseline and prior prompts but retains metrics."""
    mock_sb = MagicMock()

    with (
        patch("core.db.get_async_supabase_client", return_value=mock_sb),
        patch("autoresearch.evaluator.compute_wall_street_metrics", new_callable=AsyncMock) as mock_metrics,
        patch("autoresearch.evaluator._spy_returns", new_callable=AsyncMock) as mock_spy,
        patch("autoresearch.evaluator._fetch_actual_bond_yield", new_callable=AsyncMock) as mock_bond,
        patch("autoresearch.evaluator._fetch_dollar_index_return", new_callable=AsyncMock) as mock_dxy,
        patch("autoresearch.evaluator.get_active_prompt", new_callable=AsyncMock) as mock_act,
        patch("autoresearch.evaluator.get_all_time_baseline", new_callable=AsyncMock) as mock_base,
        patch("autoresearch.evaluator.get_previous_variants", new_callable=AsyncMock) as mock_prev,
        patch("autoresearch.evaluator.fetch_trade_rejections", new_callable=AsyncMock) as mock_rej,
    ):
        mock_metrics.return_value = {"total_return_pct": 1.0, "max_drawdown": 0.01}
        mock_spy.return_value = [0.005]
        mock_bond.return_value = 4.25
        mock_dxy.return_value = 0.1
        mock_act.return_value = (
            f"{prompts.SYSTEM_PROMPT_CONSTRAINTS_HEADER}Active Strategy Text{prompts.SYSTEM_PROMPT_CONSTRAINTS_FOOTER}"
        )
        mock_base.return_value = {
            "variant_tag": "v_baseline_123",
            "prompt_content": f"{prompts.SYSTEM_PROMPT_CONSTRAINTS_HEADER}Baseline Strategy Text{prompts.SYSTEM_PROMPT_CONSTRAINTS_FOOTER}",
            "metrics": {"score": 2.5},
        }
        mock_prev.return_value = []
        mock_rej.return_value = {"total": 0, "by_reason": {}}

        # Normal run: cold_start=False
        report_normal, _, _ = await evaluator.evaluate_week(
            date(2026, 9, 1), date(2026, 9, 7), track_id="track_default", cold_start=False
        )
        assert "# Baseline Prompt (All-Time Best)" in report_normal
        assert "Baseline Strategy Text" in report_normal
        assert "# Latest Experiment Prompt (Just Evaluated)" in report_normal
        assert "Active Strategy Text" in report_normal

        # Cold start run: cold_start=True
        report_cold, _, baseline_tag = await evaluator.evaluate_week(
            date(2026, 9, 1), date(2026, 9, 7), track_id="track_default", cold_start=True
        )
        assert "# Baseline Prompt (All-Time Best)" not in report_cold
        assert "Baseline Strategy Text" not in report_cold
        assert "# Latest Experiment Prompt (Just Evaluated)" not in report_cold
        assert "Active Strategy Text" not in report_cold
        assert "COLD START RESET" in report_cold
        assert "FROZEN" in report_cold
        assert baseline_tag == "v_baseline_123"


@pytest.mark.asyncio
async def test_runner_cold_start_preserves_frozen_sections():
    """Verify runner.run on cold start tags radical experiment and preserves frozen header/footer."""
    with (
        patch("autoresearch.runner._check_safety", new_callable=AsyncMock) as mock_safety,
        patch("autoresearch.runner.evaluate_week", new_callable=AsyncMock) as mock_eval,
        patch("autoresearch.runner.get_active_variant", new_callable=AsyncMock) as mock_active_var,
        patch("autoresearch.runner.get_baseline_metrics", new_callable=AsyncMock) as mock_baseline_metrics,
        patch("autoresearch.runner.update_variant_metrics", new_callable=AsyncMock),
        patch("autoresearch.runner.revert_to_baseline", new_callable=AsyncMock),
        patch("autoresearch.runner.run_research", new_callable=AsyncMock) as mock_research,
        patch("autoresearch.runner.save_variant", new_callable=AsyncMock) as mock_save_var,
        patch("autoresearch.runner.roll_cold_start_dice", return_value=True),
        patch("memory.store.add_memory", return_value="mem_123"),
    ):
        mock_safety.return_value = (False, "")
        mock_eval.return_value = ("Report", {"score": 0.5}, "v_base_999")
        mock_active_var.return_value = {"variant_tag": "v_active_1"}
        mock_baseline_metrics.return_value = {"score": 2.0}

        mock_res = MagicMock()
        mock_res.experiment_type = (
            "incremental"  # Model output may say incremental, but runner overrides to radical on cold start
        )
        mock_res.confidence = 85
        mock_res.change_description = "Fresh strategy from scratch"
        mock_res.new_prompt_text = "Brand New Strategy Written From 0"
        mock_res.model_dump.return_value = {"tools": []}
        mock_res.research_insight = "Lesson learned"
        mock_research.return_value = mock_res
        mock_save_var.return_value = "v_cold_new"

        # Automated run: cold_start=None triggers dice roll (mocked to True)
        await runner.run(dry_run=False, track_id="track_default")

        # Confirm evaluate_week and run_research received cold_start=True from the dice roll
        assert mock_eval.call_args.kwargs.get("cold_start") is True
        assert mock_research.call_args.kwargs.get("cold_start") is True

        # Confirm save_variant arguments
        save_kwargs = mock_save_var.call_args.kwargs
        assert save_kwargs["experiment_type"] == "radical"
        assert save_kwargs["research_output"].get("is_cold_start") is True

        saved_prompt = save_kwargs["prompt_content"]
        assert saved_prompt.startswith(prompts.SYSTEM_PROMPT_CONSTRAINTS_HEADER)
        assert saved_prompt.endswith(prompts.SYSTEM_PROMPT_CONSTRAINTS_FOOTER)
        assert "Brand New Strategy Written From 0" in saved_prompt


@pytest.mark.asyncio
async def test_runner_run_all_max_one_cold_start_guardrail():
    """Verify run_all permits at most one track to trigger cold start in a single run when automated."""
    with (
        patch("core.config.AUTORESEARCH_TRACKS", {"track_default": [], "track_claude": [], "track_openai": []}),
        patch("autoresearch.runner.run", new_callable=AsyncMock) as mock_run,
        patch("autoresearch.runner.roll_cold_start_dice", return_value=True),
    ):
        # Automated run: cold_start=None triggers dice with max-1 guardrail
        await runner.run_all(dry_run=True)

        # Track 1 got cold_start=True; tracks 2 and 3 should have received cold_start=False
        assert mock_run.call_count == 3
        calls = mock_run.call_args_list
        assert calls[0].kwargs.get("cold_start") is True
        assert calls[1].kwargs.get("cold_start") is False
        assert calls[2].kwargs.get("cold_start") is False

        # Explicit run with cold_start=False bypasses dice completely
        mock_run.reset_mock()
        await runner.run_all(dry_run=True, cold_start=False)
        assert mock_run.call_count == 3
        calls_disabled = mock_run.call_args_list
        assert calls_disabled[0].kwargs.get("cold_start") is False
        assert calls_disabled[1].kwargs.get("cold_start") is False
        assert calls_disabled[2].kwargs.get("cold_start") is False


@pytest.mark.asyncio
async def test_daily_autoresearch_cold_start_preserves_frozen_sections():
    """Verify generate_new_daily_prompt with cold_start=True omits prior strategy and preserves frozen sections."""
    old_prompt = (
        f"{daily_predictor_prompts.DAILY_PREDICTOR_CONSTRAINTS_HEADER}"
        "Old SPY Intraday Strategy Rules"
        f"{daily_predictor_prompts.DAILY_PREDICTOR_CONSTRAINTS_FOOTER}"
    )

    mock_meta_response = MagicMock()
    mock_meta_response.new_prompt = "New Clean SPY Strategy Written From 0"
    mock_meta_response.research_insight = "SPY gap-downs offer asymmetric mean-reversion"

    mock_llm = MagicMock()
    mock_llm.chat.completions.create = AsyncMock(return_value=mock_meta_response)

    assembled_prompt, insight = await daily_autoresearch.generate_new_daily_prompt(
        old_prompt=old_prompt,
        baseline_score=50.0,
        predictions=[],
        macro_context={},
        meta_researcher=mock_llm,
        cold_start=True,
    )

    call_args = mock_llm.chat.completions.create.call_args
    meta_prompt_sent = call_args.kwargs["messages"][0]["content"]

    # Verify old strategy rules were omitted from meta_prompt
    assert "Old SPY Intraday Strategy Rules" not in meta_prompt_sent
    assert "COLD START RESET" in meta_prompt_sent

    # Verify assembled output preserves frozen constraints
    assert assembled_prompt.startswith(daily_predictor_prompts.DAILY_PREDICTOR_CONSTRAINTS_HEADER)
    assert assembled_prompt.endswith(daily_predictor_prompts.DAILY_PREDICTOR_CONSTRAINTS_FOOTER)
    assert "New Clean SPY Strategy Written From 0" in assembled_prompt
    assert insight == "SPY gap-downs offer asymmetric mean-reversion"


@pytest.mark.asyncio
async def test_sector_autoresearch_cold_start_preserves_frozen_sections():
    """Verify generate_new_prompt in sector autoresearch with cold_start=True preserves frozen sections."""
    old_prompt = (
        f"{predictor_prompts.SECTOR_PREDICTOR_CONSTRAINTS_HEADER}"
        "Old Sector Rotation Strategy"
        f"{predictor_prompts.SECTOR_PREDICTOR_CONSTRAINTS_FOOTER}"
    )

    mock_meta_response = MagicMock()
    mock_meta_response.new_prompt = "New Sector Rotation Rules From 0"
    mock_meta_response.research_insight = "Tech vs Utilities divergence indicates growth regime"

    mock_llm = MagicMock()
    mock_llm.chat.completions.create = AsyncMock(return_value=mock_meta_response)

    assembled_prompt, insight = await predictor_autoresearch.generate_new_prompt(
        old_prompt=old_prompt,
        baseline_score=60.0,
        meta_researcher=mock_llm,
        cold_start=True,
    )

    call_args = mock_llm.chat.completions.create.call_args
    meta_prompt_sent = call_args.kwargs["messages"][0]["content"]

    assert "Old Sector Rotation Strategy" not in meta_prompt_sent
    assert "COLD START RESET" in meta_prompt_sent

    assert assembled_prompt.startswith(predictor_prompts.SECTOR_PREDICTOR_CONSTRAINTS_HEADER)
    assert assembled_prompt.endswith(predictor_prompts.SECTOR_PREDICTOR_CONSTRAINTS_FOOTER)
    assert "New Sector Rotation Rules From 0" in assembled_prompt
    assert insight == "Tech vs Utilities divergence indicates growth regime"
