import pytest

from core.llm import prompts
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


class TestPureDataInjectionUserPrompts:
    """
    RED-phase tests enforcing the pure data-injection contract on all user prompt
    templates. Each test will FAIL against the current code and PASS after the
    prompts.py refactor.

    Invariants:
      - User prompts must NOT contain persona openers ("You are a ...")
      - User prompts must NOT contain instruction/SOP blocks
      - User prompts MUST contain all {placeholder} variables
      - User prompts MUST end with a single closing task directive
      - System prompts MUST own all rules previously embedded in user prompts
    """

    # ------------------------------------------------------------------ #
    # ANALYSIS                                                             #
    # ------------------------------------------------------------------ #

    def test_analysis_user_no_persona_opener(self):
        """The analysis user prompt must not begin with an instruction sentence."""
        assert "You are a hedge fund trading algorithm. Analyze" not in prompts.ANALYSIS_USER_PROMPT_TEMPLATE, (
            "Persona/task opener belongs in the system prompt, not the user prompt."
        )

    def test_analysis_user_has_required_placeholders(self):
        """Analysis user prompt must preserve all data injection slots."""
        for placeholder in [
            "{current_day_info}",
            "{portfolio_context}",
            "{news_content}",
            "{context}",
            "{macro_context}",
            "{held_tickers_list}",
            "{market_data_block}",
        ]:
            assert placeholder in prompts.ANALYSIS_USER_PROMPT_TEMPLATE, (
                f"Missing placeholder {placeholder} in ANALYSIS_USER_PROMPT_TEMPLATE"
            )

    # ------------------------------------------------------------------ #
    # CONTRARIAN                                                           #
    # ------------------------------------------------------------------ #

    def test_contrarian_user_no_persona(self):
        assert "You are a contrarian hedge fund manager" not in prompts.CONTRARIAN_USER_PROMPT_TEMPLATE, (
            "Persona belongs in CONTRARIAN_SYSTEM_PROMPT."
        )

    def test_contrarian_user_no_sophisticated_logic_block(self):
        assert "SOPHISTICATED CONTRARIAN LOGIC" not in prompts.CONTRARIAN_USER_PROMPT_TEMPLATE, (
            "Strategy instructions belong in CONTRARIAN_SYSTEM_PROMPT."
        )

    def test_contrarian_user_no_how_prices_work(self):
        assert "HOW PRICES WORK" not in prompts.CONTRARIAN_USER_PROMPT_TEMPLATE, (
            "HOW PRICES WORK is a standing instruction — belongs in system prompt."
        )

    def test_contrarian_user_no_hard_enforcement(self):
        assert "HARD ENFORCEMENT" not in prompts.CONTRARIAN_USER_PROMPT_TEMPLATE, (
            "Tool-enforcement rule belongs in CONTRARIAN_SYSTEM_PROMPT."
        )

    def test_contrarian_user_has_required_placeholders(self):
        for placeholder in [
            "{market_data_block}",
            "{news_content}",
            "{decisions_context}",
            "{context}",
            "{portfolio_context}",
        ]:
            assert placeholder in prompts.CONTRARIAN_USER_PROMPT_TEMPLATE, (
                f"Missing placeholder {placeholder} in CONTRARIAN_USER_PROMPT_TEMPLATE"
            )

    def test_contrarian_system_owns_sophisticated_logic(self):
        assert "SOPHISTICATED CONTRARIAN LOGIC" in prompts.CONTRARIAN_SYSTEM_PROMPT, (
            "CONTRARIAN_SYSTEM_PROMPT must own SOPHISTICATED CONTRARIAN LOGIC."
        )

    def test_contrarian_system_owns_how_prices_work(self):
        assert "HOW PRICES WORK" in prompts.CONTRARIAN_SYSTEM_PROMPT, (
            "CONTRARIAN_SYSTEM_PROMPT must own HOW PRICES WORK block."
        )

    def test_contrarian_system_owns_hard_enforcement(self):
        assert "HARD ENFORCEMENT" in prompts.CONTRARIAN_SYSTEM_PROMPT, (
            "CONTRARIAN_SYSTEM_PROMPT must own hard tool-enforcement rules."
        )

    # ------------------------------------------------------------------ #
    # VERIFIER                                                             #
    # ------------------------------------------------------------------ #

    def test_verifier_user_no_persona(self):
        assert "You are a skeptical senior investment verifier" not in prompts.VERIFIER_USER_PROMPT_TEMPLATE, (
            "Persona belongs in VERIFIER_SYSTEM_PROMPT."
        )

    def test_verifier_user_no_sop_block(self):
        assert "YOUR SKEPTICAL ANALYSIS SOP" not in prompts.VERIFIER_USER_PROMPT_TEMPLATE, (
            "SOP belongs in VERIFIER_SYSTEM_PROMPT."
        )

    def test_verifier_user_has_required_placeholders(self):
        for placeholder in [
            "{ticker}",
            "{signal}",
            "{reasoning}",
            "{portfolio_context}",
            "{context}",
            "{uncrowded_context}",
            "{contrarian_context}",
        ]:
            assert placeholder in prompts.VERIFIER_USER_PROMPT_TEMPLATE, (
                f"Missing placeholder {placeholder} in VERIFIER_USER_PROMPT_TEMPLATE"
            )

    def test_verifier_system_owns_sop(self):
        assert "YOUR SKEPTICAL ANALYSIS SOP" in prompts.VERIFIER_SYSTEM_PROMPT, (
            "VERIFIER_SYSTEM_PROMPT must own the skeptical analysis SOP."
        )

    # ------------------------------------------------------------------ #
    # SYNTHESIS                                                            #
    # ------------------------------------------------------------------ #

    def test_synthesis_user_no_persona(self):
        assert "You are a senior financial analyst. Synthesize" not in prompts.SYNTHESIS_USER_PROMPT_TEMPLATE, (
            "Persona belongs in SYNTHESIS_SYSTEM_PROMPT."
        )

    def test_synthesis_user_no_task_instructions(self):
        # The numbered task list is an instruction block, not data
        assert "Your task:\n1." not in prompts.SYNTHESIS_USER_PROMPT_TEMPLATE, (
            "Task instruction list belongs in SYNTHESIS_SYSTEM_PROMPT."
        )

    def test_synthesis_user_has_required_placeholders(self):
        for placeholder in [
            "{event_name}",
            "{impact}",
            "{combined_reasonings}",
            "{combined_scenarios}",
        ]:
            assert placeholder in prompts.SYNTHESIS_USER_PROMPT_TEMPLATE, (
                f"Missing placeholder {placeholder} in SYNTHESIS_USER_PROMPT_TEMPLATE"
            )

    def test_synthesis_system_owns_specificity_rule(self):
        assert "SPECIFICITY RULE" in prompts.SYNTHESIS_SYSTEM_PROMPT, (
            "SYNTHESIS_SYSTEM_PROMPT must own the SPECIFICITY RULE for event naming."
        )

    def test_synthesis_system_owns_future_catalyst_constraints(self):
        assert "CRITICAL: Do NOT mark broad themes" in prompts.SYNTHESIS_SYSTEM_PROMPT, (
            "SYNTHESIS_SYSTEM_PROMPT must own future-catalyst guard rails."
        )

    # ------------------------------------------------------------------ #
    # MANAGER                                                              #
    # ------------------------------------------------------------------ #

    def test_manager_user_no_persona(self):
        assert "You are a senior investment manager" not in prompts.MANAGER_USER_PROMPT_TEMPLATE, (
            "Persona belongs in MANAGER_SYSTEM_PROMPT."
        )

    def test_manager_user_no_your_task_block(self):
        assert "YOUR TASK:\n1. Evaluate the agent" not in prompts.MANAGER_USER_PROMPT_TEMPLATE, (
            "Task instructions belong in MANAGER_SYSTEM_PROMPT."
        )

    def test_manager_user_has_required_placeholders(self):
        # entry_price and current_price use format specs (${entry_price:.2f}) in the template
        for placeholder in ["{ticker}", "{signal}", "{entry_price:.2f}", "{current_price:.2f}", "{reasoning}"]:
            assert placeholder in prompts.MANAGER_USER_PROMPT_TEMPLATE, (
                f"Missing placeholder {placeholder} in MANAGER_USER_PROMPT_TEMPLATE"
            )

    def test_manager_system_owns_root_cause_analysis(self):
        assert "ROOT CAUSE ANALYSIS (MANDATORY)" in prompts.MANAGER_SYSTEM_PROMPT, (
            "MANAGER_SYSTEM_PROMPT must own ROOT CAUSE ANALYSIS block."
        )

    def test_manager_system_owns_5_whys(self):
        assert "5 Whys" in prompts.MANAGER_SYSTEM_PROMPT, "MANAGER_SYSTEM_PROMPT must own the 5 Whys technique."

    # ------------------------------------------------------------------ #
    # RELATIONSHIP                                                         #
    # ------------------------------------------------------------------ #

    def test_relationship_user_no_persona(self):
        assert "You are a market logic validator" not in prompts.RELATIONSHIP_USER_PROMPT_TEMPLATE, (
            "Persona belongs in RELATIONSHIP_SYSTEM_PROMPT."
        )

    def test_relationship_user_no_task_instructions(self):
        assert "Your Task:\n1. Identify if the new event" not in prompts.RELATIONSHIP_USER_PROMPT_TEMPLATE, (
            "Task instructions belong in RELATIONSHIP_SYSTEM_PROMPT."
        )

    def test_relationship_user_has_required_placeholders(self):
        for placeholder in ["{new_event}", "{ancestors_text}"]:
            assert placeholder in prompts.RELATIONSHIP_USER_PROMPT_TEMPLATE, (
                f"Missing placeholder {placeholder} in RELATIONSHIP_USER_PROMPT_TEMPLATE"
            )

    def test_relationship_system_owns_task_instructions(self):
        assert "REVERSAL" in prompts.RELATIONSHIP_SYSTEM_PROMPT, (
            "RELATIONSHIP_SYSTEM_PROMPT must define relationship types (REVERSAL, RESOLUTION, UPDATE)."
        )

    # ------------------------------------------------------------------ #
    # CAUSE AND EFFECT                                                     #
    # ------------------------------------------------------------------ #

    def test_cause_effect_user_no_persona(self):
        assert "You are a market historian" not in prompts.CAUSE_AND_EFFECT_USER_PROMPT_TEMPLATE, (
            "Persona belongs in CAUSE_AND_EFFECT_SYSTEM_PROMPT."
        )

    def test_cause_effect_user_no_task_block(self):
        assert "YOUR TASK:\n1. Analyze how this event" not in prompts.CAUSE_AND_EFFECT_USER_PROMPT_TEMPLATE, (
            "Task instructions belong in CAUSE_AND_EFFECT_SYSTEM_PROMPT."
        )

    def test_cause_effect_user_has_required_placeholders(self):
        for placeholder in ["{event_name}", "{event_summary}", "{scenario_analysis}", "{market_performance}"]:
            assert placeholder in prompts.CAUSE_AND_EFFECT_USER_PROMPT_TEMPLATE, (
                f"Missing placeholder {placeholder} in CAUSE_AND_EFFECT_USER_PROMPT_TEMPLATE"
            )

    def test_cause_effect_system_owns_causal_recursion(self):
        assert "CAUSAL RECURSION" in prompts.CAUSE_AND_EFFECT_SYSTEM_PROMPT, (
            "CAUSE_AND_EFFECT_SYSTEM_PROMPT must own CAUSAL RECURSION (5 WHYS) instructions."
        )

    # ------------------------------------------------------------------ #
    # DE-ADVERTISEMENT                                                     #
    # ------------------------------------------------------------------ #

    def test_de_advertisement_user_no_persona(self):
        assert (
            "You are an expert editor for a financial news service" not in prompts.DE_ADVERTISEMENT_USER_PROMPT_TEMPLATE
        ), "Persona belongs in DE_ADVERTISEMENT_SYSTEM_PROMPT."

    def test_de_advertisement_user_no_task_instructions(self):
        assert "YOUR TASK:\n1. Identify and remove" not in prompts.DE_ADVERTISEMENT_USER_PROMPT_TEMPLATE, (
            "Task instructions belong in DE_ADVERTISEMENT_SYSTEM_PROMPT."
        )

    def test_de_advertisement_user_has_required_placeholder(self):
        assert "{content}" in prompts.DE_ADVERTISEMENT_USER_PROMPT_TEMPLATE, (
            "Missing {content} placeholder in DE_ADVERTISEMENT_USER_PROMPT_TEMPLATE"
        )

    def test_de_advertisement_system_owns_task_instructions(self):
        assert "STICK TO THE FACTS" in prompts.DE_ADVERTISEMENT_SYSTEM_PROMPT, (
            "DE_ADVERTISEMENT_SYSTEM_PROMPT must own the content filtering task instructions."
        )
