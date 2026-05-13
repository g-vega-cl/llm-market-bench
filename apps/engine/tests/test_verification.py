"""Tests for second-step verification logic."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.config import ANTHROPIC_MODEL, GEMINI_MODEL
from core.llm.verification import verify_trading_decision
from core.models import DecisionObject, VerificationResult


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
        
        # Mock generate_content for the tool loop
        mock_gen_resp = MagicMock()
        mock_gen_resp.candidates = [MagicMock(content=MagicMock(parts=[]))] # No tool calls
        mock_client.client.aio.models.generate_content = AsyncMock(return_value=mock_gen_resp)
        
        mock_factory.return_value = mock_client
        mock_factories.get.return_value = mock_factory
        
        with patch("core.llm.clients.close_client", new_callable=AsyncMock):
            result = await verify_trading_decision(
                decision=decision,
                portfolio_context="Cash: $10,000",
                aggregated_context="Historical context"
            )
            
    assert result.status == "APPROVED"
    assert result.confidence_score == 90

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
        
        with patch("core.llm.clients.close_client", new_callable=AsyncMock):
            result = await verify_trading_decision(
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
        model_name=ANTHROPIC_MODEL
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
        with patch("core.llm.handlers.anthropic.run_tool_loop", new_callable=AsyncMock) as mock_loop:
            mock_factory.return_value = mock_client
            mock_factories.get.return_value = mock_factory
            
            with patch("core.llm.clients.close_client", new_callable=AsyncMock):
                result = await verify_trading_decision(
                    decision=decision,
                    portfolio_context="Positions: AAPL (100)",
                    aggregated_context="Historical context"
                )
                
    assert result.status == "APPROVED"
    assert mock_loop.called

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
        model_name=GEMINI_MODEL
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
        with patch("core.llm.handlers.gemini.run_tool_loop", new_callable=AsyncMock) as mock_loop:
            mock_factory.return_value = mock_client
            mock_factories.get.return_value = mock_factory
            
            with patch("core.llm.clients.close_client", new_callable=AsyncMock):
                result = await verify_trading_decision(
                    decision=decision,
                    portfolio_context="Cash: $10,000",
                    aggregated_context="Historical context"
                )
                
    assert result.status == "APPROVED"
    assert mock_loop.called

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
        model_name=GEMINI_MODEL
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
        
        with patch("core.llm.handlers.gemini.run_tool_loop", new_callable=AsyncMock):
            mock_factory.return_value = mock_client
            mock_factories.get.return_value = mock_factory
            
            with patch("core.llm.clients.close_client", new_callable=AsyncMock):
                result = await verify_trading_decision(
                    decision=decision,
                    portfolio_context="Cash: $10,000",
                    aggregated_context="Historical context"
                )
                
    assert result.status == "APPROVED"
    assert result.confidence_score == 95
    assert result.verification_reasoning == "Handled sync response correctly."


@pytest.mark.asyncio
async def test_verify_trading_decision_exception_defaults_to_rejected():
    """Test that verification exceptions default to REJECTED (safer default)."""
    decision = DecisionObject(
        signal="BUY",
        confidence=80,
        reasoning="Some trade",
        ticker="FAIL",
        source_id="src_fail",
        price=100.0
    )

    with patch("core.llm.clients.CLIENT_FACTORIES") as mock_factories:
        mock_factory = MagicMock()
        mock_client = MagicMock()

        # Simulate an exception during the verification call
        mock_instructor_client = MagicMock()
        mock_completions = MagicMock()
        mock_completions.create.side_effect = RuntimeError("API connection failed")
        mock_instructor_client.completions = mock_completions
        mock_client.chat = mock_instructor_client
        mock_client.client = MagicMock()

        mock_factory.return_value = mock_client
        mock_factories.get.return_value = mock_factory

        with patch("core.llm.clients.close_client", new_callable=AsyncMock):
            result = await verify_trading_decision(
                decision=decision,
                portfolio_context="Cash: $10,000",
                aggregated_context="Historical context"
            )

    # Should default to REJECTED (safer) not APPROVED
    assert result.status == "REJECTED_VERIFICATION"
    assert "API connection failed" in result.verification_reasoning
    assert "Defaulting to rejection" in result.verification_reasoning


@pytest.mark.asyncio
async def test_verification_retry_validation_error():
    """Test retry on Instructor validation error for deepseek."""
    decision = DecisionObject(
        signal="BUY",
        confidence=80,
        reasoning="Strong earnings growth",
        ticker="AAPL",
        source_id="src_retry_val",
        price=180.0,
        model_provider="deepseek",
        model_name="deepseek-v4-flash"
    )

    valid_response = VerificationResult(
        status="APPROVED",
        verification_reasoning="After retry, approved.",
        confidence_score=85
    )

    with patch("core.llm.clients.CLIENT_FACTORIES") as mock_factories:
        mock_factory = MagicMock()
        mock_client = MagicMock()

        mock_instructor_client = MagicMock()
        mock_completions = MagicMock()
        # First call raises validation error, second returns valid
        mock_completions.create = AsyncMock(side_effect=[
            Exception("validation error: Invalid JSON"),
            [valid_response]
        ])
        mock_instructor_client.completions = mock_completions
        mock_client.chat = mock_instructor_client
        mock_client.client = MagicMock()

        mock_factory.return_value = mock_client
        mock_factories.get.return_value = mock_factory

        with patch("core.llm.handlers.deepseek.run_tool_loop", new_callable=AsyncMock):
            with patch("core.llm.clients.close_client", new_callable=AsyncMock):
                result = await verify_trading_decision(
                    decision=decision,
                    portfolio_context="Cash: $10,000",
                    aggregated_context="Historical context"
                )

    assert result.status == "APPROVED"
    assert result.verification_reasoning == "After retry, approved."
    assert result.confidence_score == 85
    assert mock_completions.create.call_count == 2, (
        f"Expected 2 Instructor calls (1 fail + 1 success), got {mock_completions.create.call_count}"
    )


@pytest.mark.asyncio
async def test_verification_retry_on_empty_result():
    """Test retry when Instructor returns None then succeeds."""
    decision = DecisionObject(
        signal="BUY",
        confidence=80,
        reasoning="Test retry on empty",
        ticker="MSFT",
        source_id="src_retry_empty",
        price=350.0,
        model_provider="deepseek",
        model_name="deepseek-v4-flash"
    )

    valid_response = VerificationResult(
        status="APPROVED",
        verification_reasoning="Recovered from empty response.",
        confidence_score=80
    )

    with patch("core.llm.clients.CLIENT_FACTORIES") as mock_factories:
        mock_factory = MagicMock()
        mock_client = MagicMock()

        mock_instructor_client = MagicMock()
        mock_completions = MagicMock()
        # First returns None (empty), second returns valid
        mock_completions.create = AsyncMock(side_effect=[
            None,
            [valid_response]
        ])
        mock_instructor_client.completions = mock_completions
        mock_client.chat = mock_instructor_client
        mock_client.client = MagicMock()

        mock_factory.return_value = mock_client
        mock_factories.get.return_value = mock_factory

        with patch("core.llm.handlers.deepseek.run_tool_loop", new_callable=AsyncMock):
            with patch("core.llm.clients.close_client", new_callable=AsyncMock):
                result = await verify_trading_decision(
                    decision=decision,
                    portfolio_context="Cash: $10,000",
                    aggregated_context="Historical context"
                )

    assert result.status == "APPROVED"
    assert result.verification_reasoning == "Recovered from empty response."
    assert result.confidence_score == 80
    assert mock_completions.create.call_count == 2, (
        f"Expected 2 Instructor calls (1 empty + 1 success), got {mock_completions.create.call_count}"
    )


@pytest.mark.asyncio
async def test_verification_all_retries_fail():
    """Test that all 3 attempts fail and fallback to REJECTED."""
    decision = DecisionObject(
        signal="BUY",
        confidence=80,
        reasoning="Test all retries fail",
        ticker="FAIL",
        source_id="src_all_fail",
        price=50.0,
        model_provider="deepseek",
        model_name="deepseek-v4-flash"
    )

    with patch("core.llm.clients.CLIENT_FACTORIES") as mock_factories:
        mock_factory = MagicMock()
        mock_client = MagicMock()

        mock_instructor_client = MagicMock()
        mock_completions = MagicMock()
        # All 3 calls return None
        mock_completions.create = AsyncMock(return_value=None)
        mock_instructor_client.completions = mock_completions
        mock_client.chat = mock_instructor_client
        mock_client.client = MagicMock()

        mock_factory.return_value = mock_client
        mock_factories.get.return_value = mock_factory

        with patch("core.llm.handlers.deepseek.run_tool_loop", new_callable=AsyncMock):
            with patch("core.llm.clients.close_client", new_callable=AsyncMock):
                result = await verify_trading_decision(
                    decision=decision,
                    portfolio_context="Cash: $10,000",
                    aggregated_context="Historical context"
                )

    assert result.status == "REJECTED_VERIFICATION"
    assert result.confidence_score == 0
    assert mock_completions.create.call_count == 3, (
        f"Expected 3 Instructor calls (all empty), got {mock_completions.create.call_count}"
    )


@pytest.mark.asyncio
async def test_verification_deepseek_empty_content_recovery():
    """Test that deepseek's empty content from thinking mode triggers recovery prompt."""
    decision = DecisionObject(
        signal="BUY",
        confidence=80,
        reasoning="DeepSeek thinking mode test",
        ticker="NVDA",
        source_id="src_ds_think",
        price=120.0,
        model_provider="deepseek",
        model_name="deepseek-v4-flash"
    )

    valid_response = VerificationResult(
        status="APPROVED",
        verification_reasoning="Recovered from empty thinking mode content.",
        confidence_score=90
    )

    with patch("core.llm.clients.CLIENT_FACTORIES") as mock_factories:
        mock_factory = MagicMock()
        mock_client = MagicMock()

        mock_instructor_client = MagicMock()
        mock_completions = MagicMock()
        mock_completions.create = AsyncMock(return_value=[valid_response])
        mock_instructor_client.completions = mock_completions
        mock_client.chat = mock_instructor_client
        mock_client.client = MagicMock()

        mock_factory.return_value = mock_client
        mock_factories.get.return_value = mock_factory

        # Simulate deepseek's empty-content message from thinking mode
        messages_with_empty_content = [
            {"role": "user", "content": "Verify this trade"},
            {
                "role": "assistant",
                "content": "",
                "reasoning_content": "<think>Some reasoning here</think>",
                "tool_calls": None
            }
        ]

        async def fake_tool_loop(raw_client, model_name, messages, provider, max_tool_steps=5, override_tools=None, enable_web_search=False):
            messages.clear()
            messages.extend(messages_with_empty_content)

        with patch("core.llm.handlers.deepseek.run_tool_loop", new_callable=AsyncMock, side_effect=fake_tool_loop):
            with patch("core.llm.clients.close_client", new_callable=AsyncMock):
                result = await verify_trading_decision(
                    decision=decision,
                    portfolio_context="Cash: $10,000",
                    aggregated_context="Historical context"
                )

    assert result.status == "APPROVED"
    assert result.verification_reasoning == "Recovered from empty thinking mode content."
    assert result.confidence_score == 90


@pytest.mark.asyncio
async def test_verification_deepseek_retry_across_3_empty_then_success():
    """Test retry across multiple empty results with deepseek."""
    decision = DecisionObject(
        signal="BUY",
        confidence=80,
        reasoning="Multi-empty retry test",
        ticker="GOOG",
        source_id="src_multi_empty",
        price=180.0,
        model_provider="deepseek",
        model_name="deepseek-v4-flash"
    )

    valid_response = VerificationResult(
        status="APPROVED",
        verification_reasoning="Succeeded after 2 empty retries.",
        confidence_score=75
    )

    with patch("core.llm.clients.CLIENT_FACTORIES") as mock_factories:
        mock_factory = MagicMock()
        mock_client = MagicMock()

        mock_instructor_client = MagicMock()
        mock_completions = MagicMock()
        # Two empty results, then success
        mock_completions.create = AsyncMock(side_effect=[
            None,
            None,
            [valid_response]
        ])
        mock_instructor_client.completions = mock_completions
        mock_client.chat = mock_instructor_client
        mock_client.client = MagicMock()

        mock_factory.return_value = mock_client
        mock_factories.get.return_value = mock_factory

        with patch("core.llm.handlers.deepseek.run_tool_loop", new_callable=AsyncMock):
            with patch("core.llm.clients.close_client", new_callable=AsyncMock):
                result = await verify_trading_decision(
                    decision=decision,
                    portfolio_context="Cash: $10,000",
                    aggregated_context="Historical context"
                )

    assert result.status == "APPROVED"
    assert result.verification_reasoning == "Succeeded after 2 empty retries."
    assert result.confidence_score == 75
    assert mock_completions.create.call_count == 3, (
        f"Expected 3 calls (2 empty + 1 success), got {mock_completions.create.call_count}"
    )


@pytest.mark.asyncio
async def test_verification_deepseek_all_validation_errors_then_fallback():
    """Test deepseek: all 3 attempts raise validation errors, falls back to REJECTED."""
    decision = DecisionObject(
        signal="BUY",
        confidence=80,
        reasoning="Validation error cascade",
        ticker="CASCADE",
        source_id="src_cascade",
        price=50.0,
        model_provider="deepseek",
        model_name="deepseek-v4-flash"
    )

    with patch("core.llm.clients.CLIENT_FACTORIES") as mock_factories:
        mock_factory = MagicMock()
        mock_client = MagicMock()

        mock_instructor_client = MagicMock()
        mock_completions = MagicMock()
        # All 3 calls raise validation error
        mock_completions.create = AsyncMock(side_effect=[
            Exception("validation error: list_type expected array"),
            Exception("validation error: input should be a valid"),
            Exception("validation error: EOF while parsing"),
        ])
        mock_instructor_client.completions = mock_completions
        mock_client.chat = mock_instructor_client
        mock_client.client = MagicMock()

        mock_factory.return_value = mock_client
        mock_factories.get.return_value = mock_factory

        with patch("core.llm.handlers.deepseek.run_tool_loop", new_callable=AsyncMock):
            with patch("core.llm.clients.close_client", new_callable=AsyncMock):
                result = await verify_trading_decision(
                    decision=decision,
                    portfolio_context="Cash: $10,000",
                    aggregated_context="Historical context"
                )

    assert result.status == "REJECTED_VERIFICATION"
    assert result.confidence_score == 0
    assert mock_completions.create.call_count == 3, (
        f"Expected 3 validation error attempts, got {mock_completions.create.call_count}"
    )


@pytest.mark.asyncio
async def test_verification_deepseek_non_retryable_error_raises():
    """Test deepseek: non-validation errors are re-raised immediately (no retry)."""
    decision = DecisionObject(
        signal="BUY",
        confidence=80,
        reasoning="Non-retryable error",
        ticker="HARD",
        source_id="src_hard_fail",
        price=50.0,
        model_provider="deepseek",
        model_name="deepseek-v4-flash"
    )

    with patch("core.llm.clients.CLIENT_FACTORIES") as mock_factories:
        mock_factory = MagicMock()
        mock_client = MagicMock()

        mock_instructor_client = MagicMock()
        mock_completions = MagicMock()
        # Rate limit error — should NOT retry
        mock_completions.create = AsyncMock(side_effect=Exception("Rate limit exceeded"))
        mock_instructor_client.completions = mock_completions
        mock_client.chat = mock_instructor_client
        mock_client.client = MagicMock()

        mock_factory.return_value = mock_client
        mock_factories.get.return_value = mock_factory

        with patch("core.llm.handlers.deepseek.run_tool_loop", new_callable=AsyncMock):
            with patch("core.llm.clients.close_client", new_callable=AsyncMock):
                result = await verify_trading_decision(
                    decision=decision,
                    portfolio_context="Cash: $10,000",
                    aggregated_context="Historical context"
                )

    # Non-retryable errors should be caught at the outer try/except
    # and default to REJECTED with error message
    assert result.status == "REJECTED_VERIFICATION"
    assert "Rate limit exceeded" in result.verification_reasoning
    assert mock_completions.create.call_count == 1, (
        f"Expected only 1 call (no retry for non-validation errors), got {mock_completions.create.call_count}"
    )
