"""Tests for second-step verification logic."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from core.models import DecisionObject, VerificationResult
from core.llm.verification import verify_trading_decision

@pytest.mark.asyncio
async def test_verify_trading_decision_approved():
    """Test that verifier can approve a trade."""
    decision = DecisionObject(
        signal="BUY",
        confidence=80,
        reasoning="Strong earnings growth",
        ticker="NVDA",
        source_id="src_1",
        price=120.0
    )
    
    mock_result = VerificationResult(
        status="APPROVED",
        verification_reasoning="Consensus is strong and news is not fully priced in.",
        confidence_score=90
    )
    
    # Mock the LLM client and Instructor extraction
    with patch("core.llm.clients.CLIENT_FACTORIES") as mock_factories:
        mock_factory = MagicMock()
        mock_client = MagicMock()
        
        # Instructor client mock
        mock_instructor_client = MagicMock()
        mock_completions = MagicMock()
        mock_completions.create = AsyncMock(return_value=[mock_result])
        mock_instructor_client.completions = mock_completions
        mock_client.chat = mock_instructor_client
        
        mock_client.client = MagicMock() # For the tool loop
        
        # Mock run_tool_loop to simulate mandatory tool calls
        async def mock_run_tool_loop(client, model, messages, *args, **kwargs):
            messages.append({"role": "assistant", "tool_calls": [{"id": "c1", "function": {"name": "get_stock_quote", "arguments": "{}"}}]})
            messages.append({"role": "assistant", "tool_calls": [{"id": "c2", "function": {"name": "calculate_buy_quantity", "arguments": "{}"}}]})

        with patch("core.llm.verification.openai.run_tool_loop", side_effect=mock_run_tool_loop):
            mock_factory.return_value = mock_client
            mock_factories.get.return_value = mock_factory

            with patch("core.llm.clients.close_client", new_callable=AsyncMock), \
                 patch("core.llm.verification.log_reasoning_trace", new_callable=AsyncMock):
                result, log_id = await verify_trading_decision(
                    decision=decision,
                    portfolio_context="Cash: $10,000",
                    aggregated_context="Historical context"
                )
            
    assert result.status == "APPROVED"
    assert result.confidence_score == 90


@pytest.mark.asyncio
async def test_verify_trading_decision_anchors_to_persisted_decision_id():
    """Test that verification logs use the persisted decision id anchor."""
    decision = DecisionObject(
        signal="BUY",
        confidence=80,
        reasoning="Strong earnings growth",
        ticker="NVDA",
        source_id="src_1",
        price=120.0
    )

    mock_result = VerificationResult(
        status="APPROVED",
        verification_reasoning="Consensus is strong and news is not fully priced in.",
        confidence_score=90
    )

    with patch("core.llm.clients.CLIENT_FACTORIES") as mock_factories:
        mock_factory = MagicMock()
        mock_client = MagicMock()

        mock_instructor_client = MagicMock()
        mock_completions = MagicMock()
        mock_completions.create = AsyncMock(return_value=[mock_result])
        mock_instructor_client.completions = mock_completions
        mock_client.chat = mock_instructor_client
        mock_client.client = MagicMock()

        async def mock_run_tool_loop(client, model, messages, *args, **kwargs):
            messages.append({"role": "assistant", "tool_calls": [{"id": "c1", "function": {"name": "get_stock_quote", "arguments": "{}"}}]})
            messages.append({"role": "assistant", "tool_calls": [{"id": "c2", "function": {"name": "calculate_buy_quantity", "arguments": "{}"}}]})

        with patch("core.llm.verification.openai.run_tool_loop", side_effect=mock_run_tool_loop):
            mock_factory.return_value = mock_client
            mock_factories.get.return_value = mock_factory

            with patch("core.llm.clients.close_client", new_callable=AsyncMock), \
                 patch("core.llm.verification.log_reasoning_trace", new_callable=AsyncMock) as mock_log:
                result, log_id = await verify_trading_decision(
                    decision=decision,
                    portfolio_context="Cash: $10,000",
                    aggregated_context="Historical context",
                    decision_id="decision-db-123"
                )

    assert result.status == "APPROVED"
    assert mock_log.call_args.kwargs["metadata"]["decision_id"] == "decision-db-123"
    assert "decision_id" not in mock_log.call_args.kwargs["metadata"] or mock_log.call_args.kwargs["metadata"]["decision_id"] != decision.provisional_id

@pytest.mark.asyncio
async def test_verify_trading_decision_rejected():
    """Test that verifier can reject a trade."""
    decision = DecisionObject(
        signal="BUY",
        confidence=80,
        reasoning="Hype cycle",
        ticker="SPEC",
        source_id="src_1",
        price=10.0
    )
    
    mock_result = VerificationResult(
        status="REJECTED_VERIFICATION",
        verification_reasoning="Too much volatility, already spiked.",
        confidence_score=95
    )
    
    with patch("core.llm.clients.CLIENT_FACTORIES") as mock_factories:
        mock_factory = MagicMock()
        mock_client = MagicMock()
        
        mock_instructor_client = MagicMock()
        mock_completions = MagicMock()
        mock_completions.create = AsyncMock(return_value=[mock_result])
        mock_instructor_client.completions = mock_completions
        mock_client.chat = mock_instructor_client
        
        mock_client.client = MagicMock()
        
        mock_gen_resp = MagicMock()
        mock_gen_resp.candidates = [MagicMock(content=MagicMock(parts=[]))]
        mock_client.client.aio.models.generate_content = AsyncMock(return_value=mock_gen_resp)
        
        mock_factory.return_value = mock_client
        mock_factories.get.return_value = mock_factory
        
        with patch("core.llm.clients.close_client", new_callable=AsyncMock), \
             patch("apps.engine.core.llm.verification.log_reasoning_trace", new_callable=AsyncMock):
            result, log_id = await verify_trading_decision(
                decision=decision,
                portfolio_context="Cash: $10,000",
                aggregated_context="Historical context"
            )
            
    assert result.status == "REJECTED_VERIFICATION"
    assert "Too much volatility" in result.verification_reasoning

@pytest.mark.asyncio
async def test_verify_trading_decision_anthropic():
    """Test that verifier works with Anthropic provider."""
    decision = DecisionObject(
        signal="SELL",
        confidence=70,
        reasoning="Take profits",
        ticker="AAPL",
        source_id="src_anth",
        model_provider="anthropic",
        model_name="claude-3-5-sonnet"
    )
    
    mock_result = VerificationResult(
        status="APPROVED",
        verification_reasoning="Reasonable profit taking.",
        confidence_score=100
    )
    
    with patch("core.llm.clients.CLIENT_FACTORIES") as mock_factories:
        mock_factory = MagicMock()
        mock_client = MagicMock()
        
        mock_instructor_client = MagicMock()
        mock_completions = MagicMock()
        mock_completions.create = AsyncMock(return_value=[mock_result])
        mock_instructor_client.completions = mock_completions
        mock_client.chat = mock_instructor_client
        mock_client.client = MagicMock() # Mock raw Anthropic client
        
        # Mock run_tool_loop for Anthropic (to avoid actually calling Anthropic)
        async def mock_loop_fn(client, model, messages, *args, **kwargs):
            messages.append({"role": "assistant", "content": [{"type": "tool_use", "id": "t1", "name": "get_stock_quote", "input": {}}]})
            messages.append({"role": "assistant", "content": [{"type": "tool_use", "id": "t2", "name": "calculate_sell_quantity", "input": {}}]})

        with patch("core.llm.verification.anthropic.run_tool_loop", side_effect=mock_loop_fn) as mock_loop:
            mock_factory.return_value = mock_client
            mock_factories.get.return_value = mock_factory
            
            with patch("core.llm.clients.close_client", new_callable=AsyncMock), \
                 patch("core.llm.verification.log_reasoning_trace", new_callable=AsyncMock) as mock_log:
                result, log_id = await verify_trading_decision(
                    decision=decision,
                    portfolio_context="Positions: AAPL (100)",
                    aggregated_context="Historical context"
                )
                
    assert result.status == "APPROVED"
    assert mock_loop.called
    prompt = mock_log.call_args.kwargs["prompt"]
    assert any(isinstance(msg, dict) and isinstance(msg.get("content"), list) for msg in prompt)

@pytest.mark.asyncio
async def test_verify_trading_decision_gemini():
    """Test that verifier works with Gemini provider."""
    decision = DecisionObject(
        signal="BUY",
        confidence=90,
        reasoning="Strong technical breakout",
        ticker="TSLA",
        source_id="src_gem",
        model_provider="gemini",
        model_name="gemini-3-flash-preview"
    )
    
    mock_result = VerificationResult(
        status="APPROVED",
        verification_reasoning="Technical setup is valid.",
        confidence_score=90
    )
    
    with patch("core.llm.clients.CLIENT_FACTORIES") as mock_factories:
        mock_factory = MagicMock()
        mock_client = MagicMock()
        
        mock_instructor_client = MagicMock()
        mock_completions = MagicMock()
        mock_completions.create = AsyncMock(return_value=[mock_result])
        mock_instructor_client.completions = mock_completions
        mock_client.chat = mock_instructor_client
        mock_client.client = MagicMock() # Mock raw Gemini client (using genai SDK)
        
        # Mock run_tool_loop for Gemini
        async def mock_loop_fn(client, model, messages, *args, **kwargs):
            from google.genai import types
            messages.append(types.Content(role="model", parts=[types.Part.from_function_call(name="get_stock_quote", args={})]))
            messages.append(types.Content(role="model", parts=[types.Part.from_function_call(name="calculate_buy_quantity", args={})]))

        with patch("core.llm.verification.gemini.run_tool_loop", side_effect=mock_loop_fn) as mock_loop:
            mock_factory.return_value = mock_client
            mock_factories.get.return_value = mock_factory
            
            with patch("core.llm.clients.close_client", new_callable=AsyncMock), \
                 patch("core.llm.verification.log_reasoning_trace", new_callable=AsyncMock) as mock_log:
                result, log_id = await verify_trading_decision(
                    decision=decision,
                    portfolio_context="Cash: $10,000",
                    aggregated_context="Historical context"
                )
                
    assert result.status == "APPROVED"
    assert mock_loop.called
    prompt = mock_log.call_args.kwargs["prompt"]
    assert any(hasattr(msg, "parts") for msg in prompt)

@pytest.mark.asyncio
async def test_verify_trading_decision_sync_resilience():
    """Test that verifier handles synchronous responses (e.g. from Gemini)."""
    decision = DecisionObject(
        signal="BUY",
        confidence=90,
        reasoning="Technical breakout",
        ticker="RESIL",
        source_id="src_resil",
        model_provider="gemini",
        model_name="gemini-3-flash-preview"
    )
    
    mock_result = VerificationResult(
        status="APPROVED",
        verification_reasoning="Handled sync response correctly.",
        confidence_score=95
    )
    
    with patch("core.llm.clients.CLIENT_FACTORIES") as mock_factories:
        mock_factory = MagicMock()
        mock_client = MagicMock()
        
        # Simulate a SYNCHRONOUS response (no await/asyncio.iscoroutine)
        mock_instructor_client = MagicMock()
        mock_completions = MagicMock()
        mock_completions.create.return_value = [mock_result] # NOT an AsyncMock
        mock_instructor_client.completions = mock_completions
        mock_client.chat = mock_instructor_client
        mock_client.client = MagicMock()
        
        async def mock_loop_fn(client, model, messages, *args, **kwargs):
            from google.genai import types
            messages.append(types.Content(role="model", parts=[types.Part.from_function_call(name="get_stock_quote", args={})]))
            messages.append(types.Content(role="model", parts=[types.Part.from_function_call(name="calculate_buy_quantity", args={})]))

        with patch("core.llm.verification.gemini.run_tool_loop", side_effect=mock_loop_fn):
            mock_factory.return_value = mock_client
            mock_factories.get.return_value = mock_factory
            
            with patch("core.llm.clients.close_client", new_callable=AsyncMock), \
                 patch("core.llm.verification.log_reasoning_trace", new_callable=AsyncMock):
                result, log_id = await verify_trading_decision(
                    decision=decision,
                    portfolio_context="Cash: $10,000",
                    aggregated_context="Historical context"
                )
                
    assert result.status == "APPROVED"
    assert result.confidence_score == 95
    assert result.verification_reasoning == "Handled sync response correctly."
