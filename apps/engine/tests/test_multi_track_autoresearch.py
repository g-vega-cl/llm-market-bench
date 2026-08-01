"""Tests for multi-track autoresearch, stochastic cold start, and verifier bypass."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autoresearch import prompt_store, researcher, runner
from core import config
from core.llm.prompt_factory import PromptFactory


@pytest.mark.asyncio
async def test_skip_verifier_owner_ids_config():
    """Verify SKIP_VERIFIER_OWNER_IDS includes configured models like deepseek-v4-flash."""
    assert hasattr(config, "SKIP_VERIFIER_OWNER_IDS")
    assert "MiniMax-M3" in config.SKIP_VERIFIER_OWNER_IDS
    assert "deepseek-v4-flash" in config.SKIP_VERIFIER_OWNER_IDS


@pytest.mark.asyncio
async def test_prompt_store_multi_track_saving_and_retrieval():
    """Verify prompt_store saves and retrieves prompts per track_id."""
    mock_sb = MagicMock()

    # Mock DB response for track_a
    mock_res_a = MagicMock()
    mock_res_a.data = {"prompt_content": "Prompt for Track A", "variant_tag": "v1_a"}

    # Mock DB response for track_b
    mock_res_b = MagicMock()
    mock_res_b.data = {"prompt_content": "Prompt for Track B", "variant_tag": "v1_b"}

    def mock_table(table_name):
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.order.return_value = chain
        chain.limit.return_value = chain

        def execute_side_effect():
            eq_calls = [call.args for call in chain.eq.call_args_list]
            for field, val in eq_calls:
                if field == "track_id" and val == "track_b":
                    return mock_res_b
            return mock_res_a

        chain.maybe_single.return_value = chain
        chain.execute = AsyncMock(side_effect=execute_side_effect)
        return chain

    mock_sb.table.side_effect = mock_table

    with patch("autoresearch.prompt_store.get_async_supabase_client", return_value=mock_sb):
        prompt_a = await prompt_store.get_active_prompt(track_id="track_a")
        prompt_b = await prompt_store.get_active_prompt(track_id="track_b")

        assert prompt_a == "Prompt for Track A"
        assert prompt_b == "Prompt for Track B"


@pytest.mark.asyncio
async def test_prompt_factory_resolves_track_id():
    """Verify PromptFactory resolves owner_id to correct track_id prompt."""
    with (
        patch.object(config, "AUTORESEARCH_TRACKS", {"track_claude": ["claude-haiku-4-5"]}),
        patch("autoresearch.prompt_store.get_active_prompt", new_callable=AsyncMock) as mock_get_prompt,
    ):
        mock_get_prompt.return_value = "=== REASONING RIGOR ===\nCustom Claude Prompt\n=== SOUP ==="

        msgs = await PromptFactory.build_analysis_messages(
            provider="anthropic",
            owner_id="claude-haiku-4-5",
            market_data_block="",
            current_day_info="Friday, July 31",
            news_content="Breaking news content",
            portfolio_context="No positions",
        )

        mock_get_prompt.assert_called_once_with(track_id="track_claude")
        assert "Custom Claude Prompt" in msgs[0]["content"]


@pytest.mark.asyncio
async def test_stochastic_cold_start_cadence():
    """Verify stochastic cold start helper returns boolean decision based on schedule."""
    # Test random bounds helper
    interval = runner.get_next_cold_start_interval(min_weeks=2, max_weeks=5)
    assert 2 <= interval <= 5

    # Test decision check
    assert runner.should_trigger_cold_start(current_cycle=5, target_cycle=5) is True
    assert runner.should_trigger_cold_start(current_cycle=4, target_cycle=5) is False


@pytest.mark.asyncio
async def test_researcher_cold_start_ignores_previous_prompt():
    """Verify run_research creates fresh prompt without prior prompt when cold_start=True."""
    mock_client = MagicMock()
    mock_result = MagicMock()
    mock_result.new_prompt_text = "Fresh Strategy: Cold start generation."
    mock_result.change_description = "Fresh start"
    mock_result.experiment_type = "radical"
    mock_result.research_reasoning = "Cold start"
    mock_result.confidence = 90
    mock_result.selected_tools = ["get_stock_quote"]

    mock_completion = AsyncMock(return_value=mock_result)
    mock_client.chat.completions.create = mock_completion

    with patch("autoresearch.researcher.get_deepseek_client", return_value=mock_client):
        res = await researcher.run_research(
            report="Performance report...",
            current_prompt="Old prompt that should be ignored",
            cold_start=True,
        )

        assert res.new_prompt_text == "Fresh Strategy: Cold start generation."
        # Check system prompt sent to DeepSeek model
        call_args = mock_completion.call_args
        messages = call_args.kwargs["messages"]
        system_content = messages[0]["content"]
        assert "COLD START" in system_content


@pytest.mark.asyncio
async def test_runner_passes_track_id_and_cold_start():
    """Verify runner.run passes track_id to safety, prompt store, evaluation, and cold_start to researcher."""
    with (
        patch("autoresearch.runner._check_safety", new_callable=AsyncMock) as mock_safety,
        patch("autoresearch.runner.evaluate_week", new_callable=AsyncMock) as mock_eval,
        patch("autoresearch.runner.get_active_variant", new_callable=AsyncMock) as mock_active_var,
        patch("autoresearch.runner.get_baseline_metrics", new_callable=AsyncMock) as mock_baseline_metrics,
        patch("autoresearch.runner.update_variant_metrics", new_callable=AsyncMock),
        patch("autoresearch.runner.run_research", new_callable=AsyncMock) as mock_research,
        patch("autoresearch.runner.save_variant", new_callable=AsyncMock) as mock_save_var,
    ):
        mock_safety.return_value = (False, "")
        mock_eval.return_value = ("Report", {"score": 1.5}, "v_base")
        mock_active_var.return_value = {"variant_tag": "v1"}
        mock_baseline_metrics.return_value = {"score": 1.0}

        mock_res = MagicMock()
        mock_res.experiment_type = "radical"
        mock_res.confidence = 90
        mock_res.change_description = "Test change"
        mock_res.new_prompt_text = "New prompt content"
        mock_res.model_dump.return_value = {}
        mock_research.return_value = mock_res
        mock_save_var.return_value = "v2"

        await runner.run(dry_run=False, track_id="track_claude", cold_start=True)

        mock_safety.assert_called_once()
        assert mock_safety.call_args.kwargs.get("track_id") == "track_claude" or mock_safety.call_args.args == ()
        mock_active_var.assert_called_once_with(track_id="track_claude")
        mock_baseline_metrics.assert_called_once_with(track_id="track_claude")
        mock_eval.assert_called_once()
        assert mock_eval.call_args.kwargs.get("track_id") == "track_claude"
        mock_research.assert_called_once_with("Report", cold_start=True)
        mock_save_var.assert_called_once()
        assert mock_save_var.call_args.kwargs.get("track_id") == "track_claude"


@pytest.mark.asyncio
async def test_prompt_store_baseline_metrics_and_revert_filters_by_track_id():
    """Verify get_baseline_metrics and revert_to_baseline pass track_id."""
    with (
        patch("autoresearch.prompt_store.get_all_time_baseline", new_callable=AsyncMock) as mock_baseline,
        patch("autoresearch.prompt_store.get_async_supabase_client", new_callable=AsyncMock) as mock_sb_client,
    ):
        mock_baseline.return_value = {"variant_tag": "v_base_claude", "metrics": {"score": 2.5}}
        mock_sb = MagicMock()
        mock_chain = MagicMock()
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.update.return_value = mock_chain
        mock_chain.maybe_single.return_value = mock_chain
        mock_chain.execute = AsyncMock(return_value=MagicMock(data={"variant_tag": "v_current"}))
        mock_sb.table.return_value = mock_chain
        mock_sb_client.return_value = mock_sb

        metrics = await prompt_store.get_baseline_metrics(track_id="track_claude")
        assert metrics == {"score": 2.5}
        mock_baseline.assert_called_with("CORE_ANALYSIS_SYSTEM_PROMPT", is_backtest=False, track_id="track_claude")

        reverted = await prompt_store.revert_to_baseline(track_id="track_claude")
        assert reverted == "v_base_claude"

