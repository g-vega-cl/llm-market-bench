import pytest
import asyncio
from unittest.mock import MagicMock, patch
from apps.engine.core.models import DecisionObject, VerificationResult
from apps.engine.core.llm.verification import verify_trading_decision

@pytest.fixture
def mock_client():
    mock_client = MagicMock()
    # Deeply mock the CLIENT_FACTORIES dictionary and its get method
    mock_factory = MagicMock(return_value=mock_client)

    with patch("apps.engine.core.llm.verification.clients.CLIENT_FACTORIES", {"openai": mock_factory}), \
         patch("apps.engine.core.llm.clients.close_client", return_value=None), \
         patch("apps.engine.core.llm.verification.log_reasoning_trace", return_value=None):
        yield mock_client

@pytest.mark.asyncio
async def test_verification_rejects_if_missing_tools(mock_client):
    """Ensures verification is rejected if mandatory tools were not called."""
    # Setup: BUY decision
    decision = DecisionObject(
        signal="BUY",
        confidence=90,
        reasoning="Good stuff",
        ticker="AAPL",
        source_id="news-123",
        model_provider="openai",
        model_name="gpt-4o"
    )

    # Mock tool loop to do nothing (no tools called)
    with patch("apps.engine.core.llm.handlers.openai.run_tool_loop", return_value=None):
        # Mock final response as APPROVED (but without tools)
        mock_client.chat.completions.create.return_value = [
            VerificationResult(status="APPROVED", verification_reasoning="Looks good to me!", confidence_score=100)
        ]

        result, log_id = await verify_trading_decision(
            decision=decision,
            portfolio_context="Empty",
            aggregated_context="Empty"
        )

        # Should be REJECTED despite the LLM approving it, because no tools were called
        assert result.status == "REJECTED_VERIFICATION"
        assert "missing mandatory tool calls" in result.verification_reasoning

@pytest.mark.asyncio
async def test_verification_approves_if_tools_called(mock_client):
    """Ensures verification is approved if mandatory tools were called."""
    decision = DecisionObject(
        signal="BUY",
        confidence=90,
        reasoning="Good stuff",
        ticker="AAPL",
        source_id="news-123",
        model_provider="openai",
        model_name="gpt-4o"
    )

    # Simulate tool calls in instructor_messages
    async def mock_run_tool_loop(client, model, messages, *args, **kwargs):
        messages.append({"role": "assistant", "tool_calls": [{"id": "call_1", "function": {"name": "get_stock_quote"}}]})
        messages.append({"role": "tool", "tool_call_id": "call_1", "content": "Price: 150"})
        messages.append({"role": "assistant", "tool_calls": [{"id": "call_2", "function": {"name": "calculate_buy_quantity"}}]})
        messages.append({"role": "tool", "tool_call_id": "call_2", "content": "Qty: 10"})

    with patch("apps.engine.core.llm.verification.openai.run_tool_loop", side_effect=mock_run_tool_loop):
        mock_client.chat.completions.create.return_value = [
            VerificationResult(status="APPROVED", verification_reasoning="Tools were used.", confidence_score=100)
        ]

        result, log_id = await verify_trading_decision(
            decision=decision,
            portfolio_context="Empty",
            aggregated_context="Empty"
        )

        assert result.status == "APPROVED"
