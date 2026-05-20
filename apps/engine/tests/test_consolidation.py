"""Tests for decision consolidation logic."""

from unittest.mock import patch

import pytest

from analysis.consensus import process_decision_consensus
from core.models import DecisionObject


@pytest.fixture
def sample_decisions():
    return [
        DecisionObject(
            ticker="AAPL",
            signal="BUY",
            confidence=90,
            reasoning="Strong iPhone sales expected.",
            source_id="news_1",
            model_provider="openai",
            model_name="gpt-4",
        ),
        DecisionObject(
            ticker="AAPL",
            signal="BUY",
            confidence=85,
            reasoning="Apple Intelligence is a major catalyst.",
            source_id="news_1",
            model_provider="anthropic",
            model_name="claude-3",
        ),
        DecisionObject(
            ticker="TSLA",
            signal="SELL",
            confidence=70,
            reasoning="Margins are compression due to price cuts.",
            source_id="news_2",
            model_provider="openai",
            model_name="gpt-4",
        ),
    ]


@patch("analysis.consensus.synthesize_event")
@pytest.mark.asyncio
async def test_process_decision_consensus_groups_correctly(mock_synthesize, sample_decisions):
    # Mock synthesis return
    mock_synthesize.side_effect = [
        {"name": "Consensus BUY on AAPL", "summary": "Synthesized AAPL reasoning"},
        {"name": "Consensus SELL on TSLA", "summary": "Synthesized TSLA reasoning"},
    ]

    consolidated = await process_decision_consensus(sample_decisions)

    # We should have 2 groups: AAPL BUY and TSLA SELL
    assert len(consolidated) == 2

    # Check AAPL group
    aapl = next(c for c in consolidated if c["ticker"] == "AAPL")
    assert aapl["signal"] == "BUY"
    assert len(aapl["models_involved"]) == 2
    assert "openai_gpt-4" in aapl["models_involved"]
    assert "anthropic_claude-3" in aapl["models_involved"]
    assert len(aapl["original_reasonings"]) == 2

    # Check TSLA group
    tsla = next(c for c in consolidated if c["ticker"] == "TSLA")
    assert tsla["signal"] == "SELL"
    assert len(tsla["models_involved"]) == 1
    assert "openai_gpt-4" in tsla["models_involved"]


@patch("analysis.consensus.synthesize_event")
@pytest.mark.asyncio
async def test_process_decision_consensus_skips_hold(mock_synthesize):
    decisions = [
        DecisionObject(
            ticker="MSFT",
            signal="HOLD",
            confidence=50,
            reasoning="No clear trend.",
            source_id="news_3",
            model_provider="openai",
            model_name="gpt-4",
        )
    ]

    consolidated = await process_decision_consensus(decisions)
    assert len(consolidated) == 0
    assert not mock_synthesize.called
