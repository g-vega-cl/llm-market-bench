"""Tests for the Government Ingestion Pipeline."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.models import DecisionsResponse, MacroEvent
from ingest.government import GovernmentPipeline


@pytest.mark.asyncio
async def test_government_pipeline_await_crash():
    """Test that GovernmentPipeline.run() works without raising a TypeError from awaiting the Gemini call."""
    mock_client = MagicMock()
    mock_supabase = MagicMock()

    # Mock Gemini client chat.completions.create return value
    # If the client is synchronous, create() returns a DecisionsResponse.
    # If it is async, it returns a coroutine. Let's start with a synchronous return
    # to reproduce the TypeErrors that occur when awaiting a sync return.
    mock_response = DecisionsResponse(
        decisions=[],
        macro_events=[
            MacroEvent(
                event_name="Test Policy",
                impact="BULLISH",
                confidence=80,
                reasoning="Test policy reasoning",
                source_id="test_src",
            )
        ],
    )
    mock_client.chat.completions.create.return_value = mock_response

    with (
        patch("ingest.government.get_gemini_client", return_value=mock_client),
        patch("ingest.government.get_supabase_client", return_value=mock_supabase),
        patch("ingest.government.add_memory", return_value="some-uuid") as mock_add_memory,
        patch(
            "ingest.government.GovernmentPipeline.fetch_policy_grounding_context",
            new_callable=AsyncMock,
            return_value="Federal Register Document: Test Infrastructure Rule (2026-11-10)",
        ),
        patch("ingest.government.GovernmentPipeline.ingest_liquidity", return_value=0),
        patch("ingest.government.GovernmentPipeline.ingest_contracts", return_value={}),
        patch("ingest.government.GovernmentPipeline.ingest_whales", return_value={}),
        patch("ingest.government.GovernmentPipeline.ingest_congress", return_value=0),
        patch("ingest.government.GovernmentPipeline.ingest_insiders", return_value=0),
    ):
        pipeline = GovernmentPipeline()
        count = await pipeline.run()

        assert count == 1
        mock_add_memory.assert_called_once()
        assert "Test Policy" in mock_add_memory.call_args[1]["content"]


@pytest.mark.asyncio
async def test_extract_policy_memories_skips_when_ungrounded():
    """Verify extract_policy_memories refuses to call LLM when no real grounding context is retrieved."""
    mock_client = MagicMock()
    with (
        patch("ingest.government.get_gemini_client", return_value=mock_client),
        patch("ingest.government.get_supabase_client", return_value=MagicMock()),
        patch(
            "ingest.government.GovernmentPipeline.fetch_policy_grounding_context",
            new_callable=AsyncMock,
            return_value="",
        ),
    ):
        pipeline = GovernmentPipeline()
        count = await pipeline.extract_policy_memories()

        assert count == 0
        mock_client.chat.completions.create.assert_not_called()


@pytest.mark.asyncio
async def test_extract_policy_memories_passes_grounded_context():
    """Verify Federal Register docs and gov DB context are injected into Gemini policy synthesis."""
    mock_client = MagicMock()
    mock_response = DecisionsResponse(
        decisions=[],
        macro_events=[
            MacroEvent(
                event_name="CHIPS Act Foundry Grant Expansion",
                impact="BULLISH",
                confidence=85,
                reasoning="Federal Register notice confirms domestic semiconductor allocation.",
                source_id="fr_2026_1",
            )
        ],
    )
    mock_client.chat.completions.create.return_value = mock_response

    mock_sb = MagicMock()

    def route_table(name):
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.gte.return_value = chain
        chain.order.return_value = chain
        chain.limit.return_value = chain
        if name == "gov_contracts":
            chain.execute.return_value = MagicMock(
                data=[
                    {
                        "country": "US",
                        "recipient_name": "LOCKHEED MARTIN CORP",
                        "award_amount": 450000000.0,
                        "agency_name": "Department of Defense",
                        "award_date": "2026-11-10",
                        "description": "Next-gen interceptor contract",
                    }
                ]
            )
        elif name == "gov_macro_liquidity":
            chain.execute.return_value = MagicMock(
                data=[
                    {
                        "record_date": "2026-11-12",
                        "tga_balance": 815000000000.0,
                        "monthly_deficit_surplus": -120000000000.0,
                    }
                ]
            )
        else:
            chain.execute.return_value = MagicMock(data=[])
        return chain

    mock_sb.table.side_effect = route_table

    fr_docs = [
        {
            "document_number": "2026-24100",
            "title": "Semiconductor Manufacturing Incentive Rule",
            "publication_date": "2026-11-12",
            "agency_names": ["Department of Commerce"],
            "abstract": "Expands domestic semiconductor tax credits and awards.",
        }
    ]

    with (
        patch("ingest.government.get_gemini_client", return_value=mock_client),
        patch("ingest.government.get_supabase_client", return_value=mock_sb),
        patch("ingest.government.fetch_federal_register_documents", new_callable=AsyncMock, return_value=fr_docs),
        patch("ingest.government.add_memory", return_value="mem-uuid") as mock_add_memory,
    ):
        pipeline = GovernmentPipeline()
        count = await pipeline.extract_policy_memories()

        assert count == 1
        sent_messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
        user_prompt = sent_messages[1]["content"]
        assert "Semiconductor Manufacturing Incentive Rule" in user_prompt
        assert "LOCKHEED MARTIN CORP" in user_prompt
        mock_add_memory.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_federal_register_documents_parses_results():
    """Verify Federal Register API documents are parsed and truncated cleanly."""
    from ingest.federal_register import fetch_federal_register_documents

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": [
            {
                "document_number": "2026-99999",
                "title": "Critical Minerals Tax Credit Rule",
                "type": "Rule",
                "publication_date": "2026-11-12",
                "agencies": [{"name": "Department of Energy"}],
                "abstract": "Expands domestic lithium refining eligibility.",
                "html_url": "https://www.federalregister.gov/d/2026-99999",
            }
        ]
    }
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    with patch("ingest.federal_register.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value = mock_client
        docs = await fetch_federal_register_documents(limit=5)

    assert len(docs) == 1
    assert docs[0]["document_number"] == "2026-99999"
    assert docs[0]["agency_names"] == ["Department of Energy"]
