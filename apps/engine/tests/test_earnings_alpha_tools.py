"""Unit tests for the earnings alpha canonical LLM tools."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from core.llm.handlers.base import execute_tool
from tools.earnings_alpha_tools import (
    handle_get_earnings_revisions,
    handle_get_pead_candidates,
    handle_get_sector_bellwethers,
)


@pytest.mark.asyncio
async def test_get_pead_candidates_tool_filtering():
    """Verify get_pead_candidates returns top-decile SUE candidates with clear fields."""
    mock_db_records = [
        {
            "ticker": "NVDA",
            "sector": "XLK",
            "report_date": "2026-08-26",
            "sue_score": 5.30,
            "is_top_decile_sue": True,
            "revenue_surprise_pct": 4.28,
            "has_sufficient_earnings_history": True,
            "is_sloan_accrual_clean": True,
            "has_extreme_pre_earnings_runup": False,
            "days_since_earnings_report": 7,
            "post_earnings_drift_pct": 6.2,
            "post_earnings_alpha_vs_spy": 4.1,
        },
        {
            "ticker": "INTC",
            "sector": "XLK",
            "report_date": "2026-08-20",
            "sue_score": 0.80,
            "is_top_decile_sue": False,
            "revenue_surprise_pct": -1.2,
            "has_sufficient_earnings_history": True,
            "is_sloan_accrual_clean": False,
            "has_extreme_pre_earnings_runup": False,
            "days_since_earnings_report": 13,
            "post_earnings_drift_pct": -3.5,
            "post_earnings_alpha_vs_spy": -5.0,
        },
    ]

    with patch("tools.earnings_alpha_tools.fetch_pead_candidates_from_db", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_db_records

        result_json = await handle_get_pead_candidates({"sector": "XLK", "min_sue": 2.0})
        data = json.loads(result_json)

        assert data["count"] == 1
        candidate = data["candidates"][0]
        assert candidate["ticker"] == "NVDA"
        assert candidate["sue_score"] == 5.30
        assert candidate["is_top_decile_sue"] is True
        assert candidate["has_sufficient_earnings_history"] is True
        assert candidate["is_sloan_accrual_clean"] is True


@pytest.mark.asyncio
async def test_get_earnings_revisions_tool():
    """Verify get_earnings_revisions returns analyst consensus and upside distribution."""
    mock_fmp_grades = {
        "symbol": "NVDA",
        "strongBuy": 2,
        "buy": 58,
        "hold": 16,
        "sell": 3,
        "strongSell": 0,
        "consensus": "Buy",
    }
    mock_fmp_target = {
        "symbol": "NVDA",
        "targetHigh": 515.0,
        "targetLow": 270.0,
        "targetConsensus": 345.21,
        "targetMedian": 322.5,
    }

    with patch("tools.earnings_alpha_tools.fetch_fmp_grades_and_targets", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = (mock_fmp_grades, mock_fmp_target, 300.0)

        result_json = await handle_get_earnings_revisions({"ticker": "NVDA"})
        data = json.loads(result_json)

        assert data["ticker"] == "NVDA"
        assert data["analyst_consensus"] == "Buy"
        assert data["analyst_coverage_count"] == 79
        assert data["analyst_buy_ratio_pct"] == pytest.approx(75.9, rel=1e-1)
        assert data["target_consensus_price"] == 345.21
        assert data["target_consensus_upside_pct"] == pytest.approx(15.07, rel=1e-1)


@pytest.mark.asyncio
async def test_get_sector_bellwethers_tool():
    """Verify get_sector_bellwethers returns active reported signals and unannounced peers."""
    mock_bellwether_data = {
        "sector": "XLF",
        "active_reported_bellwethers": [
            {
                "ticker": "JPM",
                "report_date": "2026-07-14",
                "sue_score": 7.77,
                "revenue_surprise_pct": 13.06,
                "days_since_report": 10,
                "is_active_bellwether_signal": True,
            }
        ],
        "unannounced_peers": [
            {
                "ticker": "MS",
                "upcoming_earnings_date": "2026-10-16",
                "days_until_report": 44,
            }
        ],
    }

    with patch("tools.earnings_alpha_tools.fetch_sector_bellwethers_from_db", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_bellwether_data

        result_json = await handle_get_sector_bellwethers({"sector": "XLF"})
        data = json.loads(result_json)

        assert data["sector"] == "XLF"
        assert len(data["active_reported_bellwethers"]) == 1
        assert data["active_reported_bellwethers"][0]["ticker"] == "JPM"
        assert len(data["unannounced_peers"]) == 1
        assert data["unannounced_peers"][0]["ticker"] == "MS"


@pytest.mark.asyncio
async def test_tool_dispatcher_dispatches_earnings_alpha_tools():
    """Verify execute_tool dispatches to earnings alpha tools cleanly."""
    with patch("tools.earnings_alpha_tools.handle_get_pead_candidates", new_callable=AsyncMock) as mock_handler:
        mock_handler.return_value = json.dumps({"status": "ok"})
        res = await execute_tool("get_pead_candidates", {"sector": "XLK"}, "model-test")
        assert "status" in res
