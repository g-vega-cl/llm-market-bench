import pytest

from core.llm.predictor_prompts import (
    SECTOR_PREDICTOR_CONSTRAINTS_FOOTER,
    SECTOR_PREDICTOR_CONSTRAINTS_HEADER,
    SECTOR_PREDICTOR_MUTABLE_STRATEGIES,
    SECTOR_PREDICTOR_PROMPT,
    split_predictor_prompt,
)
from tasks.predictor_autoresearch import generate_new_prompt


def test_split_predictor_prompt_standard():
    header, mutable, footer = split_predictor_prompt(SECTOR_PREDICTOR_PROMPT)
    assert header == SECTOR_PREDICTOR_CONSTRAINTS_HEADER
    assert footer == SECTOR_PREDICTOR_CONSTRAINTS_FOOTER
    assert mutable == SECTOR_PREDICTOR_MUTABLE_STRATEGIES


def test_split_predictor_prompt_legacy_fallback():
    legacy_prompt = "Legacy system prompt without standard sandwich header and footer.\nDo analysis and return JSON."
    header, mutable, footer = split_predictor_prompt(legacy_prompt)
    assert header == SECTOR_PREDICTOR_CONSTRAINTS_HEADER
    assert footer == SECTOR_PREDICTOR_CONSTRAINTS_FOOTER
    assert mutable == legacy_prompt


@pytest.mark.asyncio
async def test_generate_new_prompt_preserves_sandwich_and_mutates_only_strategies():
    class FakeLLMResponse:
        def __init__(self, text):
            self.new_prompt = text

    class FakeCompletions:
        def __init__(self):
            self.last_meta_prompt = None

        def create(self, model, response_model, messages):
            self.last_meta_prompt = messages[0]["content"]
            # Return mutated strategy content
            return FakeLLMResponse("=== INSTRUCTIONS ===\n1. Enhanced sector analysis.\n2. New quantitative rule.")

    class FakeMetaResearcher:
        def __init__(self):
            self.chat = MagicMock()
            self.chat.completions = FakeCompletions()

    from unittest.mock import MagicMock

    fake_researcher = FakeMetaResearcher()
    old_prompt = SECTOR_PREDICTOR_PROMPT

    result, insight = await generate_new_prompt(old_prompt, 75.0, fake_researcher)

    # Verify meta-prompt sent to LLM contains ONLY the mutable strategies
    meta_prompt_sent = fake_researcher.chat.completions.last_meta_prompt
    assert SECTOR_PREDICTOR_MUTABLE_STRATEGIES in meta_prompt_sent
    assert SECTOR_PREDICTOR_CONSTRAINTS_HEADER not in meta_prompt_sent
    assert "REQUIRED OUTPUT FORMAT" not in meta_prompt_sent

    # Verify resulting assembled prompt wraps mutated strategies with standard header and footer
    assert result.startswith(SECTOR_PREDICTOR_CONSTRAINTS_HEADER)
    assert result.endswith(SECTOR_PREDICTOR_CONSTRAINTS_FOOTER)
    assert "=== INSTRUCTIONS ===\n1. Enhanced sector analysis.\n2. New quantitative rule." in result


def test_calculate_baseline_metrics_empty():
    from tasks.predictor_autoresearch import calculate_baseline_metrics, calculate_baseline_score

    metrics = calculate_baseline_metrics([])
    assert metrics["score"] == 0.0
    assert metrics["predictions_evaluated"] == 0
    assert metrics["base_percentile"] == 50.0
    assert calculate_baseline_score([]) == 0.0


def test_calculate_baseline_metrics_with_predictions():
    from tasks.predictor_autoresearch import (
        DEFAULT_SECTOR_PREDICTOR_TOOLS,
        calculate_baseline_metrics,
        calculate_baseline_score,
    )

    sample = [
        {
            "sector_percentile_score": 90.0,
            "worst_sector_percentile_score": 80.0,
            "pair_percentile_score": 70.0,
            "sector_sp_diff": 3.0,
            "brier_score": 0.10,
        },
        {
            "sector_percentile_score": 80.0,
            "worst_sector_percentile_score": 70.0,
            "pair_percentile_score": 60.0,
            "predicted_sector_return": 4.0,
            "benchmark_spy_return": 2.0,
            "brier_score": 0.20,
        },
    ]

    # Pred 1: base = 80.0, alpha = 3.0, brier = 0.10
    # Pred 2: base = 70.0, alpha = 2.0, brier = 0.20
    # Avg base = 75.0, Avg alpha = 2.5, Mean brier = 0.15
    # Score = 75.0 + 2.5 - (0.15 * 50) = 77.5 - 7.5 = 70.0
    metrics = calculate_baseline_metrics(sample)
    assert metrics["score"] == pytest.approx(70.0)
    assert metrics["base_percentile"] == pytest.approx(75.0)
    assert metrics["alpha_bonus"] == pytest.approx(2.5)
    assert metrics["mean_brier"] == pytest.approx(0.15)
    assert metrics["predictions_evaluated"] == 2
    assert calculate_baseline_score(sample) == pytest.approx(70.0)

    assert "get_historical_correlation" in DEFAULT_SECTOR_PREDICTOR_TOOLS
    assert "get_sector_fundamentals" in DEFAULT_SECTOR_PREDICTOR_TOOLS
