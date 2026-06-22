"""Mocked tests for the Gemini tool-calling loop."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.config import GEMINI_MODEL
from core.llm import analyze_with_provider
from core.llm.handlers.gemini import _build_gemini_tools
from core.models import DecisionObject, DecisionsResponse


def test_build_gemini_tools_includes_search_with_function_tools():
    """Google Search grounding should be added even when function tools exist."""
    function_tools = [{"name": "run_stock_screener", "parameters": {}}]

    gemini_tools = _build_gemini_tools(function_tools=function_tools, enable_google_search=True)

    assert len(gemini_tools) == 2
    assert getattr(gemini_tools[0], "function_declarations", None) is not None
    assert getattr(gemini_tools[1], "google_search", None) is not None


@pytest.mark.asyncio
async def test_gemini_tool_loop_sets_include_server_side_tool_invocations():
    """When google_search is enabled, tool_config with include_server_side_tool_invocations must be set.

    This is the TDD reproduction test for the Gemini 400 INVALID_ARGUMENT bug.
    The Gemini 3 API requires this flag to mix built-in tools with function calling.
    Without it, the API throws 400, the loop falls back to basic analysis, and
    HARD ENFORCEMENT silently discards all Gemini trade signals.

    MUST FAIL before the fix, MUST PASS after.
    """
    from core.llm.handlers import gemini

    raw_client = MagicMock()
    mock_aio = raw_client.aio
    mock_aio.models.generate_content = AsyncMock(return_value=MagicMock(candidates=[MagicMock(content=None)]))

    messages = [{"role": "user", "content": "analyse markets"}]

    mock_config = MagicMock()
    with (
        patch.object(gemini, "_generate_content_config_supports", return_value=True),
        patch("google.genai.types.GenerateContentConfig", return_value=mock_config) as mock_config_class,
    ):
        await gemini.run_tool_loop(
            raw_client=raw_client,
            model_name="gemini-3.1-flash-lite",
            messages=messages,
            override_tools=[{"type": "function", "function": {"name": "foo", "description": "stub", "parameters": {}}}],
            enable_google_search=True,
        )

    assert mock_aio.models.generate_content.called
    assert mock_config_class.called
    kwargs = mock_config_class.call_args.kwargs

    # The flag must be set nested under tool_config — this is what fixes the 400 error and Pydantic validation
    assert kwargs.get("tool_config") is not None
    assert kwargs.get("tool_config").include_server_side_tool_invocations is True
    # Note: we now always pass automatic_function_calling.disable=True in config_kwargs
    # to suppress SDK warnings. The SDK ignores AFC when tool_config is set (they're
    # mutually exclusive in effect). See test_gemini_tool_loop_always_disables_afc_when_search_enabled.
    afc = kwargs.get("automatic_function_calling")
    if afc is not None:
        assert afc.disable is True, "AFC must be disabled if set"


@pytest.mark.asyncio
async def test_gemini_config_pydantic_validation():
    """Verify that using the nested tool_config in GenerateContentConfig passes Pydantic validation."""
    from google.genai import types

    from core.llm.handlers import gemini

    raw_client = MagicMock()
    mock_aio = raw_client.aio
    mock_aio.models.generate_content = AsyncMock(return_value=MagicMock(candidates=[MagicMock(content=None)]))

    messages = [{"role": "user", "content": "analyse markets"}]

    # In this test, we do NOT mock types.GenerateContentConfig, to ensure it actually parses correctly
    with patch.object(gemini, "_generate_content_config_supports", return_value=True):
        await gemini.run_tool_loop(
            raw_client=raw_client,
            model_name="gemini-3.1-flash-lite",
            messages=messages,
            override_tools=[{"type": "function", "function": {"name": "foo", "description": "stub", "parameters": {}}}],
            enable_google_search=True,
        )

    # Ensure generate_content was called with a valid GenerateContentConfig instance
    assert mock_aio.models.generate_content.called
    config_arg = mock_aio.models.generate_content.call_args.kwargs["config"]
    assert isinstance(config_arg, types.GenerateContentConfig)
    assert config_arg.tool_config is not None
    assert config_arg.tool_config.include_server_side_tool_invocations is True


@pytest.mark.asyncio
async def test_gemini_tool_loop_afc_fallback_when_sdk_lacks_flag():
    """When the SDK does not support include_server_side_tool_invocations, fall back to AFC disable.

    This covers older google-genai SDK versions that don't have the field yet.
    """
    from core.llm.handlers import gemini

    raw_client = MagicMock()
    mock_aio = raw_client.aio
    mock_aio.models.generate_content = AsyncMock(return_value=MagicMock(candidates=[MagicMock(content=None)]))

    messages = [{"role": "user", "content": "hi"}]

    with patch.object(gemini, "_generate_content_config_supports", return_value=False):
        await gemini.run_tool_loop(
            raw_client=raw_client,
            model_name="gemini-3.1-flash-lite",
            messages=messages,
            override_tools=[{"type": "function", "function": {"name": "foo", "description": "stub", "parameters": {}}}],
            enable_google_search=True,
        )

    config = mock_aio.models.generate_content.call_args.kwargs["config"]
    # Old SDK path: AFC should be disabled as before
    assert config.automatic_function_calling is not None
    assert config.automatic_function_calling.disable is True


@pytest.mark.asyncio
async def test_gemini_tool_loop_always_disables_afc_when_search_enabled():
    """When google_search is enabled and SDK supports include_server_side_tool_invocations,
    automatic_function_calling must STILL be explicitly disabled (the SDK defaults
    AFC=true which causes noisy '[AFC] Tools at indices [0] are not compatible'
    warnings on every request).

    This is a defense-in-depth test: the existing
    test_gemini_tool_loop_sets_include_server_side_tool_invocations only checks that
    tool_config is set; it doesn't verify that AFC is also explicitly disabled,
    which is what suppresses the SDK warning.
    """
    from core.llm.handlers import gemini

    raw_client = MagicMock()
    mock_aio = raw_client.aio
    mock_aio.models.generate_content = AsyncMock(return_value=MagicMock(candidates=[MagicMock(content=None)]))

    messages = [{"role": "user", "content": "analyse markets"}]

    mock_config = MagicMock()
    with (
        patch.object(gemini, "_generate_content_config_supports", return_value=True),
        patch("google.genai.types.GenerateContentConfig", return_value=mock_config) as mock_config_class,
    ):
        await gemini.run_tool_loop(
            raw_client=raw_client,
            model_name="gemini-3.1-flash-lite",
            messages=messages,
            override_tools=[{"type": "function", "function": {"name": "foo", "description": "stub", "parameters": {}}}],
            enable_google_search=True,
        )

    kwargs = mock_config_class.call_args.kwargs

    # tool_config must still be set (per existing test)
    assert kwargs.get("tool_config") is not None
    assert kwargs.get("tool_config").include_server_side_tool_invocations is True

    # AND automatic_function_calling.disable must be True to suppress SDK warning.
    # Note: when tool_config is set, the SDK ignores AFC settings. But explicitly
    # passing AFC=disable documents intent and prevents future regressions where
    # someone removes the tool_config branch.
    afc = kwargs.get("automatic_function_calling")
    assert afc is not None, "automatic_function_calling must be explicitly set to disable"
    assert afc.disable is True, "automatic_function_calling.disable must be True"


@pytest.mark.asyncio
async def test_gemini_tool_loop_echoes_function_call_id():
    """Function call ids from Gemini 3 responses must be echoed in function_response parts.

    When include_server_side_tool_invocations is active, the Gemini 3 API assigns a unique
    id to every function_call and requires that exact id in the corresponding function_response
    for tool context circulation to work. Dropping the id silently breaks multi-turn context.

    MUST FAIL before the fix, MUST PASS after.
    """
    from unittest.mock import patch

    from google.genai import types

    from core.llm.handlers import gemini

    # Build a mock response where the function_call has an id
    mock_fc = MagicMock()
    mock_fc.name = "calculate_buy_quantity"
    mock_fc.args = {"ticker": "AAPL", "percentage": 10}
    mock_fc.id = "fc-abc-123"  # Gemini 3 assigns this

    mock_part_with_call = MagicMock()
    mock_part_with_call.function_call = mock_fc

    mock_content_with_call = MagicMock()
    mock_content_with_call.parts = [mock_part_with_call]

    mock_candidate_with_call = MagicMock()
    mock_candidate_with_call.content = mock_content_with_call

    # Second response: no tool call, ends loop
    mock_part_final = MagicMock()
    mock_part_final.function_call = None
    mock_content_final = MagicMock()
    mock_content_final.parts = [mock_part_final]
    mock_candidate_final = MagicMock()
    mock_candidate_final.content = mock_content_final

    raw_client = MagicMock()
    raw_client.aio.models.generate_content = AsyncMock(
        side_effect=[
            MagicMock(candidates=[mock_candidate_with_call]),
            MagicMock(candidates=[mock_candidate_final]),
        ]
    )

    messages = [{"role": "user", "content": "buy something"}]

    with patch("core.llm.handlers.base.execute_tool", AsyncMock(return_value="result")):
        await gemini.run_tool_loop(
            raw_client=raw_client,
            model_name="gemini-3.1-flash-lite",
            messages=messages,
        )

    # Let's find the tool response message in history
    tool_resp_msg = None
    for m in messages:
        if (
            isinstance(m, types.Content)
            and m.role == "user"
            and any(getattr(p, "function_response", None) for p in m.parts)
        ):
            tool_resp_msg = m
            break

    assert tool_resp_msg is not None
    part = next(p for p in tool_resp_msg.parts if getattr(p, "function_response", None))
    # The id from the function_call must be echoed in the function_response
    assert part.function_response.id == "fc-abc-123"


@pytest.mark.asyncio
async def test_analyze_with_provider_gemini_tool_loop():
    """Test that analyze_with_provider handles a Gemini tool call loop."""

    mock_chunks = [{"source_id": "src_g1", "content": "Check Apple price"}]

    # Mock Gemini Client and candidates
    mock_client = MagicMock()
    mock_raw_client = mock_client.client

    # 1. First response: Function Call
    mock_part = MagicMock()
    mock_part.text = "I'll check the price."
    mock_part.function_call.name = "get_stock_quote"
    mock_part.function_call.args = {"ticker": "AAPL"}

    mock_content = MagicMock()
    mock_content.parts = [mock_part]

    mock_candidate = MagicMock()
    mock_candidate.content = mock_content

    mock_resp_1 = MagicMock()
    mock_resp_1.candidates = [mock_candidate]

    # 2. Second response: No Function Call (break loop)
    mock_part_2 = MagicMock()
    mock_part_2.text = "Done."
    mock_part_2.function_call = None

    mock_content_2 = MagicMock()
    mock_content_2.parts = [mock_part_2]

    mock_candidate_2 = MagicMock()
    mock_candidate_2.content = mock_content_2

    mock_resp_2 = MagicMock()
    mock_resp_2.candidates = [mock_candidate_2]

    # Mock final decision
    mock_final_decision = DecisionsResponse(
        decisions=[
            DecisionObject(
                signal="HOLD", confidence=95, reasoning="Price is good.", ticker="AAPL", source_id="src_g1", price=150.0
            )
        ]
    )

    with (
        patch("core.llm.tools.MarketDataManager") as mock_manager_cls,
        patch("core.llm.analysis.clients.CLIENT_FACTORIES") as mock_factories,
        patch("autoresearch.prompt_store.get_active_prompt", AsyncMock(return_value="FAKE_ACTIVE_PROMPT")),
    ):
        mock_manager = mock_manager_cls.return_value
        mock_manager.get_quote = AsyncMock(
            return_value=MagicMock(ticker="AAPL", price=150.0, market_cap=2.5e12, exists=True)
        )

        mock_factories.get.return_value = lambda: mock_client

        # Configure raw client for async generate_content
        # In analysis.py we use raw_client.aio.models.generate_content
        mock_aio = mock_raw_client.aio
        mock_aio.models.generate_content = AsyncMock(side_effect=[mock_resp_1, mock_resp_2])

        # Mock final instructor extraction
        mock_client.chat.completions.create = AsyncMock(return_value=[mock_final_decision])

        # Execute
        result = await analyze_with_provider("gemini", GEMINI_MODEL, mock_chunks)

        # Assertions
        assert len(result.decisions) == 1
        assert result.decisions[0].ticker == "AAPL"
        assert mock_manager.get_quote.call_count == 1
        assert mock_aio.models.generate_content.call_count == 2
