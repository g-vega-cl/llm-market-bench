"""Unit tests for Modular Prompt Blocks and Tool-First Agency."""

from autoresearch.prompt_blocks import AVAILABLE_PROMPT_BLOCKS, render_prompt_blocks
from core.llm.daily_predictor_prompts import (
    DAILY_PREDICTOR_CONSTRAINTS_FOOTER,
    DAILY_PREDICTOR_CONSTRAINTS_HEADER,
    DAILY_PREDICTOR_PROMPT,
)


def test_new_modular_prompt_blocks_registered():
    """Verify that new quantitative reasoning blocks are registered in AVAILABLE_PROMPT_BLOCKS."""
    expected_blocks = [
        "market_regime_classification",
        "option_pin_gamma_levels",
        "anti_pessimism_prior_conditioning",
        "dialectical_thesis_deliberation",
        "regime_gated_confidence_calibration",
    ]
    for block_id in expected_blocks:
        assert block_id in AVAILABLE_PROMPT_BLOCKS, f"Missing registered block: {block_id}"
        block = AVAILABLE_PROMPT_BLOCKS[block_id]
        assert "title" in block and block["title"]
        assert "content" in block and block["content"]


def test_render_prompt_blocks_with_new_blocks():
    """Verify that render_prompt_blocks formats the new blocks into markdown."""
    rendered = render_prompt_blocks(
        [
            "market_regime_classification",
            "option_pin_gamma_levels",
            "anti_pessimism_prior_conditioning",
            "dialectical_thesis_deliberation",
            "regime_gated_confidence_calibration",
        ]
    )
    assert "=== MODULAR TRADING DISCIPLINE & REASONING BLOCKS ===" in rendered
    assert "MARKET REGIME CLASSIFICATION" in rendered
    assert "OPTION PINNING & DEALER GAMMA" in rendered or "GAMMA" in rendered
    assert "ANTI-PESSIMISM" in rendered or "BASE-RATE PRIOR" in rendered
    assert "DIALECTICAL THESIS DELIBERATION" in rendered
    assert "REGIME-GATED CONFIDENCE CALIBRATION" in rendered


def test_modular_blocks_not_baked_into_frozen_baseline():
    """Verify Principle 8: Modular prompt blocks must NOT be hardcoded into frozen baseline prompts."""
    for forbidden in [
        "LOW_VOL_PIN",
        "TREND_EXPANSION",
        "dealer gamma",
        "Max Pain strike gravitation",
        "historically close green ~54%",
    ]:
        assert forbidden.lower() not in DAILY_PREDICTOR_CONSTRAINTS_HEADER.lower()
        assert forbidden.lower() not in DAILY_PREDICTOR_CONSTRAINTS_FOOTER.lower()
        assert forbidden.lower() not in DAILY_PREDICTOR_PROMPT.lower()
