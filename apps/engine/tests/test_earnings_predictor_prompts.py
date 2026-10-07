"""Hermetic unit tests for earnings predictor prompts, schemas, and Jev criteria."""

from core.llm.earnings_predictor_prompts import (
    EARNINGS_JEV_DEFAULT_CRITERIA,
    EARNINGS_JEV_QUESTION_KEY,
    EARNINGS_JEV_QUESTION_TYPE,
    EarningsPredictionOutput,
    format_earnings_jev_criteria,
    parse_earnings_jev_criteria,
)


def test_earnings_prediction_output_schema():
    """Verify validation of EarningsPredictionOutput."""
    out = EarningsPredictionOutput(
        predicted_direction="UP",
        confidence=82.5,
        expected_return_pct=2.4,
        rationale="Strong SUE beat with clean cash accruals.",
        catalysts=["SUE +3.2", "Raised guidance"],
    )
    assert out.predicted_direction == "UP"
    assert out.confidence == 82.5
    assert out.expected_return_pct == 2.4
    assert len(out.catalysts) == 2


def test_earnings_jev_criteria_formatting_and_parsing():
    """Verify Jev criteria serialization and fallback parsing."""
    assert EARNINGS_JEV_QUESTION_KEY == "day1_earnings_direction"
    assert EARNINGS_JEV_QUESTION_TYPE == "choice"

    formatted = format_earnings_jev_criteria(EARNINGS_JEV_DEFAULT_CRITERIA)
    assert "Continuation" in formatted
    assert "Fade the News" in formatted

    parsed = parse_earnings_jev_criteria(formatted)
    assert parsed["UP"] == EARNINGS_JEV_DEFAULT_CRITERIA["UP"]
    assert parsed["DOWN"] == EARNINGS_JEV_DEFAULT_CRITERIA["DOWN"]

    # Test fallback
    fallback = parse_earnings_jev_criteria("invalid json")
    assert fallback == EARNINGS_JEV_DEFAULT_CRITERIA

    fallback_none = parse_earnings_jev_criteria(None)
    assert fallback_none == EARNINGS_JEV_DEFAULT_CRITERIA
