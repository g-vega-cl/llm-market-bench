"""Tests for second-step verification logic."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from core.models import DecisionObject, VerificationResult
from core.llm.verification import verify_trading_decision
from core.config import GEMINI_MODEL, ANTHROPIC_MODEL

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
