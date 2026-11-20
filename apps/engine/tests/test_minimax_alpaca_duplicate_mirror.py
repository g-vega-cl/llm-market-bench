import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from execution.portfolio import Portfolio


@pytest.mark.asyncio
async def test_execute_trade_honors_skip_alpaca_mirror():
    """
    Test that execute_trade does NOT trigger AlpacaBroker.submit_limit_order
    when skip_alpaca_mirror=True is passed, but DOES when it is False (default).
    """
    p = Portfolio("test_agent")
    p.id = "portfolio-123"
    p.cash_balance = 10000.00
    p.sma = 10000.00
    p.positions = {}

    mock_db = MagicMock()
    mock_db.rpc.return_value.execute.return_value = MagicMock(
        data={
            "trade_id": "trade-uuid-123",
            "cash_balance": 8500.0,
            "sma": 8500.0,
            "quantity": 10,
            "total_cost": 1500.0,
            "position_quantity": 10,
            "position_avg_cost": 150.0,
            "idempotent_replay": False,
        }
    )

    # We mock AlpacaBroker and submit_limit_order
    with (
        patch("execution.portfolio.get_supabase_client", return_value=mock_db),
        patch("execution.alpaca_broker.AlpacaBroker") as MockBroker,
    ):
        mock_broker_instance = MagicMock()
        mock_broker_instance.submit_limit_order = AsyncMock()
        MockBroker.return_value = mock_broker_instance

        # 1. First test: skip_alpaca_mirror=True
        trade_id = await p.execute_trade(ticker="AAPL", quantity=10, price=150.0, signal="BUY", skip_alpaca_mirror=True)

        assert trade_id == "trade-uuid-123"

        # Wait a brief moment to ensure any spawned tasks get time to resolve (though skip shouldn't spawn one)
        await asyncio.sleep(0.05)

        # Verify AlpacaBroker submit_limit_order was NOT called
        mock_broker_instance.submit_limit_order.assert_not_called()

        # 2. Second test: skip_alpaca_mirror=False (default)
        trade_id_2 = await p.execute_trade(
            ticker="AAPL",
            quantity=10,
            price=150.0,
            signal="BUY",
        )

        assert trade_id_2 == "trade-uuid-123"

        # Wait for the task to schedule/run
        await asyncio.sleep(0.05)

        # Verify AlpacaBroker submit_limit_order WAS called
        assert mock_broker_instance.submit_limit_order.called is True
