"""Tests verifying that OpenAI models receive clean baseline prompts without hardcoded pre-audit rules."""

from unittest.mock import patch

import pytest

from core.llm.prompt_factory import PromptFactory


def get_sample_kwargs():
    return {
        "current_day_info": "Tuesday, July 28, 2026",
        "market_data_block": "Market data sample",
        "portfolio_context": "Cash: $10000",
        "held_tickers_list": "None",
        "macro_context": "Macro context sample",
        "context": "Historical context sample",
        "news_content": "Newsletter content",
    }


@pytest.mark.asyncio
async def test_openai_models_receive_clean_baseline_prompt():
    """Verify that OpenAI models (gpt-5.6-luna, gpt-5.4-nano) do NOT receive hardcoded pre-audit rules."""
    openai_models = ["gpt-5.6-luna", "gpt-5.4-nano"]

    for model in openai_models:
        with patch("core.db.get_async_supabase_client", side_effect=Exception("Mocked DB")):
            messages = await PromptFactory.build_analysis_messages(
                provider="openai",
                owner_id=model,
                **get_sample_kwargs(),
            )

        system_and_user_text = " ".join(m.get("content", "") for m in messages if isinstance(m.get("content"), str))
        assert "VALUATION & OVEREXTENSION SELF-AUDIT" not in system_and_user_text


@pytest.mark.asyncio
async def test_all_models_prompt_clean_from_hardcoded_audit():
    """Verify that all other evolvable models also do not receive hardcoded pre-audit prompts."""
    owners = ["claude-haiku-4-5", "deepseek-v4-pro", "gemini-3.5-flash-lite", "MiniMax-M3"]

    for owner in owners:
        with patch("core.db.get_async_supabase_client", side_effect=Exception("Mocked DB")):
            messages = await PromptFactory.build_analysis_messages(
                provider="anthropic",
                owner_id=owner,
                **get_sample_kwargs(),
            )

        system_and_user_text = " ".join(m.get("content", "") for m in messages if isinstance(m.get("content"), str))
        assert "VALUATION & OVEREXTENSION SELF-AUDIT" not in system_and_user_text
