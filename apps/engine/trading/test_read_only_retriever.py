"""Hermetic unit tests for read-only data & memory retriever."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from trading.read_only_retriever import (
    format_read_only_grounding,
    retrieve_read_only_market_data,
)


@pytest.mark.asyncio
async def test_retrieve_read_only_market_data_fetches_all_domains():
    mock_sb = MagicMock()

    # Mock memories
    mock_memories_resp = MagicMock()
    mock_memories_resp.data = [
        {"id": "mem-1", "content": "SPY morning dip absorption rule", "ticker": "SPY", "importance_score": 8}
    ]

    # Mock cause_and_effect
    mock_ce_resp = MagicMock()
    mock_ce_resp.data = [{"id": "ce-1", "cause": "Fed rate cut pause", "effect": "Growth stock compression"}]

    # Mock trades
    mock_trades_resp = MagicMock()
    mock_trades_resp.data = [
        {"id": "tr-1", "ticker": "SPY", "action": "BUY", "execution_price": 580.5, "reasoning": "VWAP bounce"}
    ]

    # Mock decisions
    mock_dec_resp = MagicMock()
    mock_dec_resp.data = [
        {"id": "dec-1", "ticker": "SPY", "action": "BUY", "confidence_score": 80, "reasoning": "Trend strength"}
    ]

    # Mock barometer
    mock_baro_resp = MagicMock()
    mock_baro_resp.data = [{"id": "baro-1", "score": 72, "status": "BULLISH", "regime": "ACCUMULATION"}]

    # Mock catalyst_radar
    mock_radar_resp = MagicMock()
    mock_radar_resp.data = [
        {"id": "rad-1", "narrative": "Semiconductor earnings", "catalyst": "NVDA print", "urgency": "HIGH"}
    ]

    def mock_table(table_name: str):
        builder = MagicMock()
        select_builder = MagicMock()
        builder.select.return_value = select_builder
        select_builder.order.return_value = select_builder
        select_builder.limit.return_value = select_builder
        select_builder.ilike.return_value = select_builder

        if table_name == "memories":
            select_builder.execute.return_value = mock_memories_resp
        elif table_name == "cause_and_effect":
            select_builder.execute.return_value = mock_ce_resp
        elif table_name == "trades":
            select_builder.execute.return_value = mock_trades_resp
        elif table_name == "decisions":
            select_builder.execute.return_value = mock_dec_resp
        elif table_name == "market_barometer":
            select_builder.execute.return_value = mock_baro_resp
        elif table_name == "catalyst_radar":
            select_builder.execute.return_value = mock_radar_resp
        else:
            empty_resp = MagicMock()
            empty_resp.data = []
            select_builder.execute.return_value = empty_resp
        return builder

    mock_sb.table.side_effect = mock_table

    data = await retrieve_read_only_market_data(
        sb_client=mock_sb,
        query="What happened during the last Fed rate pause?",
        ticker="SPY",
    )

    assert "memories" in data
    assert len(data["memories"]) == 1
    assert data["memories"][0]["id"] == "mem-1"

    assert "cause_and_effect" in data
    assert len(data["cause_and_effect"]) == 1

    assert "trades" in data
    assert "decisions" in data
    assert "barometer" in data
    assert "catalyst_radar" in data

    grounding_text = format_read_only_grounding(data)
    assert "HISTORICAL MEMORIES & LESSONS" in grounding_text
    assert "SPY morning dip absorption rule" in grounding_text
    assert "CAUSAL CHAINS" in grounding_text
    assert "Fed rate cut pause" in grounding_text
    assert "RECENT TRADES & AUDIT DECISIONS" in grounding_text
    assert "VWAP bounce" in grounding_text


@pytest.mark.asyncio
async def test_retrieve_read_only_market_data_production_schema():
    mock_sb = MagicMock()
    select_calls = {}

    def mock_table(table_name: str):
        builder = MagicMock()
        select_builder = MagicMock()

        def capture_select(cols: str):
            select_calls[table_name] = cols
            return select_builder

        builder.select.side_effect = capture_select
        select_builder.order.return_value = select_builder
        select_builder.limit.return_value = select_builder
        select_builder.ilike.return_value = select_builder

        mock_resp = MagicMock()
        if table_name == "memories":
            mock_resp.data = [{"id": "m1", "content": "SPY bounce memory", "importance_score": 9}]
        elif table_name == "cause_and_effect":
            mock_resp.data = [
                {"id": "ce1", "analysis": "Rate spike", "market_outcome": "Tech selloff", "confidence": 85}
            ]
        elif table_name == "trades":
            mock_resp.data = [
                {"id": "t1", "ticker": "SPY", "signal": "BUY", "price": 590.25, "reasoning": "Mean reversion"}
            ]
        elif table_name == "decisions":
            mock_resp.data = [
                {"id": "d1", "ticker": "SPY", "signal": "HOLD", "confidence": 75, "reasoning": "Choppy tape"}
            ]
        elif table_name == "market_barometer_history":
            mock_resp.data = [
                {"date": "2026-10-30", "pe_ratio": 26.5, "forward_pe": 22.1, "earnings_surprise_momentum": 1.4}
            ]
        elif table_name == "catalyst_radar":
            mock_resp.data = [
                {
                    "id": "c1",
                    "concept_name": "AI CapEx",
                    "catalyst_title": "Mega-cap guidance",
                    "impact": "BULLISH",
                    "target_date": "2026-11-05",
                }
            ]
        else:
            mock_resp.data = []

        select_builder.execute.return_value = mock_resp
        return builder

    mock_sb.table.side_effect = mock_table

    data = await retrieve_read_only_market_data(
        sb_client=mock_sb,
        query="rate cut",
        ticker="SPY",
    )

    # Verify queries use the production PostgreSQL table & column schemas
    assert "content" in select_calls.get("memories", "")
    assert "ticker" not in select_calls.get("memories", "")  # memories has no ticker column
    assert "analysis" in select_calls.get("cause_and_effect", "")
    assert "market_outcome" in select_calls.get("cause_and_effect", "")
    assert "signal" in select_calls.get("trades", "")
    assert "price" in select_calls.get("trades", "")
    assert "signal" in select_calls.get("decisions", "")
    assert "confidence" in select_calls.get("decisions", "")
    assert "market_barometer_history" in select_calls
    assert "concept_name" in select_calls.get("catalyst_radar", "")
    assert "catalyst_title" in select_calls.get("catalyst_radar", "")

    # Verify formatting with production schema keys
    text = format_read_only_grounding(data)
    assert "Cause: Rate spike -> Outcome: Tech selloff" in text
    assert "Trade: BUY SPY @ $590.25 - Mean reversion" in text
    assert "Decision: HOLD SPY (Conv: 75%) - Choppy tape" in text
    assert "Barometer (2026-10-30): P/E 26.5" in text
    assert "Catalyst: [BULLISH] AI CapEx (Mega-cap guidance)" in text


def test_format_read_only_grounding_tolerates_null_columns():
    """Live rows carry explicit NULLs (e.g. trades.reasoning); formatting must not crash."""
    data = {
        "memories": [{"id": "m1", "content": None, "importance_score": None}],
        "cause_and_effect": [{"id": "ce1", "analysis": None, "market_outcome": None}],
        "trades": [{"id": "t1", "ticker": "SPY", "signal": "BUY", "price": None, "reasoning": None}],
        "decisions": [{"id": "d1", "ticker": "SPY", "signal": "HOLD", "confidence": None, "reasoning": None}],
        "barometer": None,
        "catalyst_radar": [{"concept_name": None, "catalyst_title": None, "impact": None}],
    }

    text = format_read_only_grounding(data)

    assert "Trade: BUY SPY @ $0.00" in text
    assert "Decision: HOLD SPY" in text
