from apps.engine.core.llm.prompts import (
    CAUSE_AND_EFFECT_SYSTEM_PROMPT,
    MANAGER_SYSTEM_PROMPT,
    SYNTHESIS_SYSTEM_PROMPT,
)


def test_catalyst_logic_constraints():
    """Verify that the synthesis SYSTEM prompt contains the negative constraints for catalysts."""
    assert "CRITICAL: Do NOT mark broad themes" in SYNTHESIS_SYSTEM_PROMPT
    assert "ongoing structural shifts, or VAGUE timeframes" in SYNTHESIS_SYSTEM_PROMPT
    assert "If you cannot name the specific day or a very tight window" in SYNTHESIS_SYSTEM_PROMPT
    assert "it is NOT a future catalyst for Horizon Watch" in SYNTHESIS_SYSTEM_PROMPT


def test_scenario_probabilities_required():
    """Verify that the synthesis SYSTEM prompt requires probability percentages for each scenario."""
    assert "XX% probability" in SYNTHESIS_SYSTEM_PROMPT or "probability" in SYNTHESIS_SYSTEM_PROMPT.lower()
    assert "each scenario" in SYNTHESIS_SYSTEM_PROMPT.lower() or "probabilities" in SYNTHESIS_SYSTEM_PROMPT.lower()
    assert "sum to 100" in SYNTHESIS_SYSTEM_PROMPT.lower() or "100%" in SYNTHESIS_SYSTEM_PROMPT


def test_5_whys_integration():
    """Verify that the 5 Whys technique is mentioned in relevant prompts."""
    from apps.engine.core.llm.prompts import (
        ANALYSIS_USER_PROMPT_TEMPLATE,
        CORE_ANALYSIS_SYSTEM_PROMPT,
    )

    # Check System Prompt
    assert "5 Whys" in CORE_ANALYSIS_SYSTEM_PROMPT
    assert "**Why** is this news market-moving?" in CORE_ANALYSIS_SYSTEM_PROMPT
    assert 'REASONING RIGOR: THE "5 WHYS"' in CORE_ANALYSIS_SYSTEM_PROMPT

    # Analysis User Prompt should now be minimal data injection
    assert "{news_content}" in ANALYSIS_USER_PROMPT_TEMPLATE
    assert "{portfolio_context}" in ANALYSIS_USER_PROMPT_TEMPLATE

    # After refactor: Manager 5-Whys lives in system prompt, not user prompt
    assert "ROOT CAUSE ANALYSIS (MANDATORY)" in MANAGER_SYSTEM_PROMPT
    assert "5 Whys" in MANAGER_SYSTEM_PROMPT

    # After refactor: Cause & Effect causal recursion lives in system prompt
    assert "CAUSAL RECURSION (5 WHYS)" in CAUSE_AND_EFFECT_SYSTEM_PROMPT


def test_reasoning_toolbox_integration():
    """Verify that advanced reasoning frameworks from the toolbox are mentioned in relevant prompts."""
    from apps.engine.core.llm.prompts import (
        CAUSE_AND_EFFECT_SYSTEM_PROMPT,
        CONTRARIAN_SYSTEM_PROMPT,
        CORE_ANALYSIS_SYSTEM_PROMPT,
        MANAGER_SYSTEM_PROMPT,
    )

    for prompt in [
        CORE_ANALYSIS_SYSTEM_PROMPT,
        CONTRARIAN_SYSTEM_PROMPT,
        MANAGER_SYSTEM_PROMPT,
        CAUSE_AND_EFFECT_SYSTEM_PROMPT,
    ]:
        assert "MECE" in prompt
        assert "IS / IS NOT" in prompt
        assert "Ishikawa" in prompt
