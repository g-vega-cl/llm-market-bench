"""Unit tests for structured historical_parallel synthesis and consensus persistence."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from analysis.consensus import process_consensus
from core.llm.events import HistoricalParallelDetail, synthesize_event
from core.llm.prompt_factory import PromptFactory
from core.models import MacroEvent


@pytest.mark.asyncio
async def test_prompt_factory_build_synthesis_messages_with_candidate_parallels():
    """Verify PromptFactory includes candidate historical parallels in synthesis prompt."""
    messages = PromptFactory.build_synthesis_messages(
        provider="openai",
        event_name="Strait of Hormuz Escalation",
        impact="BEARISH",
        combined_reasonings="- Model 1: High shipping risk.",
        combined_scenarios="- Scenario A: Supply disruption.",
        candidate_parallels="- 2024 Red Sea tanker disruptions\n- 1973 Oil Embargo",
    )

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "historical_parallel" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert "2024 Red Sea tanker disruptions" in messages[1]["content"]
    assert "1973 Oil Embargo" in messages[1]["content"]


@pytest.mark.asyncio
async def test_synthesize_event_parses_structured_historical_parallel():
    """Verify synthesize_event extracts full HistoricalParallelDetail fields."""
    mock_openai_client = MagicMock()

    class FakeChallengerResponse(BaseModel):
        counter_thesis: str = "Diplomatic routes will normalize quickly."
        pre_mortem_failure_mode: str = "Ceasefire reached, oil premiums collapse."
        key_risks: list[str] = ["De-escalation", "OPEC supply increase"]

    class FakeSynthesisResponse(BaseModel):
        name: str = "Strait of Hormuz Escalation"
        summary: str = "Naval tensions threaten Gulf tanker traffic."
        future_date: str | None = None
        future_date_note: str | None = None
        is_ongoing: bool = True
        is_future_catalyst: bool = False
        scenarios: list[dict] = []
        historical_parallel: HistoricalParallelDetail = HistoricalParallelDetail(
            title="2024 Red Sea Tanker Disruptions",
            timeframe="Jan - Mar 2024",
            precedent="Houthi drone strikes forced container ships around Cape of Good Hope.",
            market_reaction="Brent crude rose 12%, container freight indices (SCFI) surged 150%.",
            takeaway="Supply disruption premiums faded after 90 days once shippers adapted routes.",
            affected_assets=["USO", "ZIM", "FRO"],
        )
        importance_score: int = 8

    mock_openai_client.chat.completions.create = AsyncMock(
        side_effect=[FakeChallengerResponse(), FakeSynthesisResponse()]
    )

    with (
        patch("core.llm.events.clients.get_openai_client", return_value=mock_openai_client),
        patch("core.llm.events.clients.close_client", new_callable=AsyncMock),
        patch("core.llm.events.log_reasoning_trace", new_callable=AsyncMock),
    ):
        result = await synthesize_event(
            event_name="Strait of Hormuz Escalation",
            impact="BEARISH",
            reasonings=["Model 1: High shipping risk."],
            scenarios=[],
            candidate_parallels=["2024 Red Sea tanker disruptions", "1973 Oil Embargo"],
        )

        assert result["historical_parallel"] is not None
        hp = result["historical_parallel"]
        assert hp["title"] == "2024 Red Sea Tanker Disruptions"
        assert hp["timeframe"] == "Jan - Mar 2024"
        assert "Brent crude rose 12%" in hp["market_reaction"]
        assert "USO" in hp["affected_assets"]


@pytest.mark.asyncio
async def test_synthesize_event_handles_none_historical_parallel():
    """Verify synthesize_event succeeds cleanly when no historical parallel is identified."""
    mock_openai_client = MagicMock()

    class FakeChallengerResponse(BaseModel):
        counter_thesis: str = "Counter thesis."
        pre_mortem_failure_mode: str = "Pre-mortem."
        key_risks: list[str] = []

    class FakeSynthesisResponse(BaseModel):
        name: str = "Routine Tech Conference"
        summary: str = "Annual software update announced."
        future_date: str | None = None
        future_date_note: str | None = None
        is_ongoing: bool = False
        is_future_catalyst: bool = False
        scenarios: list[dict] = []
        historical_parallel: HistoricalParallelDetail | None = None
        importance_score: int = 4

    mock_openai_client.chat.completions.create = AsyncMock(
        side_effect=[FakeChallengerResponse(), FakeSynthesisResponse()]
    )

    with (
        patch("core.llm.events.clients.get_openai_client", return_value=mock_openai_client),
        patch("core.llm.events.clients.close_client", new_callable=AsyncMock),
        patch("core.llm.events.log_reasoning_trace", new_callable=AsyncMock),
    ):
        result = await synthesize_event(
            event_name="Routine Tech Conference",
            impact="NEUTRAL",
            reasonings=["Routine release"],
            scenarios=[],
        )

        assert result["historical_parallel"] is None


@pytest.mark.asyncio
async def test_process_consensus_compiles_parallels_and_persists_structured_metadata():
    """Verify process_consensus passes candidate parallels to synthesizer and persists structured metadata."""
    sample_events = [
        MacroEvent(
            event_name="Strait of Hormuz Escalation",
            impact="BEARISH",
            confidence=90,
            reasoning="Naval tensions threaten Gulf oil tanker traffic.",
            source_id="news_1",
            model_provider="anthropic",
            model_name="claude-haiku-4-5",
            historical_parallel="2024 Red Sea Tanker Disruptions",
        ),
        MacroEvent(
            event_name="Strait of Hormuz Escalation",
            impact="BEARISH",
            confidence=85,
            reasoning="Oil route chokepoint risks rising.",
            source_id="news_2",
            model_provider="openai",
            model_name="gpt-5.6-luna",
            historical_parallel="1973 Oil Embargo",
        ),
    ]

    mock_synthesis = {
        "name": "Strait of Hormuz Escalation",
        "summary": "Naval tensions threaten Gulf tanker traffic.",
        "future_date": None,
        "is_ongoing": True,
        "is_future_catalyst": False,
        "importance_score": 8,
        "scenarios": [],
        "historical_parallel": {
            "title": "2024 Red Sea Tanker Disruptions",
            "timeframe": "Jan - Mar 2024",
            "precedent": "Houthi drone strikes forced rerouting around Cape of Good Hope.",
            "market_reaction": "Brent crude jumped 12% while tanker rates surged.",
            "takeaway": "Risk premium decayed after 90 days.",
            "affected_assets": ["USO", "FRO"],
        },
    }

    with (
        patch("analysis.consensus.DiscoveryService") as mock_disc,
        patch("analysis.consensus.synthesize_event", new_callable=AsyncMock, return_value=mock_synthesis) as mock_synth,
        patch("analysis.consensus.get_embeddings_batch", return_value=[[1.0, 0.0], [1.0, 0.0]]),
        patch("analysis.consensus.add_memory", return_value="mem-uuid-123") as mock_add_mem,
    ):
        mock_disc.return_value.discover_assets = AsyncMock(return_value=[])

        results = await process_consensus(sample_events, threshold=2.0)
        assert len(results) == 1

        # Check that candidate parallels were passed to synthesize_event
        assert mock_synth.called
        synth_call_kwargs = mock_synth.call_args.kwargs
        assert "candidate_parallels" in synth_call_kwargs
        assert "2024 Red Sea Tanker Disruptions" in synth_call_kwargs["candidate_parallels"]
        assert "1973 Oil Embargo" in synth_call_kwargs["candidate_parallels"]

        # Check memory persistence
        assert mock_add_mem.called
        add_kwargs = mock_add_mem.call_args.kwargs
        assert "[Historical Parallel: 2024 Red Sea Tanker Disruptions (Jan - Mar 2024)]" in add_kwargs["content"]
        assert "metadata" in add_kwargs
        assert "historical_parallel" in add_kwargs["metadata"]
        hp_meta = add_kwargs["metadata"]["historical_parallel"]
        assert hp_meta["title"] == "2024 Red Sea Tanker Disruptions"
        assert hp_meta["timeframe"] == "Jan - Mar 2024"
        assert hp_meta["affected_assets"] == ["USO", "FRO"]
