"""TDD Unit Tests for LIN Hyper-Focused Dedicated Flow."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from analysis.lin_agent import LinAgent, LinAgentContext
from analysis.renko import RenkoState
from execution.portfolio import Position
from tasks.lin_renko_task import execute_lin_trade_decision, run_lin_renko_flow


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
async def test_lin_agent_query_llm_with_deepseek_and_tools():
    """Verify LinAgent queries DeepSeek with web_search enabled."""
    agent = LinAgent(model_name="deepseek-v4-flash")
    state = RenkoState(
        trend_direction="BULLISH",
        last_brick_price=490.61,
        reversal_threshold=480.87,
        consecutive_bricks=2,
        brick_size=4.87,
    )
    context = LinAgentContext()

    mock_instructor_client = MagicMock()
    mock_raw_client = MagicMock()
    mock_instructor_client.client = mock_raw_client

    with (
        patch("analysis.lin_agent.get_deepseek_client", return_value=mock_instructor_client),
        patch("analysis.lin_agent.deepseek.run_tool_loop", new_callable=AsyncMock) as mock_loop,
    ):
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"decision": "BUY_LONG", "confidence": 0.92, "target_position_pct": 0.20, "reasoning": "Strong backlog"}'
                )
            )
        ]
        mock_raw_client.chat.completions.create = AsyncMock(return_value=mock_response)

        res = await agent.analyze(state, context)
        assert res["decision"] == "BUY_LONG"
        assert res["confidence"] == 0.92
        assert res["target_position_pct"] == 0.20
        mock_loop.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_lin_trade_decision_buy():
    """Verify execute_lin_trade_decision executes BUY order for LIN."""
    mock_portfolio = AsyncMock()
    mock_portfolio.owner_id = "lin-renko-agent-deepseek-flash"
    mock_portfolio.cash_balance = 10000.0
    mock_portfolio.positions = {}
    mock_trade_id = uuid4()
    mock_portfolio.execute_trade = AsyncMock(return_value=mock_trade_id)

    decision = {
        "decision": "BUY_LONG",
        "confidence": 0.88,
        "target_position_pct": 0.20,
        "reasoning": "Renko continuation",
    }

    trade_id = await execute_lin_trade_decision(mock_portfolio, decision, current_price=500.0)

    assert trade_id == mock_trade_id
    # 20% of $10,000 = $2,000 / $500 = 4 shares
    mock_portfolio.execute_trade.assert_awaited_once_with(
        ticker="LIN",
        quantity=4,
        price=500.0,
        signal="BUY",
        skip_alpaca_mirror=True,
    )


@pytest.mark.asyncio
async def test_execute_lin_trade_decision_sell():
    """Verify execute_lin_trade_decision executes SELL order when holding LIN."""
    mock_portfolio = AsyncMock()
    mock_portfolio.owner_id = "lin-renko-agent-deepseek-flash"
    mock_portfolio.cash_balance = 5000.0
    mock_portfolio.positions = {"LIN": Position(ticker="LIN", quantity=10, average_cost_basis=480.0)}
    mock_trade_id = uuid4()
    mock_portfolio.execute_trade = AsyncMock(return_value=mock_trade_id)

    decision = {
        "decision": "EXIT_LONG",
        "confidence": 0.85,
        "target_position_pct": 0.0,
        "reasoning": "2-brick downward reversal triggered",
    }

    trade_id = await execute_lin_trade_decision(mock_portfolio, decision, current_price=475.0)

    assert trade_id == mock_trade_id
    mock_portfolio.execute_trade.assert_awaited_once_with(
        ticker="LIN",
        quantity=10,
        price=475.0,
        signal="SELL",
        skip_alpaca_mirror=True,
    )


@pytest.mark.asyncio
async def test_execute_lin_trade_decision_strict_single_ticker_guard():
    """Verify execute_lin_trade_decision rejects non-LIN tickers."""
    mock_portfolio = AsyncMock()
    decision = {"decision": "BUY_LONG", "confidence": 0.9}

    with pytest.raises(ValueError, match="LIN only"):
        await execute_lin_trade_decision(mock_portfolio, decision, current_price=100.0, symbol="NVDA")


@pytest.mark.asyncio
async def test_lin_renko_flow_execution_mocked():
    """Verify full LIN Renko dedicated flow runs and executes trade on isolated portfolio."""
    mock_sb = MagicMock()
    mock_portfolio = AsyncMock()
    mock_portfolio.owner_id = "lin-renko-agent-deepseek-flash"
    mock_portfolio.cash_balance = 10000.0
    mock_portfolio.positions = {}
    mock_portfolio.execute_trade = AsyncMock(return_value=uuid4())

    with (
        patch("execution.portfolio.get_supabase_client", return_value=mock_sb),
        patch("tasks.lin_renko_task.Portfolio", return_value=mock_portfolio),
        patch("tasks.lin_renko_task.FMPProvider") as mock_fmp_cls,
        patch("tasks.lin_renko_task.LinAgent") as mock_agent_cls,
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

        mock_agent_inst = mock_agent_cls.return_value
        mock_agent_inst.model_name = "deepseek-v4-flash"
        mock_agent_inst.fetch_lin_fundamentals = AsyncMock(return_value={"roic": 0.165})
        mock_agent_inst.analyze = AsyncMock(
            return_value={
                "decision": "BUY_LONG",
                "confidence": 0.90,
                "target_position_pct": 0.20,
                "reasoning": "Breakout confirmed",
            }
        )

        result = await run_lin_renko_flow()
        assert result["symbol"] == "LIN"
        assert result["portfolio_owner"] == "lin-renko-agent-deepseek-flash"
        assert "decision" in result
        assert result["trade_executed"] is True
