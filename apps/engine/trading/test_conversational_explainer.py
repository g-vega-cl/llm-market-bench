"""Tests for decoupled conversational trader and audience Q&A explainer."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from trading.conversational_explainer import (
    extract_search_keywords,
    format_qa_context,
    process_pending_queue_item,
    retrieve_qa_grounding,
)


def test_extract_search_keywords():
    words = extract_search_keywords("What do you think will happen after midterms?")
    assert "midterms" in words or "midterm" in words
    assert "think" in words or "happen" in words


@pytest.mark.asyncio
async def test_retrieve_qa_grounding_queries_memories_and_trader_state():
    sb_mock = MagicMock()

    # Mock market_feeling select
    mf_mock = MagicMock()
    mf_mock.select.return_value.order.return_value.limit.return_value.execute.return_value.data = [
        {
            "id": "mf-1",
            "sentiment_label": "Accumulating Dips",
            "why_explanation": "SPY trades above VWAP with bullish RSI.",
            "trades_summary": {"action": "BUY", "technicals": {"vwap": 753.88, "rsi_14": 67.2}},
        }
    ]

    # Mock memories select
    mem_mock = MagicMock()
    mem_mock.select.return_value.or_.return_value.order.return_value.limit.return_value.execute.return_value.data = [
        {"id": "mem-midterm", "content": "2026 US Midterms could lead to legislative gridlock.", "importance_score": 8}
    ]

    def table_router(table_name):
        if table_name == "market_feeling":
            return mf_mock
        if table_name == "memories":
            return mem_mock
        dummy = MagicMock()
        dummy.select.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        return dummy

    sb_mock.table.side_effect = table_router

    grounding = await retrieve_qa_grounding(sb_mock, query="What do you think will happen after midterms?")

    assert "recent_decisions" in grounding
    assert len(grounding["recent_decisions"]) == 1
    assert grounding["recent_decisions"][0]["sentiment_label"] == "Accumulating Dips"

    assert "memories" in grounding
    assert len(grounding["memories"]) >= 1


def test_format_qa_context():
    grounding = {
        "recent_decisions": [
            {
                "sentiment_label": "Defensive Cash",
                "why_explanation": "Holding cash due to high volatility.",
                "trades_summary": {"action": "HOLD", "technicals": {"vwap": 750.0, "rsi_14": 55.0}},
            }
        ],
        "memories": [
            {"id": "m1", "content": "Historical midterms result in relief rally post-election.", "importance_score": 9}
        ],
        "cause_and_effect": [
            {"analysis": "Elections induce gridlock", "market_outcome": "Equities rally 4% over following quarter"}
        ],
        "barometer": {"pe_ratio": 22.5, "forward_pe": 19.8},
        "catalyst_radar": [{"concept_name": "Election Day", "catalyst_title": "Congressional vote"}],
    }

    formatted = format_qa_context(grounding)
    assert "TRADING DESK RECENT CHOICES & POSITIONING" in formatted
    assert "HISTORICAL PRECEDENTS & RETRIEVED MEMORIES" in formatted
    assert "CAUSAL CHAINS" in formatted
    assert "Defensive Cash" in formatted
    assert "Historical midterms result in relief rally" in formatted


@pytest.mark.asyncio
async def test_process_pending_queue_item_when_empty():
    sb_mock = MagicMock()
    # pop_next_queue_item returns empty list
    sb_mock.rpc.return_value.execute.return_value.data = []

    res = await process_pending_queue_item(
        sb_client=sb_mock,
        http_client=AsyncMock(),
        strata_url="http://mock:8080",
        cheap_proxy_url="http://mock:8086",
    )
    assert res is None


@pytest.mark.asyncio
async def test_process_pending_queue_item_answers_with_conversational_markdown():
    sb_mock = MagicMock()

    # Mock pop_next_queue_item returning a pending question
    popped_item = {
        "id": "q-123",
        "message": "What do you think will happen after midterms?",
        "display_name": "g.vega.cl",
        "user_id": "u-456",
    }
    sb_mock.rpc.return_value.execute.return_value.data = [popped_item]

    # Mock table routing
    update_mock = MagicMock()
    update_mock.update.return_value.eq.return_value.execute.return_value = MagicMock()

    dummy_table = MagicMock()
    dummy_table.select.return_value.order.return_value.limit.return_value.execute.return_value.data = []
    dummy_table.select.return_value.or_.return_value.order.return_value.limit.return_value.execute.return_value.data = [
        {"id": "mem-1", "content": "Midterm gridlock historically spurs equity expansion.", "importance_score": 9}
    ]

    def table_router(table_name):
        if table_name == "agent_chat_queue":
            return update_mock
        return dummy_table

    sb_mock.table.side_effect = table_router

    # Mock query_multi_tier_llm
    with patch(
        "trading.conversational_explainer.query_multi_tier_llm",
        new=AsyncMock(
            return_value="Heading into midterms, our memories show divided government historically relieves tariff uncertainty."
        ),
    ) as mock_llm:
        res = await process_pending_queue_item(
            sb_client=sb_mock,
            http_client=AsyncMock(),
            strata_url="http://mock:8080",
            cheap_proxy_url="http://mock:8086",
        )

        assert res is not None
        assert res["id"] == "q-123"
        assert "divided government historically relieves tariff uncertainty" in res["response"]

        # Verify prompt passed to LLM was conversational (not JSON schema)
        call_args = mock_llm.call_args
        messages = call_args.kwargs["messages"]
        system_msg = messages[0]["content"]
        assert "Chief Market Strategist and Conversational Trader" in system_msg
        assert "Respond ONLY with valid JSON" not in system_msg
        assert "action" not in system_msg

        # Verify DB update was executed with answered status
        update_mock.update.assert_called_once()
        update_payload = update_mock.update.call_args[0][0]
        assert update_payload["status"] == "answered"
        assert "divided government" in update_payload["agent_response"]


@pytest.mark.asyncio
async def test_process_pending_queue_item_formats_clean_desk_notice_on_llm_outage():
    import json

    sb_mock = MagicMock()
    popped_item = {
        "id": "q-crash",
        "message": "Will the market keep crashing?",
        "display_name": "g.vega.cl",
        "user_id": "u-456",
    }
    sb_mock.rpc.return_value.execute.return_value.data = [popped_item]

    update_mock = MagicMock()
    update_mock.update.return_value.eq.return_value.execute.return_value = MagicMock()

    dummy_table = MagicMock()
    dummy_table.select.return_value.order.return_value.limit.return_value.execute.return_value.data = []

    def table_router(table_name):
        if table_name == "agent_chat_queue":
            return update_mock
        return dummy_table

    sb_mock.table.side_effect = table_router

    fallback_json = json.dumps(
        {
            "action": "HOLD",
            "conviction": 50,
            "thought": "All LLM endpoints currently unavailable; holding neutral position.",
            "memories_consulted": [],
            "allocation_pct": 0,
        }
    )

    with patch(
        "trading.conversational_explainer.query_multi_tier_llm",
        new=AsyncMock(return_value=fallback_json),
    ):
        res = await process_pending_queue_item(
            sb_client=sb_mock,
            http_client=AsyncMock(),
            strata_url="http://mock:8080",
            cheap_proxy_url="http://mock:8086",
        )

        assert res is not None
        assert res["id"] == "q-crash"
        # Must NOT return raw JSON
        assert '{"action": "HOLD"' not in res["response"]
        assert "Desk Notice" in res["response"]
        assert "temporarily experiencing high inquiry volume" in res["response"]

        # Verify DB update was executed with prose response, NOT raw JSON
        update_mock.update.assert_called_once()
        update_payload = update_mock.update.call_args[0][0]
        assert update_payload["status"] == "answered"
        assert '{"action": "HOLD"' not in update_payload["agent_response"]
        assert "Desk Notice" in update_payload["agent_response"]
