"""Tests for verification retry logic on empty responses."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from core.models import DecisionObject, VerificationResult
from core.llm.verification import verify_trading_decision


@pytest.mark.asyncio
async def test_verify_trading_decision_retry_on_empty_response():
    """Test that verification retries when the first attempt returns empty/no structured output."""
    decision = DecisionObject(
        signal="BUY",
        confidence=80,
        reasoning="Strong earnings growth",
        ticker="AAPL",
        source_id="src_1",
        price=180.0,
        model_provider="deepseek",
        model_name="deepseek-v4-flash"
    )
    
    # First response is empty (simulates the "No verification returned" issue)
    # Second response should succeed
    empty_response = VerificationResult(
        status="REJECTED_VERIFICATION",
        verification_reasoning="No verification returned",
        confidence_score=0
    )
    
    success_response = VerificationResult(
        status="APPROVED",
        verification_reasoning="Trade approved on retry",
        confidence_score=85
    )
    
    with patch("core.llm.clients.CLIENT_FACTORIES") as mock_factories:
        mock_factory = MagicMock()
        mock_client = MagicMock()
        
        mock_instructor_client = MagicMock()
        mock_completions = MagicMock()
        
        # First call returns empty, second call succeeds
        mock_completions.create = AsyncMock(side_effect=[
            [empty_response],  # First attempt: returns but with "No verification"
            [success_response]  # Second attempt: succeeds
        ])
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
    
    # Should succeed on retry
    assert result.status == "APPROVED", f"Expected APPROVED but got {result.status}"
    assert result.verification_reasoning == "Trade approved on retry"
    assert result.confidence_score == 85


@pytest.mark.asyncio
async def test_verify_trading_decision_no_retry_on_valid_response():
    """Test that verification does NOT retry when first response is valid."""
    decision = DecisionObject(
        signal="BUY",
        confidence=80,
        reasoning="Strong momentum",
        ticker="NVDA",
        source_id="src_2",
        price=120.0,
        model_provider="deepseek",
        model_name="deepseek-v4-flash"
    )
    
    valid_response = VerificationResult(
        status="APPROVED",
        verification_reasoning="Strong momentum confirmed",
        confidence_score=90
    )
    
    with patch("core.llm.clients.CLIENT_FACTORIES") as mock_factories:
        mock_factory = MagicMock()
        mock_client = MagicMock()
        
        mock_instructor_client = MagicMock()
        mock_completions = MagicMock()
        # Only one call should be made
        mock_completions.create = AsyncMock(return_value=[valid_response])
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
    
    # Should succeed without retry
    assert result.status == "APPROVED"
    assert result.verification_reasoning == "Strong momentum confirmed"
    assert result.confidence_score == 90


@pytest.mark.asyncio
async def test_verify_trading_decision_max_retries_exhausted():
    """Test that verification fails after max retries are exhausted."""
    decision = DecisionObject(
        signal="BUY",
        confidence=80,
        reasoning="Test trade",
        ticker="TEST",
        source_id="src_3",
        price=50.0,
        model_provider="deepseek",
        model_name="deepseek-v4-flash"
    )
    
    # All responses are empty
    empty_response = VerificationResult(
        status="REJECTED_VERIFICATION",
        verification_reasoning="No verification returned",
        confidence_score=0
    )
    
    with patch("core.llm.clients.CLIENT_FACTORIES") as mock_factories:
        mock_factory = MagicMock()
        mock_client = MagicMock()
        
        mock_instructor_client = MagicMock()
        mock_completions = MagicMock()
        # All attempts return empty
        mock_completions.create = AsyncMock(return_value=[empty_response])
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
    
    # Should fail after exhausting retries
    assert result.status == "REJECTED_VERIFICATION"
    assert "No verification returned" in result.verification_reasoning or "Max retries" in result.verification_reasoning


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_verify_trading_decision_retry_on_empty_response())
    asyncio.run(test_verify_trading_decision_no_retry_on_valid_response())
    asyncio.run(test_verify_trading_decision_max_retries_exhausted())