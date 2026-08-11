"""TDD Unit Tests for LIN Hyper-Focused Dedicated Flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from analysis.lin_agent import LinAgent
from analysis.renko import RenkoState
from tasks.lin_renko_task import run_lin_renko_flow


def test_renko_state_serialization():
    """Verify RenkoState serializes to dict and restores accurately."""
    state = RenkoState(
        trend_direction="BULLISH",
        last_brick_price=490.61,
        reversal_threshold=480.87,
        consecutive_bricks=2,
        brick_size=4.87,
    )
    data = {
        "trend_direction": state.trend_direction,
        "last_brick_price": state.last_brick_price,
        "reversal_threshold": state.reversal_threshold,
        "consecutive_bricks": state.consecutive_bricks,
        "brick_size": state.brick_size,
    }
    restored = RenkoState(**data)
    assert restored.trend_direction == "BULLISH"
    assert restored.last_brick_price == 490.61
    assert restored.reversal_threshold == 480.87
    assert restored.consecutive_bricks == 2
    assert restored.brick_size == 4.87


@pytest.mark.asyncio
async def test_lin_agent_specialized_fmp_tools():
    """Verify LinAgent can fetch LIN-specific financial metrics via FMP provider."""
    agent = LinAgent(model_name="deepseek-v4-flash")

    mock_provider = MagicMock()
    mock_provider.get_analyst_estimates = AsyncMock(return_value=[{"estimatedRevenueAvg": 35000000000}])
    mock_provider.get_key_metrics = AsyncMock(return_value=[{"roic": 0.165, "freeCashFlowYield": 0.042}])
    mock_provider.get_earnings_history = AsyncMock(return_value=[{"epsSurprisePercent": 2.5}])

    metrics = await agent.fetch_lin_fundamentals(mock_provider)
    assert metrics["roic"] == 0.165
    assert metrics["freeCashFlowYield"] == 0.042
    assert metrics["estimated_revenue"] == 35000000000
    assert metrics["earnings_surprise_pct"] == 2.5


@pytest.mark.asyncio
async def test_lin_renko_flow_execution_mocked():
    """Verify full LIN Renko dedicated flow runs and restricts trading to LIN only."""
    mock_sb = MagicMock()
    mock_portfolio = AsyncMock()
    mock_portfolio.owner_id = "lin-renko-agent-deepseek-flash"
    mock_portfolio.cash_balance = 10000.0
    mock_portfolio.positions = {}

    with (
        patch("execution.portfolio.get_supabase_client", return_value=mock_sb),
        patch("tasks.lin_renko_task.Portfolio", return_value=mock_portfolio),
        patch("tasks.lin_renko_task.FMPProvider") as mock_fmp_cls,
    ):
        mock_fmp_inst = mock_fmp_cls.return_value
        mock_fmp_inst.get_history = AsyncMock(
            return_value=[
                {"fetched_at": "2026-08-01", "price": 485.0},
                {"fetched_at": "2026-08-05", "price": 490.61},
            ]
        )
        mock_fmp_inst.get_analyst_estimates = AsyncMock(return_value=[{"estimatedRevenueAvg": 35000000000}])
        mock_fmp_inst.get_key_metrics = AsyncMock(return_value=[{"roic": 0.165, "freeCashFlowYield": 0.042}])
        mock_fmp_inst.get_earnings_history = AsyncMock(return_value=[{"epsSurprisePercent": 2.5}])

        result = await run_lin_renko_flow()
        assert result["symbol"] == "LIN"
        assert result["portfolio_owner"] == "lin-renko-agent-deepseek-flash"
        assert "decision" in result
