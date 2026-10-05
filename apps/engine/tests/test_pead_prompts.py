"""Unit tests for PEAD prompt contracts and Jev criteria formatting/parsing."""

from core.llm.pead_prompts import (
    PEAD_DEFAULT_CRITERIA,
    PEAD_JEV_INSTRUCTIONS,
    PEAD_JEV_QUESTION_KEY,
    PEAD_JEV_QUESTION_TYPE,
    format_pead_jev_criteria,
    parse_pead_jev_criteria,
)


def test_pead_frozen_constants():
    """Verify constant values for PEAD Jev decisions question."""
    assert PEAD_JEV_QUESTION_KEY == "pead_admission"
    assert PEAD_JEV_QUESTION_TYPE == "choice"
    assert "QUALIFIED" in PEAD_DEFAULT_CRITERIA
    assert "DISQUALIFIED" in PEAD_DEFAULT_CRITERIA
    assert "Post-Earnings Announcement Drift" in PEAD_JEV_INSTRUCTIONS


def test_format_and_parse_pead_jev_criteria():
    """Verify serialization and deserialization of PEAD Jev criteria."""
    serialized = format_pead_jev_criteria(PEAD_DEFAULT_CRITERIA)
    assert '"QUALIFIED":' in serialized
    assert '"DISQUALIFIED":' in serialized

    parsed = parse_pead_jev_criteria(serialized)
    assert parsed["QUALIFIED"] == PEAD_DEFAULT_CRITERIA["QUALIFIED"]
    assert parsed["DISQUALIFIED"] == PEAD_DEFAULT_CRITERIA["DISQUALIFIED"]


def test_parse_pead_jev_criteria_fallback():
    """Verify fallback to defaults on invalid JSON or missing keys."""
    fallback = parse_pead_jev_criteria("not valid json")
    assert fallback["QUALIFIED"] == PEAD_DEFAULT_CRITERIA["QUALIFIED"]
    assert fallback["DISQUALIFIED"] == PEAD_DEFAULT_CRITERIA["DISQUALIFIED"]

    fallback_partial = parse_pead_jev_criteria('{"QUALIFIED": "Only qualified"}')
    assert fallback_partial["QUALIFIED"] == PEAD_DEFAULT_CRITERIA["QUALIFIED"]
