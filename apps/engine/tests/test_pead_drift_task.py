"""Unit tests for the PEAD Drift scheduled task.

Hermetic tests with zero live network calls.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tasks.pead_drift_task import (
    evaluate_candidate_with_jev,
    run_pead_drift_task,
)


@pytest.mark.asyncio
async def test_evaluate_candidate_with_jev_qualified():
    """Verify evaluate_candidate_with_jev parses QUALIFIED decision from OpenRouter Decisions API."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "answers": {
            "pead_admission": {
                "type": "choice",
                "choice": "QUALIFIED",
                "confidence": 0.85,
                "probabilities": {"QUALIFIED": 0.85, "DISQUALIFIED": 0.15},
            }
        }
    }
    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    candidate = {
        "ticker": "NVDA",
        "sue_score": 5.2,
        "revenue_surprise_pct": 8.0,
        "sloan_accrual_ratio": 0.04,
        "report_date": "2026-09-01",
    }

    with (
        patch("tasks.pead_drift_task.httpx.AsyncClient", return_value=mock_client),
        patch("tasks.pead_drift_task.OPENROUTER_API_KEY", "test-key"),
    ):
        res = await evaluate_candidate_with_jev(candidate)
        assert res["is_qualified"] is True
        assert res["confidence"] == 85.0
        assert res["choice"] == "QUALIFIED"


@pytest.mark.asyncio
async def test_evaluate_candidate_with_jev_disqualified():
    """Verify evaluate_candidate_with_jev rejects candidates flagged DISQUALIFIED or low confidence."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "answers": {
            "pead_admission": {
                "type": "choice",
                "choice": "DISQUALIFIED",
                "confidence": 0.90,
                "probabilities": {"QUALIFIED": 0.10, "DISQUALIFIED": 0.90},
            }
        }
    }
    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    candidate = {
        "ticker": "BAD1",
        "sue_score": 2.1,
        "revenue_surprise_pct": -1.0,
        "sloan_accrual_ratio": 0.15,
        "report_date": "2026-09-01",
    }

    with (
        patch("tasks.pead_drift_task.httpx.AsyncClient", return_value=mock_client),
        patch("tasks.pead_drift_task.OPENROUTER_API_KEY", "test-key"),
    ):
        res = await evaluate_candidate_with_jev(candidate)
        assert res["is_qualified"] is False
        assert res["choice"] == "DISQUALIFIED"


@pytest.mark.asyncio
async def test_run_pead_drift_task_dry_run():
    """Verify dry_run=True computes plan and does not execute database trades."""
    mock_supabase = MagicMock()
    mock_candidates = [
        {
            "ticker": "NVDA",
            "sue_score": 4.5,
            "revenue_surprise_pct": 5.0,
            "sloan_accrual_ratio": 0.02,
            "is_sloan_accrual_clean": True,
            "report_date": "2026-09-02",
        }
    ]

    mock_portfolio = MagicMock()
    mock_portfolio.id = "mock-pead-portfolio-id"
    mock_portfolio.cash_balance = 10000.0
    mock_portfolio.positions = {}
    mock_portfolio.initialize = AsyncMock()
    mock_portfolio.execute_trade = AsyncMock()

    mock_jev_eval = {
        "is_qualified": True,
        "confidence": 80.0,
        "choice": "QUALIFIED",
        "probabilities": {"QUALIFIED": 0.80, "DISQUALIFIED": 0.20},
    }

    with (
        patch("tasks.pead_drift_task.get_supabase_client", return_value=mock_supabase),
        patch("tasks.pead_drift_task.Portfolio", return_value=mock_portfolio),
        patch("tasks.pead_drift_task.fetch_pead_candidates_for_evaluation", return_value=mock_candidates),
        patch("tasks.pead_drift_task.evaluate_candidate_with_jev", new_callable=AsyncMock, return_value=mock_jev_eval),
        patch("tasks.pead_drift_task.fetch_current_price", return_value=120.0),
    ):
        res = await run_pead_drift_task(dry_run=True)

        assert res["status"] == "success"
        assert res["dry_run"] is True
        assert len(res["buys"]) == 1
        assert res["buys"][0]["ticker"] == "NVDA"
        # Verify execute_trade was NOT called on portfolio
        mock_portfolio.execute_trade.assert_not_called()


def test_fetch_pead_candidates_for_evaluation():
    """Verify fetch_pead_candidates_for_evaluation calls Supabase with correct filters."""
    from tasks.pead_drift_task import fetch_pead_candidates_for_evaluation

    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.gte.return_value.lte.return_value.order.return_value.order.return_value.limit.return_value.execute.return_value.data = [
        {"ticker": "NVDA", "sue_score": 5.2}
    ]

    res = fetch_pead_candidates_for_evaluation(mock_supabase, min_sue=2.0, max_days_since_report=5, limit=10)
    assert len(res) == 1
    assert res[0]["ticker"] == "NVDA"


@pytest.mark.asyncio
async def test_run_pead_drift_task_live_execution():
    """Verify live mode executes trades and updates performance."""
    mock_supabase = MagicMock()
    mock_candidates = [
        {
            "ticker": "AAPL",
            "sue_score": 3.0,
            "revenue_surprise_pct": 4.0,
            "sloan_accrual_ratio": 0.01,
            "is_sloan_accrual_clean": True,
            "report_date": "2026-09-02",
        }
    ]

    mock_portfolio = MagicMock()
    mock_portfolio.id = "pead-live-uuid"
    mock_portfolio.cash_balance = 5000.0
    mock_portfolio.positions = {}
    mock_portfolio.initialize = AsyncMock()
    mock_portfolio.execute_trade = AsyncMock()

    mock_jev_eval = {
        "is_qualified": True,
        "confidence": 75.0,
        "choice": "QUALIFIED",
        "probabilities": {"QUALIFIED": 0.75, "DISQUALIFIED": 0.25},
    }

    with (
        patch("tasks.pead_drift_task.get_supabase_client", return_value=mock_supabase),
        patch("tasks.pead_drift_task.Portfolio", return_value=mock_portfolio),
        patch("tasks.pead_drift_task.fetch_pead_candidates_for_evaluation", return_value=mock_candidates),
        patch("tasks.pead_drift_task.evaluate_candidate_with_jev", new_callable=AsyncMock, return_value=mock_jev_eval),
        patch("tasks.pead_drift_task.fetch_current_price", return_value=200.0),
    ):
        res = await run_pead_drift_task(dry_run=False)

        assert res["status"] == "success"
        assert res["dry_run"] is False
        assert len(res["buys"]) == 1
        assert res["buys"][0]["ticker"] == "AAPL"
        # Verify execute_trade was called on portfolio
        mock_portfolio.execute_trade.assert_called_once()
        assert mock_supabase.table.return_value.upsert.called
