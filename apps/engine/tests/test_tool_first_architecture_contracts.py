"""Contract tests enforcing Tool-First, Agency-Driven Architecture.

Verifies that:
1. Baseline trading analysis prompts remain clean of hardcoded developer trading filters/heuristics.
2. Modular prompt blocks in `prompt_blocks.py` remain isolated and not baked into baseline prompts.
3. Core pull-based tools are registered in the canonical tool registry.
4. Pipeline utility tasks (e.g. newsletter generator) remain distinct and allowed to define editorial prompts.
"""

from autoresearch.prompt_blocks import AVAILABLE_PROMPT_BLOCKS
from core.llm import prompts
from core.llm.tools import CANONICAL_TOOLS_REGISTRY


def test_baseline_analysis_system_prompt_has_no_hardcoded_filters():
    """Verify that CORE_ANALYSIS_SYSTEM_PROMPT has no ad-hoc developer filters or ticker-specific rules."""
    baseline_prompt = prompts.CORE_ANALYSIS_SYSTEM_PROMPT

    # Developer anti-patterns that must never be hardcoded into baseline prompts
    forbidden_injections = [
        "GPT54_NANO_PRE_AUDIT_PROMPT",
        "PRE_AUDIT_PROMPT",
        "Only buy tech if VIX",
        "Do not trade on Mondays",
        "Never trade AAPL",
        "MANDATORY PRE-SIGNAL SELF-AUDIT",
    ]

    for injection in forbidden_injections:
        assert injection not in baseline_prompt, f"Forbidden developer heuristic found in baseline prompt: {injection}"


def test_modular_prompt_blocks_isolated_from_baseline():
    """Verify that prompt blocks in prompt_blocks.py are modular and NOT baked into baseline system prompts.

    Trading discipline blocks belong in prompt_blocks.py so the Auto-Researcher can
    autonomously test and adopt them, rather than developers hardcoding them into baseline prompts.
    """
    baseline_prompt = prompts.CORE_ANALYSIS_SYSTEM_PROMPT

    for block_id, block_data in AVAILABLE_PROMPT_BLOCKS.items():
        title = block_data.get("title", "")
        content = block_data.get("content", "")

        # The full block title or discipline header should not be embedded directly in the static baseline
        assert title not in baseline_prompt, (
            f"Modular prompt block '{block_id}' ({title}) is hardcoded into CORE_ANALYSIS_SYSTEM_PROMPT. "
            f"It must remain an optional modular block selected by the Auto-Researcher."
        )
        first_line = content.split("\n")[0] if content else ""
        assert first_line not in baseline_prompt, (
            f"Modular block content '{first_line}' found in CORE_ANALYSIS_SYSTEM_PROMPT."
        )



def test_pull_tools_registered_in_canonical_registry():
    """Verify that core pull-based context tools are registered in CANONICAL_TOOLS_REGISTRY.

    Trading agents must be given tools to pull context rather than having static data
    forced into their prompts.
    """
    required_pull_tools = [
        "get_portfolio_ledger",
        "get_todays_news_menu",
        "fetch_newsletter_content",
        "get_global_macro_context",
        "get_options_vol_surface",
        "get_yield_curve_regime",
    ]

    for tool_name in required_pull_tools:
        assert tool_name in CANONICAL_TOOLS_REGISTRY, (
            f"Core pull tool '{tool_name}' missing from CANONICAL_TOOLS_REGISTRY. "
            f"Trading agents require this tool for autonomous information retrieval."
        )


def test_pipeline_utility_tasks_separation():
    """Verify that pipeline utility tasks (like newsletter generator) are recognized as editorial flows."""
    from tasks.newsletter_generator import _call_deepseek_flash

    # Pipeline generator functions exist and are distinct from trading analysis
    assert callable(_call_deepseek_flash)
