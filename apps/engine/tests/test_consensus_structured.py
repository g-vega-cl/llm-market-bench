"""Tests for Structured Scenarios and Scenario-Specific Ticker Mapping."""

from unittest.mock import AsyncMock, patch

import pytest

from analysis.consensus import process_consensus
from core.models import MacroEvent


@pytest.fixture
def sample_consensus_events():
    return [
        MacroEvent(
            event_name="Fed Policy Decision",
            impact="BULLISH",
            confidence=90,
            reasoning="Expected shift to rate cuts",
            source_id="news_chunk_1",
            model_provider="openai",
            model_name="gpt-4",
        ),
        MacroEvent(
            event_name="Fed Policy Decision",
            impact="BULLISH",
            confidence=85,
            reasoning="Shifting towards loose monetary policy",
            source_id="news_chunk_1",
            model_provider="anthropic",
            model_name="claude-3",
        ),
    ]


@patch("analysis.consensus.DiscoveryService")
@patch("analysis.consensus.synthesize_event")
@patch("analysis.consensus.get_embeddings_batch")
@patch("analysis.consensus.add_memory")
@pytest.mark.asyncio
async def test_consensus_promotes_structured_scenarios(
    mock_add_memory, mock_get_embeddings, mock_synthesize, mock_discovery, sample_consensus_events
):
    # 1. Setup mock returns
    mock_add_memory.return_value = "memory-uuid-123"

    # Mock LLM Synthesis returning structured scenarios
    mock_synthesize.return_value = {
        "name": "Fed Loose Shift",
        "summary": "Fed signals potential loose monetary policy shift.",
        "future_date": "2026-06-30",
        "scenarios": [
            {
                "cleanHeader": "Scenario A: Rate Cut",
                "percentage": "70%",
                "outcome": "Aggressive loose shift",
                "tradingPlan": "Go long high volume SPY",
            },
            {
                "cleanHeader": "Scenario B: Hold",
                "percentage": "30%",
                "outcome": "Hawkish flat hold",
                "tradingPlan": "Buy GLD safe haven",
            },
        ],
    }

    # Mock embeddings to force consensus grouping
    mock_get_embeddings.return_value = [
        [1.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
    ]

    # Mock Asset Discovery to return different assets based on the scenario queried
    async def side_effect_discover(theme, context=None):
        if "Scenario A" in theme or "SPY" in theme:
            return [{"ticker": "SPY", "name": "S&P 500 ETF", "reason": "Aggressive loose shift benefits equity beta"}]
        elif "Scenario B" in theme or "GLD" in theme:
            return [{"ticker": "GLD", "name": "Gold Trust", "reason": "Safe haven asset hedge"}]
        return []

    mock_discovery.return_value.discover_assets = AsyncMock(side_effect=side_effect_discover)

    # 2. Run consensus
    results = await process_consensus(sample_consensus_events, threshold=2)

    # 3. Assertions
    assert len(results) == 1
    consensus_res = results[0]

    # Assert structured scenarios are preserved
    assert "scenarios" in consensus_res
    scenarios_list = consensus_res["scenarios"]
    assert len(scenarios_list) == 2

    # Assert scenario A got SPY and scenario B got GLD
    assert scenarios_list[0]["cleanHeader"] == "Scenario A: Rate Cut"
    assert len(scenarios_list[0]["assets"]) == 1
    assert scenarios_list[0]["assets"][0]["ticker"] == "SPY"

    assert scenarios_list[1]["cleanHeader"] == "Scenario B: Hold"
    assert len(scenarios_list[1]["assets"]) == 1
    assert scenarios_list[1]["assets"][0]["ticker"] == "GLD"

    # Assert legacy fallbacks are populated for backward compatibility
    assert "discovered_assets" in consensus_res
    assert len(consensus_res["discovered_assets"]) == 2  # union of SPY and GLD

    assert "scenario_analysis" in consensus_res
    assert "Scenario A: Rate Cut (70% probability)" in consensus_res["scenario_analysis"]
    assert "Scenario B: Hold (30% probability)" in consensus_res["scenario_analysis"]
