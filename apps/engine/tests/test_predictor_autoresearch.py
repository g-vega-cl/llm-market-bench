from unittest.mock import MagicMock, patch

import pytest

from tasks.predictor_autoresearch import MetaPromptResponse, calculate_baseline_score, generate_new_prompt


def test_calculate_baseline_score():
    """Test that the highest score across models becomes the baseline."""
    mock_predictions = [
        {"model_name": "deepseek-flash", "sector_percentile_score": 80.0, "pair_percentile_score": 90.0},
        {"model_name": "MiniMax-M3", "sector_percentile_score": 95.0, "pair_percentile_score": 85.0},
    ]

    # Baseline logic might average the two scores for each prediction and take the max
    # DeepSeek avg: 85.0
    # MiniMax avg: 90.0
    # Baseline should be 90.0
    baseline = calculate_baseline_score(mock_predictions)
    assert baseline == 90.0


@pytest.mark.asyncio
@patch("tasks.predictor_autoresearch.get_gemini_client")
async def test_generate_new_prompt(mock_get_client):
    """Test generating a new prompt based on the baseline."""
    mock_client = MagicMock()
    mock_resp = MetaPromptResponse(new_prompt="NEW_PROMPT_CONTENT")

    # Mock the async create call
    async def mock_create(*args, **kwargs):
        return mock_resp

    mock_client.chat.completions.create = mock_create
    mock_get_client.return_value = mock_client

    old_prompt = "OLD_PROMPT"
    score = 90.0

    new_prompt = await generate_new_prompt(old_prompt, score, mock_client)
    assert new_prompt == "NEW_PROMPT_CONTENT"
