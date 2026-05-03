"""Tests for verification — no retry loop on empty responses."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from core.models import DecisionObject, VerificationResult
from core.llm.verification import verify_trading_decision


@pytest.mark.asyncio
async def test_verification_accepts_rejected_as_is():
    """Empty/REJECTED response is accepted immediately — no retry."""
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
        # Single call returns the rejection — accepted immediately
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

    # Accepted as-is, no retry
    assert result.status == "REJECTED_VERIFICATION"
    assert result.verification_reasoning == "No verification returned"
    assert result.confidence_score == 0
    # Only one call made (no retry)
    assert mock_completions.create.call_count == 1


@pytest.mark.asyncio
async def test_verification_no_retry_on_valid_response():
    """Valid response is accepted on first call — no retry."""
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

    assert result.status == "APPROVED"
    assert result.verification_reasoning == "Strong momentum confirmed"
    assert result.confidence_score == 90
    assert mock_completions.create.call_count == 1


@pytest.mark.asyncio
async def test_verification_none_response_fallback():
    """Instructor returning None yields a fallback REJECTED."""
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

    with patch("core.llm.clients.CLIENT_FACTORIES") as mock_factories:
        mock_factory = MagicMock()
        mock_client = MagicMock()

        mock_instructor_client = MagicMock()
        mock_completions = MagicMock()
        mock_completions.create = AsyncMock(return_value=None)
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
    assert result.confidence_score == 0
    assert mock_completions.create.call_count == 1


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_verification_accepts_rejected_as_is())
    asyncio.run(test_verification_no_retry_on_valid_response())
    asyncio.run(test_verification_none_response_fallback())
