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
