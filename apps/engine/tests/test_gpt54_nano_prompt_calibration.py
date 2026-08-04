"""Tests for gpt-5.4-nano prompt calibration self-audit instructions."""

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
async def test_gpt54_nano_prompt_calibration_injected():
    """Verify that gpt-5.4-nano receives the pre-signal valuation self-audit instructions."""
    with patch("core.db.get_async_supabase_client", side_effect=Exception("Mocked DB")):
        messages = await PromptFactory.build_analysis_messages(
            provider="openai",
            owner_id="gpt-5.4-nano",
            **get_sample_kwargs(),
        )

    system_and_user_text = " ".join(m.get("content", "") for m in messages if isinstance(m.get("content"), str))
    assert "VALUATION & OVEREXTENSION SELF-AUDIT" in system_and_user_text
    assert "HOLD" in system_and_user_text


@pytest.mark.asyncio
async def test_other_models_prompt_unaffected():
    """Verify that other models do not receive the gpt-5.4-nano specific pre-audit prompt."""
    other_owners = ["claude-haiku-4-5", "deepseek-v4-pro", "gemini-3.5-flash-lite", "MiniMax-M3"]

    for owner in other_owners:
        with patch("core.db.get_async_supabase_client", side_effect=Exception("Mocked DB")):
            messages = await PromptFactory.build_analysis_messages(
                provider="anthropic",
                owner_id=owner,
                **get_sample_kwargs(),
            )

        system_and_user_text = " ".join(m.get("content", "") for m in messages if isinstance(m.get("content"), str))
        assert "VALUATION & OVEREXTENSION SELF-AUDIT" not in system_and_user_text
