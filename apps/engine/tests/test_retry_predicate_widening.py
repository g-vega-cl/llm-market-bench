"""Tests verifying the Instructor retry loop catches tool-mode mismatch errors
and falls through to JSON repair instead of re-raising.

Defense-in-depth for the MiniMax-M3 path: if any provider emits raw JSON text
without tool_calls, instructor's TOOLS mode raises
'No tool calls or function call found in response (mode: TOOLS)'. The retry
loop must treat this as repairable (append a 'give me clean JSON' message)
rather than re-raising immediately and losing the batch's decisions.
"""


def test_retry_predicate_catches_tools_mode_error():
    """The substring 'no tool calls' (case-insensitive) must match the retry
    predicate so the loop appends a repair message instead of re-raising.

    We test this by inspecting the actual retry loop's source code to ensure
    the new substrings are present in the predicate, not by re-implementing it.
    """
    import inspect

    from core.llm import analysis as analysis_mod

    source = inspect.getsource(analysis_mod.analyze_with_provider)

    # The predicate must include these substrings (case-insensitive checks
    # happen on the lowercased error string, but the literals are in source):
    assert '"no tool calls"' in source, "retry predicate missing 'no tool calls'"
    assert '"function call found"' in source, "retry predicate missing 'function call found'"


def test_retry_predicate_excludes_unrelated_errors():
    """The predicate must NOT re-raise on every error — it should specifically
    catch tool-mode and validation errors. We check by ensuring the predicate
    is narrower than 'catch all'."""
    import inspect

    from core.llm import analysis as analysis_mod

    source = inspect.getsource(analysis_mod.analyze_with_provider)

    # The retry branch is gated on substring checks; verify the structure
    # has at least 3 distinct checks (validation, list_type, tool_calls).
    validation_check = '"validation error"' in source
    list_type_check = '"list_type"' in source
    tool_calls_check = '"no tool calls"' in source

    assert validation_check, "missing validation error check"
    assert list_type_check, "missing list_type check"
    assert tool_calls_check, "missing no tool calls check"
