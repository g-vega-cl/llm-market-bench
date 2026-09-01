"""Unit tests for the 2-stage Adversarial Consensus Debate with gpt-5.6-luna."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from analysis.consensus import process_consensus
from core.llm.events import synthesize_event
from core.llm.prompt_factory import PromptFactory
from core.models import MacroEvent


@pytest.mark.asyncio
async def test_prompt_factory_build_challenger_messages():
    """Verify that PromptFactory constructs the Challenger prompt correctly."""
    messages = PromptFactory.build_challenger_messages(
        provider="openai",
        event_name="AI Datacenter Power Surge",
        impact="BULLISH",
        combined_reasonings="- Model 1: Massive power demand for GPUs.",
        combined_scenarios="- Scenario A: Nuclear power deals accelerate.",
    )

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "adversarial Red-Teamer" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert "AI Datacenter Power Surge" in messages[1]["content"]
    assert "BULLISH" in messages[1]["content"]


@pytest.mark.asyncio
async def test_synthesize_event_two_stage_debate():
    """Verify synthesize_event executes the 2-stage Challenger -> Arbiter debate pipeline."""
    mock_openai_client = MagicMock()

    class FakeChallengerResponse(BaseModel):
        counter_thesis: str = "Grid interconnection queues and nuclear regulatory delays will stall rollouts."
        pre_mortem_failure_mode: str = "Utilities fail to deliver power in time, leading to capex cuts."
        key_risks: list[str] = ["3-5 year grid queue", "Regulatory pushback", "ASIC efficiency gains"]

    class FakeScenarioDetail(BaseModel):
        cleanHeader: str = "Scenario A: Grid Delays"
        percentage: str = "60%"
        outcome: str = "Capex pivots to off-grid generation"
        tradingPlan: str = "Long off-grid power providers ($GEV, $CEG)"

    class FakeSynthesisResponse(BaseModel):
        name: str = "AI Power Grid Constraints"
        summary: str = "AI power surge faces grid bottlenecks forcing off-grid solutions."
        future_date: str = "2026-12-31"
        future_date_note: str | None = None
        is_ongoing: bool = True
        is_future_catalyst: bool = False
        historical_parallel: str = "2000 Telecom Fiber Buildout"
        scenarios: list[FakeScenarioDetail] = [
            FakeScenarioDetail(
                cleanHeader="Scenario A: Off-Grid Power",
                percentage="60%",
                outcome="Behind-the-meter generation takes share",
                tradingPlan="Long nuclear and turbine producers",
            ),
            FakeScenarioDetail(
                cleanHeader="Scenario B: Power Caps",
                percentage="40%",
                outcome="Datacenter builds slow due to interconnection delays",
                tradingPlan="Short unhedged merchant power",
            ),
        ]
        importance_score: int = 8

    # First call returns ChallengerResponse, second call returns SynthesisResponse
    mock_openai_client.chat.completions.create = AsyncMock(
        side_effect=[
            FakeChallengerResponse(),
            FakeSynthesisResponse(),
        ]
    )

    with (
        patch("core.llm.events.clients.get_openai_client", return_value=mock_openai_client),
        patch("core.llm.events.clients.close_client", new_callable=AsyncMock) as mock_close,
        patch("core.llm.events.log_reasoning_trace", new_callable=AsyncMock) as mock_trace,
    ):
        result = await synthesize_event(
            event_name="AI Datacenter Power Surge",
            impact="BULLISH",
            reasonings=["Model 1: Nuclear deals with hyperscalers."],
            scenarios=["Scenario A: Hyperscalers buy nuclear plants."],
        )

        # Verify 2 OpenAI completions calls occurred
        assert mock_openai_client.chat.completions.create.call_count == 2
        assert mock_close.called

        # Verify traces logged for both stages
        assert mock_trace.call_count == 2
        trace_task_types = [call.kwargs.get("task_type") for call in mock_trace.call_args_list]
        assert "CONSENSUS_CHALLENGE" in trace_task_types
        assert "CONSENSUS_SYNTHESIS" in trace_task_types

        # Verify result contains synthesized data and debate metadata
        assert result["name"] == "AI Power Grid Constraints"
        assert len(result["scenarios"]) == 2
        assert "debate" in result
        debate = result["debate"]
        assert debate["stress_tested"] is True
        assert (
            debate["counter_thesis"] == "Grid interconnection queues and nuclear regulatory delays will stall rollouts."
        )
        assert debate["pre_mortem"] == "Utilities fail to deliver power in time, leading to capex cuts."
        assert "3-5 year grid queue" in debate["key_risks"]
        assert debate["adversary_model"] == "gpt-5.6-luna"
        assert debate["arbiter_model"] == "gpt-5.6-luna"


@pytest.mark.asyncio
async def test_process_consensus_persists_debate_metadata():
    """Verify process_consensus persists the debate record in memory metadata."""
    sample_events = [
        MacroEvent(
            event_name="AI Power Crunch",
            impact="BULLISH",
            confidence=90,
            reasoning="Hyperscalers need gigawatts of power.",
            source_id="news_1",
            model_provider="openai",
            model_name="gpt-5.6-luna",
        ),
        MacroEvent(
            event_name="AI Power Crunch",
            impact="BULLISH",
            confidence=85,
            reasoning="Grid cannot support AI demand.",
            source_id="news_1",
            model_provider="anthropic",
            model_name="claude-haiku-4-5",
        ),
    ]

    mock_synthesis = {
        "name": "AI Power Grid Constraints",
        "summary": "AI power crunch faces severe utility transmission bottlenecks.",
        "future_date": "2026-12-31",
        "future_date_note": None,
        "is_ongoing": True,
        "is_future_catalyst": False,
        "historical_parallel": None,
        "importance_score": 8,
        "scenarios": [
            {
                "cleanHeader": "Scenario A: Grid Bottleneck",
                "percentage": "60%",
                "outcome": "Onsite nuclear wins",
                "tradingPlan": "Long $CEG",
            },
            {
                "cleanHeader": "Scenario B: Grid Modernization",
                "percentage": "40%",
                "outcome": "High transmission capex",
                "tradingPlan": "Long $ETN",
            },
        ],
        "debate": {
            "challenger_critique": "Interconnection queues limit short-term upside.",
            "counter_thesis": "Utility lead times are 4+ years.",
            "pre_mortem": "Capex stalls if utilities delay hookups.",
            "key_risks": ["Lead time delays", "Regulatory friction"],
            "adversary_model": "gpt-5.6-luna",
            "arbiter_model": "gpt-5.6-luna",
            "stress_tested": True,
        },
    }

    with (
        patch("analysis.consensus.DiscoveryService") as mock_disc,
        patch("analysis.consensus.synthesize_event", new_callable=AsyncMock, return_value=mock_synthesis),
        patch("analysis.consensus.get_embeddings_batch", return_value=[[1.0, 0.0], [1.0, 0.0]]),
        patch("analysis.consensus.add_memory", return_value="mem-uuid-999") as mock_add_mem,
    ):
        mock_disc.return_value.discover_assets = AsyncMock(return_value=[])

        results = await process_consensus(sample_events, threshold=2.0)
        assert len(results) == 1
        assert mock_add_mem.called
        call_kwargs = mock_add_mem.call_args.kwargs
        assert "metadata" in call_kwargs
        assert "debate" in call_kwargs["metadata"]
        assert call_kwargs["metadata"]["debate"]["stress_tested"] is True
        assert call_kwargs["metadata"]["debate"]["adversary_model"] == "gpt-5.6-luna"
