"""Unit tests for Pydantic models and validators."""

import json

import pytest
from pydantic import ValidationError

from core.models import (
    DecisionObject,
    DecisionsResponse,
    RankedAsset,
    TickerSuggestion,
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

def test_decisions_response_parse_invalid_json_string():
    """Test that DecisionsResponse returns the string if it's invalid JSON, which then fails validation."""
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

def test_decisions_response_parse_json_string_non_string():
    """Test that DecisionsResponse returns the original value if it's not a string."""
    response = DecisionsResponse(decisions=[])
    assert response.decisions == []

def test_decision_object_injected_market_price():
    """Test that DecisionObject accepts injected_market_price."""
    # Without injected_market_price
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

    # With injected_market_price
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
