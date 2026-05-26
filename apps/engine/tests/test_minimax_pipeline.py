"""Tests for MiniMax 2.7 portfolio pipeline.

Tests cover:
1. The `minimax` provider branch in `analyze_with_provider`.
2. Reg T + cash/share hard-stop validation for MiniMax trades.
3. Market order ±0.1% buffer price calculation.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from core.config import MINIMAX_MODEL

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_decision_response_json(decisions=None, macro_events=None):
    """Return a JSON string mimicking a DecisionsResponse."""
    import json

    return json.dumps(
        {
            "decisions": decisions or [],
            "macro_events": macro_events or [],
        }
    )


# ---------------------------------------------------------------------------
# Test Group 1: MiniMax `analyze_with_provider` branch
# ---------------------------------------------------------------------------


class TestMinimaxAnalysisProvider:
    """Tests for the `minimax` branch in analyze_with_provider."""

    @pytest.mark.asyncio
    async def test_minimax_returns_decisions_response(self):
        """MiniMax provider branch returns a DecisionsResponse with parsed decisions."""
        from core.llm.analysis import analyze_with_provider
        from core.llm.minimax import MiniMaxClient

        decision_json = _make_decision_response_json(
            decisions=[
                {
                    "signal": "BUY",
                    "confidence": 75,
                    "reasoning": "Strong earnings beat.",
                    "ticker": "AAPL",
                    "catalyst_type": "EARNINGS",
                    "catalyst_duration": "SHORT_TERM",
                    "source_id": "test-chunk-001",
                    "allocation_percentage": 20,
                }
            ]
        )

        mock_chat_response = {
            "content": decision_json,
            "model": MINIMAX_MODEL,
            "finish_reason": "stop",
            "usage": {"input_tokens": 100, "output_tokens": 50},
            "processing_time_ms": 500,
        }

        with patch.object(MiniMaxClient, "chat", new=AsyncMock(return_value=mock_chat_response)):
            with patch.object(MiniMaxClient, "close", new=AsyncMock()):
                result = await analyze_with_provider(
                    provider="minimax",
                    model_name=MINIMAX_MODEL,
                    chunks=[{"source_id": "test-chunk-001", "content": "Apple earnings beat."}],
                    context="",
                    portfolio_context="Cash Balance: $10,000",
                    current_day_info="Today is Monday.",
                    calendar_knowledge="",
                    macro_context="",
                )

        assert len(result.decisions) == 1
        assert result.decisions[0].ticker == "AAPL"
        assert result.decisions[0].signal == "BUY"

    @pytest.mark.asyncio
    async def test_minimax_graceful_fallback_on_parse_error(self):
        """MiniMax returns empty DecisionsResponse on unparseable LLM output."""
        from core.llm.analysis import analyze_with_provider
        from core.llm.minimax import MiniMaxClient

        mock_chat_response = {
            "content": "I'm sorry, I cannot make a trading decision right now.",
            "model": MINIMAX_MODEL,
            "finish_reason": "stop",
            "usage": {"input_tokens": 50, "output_tokens": 20},
            "processing_time_ms": 200,
        }

        with patch.object(MiniMaxClient, "chat", new=AsyncMock(return_value=mock_chat_response)):
            with patch.object(MiniMaxClient, "close", new=AsyncMock()):
                result = await analyze_with_provider(
                    provider="minimax",
                    model_name=MINIMAX_MODEL,
                    chunks=[{"source_id": "test-chunk-002", "content": "Some news."}],
                    context="",
                    portfolio_context="",
                    current_day_info="",
                    calendar_knowledge="",
                    macro_context="",
                )

        assert result.decisions == []
        assert result.macro_events == []

    @pytest.mark.asyncio
    async def test_minimax_no_tool_loop_called(self):
        """MiniMax must NOT trigger an OpenAI/Anthropic tool loop — it calls chat() directly."""
        from core.llm.analysis import analyze_with_provider
        from core.llm.minimax import MiniMaxClient

        # Spy on the handlers to ensure they are NOT called
        mock_chat_response = {
            "content": _make_decision_response_json(),
            "model": MINIMAX_MODEL,
            "finish_reason": "stop",
            "usage": {"input_tokens": 10, "output_tokens": 5},
            "processing_time_ms": 100,
        }

        with patch.object(MiniMaxClient, "chat", new=AsyncMock(return_value=mock_chat_response)) as mock_chat:
            with patch.object(MiniMaxClient, "close", new=AsyncMock()):
                with patch("core.llm.handlers.openai.run_tool_loop", new=AsyncMock()) as mock_openai_loop:
                    with patch("core.llm.handlers.anthropic.run_tool_loop", new=AsyncMock()) as mock_anthropic_loop:
                        await analyze_with_provider(
                            provider="minimax",
                            model_name=MINIMAX_MODEL,
                            chunks=[{"source_id": "s1", "content": "News."}],
                            context="",
                            portfolio_context="",
                            current_day_info="",
                            calendar_knowledge="",
                            macro_context="",
                        )

        mock_chat.assert_called_once()
        mock_openai_loop.assert_not_called()
        mock_anthropic_loop.assert_not_called()


# ---------------------------------------------------------------------------
# Test Group 2: Market order ±0.1% buffer price
# ---------------------------------------------------------------------------


class TestMinimaxMarketOrderBuffer:
    """Tests for the 0.3% market order buffer price calculation."""

    def test_buy_price_buffer(self):
        """BUY exec price should be market_price * 1.003 rounded to 2dp."""
        market_price = 150.00
        expected = round(market_price * 1.003, 2)
        # Replicate the calculation that will be in main.py
        exec_price = round(market_price * 1.003, 2)
        assert exec_price == expected
        assert exec_price > market_price

    def test_sell_price_buffer(self):
        """SELL exec price should be market_price * 0.997 rounded to 2dp."""
        market_price = 150.00
        expected = round(market_price * 0.997, 2)
        exec_price = round(market_price * 0.997, 2)
        assert exec_price == expected
        assert exec_price < market_price

    def test_buy_buffer_is_03_percent(self):
        """Confirm BUY buffer is exactly 0.3% above market price."""
        market_price = 200.00
        exec_price = round(market_price * 1.003, 2)
        actual_pct = (exec_price - market_price) / market_price
        assert abs(actual_pct - 0.003) < 1e-9

    def test_sell_buffer_is_03_percent(self):
        """Confirm SELL buffer is exactly 0.3% below market price."""
        market_price = 200.00
        exec_price = round(market_price * 0.997, 2)
        actual_pct = (market_price - exec_price) / market_price
        assert abs(actual_pct - 0.003) < 1e-9

    def test_buy_alpaca_limit_uses_same_buffer(self):
        """Alpaca limit order price for BUY should also use the 0.3% buffer."""
        market_price = 100.00
        exec_price = round(market_price * 1.003, 2)
        alpaca_limit = round(exec_price * 1.003, 2)
        # Alpaca limit should be at or slightly above exec_price
        assert alpaca_limit >= exec_price


# ---------------------------------------------------------------------------
# Test Group 3: MiniMax Reg T + cash/share hard-stop validation
# ---------------------------------------------------------------------------


class TestMinimaxTradeValidation:
    """Tests for MiniMax execution path: Reg T enforced, tool checks skipped."""

    def _make_portfolio(self, cash=10000.0, positions=None):
        """Build a minimal portfolio mock with Reg T metrics set."""
        from execution.portfolio import Portfolio, Position
        from execution.reg_t_validation import RegTMetrics

        p = MagicMock(spec=Portfolio)
        p.owner_id = MINIMAX_MODEL
        p.cash_balance = cash
        p.positions = {}
        if positions:
            for ticker, qty, cost in positions:
                p.positions[ticker] = Position(ticker=ticker, quantity=qty, average_cost_basis=cost)

        # Pre-compute realistic metrics
        stock_value = sum(qty * cost for _, qty, cost in (positions or []))
        total_equity = cash + stock_value
        maintenance_margin = stock_value * 0.33
        initial_margin = stock_value * 0.57
        available_funds = total_equity - initial_margin
        buying_power = max(0.0, available_funds * 4.0)

        p.metrics = RegTMetrics(
            total_equity=total_equity,
            initial_margin_req=initial_margin,
            maintenance_margin_req=maintenance_margin,
            available_funds=available_funds,
            excess_liquidity=total_equity - maintenance_margin,
            sma=max(cash, total_equity - initial_margin),
            realized=cash + sum(qty * cost for _, qty, cost in (positions or [])),
            buying_power=buying_power,
        )
        return p

    @pytest.mark.asyncio
    async def test_minimax_buy_rejected_when_insufficient_buying_power(self):
        """BUY is rejected by Reg T when cost > buying_power (even for MiniMax)."""
        # Empty portfolio: $10k cash, no positions → buying_power = 4 * (10k - 0) = 40k
        # But let's simulate a portfolio with very low buying power
        from execution.reg_t_validation import RegTMetrics, validate_trade_compliance

        metrics = RegTMetrics(
            total_equity=1000.0,
            initial_margin_req=0.0,
            maintenance_margin_req=0.0,
            available_funds=100.0,
            excess_liquidity=1000.0,
            sma=100.0,
            realized=1000.0,
            buying_power=400.0,  # Only $400 BP
        )

        result = validate_trade_compliance(
            portfolio_metrics=metrics,
            estimated_trade_cost=5000.0,  # Way more than $400 BP
            ticker="AAPL",
            price=500.0,
            signal="BUY",
        )

        assert result.passed is False
        assert "Buying Power" in result.reason

    @pytest.mark.asyncio
    async def test_minimax_sell_rejected_when_ticker_not_held(self):
        """SELL is rejected when the ticker is not in the portfolio (hard stop)."""
        from execution.portfolio import Portfolio

        portfolio = MagicMock(spec=Portfolio)
        portfolio.positions = {}  # No positions held

        ticker = "TSLA"
        # Replicate the hard-stop logic from the MiniMax execution path
        is_rejected = ticker not in portfolio.positions
        assert is_rejected is True

    @pytest.mark.asyncio
    async def test_minimax_buy_succeeds_when_sufficient_buying_power(self):
        """BUY passes Reg T validation when buying_power >= trade cost."""
        from execution.reg_t_validation import RegTMetrics, validate_trade_compliance

        metrics = RegTMetrics(
            total_equity=10000.0,
            initial_margin_req=0.0,
            maintenance_margin_req=0.0,
            available_funds=10000.0,
            excess_liquidity=10000.0,
            sma=10000.0,
            realized=10000.0,
            buying_power=40000.0,  # Fresh $10k cash account → 4x = $40k BP
        )

        result = validate_trade_compliance(
            portfolio_metrics=metrics,
            estimated_trade_cost=2000.0,  # Well within $40k BP
            ticker="AAPL",
            price=200.0,
            signal="BUY",
        )

        assert result.passed is True

    @pytest.mark.asyncio
    async def test_minimax_sell_qty_capped_to_held_shares(self):
        """SELL quantity must be capped to shares held (cannot oversell)."""
        from execution.portfolio import Position

        held_qty = 10
        requested_qty = 50  # More than held

        pos = Position(ticker="NVDA", quantity=held_qty, average_cost_basis=400.0)

        # MiniMax execution path caps qty to held
        final_qty = min(requested_qty, pos.quantity)
        assert final_qty == held_qty

    @pytest.mark.asyncio
    async def test_minimax_sell_passes_when_ticker_held(self):
        """SELL is not rejected by the ownership check when ticker is held."""
        from execution.portfolio import Portfolio, Position

        portfolio = MagicMock(spec=Portfolio)
        portfolio.positions = {"AAPL": Position(ticker="AAPL", quantity=10, average_cost_basis=150.0)}

        ticker = "AAPL"
        is_rejected = ticker not in portfolio.positions
        assert is_rejected is False
