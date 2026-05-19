import pytest

from core.llm.prompt_factory import PromptFactory


@pytest.mark.asyncio
async def test_system_heavy_prompt_structure():
    """Verify that core logic has moved to System and User is minimal."""

    # 1. Build messages using the factory
    messages = await PromptFactory.build_analysis_messages(
        provider="openai",
        owner_id="test_model",  # Not in experiment group to use hardcoded baseline
        news_content="FAKE NEWS",
        portfolio_context="FAKE PORTFOLIO",
        context="FAKE CONTEXT",
        macro_context="FAKE MACRO",
        current_day_info="FAKE DATE",
        held_tickers_list="AAPL, MSFT",
    )

    system_msg = next(m["content"] for m in messages if m["role"] == "system")
    user_msg = next(m["content"] for m in messages if m["role"] == "user")

    # --- Assertions for System Prompt (The Rulebook) ---
    assert "SMA MANAGEMENT RULES" in system_msg, "SMA rules should be in System Prompt"
    assert "5 WHYS" in system_msg, "5-Whys logic should be in System Prompt"
    assert "MANDATORY QUANTITY CALCULATION" in system_msg, "Tool enforcement should be in System Prompt"
    assert "CALENDAR & SEASONAL STRATEGIES" in system_msg, "Calendar knowledge should be in System Prompt"

    # --- Assertions for User Prompt (The Data Case) ---
    # The user prompt should NO LONGER contain these blocks
    assert "SOPHISTICATED TRADING LOGIC" not in user_msg, "Trading logic should NOT be in User Prompt"
    assert "SMA MANAGEMENT RULES" not in user_msg, "SMA rules should NOT be in User Prompt"

    # But it SHOULD contain the data placeholders
    assert "FAKE NEWS" in user_msg
    assert "FAKE PORTFOLIO" in user_msg
    assert "### NEWS BATCH:" in user_msg
