"""Tests for Hard Tool Enforcement in analysis.py."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from core.llm.analysis import analyze_with_provider, _scan_history_for_tools, _validate_and_enrich_government_events
from analysis.consensus import _is_vague_government_event
from core.models import DecisionsResponse, DecisionObject, MacroEvent

@pytest.fixture
def mock_clients():
    """Mocks LLM clients and handlers."""
    with patch("core.llm.clients.CLIENT_FACTORIES") as mock_factories:
        mock_factory = MagicMock()
        mock_client = MagicMock()
        mock_factory.return_value = mock_client
        mock_factories.get.return_value = mock_factory
        
        # Mock Instructor-wrapped client
        mock_instructor_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock()
        
        yield {
            "factory": mock_factory,
            "client": mock_client,
            "instructor": mock_client.chat.completions
        }

def test_scan_history_openai_format():
    """Verify scanning OpenAI-style message history for quantity tools."""
    messages = [
        {"role": "user", "content": "Sell AAPL"},
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "function": {"name": "calculate_sell_quantity", "arguments": '{"ticker": "AAPL", "percentage": 50}'},
                    "id": "call_1"
                },
                {
                    "function": {"name": "calculate_buy_quantity", "arguments": '{"ticker": "AAPL", "percentage": 20}'},
                    "id": "call_2"
                }
            ]
        }
    ]
    
    res = _scan_history_for_tools(messages, "AAPL")
    assert res["sell_tool_found"] is True
    assert res["buy_tool_found"] is True
    
    res_msft = _scan_history_for_tools(messages, "MSFT")
    assert res_msft["sell_tool_found"] is False
    assert res_msft["buy_tool_found"] is False

def test_scan_history_anthropic_format():
    """Verify scanning Anthropic-style message history for quantity tools."""
    messages = [
        {"role": "user", "content": "Sell TSLA"},
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Let me check..."},
                {"type": "tool_use", "name": "calculate_sell_quantity", "input": {"ticker": "TSLA", "percentage": 100}, "id": "u1"}
            ]
        }
    ]
    
    res = _scan_history_for_tools(messages, "TSLA")
    assert res["sell_tool_found"] is True
    assert res["buy_tool_found"] is False

def test_scan_history_gemini_format():
    """Verify scanning Gemini-style native content history."""
    class MockFunctionCall:
        def __init__(self, name, args):
            self.name = name
            self.args = args

    class MockPart:
        def __init__(self, name, args):
            self.function_call = MockFunctionCall(name, args)
            
    class MockContent:
        def __init__(self, parts):
            self.parts = parts
            
    messages = [
        MockContent([
            MockPart("calculate_buy_quantity", {"ticker": "GOOG", "percentage": 50}),
            MockPart("calculate_sell_quantity", {"ticker": "GOOG", "percentage": 100})
        ])
    ]
    
    res = _scan_history_for_tools(messages, "GOOG")
    assert res["buy_tool_found"] is True
    assert res["sell_tool_found"] is True

def test_scan_history_robust_matching():
    """Verify that ticker matching is robust to spaces and casing."""
    messages = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "function": {"name": "calculate_buy_quantity", "arguments": '{"ticker": "  aapl  ", "percentage": 10}'},
                    "id": "c1"
                }
            ]
        }
    ]
    
    res = _scan_history_for_tools(messages, "AAPL")
    assert res["buy_tool_found"] is True
    
    res_messy = _scan_history_for_tools(messages, " aapl ")
    assert res_messy["buy_tool_found"] is True

@pytest.mark.asyncio
async def test_analyze_with_provider_hard_enforcement(mock_clients):
    """Verify that analyze_with_provider correctly updates sell_tool_called."""
    mock_instructor = mock_clients["instructor"]
    
    mock_instructor.create.return_value = [DecisionsResponse(
        decisions=[
            DecisionObject(
                signal="SELL",
                ticker="AAPL",
                confidence=90,
                reasoning="Test",
                source_id="s1",
                sell_tool_called=True,
                quantity=10
            )
        ],
        macro_events=[]
    )]
    
    with patch("core.llm.handlers.openai.run_tool_loop", new_callable=AsyncMock), \
         patch("core.llm.logger.log_reasoning_trace", new_callable=AsyncMock):
        resp = await analyze_with_provider(
            provider="openai",
            model_name="gpt-4",
            chunks=[{"source_id": "s1", "content": "..."}]
        )
        
    assert resp.decisions[0].ticker == "AAPL"
    assert resp.decisions[0].sell_tool_called is False


@pytest.mark.asyncio
async def test_validate_and_enrich_removes_vague_government_event():
    """When a vague government event exists and lookup fails, it should be removed."""
    response = DecisionsResponse(
        decisions=[],
        macro_events=[
            MacroEvent(
                event_name="Government Policy Update",
                impact="NEUTRAL",
                catalyst_type="REGULATORY",
                is_ongoing=False,
                is_future_catalyst=False,
                historical_parallel=None,
                is_government_incentive=True,
                expiry_date=None,
                importance_score=6,
                confidence=55,
                reasoning="Fallback event.",
                scenario_analysis=None,
                source_id="gov_1",
                model_provider="openai",
                model_name="gpt-4",
            )
        ],
    )

    chunks = [{"source_id": "gov_1", "content": "The government is considering new budget allocations."}]

    with patch("core.llm.analysis.lookup_policy", new_callable=AsyncMock) as mock_lookup:
        mock_lookup.return_value = None

        await _validate_and_enrich_government_events(
            response, chunks, "openai", "gpt-4"
        )

    assert len(response.macro_events) == 0


@pytest.mark.asyncio
async def test_validate_and_enrich_preserves_specific_event():
    """When a specific government event exists, it should be preserved unchanged."""
    response = DecisionsResponse(
        decisions=[],
        macro_events=[
            MacroEvent(
                event_name="US Farm Bill 2026 Agri-Tech Push",
                impact="BULLISH",
                catalyst_type="REGULATORY",
                is_ongoing=False,
                is_future_catalyst=False,
                historical_parallel=None,
                is_government_incentive=True,
                expiry_date="2026-12-31",
                importance_score=8,
                confidence=88,
                reasoning="Congress advanced new subsidy support for precision agriculture.",
                scenario_analysis="Scenario A: Passage -> Trading Plan: Buy DE.",
                source_id="gov_1",
                model_provider="openai",
                model_name="gpt-4",
            )
        ],
    )

    chunks = [{"source_id": "gov_1", "content": "Congress advanced new subsidy support for precision agriculture."}]

    with patch("core.llm.analysis.lookup_policy", new_callable=AsyncMock) as mock_lookup:
        await _validate_and_enrich_government_events(
            response, chunks, "openai", "gpt-4"
        )
        mock_lookup.assert_not_called()

    assert len(response.macro_events) == 1
    assert response.macro_events[0].event_name == "US Farm Bill 2026 Agri-Tech Push"


@pytest.mark.asyncio
async def test_validate_and_enrich_enriches_vague_event_on_lookup_success():
    """When a vague government event exists and lookup succeeds, it should be enriched."""
    response = DecisionsResponse(
        decisions=[],
        macro_events=[
            MacroEvent(
                event_name="Government Policy Update",
                impact="NEUTRAL",
                catalyst_type="REGULATORY",
                is_ongoing=False,
                is_future_catalyst=False,
                historical_parallel=None,
                is_government_incentive=True,
                expiry_date=None,
                importance_score=6,
                confidence=55,
                reasoning="Fallback event.",
                scenario_analysis=None,
                source_id="gov_1",
                model_provider="openai",
                model_name="gpt-4",
            )
        ],
    )

    chunks = [{"source_id": "gov_1", "content": "The CHIPS Act is advancing through Congress."}]

    from core.llm.policy_lookup import PolicyLookupResult

    mock_result = PolicyLookupResult(
        policy_name="CHIPS and Science Act",
        status="passed Senate",
        description="Provides $52B for domestic semiconductor manufacturing.",
        confidence=85,
    )

    with patch("core.llm.analysis.lookup_policy", new_callable=AsyncMock) as mock_lookup:
        mock_lookup.return_value = mock_result

        await _validate_and_enrich_government_events(
            response, chunks, "openai", "gpt-4"
        )

    assert len(response.macro_events) == 1
    assert response.macro_events[0].event_name == "CHIPS and Science Act [passed Senate]"
    assert response.macro_events[0].reasoning == "Provides $52B for domestic semiconductor manufacturing."
    assert response.macro_events[0].confidence == 85


def test_is_vague_government_event_true_for_generic_names():
    """Consensus helper should flag generic government event names as vague."""
    assert _is_vague_government_event("Ongoing Legislative Policy Developments") is True
    assert _is_vague_government_event("Government Policy Update") is True
    assert _is_vague_government_event("Government Policy Structural Update") is True
    assert _is_vague_government_event("Policy Structural Update") is True
    assert _is_vague_government_event("VAGUE_GOVERNMENT_EVENT") is True


def test_is_vague_government_event_false_for_specific_names():
    """Consensus helper should NOT flag specific government event names."""
    assert _is_vague_government_event("US Farm Bill 2026 Agri-Tech Push") is False
    assert _is_vague_government_event("CHIPS Act Expansion") is False
    assert _is_vague_government_event("EU Green Hydrogen Act") is False
    assert _is_vague_government_event("Japan GX Transformation Bonds") is False
    assert _is_vague_government_event("Fed Rate Cut Cycle") is False


def test_is_vague_government_event_false_for_non_policy_events():
    """Non-policy events should never be flagged as vague government."""
    assert _is_vague_government_event("AI Demand Surge", "tech sector rallies") is False
    assert _is_vague_government_event("Earnings Season Begins") is False
    assert _is_vague_government_event("Oil Supply Disruption") is False
