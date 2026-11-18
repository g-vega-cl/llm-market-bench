"""Sentiment fader must read Portfolio.positions as a mapping of Position objects.

Regression: the task iterated `portfolio.positions` (a dict of ticker -> Position)
as if it were a list of objects, raising AttributeError on every intraday tick
now that the MiniPC daemon owns the strategy hooks.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from execution.portfolio import Position


class _FakePortfolio:
    id = uuid.uuid4()
    cash_balance = 0.0
    total_equity = 5000.0
    sma = 5000.0
    metrics = None
    owner_id = "sys-sentiment-fader"

    def __init__(self):
        self.positions = {"SPY": Position(ticker="SPY", quantity=10, average_cost_basis=500.0)}
        self.executed: list[dict] = []

    async def initialize(self):
        return None

    def calculate_reg_t_metrics(self, current_prices):
        return None

    async def save_metrics(self):
        return None

    async def execute_trade(self, **kwargs):
        self.executed.append(kwargs)


@pytest.mark.asyncio
async def test_sentiment_fader_reads_position_mapping():
    from tasks.sentiment_fader_task import run_sentiment_fader_task

    fake = _FakePortfolio()
    captured: dict = {}

    def fake_plan(current_holdings, holding_evaluations, qualified_candidates, **kwargs):
        captured["current_holdings"] = current_holdings
        return {"sales": [], "retained": [], "buys": [], "freed_cash": 0.0, "remaining_cash": 0.0}

    with (
        patch("tasks.sentiment_fader_task.Portfolio", return_value=fake),
        patch("tasks.sentiment_fader_task.MassiveOptionsClient", return_value=MagicMock()),
        patch("tasks.sentiment_fader_task.fetch_ticker_price", new_callable=AsyncMock, return_value=510.0),
        patch("tasks.sentiment_fader_task.fetch_sentiment_snapshot", new_callable=AsyncMock, return_value=None),
        patch(
            "tasks.sentiment_fader_task.compute_sentiment_fader_rebalance_orders",
            side_effect=fake_plan,
        ),
        patch("tasks.sentiment_fader_task._get_holding_days", new_callable=AsyncMock, return_value=1),
    ):
        result = await run_sentiment_fader_task(action="evaluate")

    assert result["status"] == "success"
    holdings = captured["current_holdings"]
    assert holdings == [
        {
            "ticker": "SPY",
            "shares": 10,
            "cost_basis": 500.0,
            "entry_price": 500.0,
            "current_price": 510.0,
        }
    ]
