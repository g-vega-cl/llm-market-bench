"""TDD reproduction test: macro extraction pass must log task_type='MACRO_EXTRACTION',
not 'INGESTION'. Without the fix, both passes log 'INGESTION', making it impossible
to filter Global Analysis traces from trading-decision traces in the Reasoning UI.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_macro_pass_logs_macro_extraction_task_type():
    """Macro extraction pass (prompt_type='macro') must log task_type='MACRO_EXTRACTION'."""
    from core.llm.analysis import analyze_with_provider
    from core.models import MacroEventsResponse

    mock_resp = MagicMock(spec=MacroEventsResponse)
    mock_resp.macro_events = []
    mock_resp.decisions = []

    mock_instructor_client = MagicMock()
    mock_instructor_client.chat.completions.create = AsyncMock(return_value=mock_resp)

    captured_task_types: list[str] = []

    async def capture_task_type(task_type, **kwargs):
        captured_task_types.append(task_type)

    mock_factory = MagicMock(return_value=mock_instructor_client)

    with patch.dict("core.llm.clients.CLIENT_FACTORIES", {"openai": mock_factory}):
        with patch("core.llm.analysis.log_reasoning_trace", side_effect=capture_task_type):
            with patch("core.llm.handlers.openai.run_tool_loop", new=AsyncMock()):
                with patch(
                    "core.llm.prompt_factory.PromptFactory.build_macro_analysis_messages",
                    return_value=[{"role": "system", "content": "macro sys"}, {"role": "user", "content": "macro usr"}],
                ):
                    await analyze_with_provider(
                        provider="openai",
                        model_name="gpt-5.4-nano",
                        chunks=[{"source_id": "s1", "content": "News."}],
                        prompt_type="macro",
                        response_model=MacroEventsResponse,
                    )

    assert len(captured_task_types) == 1, f"Expected 1 log call, got {len(captured_task_types)}"
    assert captured_task_types[0] == "MACRO_EXTRACTION", (
        f"Macro pass must log task_type='MACRO_EXTRACTION', got '{captured_task_types[0]}'"
    )


@pytest.mark.asyncio
async def test_trading_decisions_pass_still_logs_ingestion_task_type():
    """Trading decisions pass (prompt_type='analysis') must still log task_type='INGESTION'."""
    from core.llm.analysis import analyze_with_provider

    mock_resp = MagicMock()
    mock_resp.decisions = []
    mock_resp.macro_events = []

    mock_instructor_client = MagicMock()
    mock_instructor_client.chat.completions.create = AsyncMock(return_value=mock_resp)

    captured_task_types: list[str] = []

    async def capture_task_type(task_type, **kwargs):
        captured_task_types.append(task_type)

    mock_factory = MagicMock(return_value=mock_instructor_client)

    with patch.dict("core.llm.clients.CLIENT_FACTORIES", {"openai": mock_factory}):
        with patch("core.llm.analysis.log_reasoning_trace", side_effect=capture_task_type):
            with patch("core.llm.handlers.openai.run_tool_loop", new=AsyncMock()):
                with patch(
                    "core.llm.prompt_factory.PromptFactory.build_analysis_messages",
                    new=AsyncMock(
                        return_value=[
                            {"role": "system", "content": "analysis sys"},
                            {"role": "user", "content": "analysis usr"},
                        ]
                    ),
                ):
                    await analyze_with_provider(
                        provider="openai",
                        model_name="gpt-5.4-nano",
                        chunks=[{"source_id": "s1", "content": "News."}],
                        prompt_type="analysis",
                    )

    assert len(captured_task_types) == 1, f"Expected 1 log call, got {len(captured_task_types)}"
    assert captured_task_types[0] == "INGESTION", (
        f"Trading decisions pass must log task_type='INGESTION', got '{captured_task_types[0]}'"
    )
