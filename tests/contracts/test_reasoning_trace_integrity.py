import pytest
import json
import uuid
from datetime import datetime, timezone
from apps.engine.core.models import DecisionObject, MacroEvent
from apps.engine.analysis.post_analysis import PostAnalysisResult

def test_historical_decision_deserialization():
    """Confirms old decisions still deserialize correctly into modern models."""
    # Simulation of a record from early 2024
    historical_raw = {
        "ticker": "NVDA",
        "signal": "BUY",
        "confidence": 85,
        "reasoning": "Historical catalyst reasoning.",
        "model_provider": "openai",
        "model_name": "gpt-4-0125-preview",
        "source_id": "historical-source-001",
        "catalyst_type": "EARNINGS",
        "catalyst_duration": "SHORT_TERM"
    }

    # This should succeed even if new fields (like is_priced_in) were added later
    # as long as they have defaults in the Pydantic model.
    decision = DecisionObject(**historical_raw)
    assert decision.ticker == "NVDA"
    assert decision.is_priced_in is False # Default value
    assert decision.is_priced_in_reasoning == "No explicit priced-in reasoning provided."

def test_historical_memory_deserialization():
    """Confirms old memory entries still classify correctly."""
    historical_memory = {
        "event_name": "Fed Rate Hike",
        "impact": "BEARISH",
        "catalyst_type": "MACRO",
        "confidence": 95,
        "reasoning": "Classic macro impact.",
        "source_id": "macro-source-001"
    }

    event = MacroEvent(**historical_memory)
    assert event.event_name == "Fed Rate Hike"
    assert event.is_ongoing is False # Default

def test_retired_provider_rendering_safety():
    """Ensures records from retired providers don't break models."""
    # Simulation of a decision from a provider no longer in active use
    retired_raw = {
        "ticker": "MSFT",
        "signal": "HOLD",
        "confidence": 50,
        "reasoning": "Reasoning from a retired model.",
        "model_provider": "anthropic",
        "model_name": "claude-2.1", # Retired model
        "source_id": "retired-source-999"
    }

    decision = DecisionObject(**retired_raw)
    assert decision.model_name == "claude-2.1"
