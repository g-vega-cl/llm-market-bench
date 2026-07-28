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

    result = await generate_new_prompt(old_prompt, 75.0, fake_researcher)

    # Verify meta-prompt sent to LLM contains ONLY the mutable strategies
    meta_prompt_sent = fake_researcher.chat.completions.last_meta_prompt
    assert SECTOR_PREDICTOR_MUTABLE_STRATEGIES in meta_prompt_sent
    assert SECTOR_PREDICTOR_CONSTRAINTS_HEADER not in meta_prompt_sent
    assert "REQUIRED OUTPUT FORMAT" not in meta_prompt_sent

    # Verify resulting assembled prompt wraps mutated strategies with standard header and footer
    assert result.startswith(SECTOR_PREDICTOR_CONSTRAINTS_HEADER)
    assert result.endswith(SECTOR_PREDICTOR_CONSTRAINTS_FOOTER)
    assert "=== INSTRUCTIONS ===\n1. Enhanced sector analysis.\n2. New quantitative rule." in result
