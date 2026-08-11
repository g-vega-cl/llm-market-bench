"""TDD Tests for LIN (Linde plc) Renko Engine and Hyper-Focused Agent."""

from unittest.mock import patch

import pytest

from analysis.lin_agent import LinAgent, LinAgentContext
from analysis.renko import RenkoEngine, RenkoState


def test_renko_engine_initialization():
    """Verify RenkoEngine initializes with default parameters."""
    engine = RenkoEngine(symbol="LIN", brick_size=2.0)
    assert engine.symbol == "LIN"
    assert engine.brick_size == 2.0
    assert engine.state.trend_direction == "NEUTRAL"
    assert len(engine.bricks) == 0


def test_renko_brick_generation_uptrend():
    """Verify price increases trigger green (UP) bricks."""
    engine = RenkoEngine(symbol="LIN", brick_size=2.0)

    # Initial anchor price
    engine.process_price(100.0)
    assert len(engine.bricks) == 0  # Anchor point set

    # Move up by 2.5 (crosses 1 brick threshold of 2.0)
    engine.process_price(102.5)
    assert len(engine.bricks) == 1
    assert engine.bricks[0].direction == "UP"
    assert engine.bricks[0].close_price == 102.0
    assert engine.state.trend_direction == "BULLISH"
    assert engine.state.consecutive_bricks == 1

    # Move up by another 4.1 (crosses 2 more bricks: 104.0 and 106.0)
    engine.process_price(106.6)
    assert len(engine.bricks) == 3
    assert engine.bricks[-1].close_price == 106.0
    assert engine.state.consecutive_bricks == 3


def test_renko_reversal_requires_two_bricks():
    """Verify trend reversal requires 2 brick moves in opposite direction."""
    engine = RenkoEngine(symbol="LIN", brick_size=2.0)
    engine.process_price(100.0)
    engine.process_price(106.0)  # 3 UP bricks to 106.0 (102, 104, 106)
    assert engine.state.trend_direction == "BULLISH"

    # Price drops by 2.5 (1 brick down to 104.0) -> Should NOT reverse trend yet
    engine.process_price(103.5)
    assert engine.state.trend_direction == "BULLISH"

    # Price drops by another 2.5 (down to 101.0, crossing 102.0) -> 2 bricks down triggers REVERSAL
    engine.process_price(101.5)
    assert engine.state.trend_direction == "BEARISH"
    assert engine.bricks[-1].direction == "DOWN"


def test_renko_atr_locking():
    """Verify periodic ATR snapshot locking."""
    prices = [100.0, 102.0, 101.0, 105.0, 104.0, 108.0]
    atr = RenkoEngine.calculate_atr(prices, period=5)
    assert atr > 0.0

    engine = RenkoEngine(symbol="LIN", brick_size=atr)
    assert engine.brick_size == atr


def test_lin_agent_prompt_construction():
    """Verify LIN Hyper-Focused Agent constructs prompt with ChemEng and Renko state."""
    renko_state = RenkoState(
        trend_direction="BULLISH",
        last_brick_price=454.0,
        reversal_threshold=450.0,
        consecutive_bricks=4,
        brick_size=2.15,
    )
    context = LinAgentContext(
        fab_gas_demand="HIGH",
        industrial_pmi=51.2,
        take_or_pay_backlog_billions=4.2,
        recent_news_summary="Semiconductor fab expansion in Arizona announced.",
    )

    agent = LinAgent(model_name="deepseek-v4-flash")
    prompt = agent.build_prompt(renko_state, context)

    assert "Linde plc" in prompt
    assert "BULLISH" in prompt
    assert "454.0" in prompt
    assert "$4.20B" in prompt
    assert agent.model_name == "deepseek-v4-flash"


@pytest.mark.asyncio
async def test_lin_agent_execution_mocked():
    """Verify LIN agent executes analysis with mocked DeepSeek handler."""
    agent = LinAgent(model_name="deepseek-v4-flash")
    renko_state = RenkoState(
        trend_direction="BULLISH",
        last_brick_price=454.0,
        reversal_threshold=450.0,
        consecutive_bricks=4,
        brick_size=2.15,
    )
    context = LinAgentContext(
        fab_gas_demand="HIGH",
        industrial_pmi=51.2,
        take_or_pay_backlog_billions=4.2,
        recent_news_summary="Fab expansion ongoing.",
    )

    with patch.object(agent, "query_llm") as mock_query:
        mock_query.return_value = {
            "decision": "HOLD_LONG",
            "confidence": 0.88,
            "target_position_pct": 0.15,
            "reasoning": "Renko 4 bricks green, backlog robust.",
        }
        res = await agent.analyze(renko_state, context)
        assert res["decision"] == "HOLD_LONG"
        assert res["confidence"] == 0.88
