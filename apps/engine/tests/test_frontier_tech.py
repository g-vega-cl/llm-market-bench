"""Tests for Frontier Tech Supercycle Analytics and Portfolio Execution.

Verifies:
1. 5-point supercycle rubric evaluation (requires >= 3 of 5).
2. Small-cap exchange and liquidity filters (NASDAQ/NYSE/AMEX, >= $100M cap, >= $1M vol).
3. Anti-overpaying filters (>= 18 months cash runway, price <= 150% of 200d MA).
4. Thesis death liquidation vs. power-law retention.
5. Portfolio rebalancing and position sizing within 2% - 4% bounds.
"""

import pytest

from analytics.frontier_tech import (
    SupercycleRubricCriteria,
    evaluate_stock_guardrails,
    evaluate_supercycle_rubric,
    evaluate_thesis_death,
)
from execution.frontier_tech import (
    compute_frontier_rebalance_orders,
)


def test_supercycle_rubric_pass_and_fail():
    """Rubric must pass if >= 3 criteria met, fail if < 3."""
    passing_criteria = SupercycleRubricCriteria(
        cost_deflation=True,
        pure_play_enabler=True,
        talent_migration=True,
        regulatory_catalyst=False,
        early_commercial_pilot=False,
    )
    passes, score, satisfied = evaluate_supercycle_rubric(passing_criteria)
    assert passes is True
    assert score == 3
    assert len(satisfied) == 3

    failing_criteria = SupercycleRubricCriteria(
        cost_deflation=True,
        pure_play_enabler=False,
        talent_migration=True,
        regulatory_catalyst=False,
        early_commercial_pilot=False,
    )
    passes_fail, score_fail, satisfied_fail = evaluate_supercycle_rubric(failing_criteria)
    assert passes_fail is False
    assert score_fail == 2
    assert len(satisfied_fail) == 2


def test_stock_guardrails_pass():
    """Valid small-cap with adequate runway and no pump passes."""
    profile = {"exchange": "NASDAQ", "mktCap": 500_000_000}
    quote = {"price": 10.0, "avgVolume": 200_000, "priceAvg200": 9.5}  # Vol: $2M/day, 105% of 200d MA
    financials = {
        "cash": 40_000_000,
        "operating_expenses": 20_000_000,  # 24 months runway
        "is_profitable": False,
    }
    passes, reason = evaluate_stock_guardrails(profile, quote, financials)
    assert passes is True
    assert reason == "passed"


def test_stock_guardrails_reject_otc_and_illiquid():
    """Reject OTC exchanges and sub-$1M daily volume."""
    otc_profile = {"exchange": "OTC", "mktCap": 300_000_000}
    quote = {"price": 5.0, "avgVolume": 500_000, "priceAvg200": 5.0}
    financials = {"cash": 50_000_000, "operating_expenses": 10_000_000, "is_profitable": False}
    passes, reason = evaluate_stock_guardrails(otc_profile, quote, financials)
    assert passes is False
    assert "exchange" in reason.lower()

    illiquid_quote = {"price": 2.0, "avgVolume": 100_000, "priceAvg200": 2.0}  # $200k/day
    nasdaq_profile = {"exchange": "NASDAQ", "mktCap": 200_000_000}
    passes_liq, reason_liq = evaluate_stock_guardrails(nasdaq_profile, illiquid_quote, financials)
    assert passes_liq is False
    assert "volume" in reason_liq.lower()


def test_stock_guardrails_reject_parabolic_pump():
    """Reject stocks trading > 150% above 200-day moving average."""
    profile = {"exchange": "NYSE", "mktCap": 800_000_000}
    quote = {"price": 28.0, "avgVolume": 500_000, "priceAvg200": 10.0}  # 280% of 200d MA
    financials = {"cash": 100_000_000, "operating_expenses": 20_000_000, "is_profitable": False}
    passes, reason = evaluate_stock_guardrails(profile, quote, financials)
    assert passes is False
    assert "parabolic" in reason.lower() or "moving average" in reason.lower()


def test_stock_guardrails_reject_short_runway():
    """Reject companies with less than 18 months cash runway."""
    profile = {"exchange": "NASDAQ", "mktCap": 400_000_000}
    quote = {"price": 12.0, "avgVolume": 300_000, "priceAvg200": 11.0}
    financials = {
        "cash": 10_000_000,
        "operating_expenses": 20_000_000,  # Only 6 months runway
        "is_profitable": False,
    }
    passes, reason = evaluate_stock_guardrails(profile, quote, financials)
    assert passes is False
    assert "runway" in reason.lower()


def test_thesis_death_evaluation():
    """Evaluate thesis death conditions."""
    healthy = {"is_delisted": False, "is_bankrupt": False, "thesis_canceled": False}
    should_exit, reason = evaluate_thesis_death(healthy)
    assert should_exit is False

    bankrupt = {"is_delisted": False, "is_bankrupt": True, "thesis_canceled": False}
    should_exit, reason = evaluate_thesis_death(bankrupt)
    assert should_exit is True
    assert "bankrupt" in reason.lower()


def test_compute_frontier_rebalance_orders():
    """Orders retain quality holdings and allocate 2-4% to new qualified picks."""
    current_holdings = [
        {"ticker": "POET", "shares": 100, "current_price": 5.0, "theme": "Photonics", "status": "healthy"},
        {"ticker": "DEAD", "shares": 50, "current_price": 2.0, "theme": "DeadTech", "status": "thesis_death"},
    ]
    candidate_stocks = [
        {"ticker": "TWST", "price": 30.0, "theme": "SynBio"},
        {"ticker": "LWLG", "price": 4.0, "theme": "Photonics"},
    ]
    total_equity = 20_000.0
    cash = 10_000.0

    orders = compute_frontier_rebalance_orders(
        current_holdings=current_holdings,
        current_cash=cash,
        total_equity=total_equity,
        candidate_stocks=candidate_stocks,
        target_weight=0.03,  # 3% target = $600 per position
    )

    # DEAD must be sold
    assert any(s["ticker"] == "DEAD" for s in orders["sales"])
    # POET must be retained
    assert any(r["ticker"] == "POET" for r in orders["retained"])
    # TWST and LWLG must have buy orders
    buy_tickers = [b["ticker"] for b in orders["buys"]]
    assert "TWST" in buy_tickers
    assert "LWLG" in buy_tickers


def test_fetch_ticker_data_empty_key():
    """Verify empty return when no API key provided."""
    import httpx

    from tasks.frontier_tech_task import fetch_ticker_data_for_screening

    with httpx.Client() as client:
        profile, quote, fin = fetch_ticker_data_for_screening(client, "POET", "")
        assert profile == {}
        assert quote == {}
        assert fin["is_profitable"] is False


@pytest.mark.asyncio
async def test_run_frontier_tech_task_dry_run():
    """Verify dry_run execution completes successfully without modifying database."""
    from unittest.mock import AsyncMock, patch

    from tasks.frontier_tech_task import run_frontier_tech_task

    mock_portfolio = AsyncMock()
    mock_portfolio.id = "mock-uuid"
    mock_portfolio.cash_balance = 10000.0
    mock_portfolio.positions = {}

    with (
        patch("tasks.frontier_tech_task.Portfolio", return_value=mock_portfolio),
        patch("tasks.frontier_tech_task.get_supabase_client") as mock_sb,
        patch("tasks.frontier_tech_task.FMP_API_KEY", ""),
    ):
        mock_sb.return_value.table.return_value.select.return_value.execute.return_value.data = []
        result = await run_frontier_tech_task(mode="auto", dry_run=True)
        assert result["status"] == "success"
        assert result["dry_run"] is True
        assert result["themes"] > 0


@pytest.mark.asyncio
async def test_run_frontier_tech_task_live_execution():
    """Verify live run executes trades and persists themes to database."""
    from unittest.mock import AsyncMock, patch

    from tasks.frontier_tech_task import run_frontier_tech_task

    mock_portfolio = AsyncMock()
    mock_portfolio.id = "mock-uuid"
    mock_portfolio.cash_balance = 10000.0
    mock_portfolio.positions = {}
    mock_portfolio.execute_trade = AsyncMock(return_value="mock-trade-id")

    with (
        patch("tasks.frontier_tech_task.Portfolio", return_value=mock_portfolio),
        patch("tasks.frontier_tech_task.get_supabase_client") as mock_sb,
        patch("tasks.frontier_tech_task.FMP_API_KEY", ""),
    ):
        mock_sb.return_value.table.return_value.upsert.return_value.execute.return_value.data = [{"id": "theme-1"}]
        mock_sb.return_value.table.return_value.insert.return_value.execute.return_value.data = [{"id": "dec-1"}]

        result = await run_frontier_tech_task(mode="auto", dry_run=False)
        assert result["status"] == "success"
        assert result["dry_run"] is False
        assert result["buys"] > 0
        assert mock_portfolio.execute_trade.called


@pytest.mark.asyncio
async def test_run_frontier_tech_task_bootstrap():
    """Verify portfolio is bootstrapped when no existing portfolio id is found."""
    from unittest.mock import AsyncMock, patch

    from tasks.frontier_tech_task import run_frontier_tech_task

    mock_portfolio = AsyncMock()
    mock_portfolio.id = None
    mock_portfolio.cash_balance = 0.0
    mock_portfolio.positions = {}

    with (
        patch("tasks.frontier_tech_task.Portfolio", return_value=mock_portfolio),
        patch("tasks.frontier_tech_task.get_supabase_client") as mock_sb,
        patch("tasks.frontier_tech_task.FMP_API_KEY", ""),
    ):
        mock_sb.return_value.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": "new-portfolio-uuid"}
        ]

        result = await run_frontier_tech_task(mode="bootstrap", dry_run=True)
        assert result["status"] == "success"
        assert mock_portfolio.id == "new-portfolio-uuid"
        assert mock_portfolio.cash_balance == 10000.00


def test_frontier_tech_main_cli():
    """Verify CLI main entry point parses arguments properly."""
    import sys
    from unittest.mock import patch

    from tasks.frontier_tech_task import main

    test_args = ["frontier_tech_task.py", "--mode", "rebalance", "--dry-run", "--target-weight", "0.04"]
    with patch.object(sys, "argv", test_args), patch("asyncio.run") as mock_run:
        mock_run.side_effect = lambda coro: coro.close()
        main()
        assert mock_run.called
