"""Unit tests for Pydantic models and validators."""

import json

import pytest
from pydantic import ValidationError

from core.models import (
    CauseAndEffectResult,
    DecisionObject,
    DecisionsResponse,
    MacroEvent,
    RankedAsset,
    TickerSuggestion,
    VerificationResult,
)


def test_decision_object_upper_case_ticker():
    """Test that DecisionObject uppercases the ticker."""
    decision = DecisionObject(
        signal="BUY",
        confidence=80,
        reasoning="Test reasoning",
        ticker="aapl",
        catalyst_type="MACRO",
        catalyst_duration="INTRADAY",
        source_id="test_source",
    )
    assert decision.ticker == "AAPL"


def test_decision_object_allocation_percentage_bounds():
    """Test that DecisionObject enforces allocation_percentage bounds (0-100)."""
    # Valid allocations
    DecisionObject(
        signal="BUY",
        confidence=80,
        reasoning="test",
        ticker="AAPL",
        catalyst_type="MACRO",
        catalyst_duration="INTRADAY",
        source_id="test_source",
        allocation_percentage=0,
    )
    DecisionObject(
        signal="BUY",
        confidence=80,
        reasoning="test",
        ticker="AAPL",
        catalyst_type="MACRO",
        catalyst_duration="INTRADAY",
        source_id="test_source",
        allocation_percentage=100,
    )

    # Invalid allocations
    with pytest.raises(ValidationError) as exc_info:
        DecisionObject(
            signal="BUY",
            confidence=80,
            reasoning="test",
            ticker="AAPL",
            catalyst_type="MACRO",
            catalyst_duration="INTRADAY",
            source_id="test_source",
            allocation_percentage=-1,
        )
    assert "allocation_percentage" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        DecisionObject(
            signal="BUY",
            confidence=80,
            reasoning="test",
            ticker="AAPL",
            catalyst_type="MACRO",
            catalyst_duration="INTRADAY",
            source_id="test_source",
            allocation_percentage=101,
        )
    assert "allocation_percentage" in str(exc_info.value)


def test_decision_object_confidence_bounds():
    """Test that DecisionObject enforces confidence bounds (0-100)."""
    # Valid
    DecisionObject(
        signal="BUY",
        confidence=0,
        reasoning="test",
        ticker="AAPL",
        catalyst_type="MACRO",
        catalyst_duration="INTRADAY",
        source_id="test_source",
    )
    DecisionObject(
        signal="BUY",
        confidence=100,
        reasoning="test",
        ticker="AAPL",
        catalyst_type="MACRO",
        catalyst_duration="INTRADAY",
        source_id="test_source",
    )

    # Invalid
    with pytest.raises(ValidationError) as exc_info:
        DecisionObject(
            signal="BUY",
            confidence=-1,
            reasoning="test",
            ticker="AAPL",
            catalyst_type="MACRO",
            catalyst_duration="INTRADAY",
            source_id="test_source",
        )
    assert "confidence" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        DecisionObject(
            signal="BUY",
            confidence=101,
            reasoning="test",
            ticker="AAPL",
            catalyst_type="MACRO",
            catalyst_duration="INTRADAY",
            source_id="test_source",
        )
    assert "confidence" in str(exc_info.value)


def test_decision_object_injected_market_price():
    """Test that injected_market_price can be assigned and defaults to None."""
    # Default is None
    decision1 = DecisionObject(
        signal="BUY",
        confidence=80,
        reasoning="test",
        ticker="AAPL",
        catalyst_type="MACRO",
        catalyst_duration="INTRADAY",
        source_id="test_source",
    )
    assert decision1.injected_market_price is None

    # Can be assigned
    decision2 = DecisionObject(
        signal="BUY",
        confidence=80,
        reasoning="test",
        ticker="AAPL",
        catalyst_type="MACRO",
        catalyst_duration="INTRADAY",
        source_id="test_source",
        injected_market_price=150.5,
    )
    assert decision2.injected_market_price == 150.5


def test_decisions_response_parse_json_string():
    """Test that DecisionsResponse correctly parses a JSON string of decisions."""
    json_str = json.dumps(
        [
            {
                "signal": "BUY",
                "confidence": 90,
                "reasoning": "Great earnings",
                "ticker": "msft",
                "catalyst_type": "EARNINGS",
                "catalyst_duration": "SHORT_TERM",
                "source_id": "test_source",
            }
        ]
    )

    response = DecisionsResponse(decisions=json_str)

    # Check that it parsed into a list of DecisionObject
    assert len(response.decisions) == 1
    assert isinstance(response.decisions[0], DecisionObject)
    assert response.decisions[0].ticker == "MSFT"  # Checking validator worked

    # Test fallback if invalid JSON, Pydantic should raise a ValidationError for an invalid string type
    # since it fails the JSON load and returns the string, which fails the `list` type check.
    with pytest.raises(ValidationError):
        DecisionsResponse(decisions="invalid json")


def test_ticker_suggestion_upper_case_tickers():
    """Test that TickerSuggestion normalizes all tickers in the list to uppercase."""
    suggestion = TickerSuggestion(tickers=["aapl", "Msft", "GOOGL"], reasoning="Test reasoning")
    assert suggestion.tickers == ["AAPL", "MSFT", "GOOGL"]


def test_ranked_asset_upper_case_ticker():
    """Test that RankedAsset normalizes ticker to uppercase."""
    asset = RankedAsset(ticker="tsla", name="Tesla", relevance_score=85, reason="Test reason")
    assert asset.ticker == "TSLA"


def test_ranked_asset_relevance_score_bounds():
    """Test that RankedAsset enforces relevance_score bounds (0-100)."""
    # Valid scores
    RankedAsset(ticker="AAPL", name="Apple", relevance_score=0, reason="test")
    RankedAsset(ticker="AAPL", name="Apple", relevance_score=100, reason="test")

    # Invalid scores
    with pytest.raises(ValidationError) as exc_info:
        RankedAsset(ticker="AAPL", name="Apple", relevance_score=-1, reason="test")
    assert "relevance_score" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        RankedAsset(ticker="AAPL", name="Apple", relevance_score=101, reason="test")
    assert "relevance_score" in str(exc_info.value)


def test_macro_event_bounds():
    """Test bounds on MacroEvent fields importance_score and confidence."""
    # Valid importance_score and confidence
    MacroEvent(
        event_name="Test Event",
        impact="BULLISH",
        catalyst_type="MACRO",
        importance_score=1,
        confidence=0,
        reasoning="test",
        source_id="test_source",
    )
    MacroEvent(
        event_name="Test Event",
        impact="BULLISH",
        catalyst_type="MACRO",
        importance_score=10,
        confidence=100,
        reasoning="test",
        source_id="test_source",
    )

    # Invalid importance_score
    with pytest.raises(ValidationError) as exc_info:
        MacroEvent(
            event_name="Test Event",
            impact="BULLISH",
            catalyst_type="MACRO",
            importance_score=0,
            confidence=50,
            reasoning="test",
            source_id="test_source",
        )
    assert "importance_score" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        MacroEvent(
            event_name="Test Event",
            impact="BULLISH",
            catalyst_type="MACRO",
            importance_score=11,
            confidence=50,
            reasoning="test",
            source_id="test_source",
        )
    assert "importance_score" in str(exc_info.value)

    # Invalid confidence
    with pytest.raises(ValidationError) as exc_info:
        MacroEvent(
            event_name="Test Event",
            impact="BULLISH",
            catalyst_type="MACRO",
            importance_score=5,
            confidence=-1,
            reasoning="test",
            source_id="test_source",
        )
    assert "confidence" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        MacroEvent(
            event_name="Test Event",
            impact="BULLISH",
            catalyst_type="MACRO",
            importance_score=5,
            confidence=101,
            reasoning="test",
            source_id="test_source",
        )
    assert "confidence" in str(exc_info.value)


def test_verification_result_confidence_score_bounds():
    """Test that VerificationResult enforces confidence_score bounds (0-100)."""
    # Valid
    VerificationResult(
        status="APPROVED",
        verification_reasoning="test",
        confidence_score=0,
    )
    VerificationResult(
        status="APPROVED",
        verification_reasoning="test",
        confidence_score=100,
    )

    # Invalid
    with pytest.raises(ValidationError) as exc_info:
        VerificationResult(
            status="APPROVED",
            verification_reasoning="test",
            confidence_score=-1,
        )
    assert "confidence_score" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        VerificationResult(
            status="APPROVED",
            verification_reasoning="test",
            confidence_score=101,
        )
    assert "confidence_score" in str(exc_info.value)


def test_cause_and_effect_confidence_bounds():
    """Test that CauseAndEffectResult enforces confidence bounds (0-100)."""
    # Valid
    CauseAndEffectResult(
        analysis="test analysis",
        market_outcome="test outcome",
        confidence=0,
    )
    CauseAndEffectResult(
        analysis="test analysis",
        market_outcome="test outcome",
        confidence=100,
    )

    # Invalid
    with pytest.raises(ValidationError) as exc_info:
        CauseAndEffectResult(
            analysis="test analysis",
            market_outcome="test outcome",
            confidence=-1,
        )
    assert "confidence" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        CauseAndEffectResult(
            analysis="test analysis",
            market_outcome="test outcome",
            confidence=101,
        )
    assert "confidence" in str(exc_info.value)
