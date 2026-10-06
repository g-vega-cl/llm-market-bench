"""Unit tests for the Daily Options Max Pain scheduled task.

Hermetic tests with zero live network calls.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tasks.max_pain_task import (
    evaluate_candidate_with_jev,
    fetch_max_pain_snapshot,
    run_max_pain_task,
)


@pytest.mark.asyncio
async def test_evaluate_candidate_with_jev_qualified():
    """Verify evaluate_candidate_with_jev parses QUALIFIED decision from OpenRouter Decisions API."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "answers": {
            "max_pain_admission": {
                "type": "choice",
                "choice": "QUALIFIED",
                "confidence": 0.88,
                "probabilities": {"QUALIFIED": 0.88, "DISQUALIFIED": 0.12},
            }
        }
    }
    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    candidate = {
        "ticker": "SPY",
        "price": 555.0,
        "max_pain_strike": 560.0,
        "discount_pct": 0.90,
        "put_call_oi_ratio": 1.15,
        "atm_implied_volatility": 0.14,
    }

    with (
        patch("tasks.max_pain_task.httpx.AsyncClient", return_value=mock_client),
        patch("tasks.max_pain_task.OPENROUTER_API_KEY", "test-key"),
    ):
        res = await evaluate_candidate_with_jev(candidate)
        assert res["is_qualified"] is True
        assert res["confidence"] == 88.0
        assert res["choice"] == "QUALIFIED"


@pytest.mark.asyncio
async def test_evaluate_candidate_with_jev_disqualified():
    """Verify evaluate_candidate_with_jev rejects candidates flagged DISQUALIFIED or low confidence."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "answers": {
            "max_pain_admission": {
                "type": "choice",
                "choice": "DISQUALIFIED",
                "confidence": 0.95,
                "probabilities": {"QUALIFIED": 0.05, "DISQUALIFIED": 0.95},
            }
        }
    }
    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    candidate = {
        "ticker": "QQQ",
        "price": 485.0,
        "max_pain_strike": 480.0,
        "discount_pct": -1.03,
    }

    with (
        patch("tasks.max_pain_task.httpx.AsyncClient", return_value=mock_client),
        patch("tasks.max_pain_task.OPENROUTER_API_KEY", "test-key"),
    ):
        res = await evaluate_candidate_with_jev(candidate)
        assert res["is_qualified"] is False
        assert res["choice"] == "DISQUALIFIED"


@pytest.mark.asyncio
async def test_fetch_max_pain_snapshot_fallback():
    """Verify fetch_max_pain_snapshot falls back to Supabase options_data_cache if Massive client fails."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_eq = MagicMock()
    mock_exec = MagicMock()

    mock_exec.data = [{"metrics": {"max_pain": 560.0, "put_call_oi_ratio": 1.2}}]
    mock_eq.execute.return_value = mock_exec
    mock_select.eq.return_value = mock_eq
    mock_table.select.return_value = mock_select
    mock_sb.table.return_value = mock_table

    with (
        patch("tasks.max_pain_task.MassiveOptionsClient.get_options_snapshot", side_effect=RuntimeError("API 429")),
        patch("tasks.max_pain_task.get_supabase_client", return_value=mock_sb),
    ):
        metrics = await fetch_max_pain_snapshot("SPY")
        assert metrics is not None
        assert metrics["max_pain"] == 560.0


@pytest.mark.asyncio
async def test_run_max_pain_task_dry_run():
    """Verify dry_run=True computes plan and does not execute database trades."""
    mock_portfolio = MagicMock()
    mock_portfolio.positions = {}
    mock_portfolio.cash_balance = 10000.00
    mock_portfolio.id = "mock-portfolio-id"
    mock_portfolio.initialize = AsyncMock()

    mock_metrics = {
        "max_pain": 560.0,
        "underlying_price": 555.0,
        "put_call_oi_ratio": 1.1,
        "atm_implied_volatility": 0.15,
        "total_contracts_analyzed": 120,
    }

    mock_jev = {"is_qualified": True, "confidence": 85.0, "choice": "QUALIFIED"}

    with (
        patch("tasks.max_pain_task.Portfolio", return_value=mock_portfolio),
        patch("tasks.max_pain_task.fetch_max_pain_snapshot", new_callable=AsyncMock, return_value=mock_metrics),
        patch("tasks.max_pain_task.evaluate_candidate_with_jev", new_callable=AsyncMock, return_value=mock_jev),
        patch("tasks.max_pain_task.fetch_current_price", return_value=555.0),
    ):
        res = await run_max_pain_task(dry_run=True, tickers=["SPY"])
        assert res["status"] == "success"
        assert res["dry_run"] is True
        assert len(res["buys"]) == 1
        assert res["buys"][0]["ticker"] == "SPY"
        mock_portfolio.execute_trade.assert_not_called()


@pytest.mark.asyncio
async def test_run_max_pain_task_live_execution():
    """Verify live execution executes trades via portfolio and upserts performance."""
    mock_supabase = MagicMock()
    mock_table = MagicMock()
    mock_upsert = MagicMock()
    mock_exec = MagicMock()

    mock_upsert.execute.return_value = mock_exec
    mock_table.upsert.return_value = mock_upsert
    mock_supabase.table.return_value = mock_table

    mock_portfolio = MagicMock()
    mock_portfolio.positions = {}
    mock_portfolio.cash_balance = 10000.00
    mock_portfolio.id = "mock-portfolio-id"
    mock_portfolio.initialize = AsyncMock()
    mock_portfolio.execute_trade = AsyncMock()
    mock_portfolio.save_metrics = AsyncMock()

    mock_metrics = {
        "max_pain": 560.0,
        "underlying_price": 555.0,
        "put_call_oi_ratio": 1.1,
        "atm_implied_volatility": 0.15,
        "total_contracts_analyzed": 120,
    }

    mock_jev = {"is_qualified": True, "confidence": 85.0, "choice": "QUALIFIED"}

    with (
        patch("tasks.max_pain_task.Portfolio", return_value=mock_portfolio),
        patch("tasks.max_pain_task.get_supabase_client", return_value=mock_supabase),
        patch("tasks.max_pain_task.fetch_max_pain_snapshot", new_callable=AsyncMock, return_value=mock_metrics),
        patch("tasks.max_pain_task.evaluate_candidate_with_jev", new_callable=AsyncMock, return_value=mock_jev),
        patch("tasks.max_pain_task.fetch_current_price", return_value=555.0),
    ):
        res = await run_max_pain_task(dry_run=False, tickers=["SPY"])
        assert res["status"] == "success"
        assert res["dry_run"] is False
        assert len(res["buys"]) == 1
        mock_portfolio.execute_trade.assert_called_once()
        mock_portfolio.save_metrics.assert_called_once()
        mock_supabase.table.assert_called_with("portfolio_performance")


@pytest.mark.asyncio
async def test_run_max_pain_task_error_isolation():
    """Verify portfolio init failure returns graceful error status without unhandled exception."""
    with patch("tasks.max_pain_task.Portfolio", side_effect=RuntimeError("Database offline")):
        res = await run_max_pain_task(dry_run=True)
        assert res["status"] == "error"
        assert "Database offline" in res["error"]


def test_fetch_current_price_success():
    """Verify fetch_current_price extracts price from successful quote response."""
    from tasks.max_pain_task import fetch_current_price

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{"symbol": "SPY", "price": 558.50}]
    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp

    price = fetch_current_price(mock_client, "SPY", "test-key")
    assert price == 558.50


def test_fetch_current_price_missing_key_or_error():
    """Verify fetch_current_price returns 0.0 when key is missing or request fails."""
    from tasks.max_pain_task import fetch_current_price

    mock_client = MagicMock()
    assert fetch_current_price(mock_client, "SPY", "") == 0.0

    mock_client.get.side_effect = RuntimeError("Network timeout")
    assert fetch_current_price(mock_client, "SPY", "key") == 0.0


@pytest.mark.asyncio
async def test_evaluate_candidate_with_jev_missing_key():
    """Verify evaluate_candidate_with_jev defaults to disqualified when key is not set."""
    with patch("tasks.max_pain_task.OPENROUTER_API_KEY", ""):
        res = await evaluate_candidate_with_jev({"ticker": "SPY"})
        assert res["is_qualified"] is False
        assert res["choice"] == "DISQUALIFIED"


@pytest.mark.asyncio
async def test_evaluate_candidate_with_jev_network_error():
    """Verify evaluate_candidate_with_jev handles network exception gracefully."""
    mock_client = MagicMock()
    mock_client.post = AsyncMock(side_effect=RuntimeError("Connection refused"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("tasks.max_pain_task.httpx.AsyncClient", return_value=mock_client),
        patch("tasks.max_pain_task.OPENROUTER_API_KEY", "test-key"),
    ):
        res = await evaluate_candidate_with_jev({"ticker": "SPY"})
        assert res["is_qualified"] is False
        assert res["choice"] == "DISQUALIFIED"
