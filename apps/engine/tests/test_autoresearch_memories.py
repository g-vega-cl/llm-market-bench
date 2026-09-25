from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.config import DEEPSEEK_FLASH_MODEL, GEMINI_MODEL, MINIMAX_MODEL, OPENAI_MODEL
from memory.store import decay_memories, retrieve_autoresearch_memories


def test_retrieve_autoresearch_memories_track_isolation():
    mock_client = MagicMock()
    # Mock memories in DB
    mock_data = [
        {
            "id": "1",
            "content": "[DEEPSEEK-V4-FLASH DAILY PREDICTOR] High VIX requires wider targets.",
            "importance_score": 9,
            "memory_type": "AUTORESEARCH_INSIGHT",
            "status": "ACTIVE",
            "created_at": "2026-09-10T12:00:00Z",
            "metadata": {
                "scope": "daily_predictor",
                "track_id": "deepseek-v4-flash",
                "is_baseline_beat": True,
            },
        },
        {
            "id": "2",
            "content": "[MINIMAX-M3 DAILY PREDICTOR] Gap downs mean revert intraday.",
            "importance_score": 9,
            "memory_type": "AUTORESEARCH_INSIGHT",
            "status": "ACTIVE",
            "created_at": "2026-09-10T12:00:00Z",
            "metadata": {
                "scope": "daily_predictor",
                "track_id": "MiniMax-M3",
                "is_baseline_beat": True,
            },
        },
        {
            "id": "3",
            "content": "[DEEPSEEK-V4-FLASH SECTOR PREDICTOR] Tech vs Energy rotation favors XLK.",
            "importance_score": 8,
            "memory_type": "AUTORESEARCH_INSIGHT",
            "status": "ACTIVE",
            "created_at": "2026-09-11T12:00:00Z",
            "metadata": {
                "scope": "sector_predictor",
                "track_id": "deepseek-v4-flash",
                "is_baseline_beat": True,
            },
        },
    ]

    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.limit.return_value = mock_table
    mock_table.execute.return_value = MagicMock(data=mock_data)

    with patch("memory.store.get_supabase_client", return_value=mock_client):
        # 1. DeepSeek Daily Predictor should only get Memory 1
        res_deepseek_daily = retrieve_autoresearch_memories(track_id="deepseek-v4-flash", scope="daily_predictor")
        assert "High VIX requires wider targets" in res_deepseek_daily
        assert "Gap downs mean revert intraday" not in res_deepseek_daily
        assert "Tech vs Energy rotation" not in res_deepseek_daily

        # 2. MiniMax Daily Predictor should only get Memory 2
        res_minimax_daily = retrieve_autoresearch_memories(track_id="MiniMax-M3", scope="daily_predictor")
        assert "Gap downs mean revert intraday" in res_minimax_daily
        assert "High VIX requires wider targets" not in res_minimax_daily
        assert "Tech vs Energy rotation" not in res_minimax_daily

        # 3. DeepSeek Sector Predictor should only get Memory 3
        res_deepseek_sector = retrieve_autoresearch_memories(track_id="deepseek-v4-flash", scope="sector_predictor")
        assert "Tech vs Energy rotation" in res_deepseek_sector
        assert "High VIX requires wider targets" not in res_deepseek_sector
        assert "Gap downs mean revert intraday" not in res_deepseek_sector


def test_decay_autoresearch_memories():
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.lt.return_value = mock_table
    mock_table.gt.return_value = mock_table

    # Sample memories:
    # 1. Baseline winner: importance=9, is_baseline_beat=True -> should NOT decay
    # 2. Failed experiment: importance=5, is_baseline_beat=False -> should decay by 50%
    mock_memories = [
        {
            "id": "mem-win",
            "relevance_score": 1.0,
            "created_at": "2026-08-01T00:00:00Z",
            "memory_type": "AUTORESEARCH_INSIGHT",
            "importance_score": 9,
            "metadata": {"is_baseline_beat": True},
        },
        {
            "id": "mem-fail",
            "relevance_score": 1.0,
            "created_at": "2026-08-01T00:00:00Z",
            "memory_type": "AUTORESEARCH_INSIGHT",
            "importance_score": 5,
            "metadata": {"is_baseline_beat": False},
        },
    ]
    mock_table.execute.return_value = MagicMock(data=mock_memories)

    update_mock = MagicMock()
    mock_table.update.return_value = update_mock
    update_mock.eq.return_value = MagicMock(execute=MagicMock())

    decay_memories(mock_client, decay_days=30)

    # mem-win should NOT have been updated (no decay)
    # mem-fail should have been updated with relevance_score = 0.5
    updated_payloads = [call.args[0] for call in mock_table.update.call_args_list]

    assert {"relevance_score": 0.5} in updated_payloads
    assert len(updated_payloads) == 1


@pytest.mark.asyncio
async def test_daily_autoresearch_persists_track_memory():
    from datetime import date

    from tasks.daily_autoresearch import run_daily_autoresearch_for_model

    mock_client = MagicMock()
    mock_meta = MagicMock()

    # Mock predictions returned
    predictions = [
        {"is_correct": True, "intraday_hit": True, "brier_score": 0.04, "expected_return_pct": 0.3},
    ]
    # Mock active prompt
    active_prompt_data = [
        {
            "variant_tag": "daily-pred-old",
            "prompt_content": "Header\nOld strategy\nFooter",
            "metrics": {"score": 60.0},
        }
    ]

    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.gte.return_value = mock_table
    mock_table.lte.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.limit.return_value = mock_table
    mock_table.update.return_value = mock_table

    def execute_mock():
        res = MagicMock()
        # Predictions vs prompt_experiments
        res.data = active_prompt_data
        return res

    mock_table.execute.side_effect = [
        MagicMock(data=predictions),  # daily_predictions query
        MagicMock(data=active_prompt_data),  # prompt_experiments active query
        MagicMock(data=active_prompt_data),  # prompt_experiments all variants query
        MagicMock(data=[]),  # update metrics
        MagicMock(data=[]),  # newsletter snapshots query (in context)
        MagicMock(data=[]),  # memories query (in context)
        MagicMock(data=[]),  # concept_metrics query (in context)
        MagicMock(data=[]),  # demote active
        MagicMock(data=[]),  # insert new prompt
    ]

    mock_meta.chat.completions.create.return_value = MagicMock(
        new_prompt="New strategy instructions for SPY.",
        research_insight="Momentum persists on post-CPI gap-ups.",
    )

    today = date(2026, 9, 15)
    seven_days = date(2026, 9, 8)
    fourteen_days = date(2026, 9, 1)

    with patch("memory.store.add_memory") as mock_add_memory:
        await run_daily_autoresearch_for_model(
            model_name=DEEPSEEK_FLASH_MODEL,
            client=mock_client,
            today=today,
            seven_days_ago=seven_days,
            fourteen_days_ago=fourteen_days,
            deepseek_meta=mock_meta,
            dry_run=False,
        )

        assert mock_add_memory.called
        kwargs = mock_add_memory.call_args.kwargs
        assert kwargs["memory_type"] == "AUTORESEARCH_INSIGHT"
        assert kwargs["metadata"]["scope"] == "daily_predictor"
        assert kwargs["metadata"]["track_id"] == DEEPSEEK_FLASH_MODEL
        assert "Momentum persists on post-CPI gap-ups" in kwargs["content"]


@pytest.mark.asyncio
async def test_sector_autoresearch_loops_all_4_models_and_persists_memories():
    from tasks.predictor_autoresearch import TARGET_SECTOR_MODELS, run_predictor_autoresearch

    assert len(TARGET_SECTOR_MODELS) == 4
    assert set(TARGET_SECTOR_MODELS) == {DEEPSEEK_FLASH_MODEL, MINIMAX_MODEL, GEMINI_MODEL, OPENAI_MODEL}

    mock_client = MagicMock()
    mock_meta = MagicMock()

    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.gte.return_value = mock_table
    mock_table.lte.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.limit.return_value = mock_table
    mock_table.update.return_value = mock_table
    mock_table.insert.return_value = mock_table

    predictions = [
        {
            "sector_percentile_score": 85.0,
            "worst_sector_percentile_score": 90.0,
            "pair_percentile_score": 80.0,
            "brier_score": 0.05,
        }
    ]
    active_prompt = [
        {"variant_tag": "sector-old", "prompt_content": "Header\nStrategy\nFooter", "metrics": {"score": 70.0}}
    ]

    def mock_table_select(table_name):
        mock_chain = MagicMock()
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.gte.return_value = mock_chain
        mock_chain.lte.return_value = mock_chain
        mock_chain.order.return_value = mock_chain
        mock_chain.limit.return_value = mock_chain
        mock_chain.update.return_value = mock_chain
        mock_chain.insert.return_value = mock_chain
        mock_chain.in_.return_value = mock_chain
        mock_chain.neq.return_value = mock_chain

        if table_name == "sector_predictions":
            mock_chain.execute.return_value = MagicMock(data=predictions)
        elif table_name == "prompt_experiments":
            mock_chain.execute.return_value = MagicMock(data=active_prompt)
        else:
            mock_chain.execute.return_value = MagicMock(data=[])
        return mock_chain

    mock_client.table.side_effect = mock_table_select

    mock_meta.chat.completions.create.return_value = MagicMock(
        new_prompt="Mutated sector strategy rules",
        research_insight="Tech capex surge favors semiconductors over utilities in high rate regimes.",
    )

    with (
        patch("tasks.predictor_autoresearch.get_supabase_client", return_value=mock_client),
        patch("tasks.predictor_autoresearch.get_gemini_client", return_value=mock_meta),
        patch("tasks.predictor_autoresearch.close_client", new_callable=AsyncMock),
        patch("memory.store.add_memory") as mock_add_memory,
    ):
        await run_predictor_autoresearch(dry_run=False)

        # Ensure all 4 models were evaluated and recorded memories
        assert mock_add_memory.call_count == 4
        recorded_tracks = {call.kwargs["metadata"]["track_id"] for call in mock_add_memory.call_args_list}
        assert recorded_tracks == {DEEPSEEK_FLASH_MODEL, MINIMAX_MODEL, GEMINI_MODEL, OPENAI_MODEL}
        for call in mock_add_memory.call_args_list:
            assert call.kwargs["metadata"]["scope"] == "sector_predictor"
            assert call.kwargs["memory_type"] == "AUTORESEARCH_INSIGHT"


@pytest.mark.asyncio
async def test_portfolio_autoresearch_persists_track_memory():
    from autoresearch.researcher import PromptResearchResult
    from autoresearch.runner import run

    mock_eval = (
        "# Weekly Report",
        {"score": 2.5, "composite": 2.5},
        "baseline-tag",
    )
    fake_result = PromptResearchResult(
        new_prompt_text="Strategy rules",
        selected_tools=["get_portfolio_ledger"],
        selected_prompt_blocks=["let_winners_run"],
        change_description="Improved exit logic",
        experiment_type="incremental",
        research_reasoning="Detailed reasoning",
        confidence=80,
        research_insight="Holding past 48h after earnings announcement increases drawdown.",
    )

    with (
        patch("autoresearch.runner._check_safety", new_callable=AsyncMock, return_value=(False, "")),
        patch("autoresearch.runner.evaluate_week", new_callable=AsyncMock, return_value=mock_eval),
        patch(
            "autoresearch.runner.get_active_variant",
            new_callable=AsyncMock,
            return_value={"variant_tag": "old", "prompt_content": "prompt"},
        ),
        patch("autoresearch.runner.get_baseline_metrics", new_callable=AsyncMock, return_value={"score": 1.0}),
        patch("autoresearch.prompt_store.get_all_time_baseline", new_callable=AsyncMock, return_value=None),
        patch("autoresearch.runner.update_variant_metrics", new_callable=AsyncMock),
        patch("autoresearch.runner.run_research", new_callable=AsyncMock, return_value=fake_result),
        patch("autoresearch.runner.save_variant", new_callable=AsyncMock, return_value="new-tag"),
        patch("memory.store.add_memory") as mock_add_memory,
    ):
        await run(dry_run=False, track_id="track_claude")

        assert mock_add_memory.called
        kwargs = mock_add_memory.call_args.kwargs
        assert kwargs["memory_type"] == "AUTORESEARCH_INSIGHT"
        assert kwargs["metadata"]["scope"] == "portfolio_trading"
        assert kwargs["metadata"]["track_id"] == "track_claude"
        assert "Holding past 48h" in kwargs["content"]


@pytest.mark.asyncio
async def test_query_past_research_memories_tool():
    from autoresearch.tools import query_past_research_memories

    with patch("memory.store.retrieve_autoresearch_memories", return_value="- (Importance: 9/10) Lesson 1"):
        res = await query_past_research_memories(track_id="track_claude")
        assert "=== PAST AUTORESEARCH MEMORIES (Track: track_claude) ===" in res
        assert "Lesson 1" in res

    with patch("memory.store.retrieve_autoresearch_memories", return_value=""):
        res = await query_past_research_memories(track_id="track_openai")
        assert "No past autoresearch insight memories found" in res
