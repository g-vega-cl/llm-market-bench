import pytest
from apps.engine.core.llm.prompts import SYNTHESIS_USER_PROMPT_TEMPLATE

def test_catalyst_logic_constraints():
    """Verify that the synthesis prompt contains the negative constraints for catalysts."""
    assert "CRITICAL: Do NOT mark broad themes" in SYNTHESIS_USER_PROMPT_TEMPLATE
    assert "ongoing structural shifts, or VAGUE timeframes" in SYNTHESIS_USER_PROMPT_TEMPLATE
    assert "If you cannot name the specific day or a very tight window" in SYNTHESIS_USER_PROMPT_TEMPLATE
    assert "it is NOT a future catalyst for Horizon Watch" in SYNTHESIS_USER_PROMPT_TEMPLATE

def test_5_whys_integration():
    """Verify that the 5 Whys technique is mentioned in relevant prompts."""
    from apps.engine.core.llm.prompts import CORE_ANALYSIS_SYSTEM_PROMPT, MANAGER_USER_PROMPT_TEMPLATE, CAUSE_AND_EFFECT_USER_PROMPT_TEMPLATE, ANALYSIS_USER_PROMPT_TEMPLATE
    
    # Check System Prompt
    assert "5 Whys" in CORE_ANALYSIS_SYSTEM_PROMPT
    assert "**Why** is this news market-moving?" in CORE_ANALYSIS_SYSTEM_PROMPT
    
    # Check Analysis User Prompt
    assert "REASONING RIGOR: THE \"5 WHYS\"" in ANALYSIS_USER_PROMPT_TEMPLATE
    
    # Check Manager Post-Mortem
    assert "ROOT CAUSE ANALYSIS (MANDATORY)" in MANAGER_USER_PROMPT_TEMPLATE
    assert "5 Whys" in MANAGER_USER_PROMPT_TEMPLATE
    
    # Check Cause & Effect Causal Recursion
    assert "CAUSAL RECURSION (5 WHYS)" in CAUSE_AND_EFFECT_USER_PROMPT_TEMPLATE
