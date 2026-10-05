"""Unit tests for Max Pain Jev prompt contracts and criteria parsing.

Hermetic tests with zero live network calls.
"""

from core.llm.max_pain_prompts import (
    MAX_PAIN_DEFAULT_CRITERIA,
    MAX_PAIN_JEV_QUESTION_KEY,
    MAX_PAIN_JEV_QUESTION_TYPE,
    format_max_pain_jev_criteria,
    parse_max_pain_jev_criteria,
)


def test_max_pain_jev_question_constants():
    assert MAX_PAIN_JEV_QUESTION_KEY == "max_pain_admission"
    assert MAX_PAIN_JEV_QUESTION_TYPE == "choice"
    assert "QUALIFIED" in MAX_PAIN_DEFAULT_CRITERIA
    assert "DISQUALIFIED" in MAX_PAIN_DEFAULT_CRITERIA


def test_format_and_parse_max_pain_jev_criteria():
    custom = {
        "QUALIFIED": "Custom strong pinning criteria",
        "DISQUALIFIED": "Custom unpinning breakout criteria",
    }
    raw_json = format_max_pain_jev_criteria(custom)
    parsed = parse_max_pain_jev_criteria(raw_json)
    assert parsed["QUALIFIED"] == "Custom strong pinning criteria"
    assert parsed["DISQUALIFIED"] == "Custom unpinning breakout criteria"


def test_parse_max_pain_jev_criteria_fallback():
    assert parse_max_pain_jev_criteria(None) == MAX_PAIN_DEFAULT_CRITERIA
    assert parse_max_pain_jev_criteria("invalid json") == MAX_PAIN_DEFAULT_CRITERIA
    assert parse_max_pain_jev_criteria('{"incomplete": true}') == MAX_PAIN_DEFAULT_CRITERIA
