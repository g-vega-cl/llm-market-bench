"""Unit tests for Future Forces analytics and OpenAI Luna sentinel audit."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from analytics.future_forces import (
    DEFAULT_FUTURE_FORCES,
    ForceAuditResult,
    ForceEvaluationResult,
    FutureForceCandidate,
    audit_force_invalidation,
    check_deterministic_invalidation,
    evaluate_future_force,
)


def test_future_force_candidate_horizon_validation():
    """Verify FutureForceCandidate enforces the 2 to 24 month horizon window."""
    # Valid 2-month floor
    cand = FutureForceCandidate(
        force_title="Test Force",
        archetype="sleeping_giant",
        thesis="Valid thesis",
        catalyst_event="Earnings print",
        horizon_months=2,
        invalidation_triggers="Revenue down",
        transmission_mechanism="EPS expansion",
        tickers=["GOOGL"],
    )
    assert cand.horizon_months == 2

    # Under 2 months (e.g. 1 month) must raise ValidationError
    with pytest.raises(ValidationError):
        FutureForceCandidate(
            force_title="Too Short",
            archetype="sleeping_giant",
            thesis="Valid thesis",
            catalyst_event="Earnings print",
            horizon_months=1,
            invalidation_triggers="Revenue down",
            transmission_mechanism="EPS expansion",
            tickers=["GOOGL"],
        )

    # Over 24 months (e.g. 30 months) must raise ValidationError
    with pytest.raises(ValidationError):
        FutureForceCandidate(
            force_title="Too Long",
            archetype="sleeping_giant",
            thesis="Valid thesis",
            catalyst_event="Earnings print",
            horizon_months=30,
            invalidation_triggers="Revenue down",
            transmission_mechanism="EPS expansion",
            tickers=["GOOGL"],
        )


def test_default_future_forces_structure():
    """Verify baseline vetted future forces conform to schema."""
    assert len(DEFAULT_FUTURE_FORCES) >= 5
    for force in DEFAULT_FUTURE_FORCES:
        cand = FutureForceCandidate(**force)
        assert cand.horizon_months >= 2
        assert len(cand.tickers) >= 1
        assert cand.conviction_score >= 1


def test_check_deterministic_invalidation():
    """Verify deterministic guardrails catch bankruptcy, delisting, and expired target dates."""
    # Healthy
    assert check_deterministic_invalidation({"is_bankrupt": False, "is_delisted": False})[0] is False

    # Bankrupt
    inv, reason = check_deterministic_invalidation({"is_bankrupt": True})
    assert inv is True
    assert "bankruptcy" in reason.lower()

    # Delisted
    inv, reason = check_deterministic_invalidation({"is_delisted": True})
    assert inv is True
    assert "delisted" in reason.lower()

    # Target date expired > 30 days with negative PnL
    inv, reason = check_deterministic_invalidation({"target_date": "2024-01-01", "unrealized_pnl_usd": -500.0})
    assert inv is True
    assert "expired" in reason.lower()


@pytest.mark.asyncio
async def test_evaluate_future_force_uses_luna_with_thinking():
    """Verify evaluate_future_force calls gpt-5.6-luna with reasoning_effort='medium'."""
    mock_client = MagicMock()
    mock_response = ForceEvaluationResult(
        passes_rubric=True,
        conviction_score=5,
        priced_in_assessment="Priced for failure; 20% upside on realization",
        critique="Key risk is execution timing",
        recommended_horizon_months=4,
        falsification_clarity_score=5,
    )
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    candidate = FutureForceCandidate(
        force_title="Hormuz Tanker Squeeze",
        archetype="geopolitical_chokepoint",
        thesis="Naval chokepoint friction increases spot tanker day rates.",
        catalyst_event="Q3 charter rate prints",
        horizon_months=3,
        invalidation_triggers="Free transit treaty signed.",
        transmission_mechanism="High spot rates flow straight to FCF.",
        tickers=["FRO", "STNG"],
    )

    result = await evaluate_future_force(
        candidate=candidate,
        client=mock_client,
        model="gpt-5.6-luna",
    )

    assert result.passes_rubric is True
    assert result.conviction_score == 5
    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs["model"] == "gpt-5.6-luna"
    assert call_kwargs["reasoning_effort"] == "medium"


@pytest.mark.asyncio
async def test_audit_force_invalidation_sentinel():
    """Verify audit_force_invalidation calls gpt-5.6-luna to assess breaking news against triggers."""
    mock_client = MagicMock()
    mock_response = ForceAuditResult(
        is_invalidated=True,
        is_realized=False,
        confidence=0.95,
        explanation="Naval demilitarization treaty eliminates war-risk premium on tanker charter rates.",
        recommended_action="LIQUIDATE_INVALIDATED",
    )
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    force_data = {
        "force_title": "Hormuz Tanker Squeeze",
        "archetype": "geopolitical_chokepoint",
        "tickers": ["FRO", "STNG"],
        "thesis": "Naval chokepoint friction increases spot tanker day rates.",
        "invalidation_triggers": "Formal international naval demilitarization treaty signed.",
        "catalyst_event": "Q3 charter rate prints",
    }

    news = "Breaking: UN signs historic maritime demilitarization and free transit accord for Persian Gulf."

    result = await audit_force_invalidation(
        force_data=force_data,
        news_context=news,
        client=mock_client,
        model="gpt-5.6-luna",
    )

    assert result.is_invalidated is True
    assert result.recommended_action == "LIQUIDATE_INVALIDATED"
    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs["model"] == "gpt-5.6-luna"
    assert call_kwargs["reasoning_effort"] == "medium"
