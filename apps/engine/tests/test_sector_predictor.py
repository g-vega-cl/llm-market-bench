from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.config import DEEPSEEK_FLASH_MODEL, GEMINI_MODEL, MINIMAX_MODEL, OPENAI_MODEL
from tasks.sector_predictor import SectorPredictionResponse, run_sector_predictions


@pytest.mark.asyncio
async def test_run_sector_predictions_all_four_models():
    """Verify that run_sector_predictions executes all 4 LLMs (DeepSeek Flash, MiniMax, Gemini, OpenAI)

    and upserts their sector/pair predictions to Supabase.
    """
    mock_client = MagicMock()
    mock_chain = MagicMock()
    mock_client.table.return_value = mock_chain
    mock_chain.select.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain
    mock_chain.order.return_value = mock_chain
    mock_chain.limit.return_value = mock_chain
    mock_chain.upsert.return_value = mock_chain

    # Mock active prompt DB query
    mock_prompt_res = MagicMock()
    mock_prompt_res.data = [{"variant_tag": "test-tag", "prompt_content": "TEST_PROMPT"}]

    # Mock correlation runs DB query
    mock_runs_res = MagicMock()
    mock_runs_res.data = [{"id": "run-1", "run_date": "2026-08-01"}]

    # Mock correlation data DB query
    mock_corr_res = MagicMock()
    mock_corr_res.data = [
        {
            "ticker_a": "XLK",
            "ticker_b": "XLV",
            "returns_a_7d": 1.0,
            "returns_a_30d": 2.0,
            "returns_a_90d": 3.0,
            "returns_b_7d": 0.5,
            "returns_b_30d": 1.0,
            "returns_b_90d": 1.5,
            "pearson_corr": 0.1,
        }
    ]

    def mock_table_routing(table_name):
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.order.return_value = chain
        chain.limit.return_value = chain
        chain.upsert.return_value = chain

        def mock_execute():
            if table_name == "prompt_experiments":
                return mock_prompt_res
            if table_name == "correlation_runs":
                return mock_runs_res
            if table_name == "correlation_data":
                return mock_corr_res
            if table_name == "sector_predictions":
                return MagicMock(data=[])
            return MagicMock(data=[])

        chain.execute.side_effect = mock_execute
        return chain

    mock_client.table.side_effect = mock_table_routing

    # Intercept upsert calls to verify model names
    upserted_predictions = []

    def mock_upsert_chain(data, on_conflict=None):
        upserted_predictions.append(data)
        chain = MagicMock()
        chain.execute.return_value = MagicMock(data=[data])
        return chain

    # Mock instructor client response
    mock_instructor_resp = SectorPredictionResponse(
        predicted_sector="XLK",
        predicted_pair=["XLK", "XLV"],
        reasoning="Test instructor reasoning",
    )

    async def mock_instructor_create(*args, **kwargs):
        return mock_instructor_resp

    mock_inst_client = MagicMock()
    mock_inst_client.chat.completions.create = mock_instructor_create

    # Mock MiniMax client
    mock_minimax_client = MagicMock()
    mock_minimax_client.chat_with_json_response = AsyncMock(
        return_value={
            "predicted_sector": "XLK",
            "predicted_pair": ["XLK", "XLV"],
            "reasoning": "Test MiniMax reasoning",
        }
    )
    mock_minimax_client.close = AsyncMock()

    # Route tables and upsert
    def mock_table_routing_with_upsert(table_name):
        chain = mock_table_routing(table_name)
        if table_name == "sector_predictions":
            chain.upsert.side_effect = mock_upsert_chain
        return chain

    mock_client.table.side_effect = mock_table_routing_with_upsert

    with (
        patch("tasks.sector_predictor.get_supabase_client", return_value=mock_client),
        patch("tasks.sector_predictor.get_deepseek_client", return_value=mock_inst_client),
        patch("tasks.sector_predictor.get_gemini_client", return_value=mock_inst_client),
        patch("tasks.sector_predictor.get_openai_client", return_value=mock_inst_client),
        patch("tasks.sector_predictor.MiniMaxClient", return_value=mock_minimax_client),
        patch("tasks.sector_predictor.close_client", new_callable=AsyncMock),
    ):
        await run_sector_predictions()

    # Model names that MUST have predictions generated across the 4 timeframes
    upserted_model_names = {p["model_name"] for p in upserted_predictions}

    expected_models = {
        DEEPSEEK_FLASH_MODEL,
        MINIMAX_MODEL,
        GEMINI_MODEL,
        OPENAI_MODEL,
    }

    assert expected_models.issubset(upserted_model_names), (
        f"Expected all models {expected_models} to be executed, but got {upserted_model_names}"
    )


@pytest.mark.asyncio
async def test_openai_reasoning_effort_none_passed():
    """Verify that OpenAI completions call explicitly passes reasoning_effort='none'."""
    mock_client = MagicMock()
    mock_chain = MagicMock()
    mock_client.table.return_value = mock_chain
    mock_chain.select.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain
    mock_chain.order.return_value = mock_chain
    mock_chain.limit.return_value = mock_chain
    mock_chain.upsert.return_value = mock_chain

    mock_prompt_res = MagicMock()
    mock_prompt_res.data = [{"variant_tag": "test-tag", "prompt_content": "TEST_PROMPT"}]
    mock_runs_res = MagicMock()
    mock_runs_res.data = [{"id": "run-1", "run_date": "2026-08-01"}]
    mock_corr_res = MagicMock()
    mock_corr_res.data = [{"ticker_a": "XLK", "ticker_b": "XLV", "pearson_corr": 0.1}]

    def mock_table_routing(table_name):
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.order.return_value = chain
        chain.limit.return_value = chain
        chain.upsert.return_value = chain

        def mock_execute():
            if table_name == "prompt_experiments":
                return mock_prompt_res
            if table_name == "correlation_runs":
                return mock_runs_res
            if table_name == "correlation_data":
                return mock_corr_res
            return MagicMock(data=[])

        chain.execute.side_effect = mock_execute
        return chain

    mock_client.table.side_effect = mock_table_routing

    mock_instructor_resp = SectorPredictionResponse(
        predicted_sector="XLK",
        predicted_pair=["XLK", "XLV"],
        reasoning="Test instructor reasoning",
    )

    openai_create_calls = []

    async def mock_openai_create(*args, **kwargs):
        openai_create_calls.append(kwargs)
        return mock_instructor_resp

    async def mock_other_create(*args, **kwargs):
        return mock_instructor_resp

    mock_openai_inst_client = MagicMock()
    mock_openai_inst_client.chat.completions.create = mock_openai_create

    mock_other_inst_client = MagicMock()
    mock_other_inst_client.chat.completions.create = mock_other_create

    mock_minimax_client = MagicMock()
    mock_minimax_client.chat_with_json_response = AsyncMock(
        return_value={"predicted_sector": "XLK", "predicted_pair": ["XLK", "XLV"], "reasoning": "r"}
    )
    mock_minimax_client.close = AsyncMock()

    with (
        patch("tasks.sector_predictor.get_supabase_client", return_value=mock_client),
        patch("tasks.sector_predictor.get_deepseek_client", return_value=mock_other_inst_client),
        patch("tasks.sector_predictor.get_gemini_client", return_value=mock_other_inst_client),
        patch("tasks.sector_predictor.get_openai_client", return_value=mock_openai_inst_client),
        patch("tasks.sector_predictor.MiniMaxClient", return_value=mock_minimax_client),
        patch("tasks.sector_predictor.close_client", new_callable=AsyncMock),
    ):
        await run_sector_predictions()

    assert len(openai_create_calls) == 4, f"Expected 4 OpenAI calls across 4 timeframes, got {len(openai_create_calls)}"
    for call_kwargs in openai_create_calls:
        assert call_kwargs.get("reasoning_effort") == "none", (
            f"Expected reasoning_effort='none' in OpenAI call, got {call_kwargs}"
        )
