"""Test suite verifying validation resilience and normalization for Pydantic models."""

from core.models import DecisionObject, MacroEvent, VerificationResult


def test_decision_object_resilience():
    """Verify DecisionObject normalizes signal/duration and gracefully handles invalid catalyst types."""
    # This should parse successfully with our resilience validators:
    decision = DecisionObject(
        signal="buy",
        confidence=85,
        reasoning="Test reasoning.",
        ticker="aapl",
        catalyst_type="geopolitical_risk_trade_rerouting",  # Mismatched Literal -> Fallback to OTHER
        catalyst_duration="short term",  # Spaced Literal -> SHORT_TERM
        source_id="src_123",
    )
    assert decision.signal == "BUY"
    assert decision.ticker == "AAPL"
    assert decision.catalyst_type == "OTHER"
    assert decision.catalyst_duration == "SHORT_TERM"


def test_macro_event_resilience():
    """Verify MacroEvent normalizes impact and handles invalid catalyst types."""
    event = MacroEvent(
        event_name="Fed Rate Decision",
        impact="bullish",  # Lowercase Literal -> BULLISH
        catalyst_type="interest_rate_regime",  # Mismatched Literal -> Fallback to MACRO
        confidence=90,
        reasoning="Hawkish pause is bullish.",
    )
    assert event.impact == "BULLISH"
    assert event.catalyst_type == "MACRO"


def test_verification_result_resilience():
    """Verify VerificationResult normalizes status."""
    result = VerificationResult(
        status="approved",  # Lowercase Literal -> APPROVED
        verification_reasoning="Valid trade parameters.",
        confidence_score=95,
    )
    assert result.status == "APPROVED"
