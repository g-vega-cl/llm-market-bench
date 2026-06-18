"""Tests to reproduce and verify the MiniMax JSON repair scoping bug."""

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from core.llm.analysis import _try_parse_decisions_response


def test_try_parse_escaped_json_string_repair():
    """Test that _try_parse_decisions_response successfully repairs and parses double-escaped JSON strings."""
    # This string requires _repair_json_string to unescape quotes and newlines
    escaped_data = '"{\\"decisions\\": [], \\"macro_events\\": []}"'

    result = _try_parse_decisions_response(escaped_data)
    assert result is not None
    assert len(result.decisions) == 0
    assert len(result.macro_events) == 0


def test_try_parse_json_string_with_raw_newlines():
    """Test that _try_parse_decisions_response handles raw unescaped newlines in JSON string values using strict=False."""
    raw_data_with_newlines = '{"decisions": [{"signal": "BUY", "confidence": 88, "reasoning": "Line 1\nLine 2", "ticker": "DELL", "catalyst_type": "EARNINGS", "catalyst_duration": "SHORT_TERM", "source_id": "s1", "allocation_percentage": 10}], "macro_events": []}'
    result = _try_parse_decisions_response(raw_data_with_newlines)
    assert result is not None
    assert len(result.decisions) == 1
    assert result.decisions[0].reasoning == "Line 1\nLine 2"


def test_try_parse_double_escaped_json_string_with_newlines():
    """Test that double-escaped JSON containing escaped newlines is repaired and successfully parsed."""
    escaped_data = '"{\\"decisions\\": [{\\"signal\\": \\"BUY\\", \\"confidence\\": 88, \\"reasoning\\": \\"Line 1\\\\nLine 2\\", \\"ticker\\": \\"DELL\\", \\"catalyst_type\\": \\"EARNINGS\\", \\"catalyst_duration\\": \\"SHORT_TERM\\", \\"source_id\\": \\"s1\\", \\"allocation_percentage\\": 10}], \\"macro_events\\": []}"'
    result = _try_parse_decisions_response(escaped_data)
    assert result is not None
    assert len(result.decisions) == 1
    assert result.decisions[0].reasoning == "Line 1\nLine 2"


def test_try_parse_json_with_trailing_backslash_escape():
    """Test that a JSON string with a trailing backslash escaping the closing quote is repaired and successfully parsed."""
    raw_data = '{"decisions": [{"signal": "HOLD", "confidence": 75, "reasoning": "thesis is intact despite -7.3% pullback from cost basis\\", "ticker": "GLW", "catalyst_type": "TECHNICAL", "catalyst_duration": "MEDIUM_TERM", "source_id": "s1", "allocation_percentage": 0, "is_priced_in": false, "is_priced_in_reasoning": "", "profit_potential_reasoning": "", "strategy_reasoning": "", "advance_planning_notes": "", "buy_tool_called": false, "sell_tool_called": false, "quantity": 0}], "macro_events": []}'
    result = _try_parse_decisions_response(raw_data)
    assert result is not None
    assert len(result.decisions) == 1
    assert "pullback from cost basis" in result.decisions[0].reasoning
