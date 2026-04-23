"""Tests for Alpaca paper trading broker integration.

Verifies:
- AlpacaBroker initialization logic (enabled/disabled, missing keys)
- submit_limit_order success path with mocked TradingClient
- submit_limit_order failure handling (fire-and-forget isolation)
- _update_trade Supabase persistence with UUID serialization
- Order parameter correctness (DAY limit, agent-tagged client_order_id)

NO real API keys or network calls are used. All external dependencies are mocked.
"""

import asyncio
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from uuid import uuid4

from alpaca.trading.enums import OrderSide, TimeInForce
from execution.alpaca_broker import AlpacaBroker


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_trading_client():
    """Provides a mocked Alpaca TradingClient instance."""
    client = MagicMock()
    mock_order = MagicMock()
    mock_order.id = "alpaca-order-123"
    mock_order.status = "PENDING_NEW"
    mock_order.symbol = "AAPL"
    mock_order.qty = "10"
    mock_order.limit_price = "150.00"
    mock_order.time_in_force = "DAY"
    mock_order.created_at = "2026-04-23T19:56:11.318735+00:00"
    client.submit_order = MagicMock(return_value=mock_order)
    return client


@pytest.fixture
def mock_supabase_table():
    """Provides a mocked Supabase table builder chain."""
    mock_table = MagicMock()
    mock_eq = MagicMock()
    mock_execute = MagicMock()
    mock_eq.return_value = mock_execute
    mock_table.update.return_value.eq = mock_eq
    return mock_table, mock_eq, mock_execute


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

class TestAlpacaBrokerInit:

    def test_init_success_when_enabled_and_keys_present(self):
        """Broker initializes TradingClient when ALPACA_ENABLED=True and keys exist."""
        with patch("execution.alpaca_broker.ALPACA_ENABLED", True), \
             patch("execution.alpaca_broker.ALPACA_API_KEY", "test-key"), \
             patch("execution.alpaca_broker.ALPACA_SECRET_KEY", "test-secret"):
            with patch("execution.alpaca_broker.TradingClient") as MockTC:
                broker = AlpacaBroker()
                assert broker._client is not None
                MockTC.assert_called_once_with(
                    "test-key",
                    "test-secret",
                    paper=True,
                    url_override="https://paper-api.alpaca.markets",
                )

    def test_init_disabled_when_constant_false(self):
        """Broker skips initialization when ALPACA_ENABLED is hardcoded False."""
        with patch("execution.alpaca_broker.ALPACA_ENABLED", False):
            broker = AlpacaBroker()
            assert broker._client is None

    def test_init_disabled_when_api_key_missing(self):
        """Broker skips initialization when API key env var is missing."""
        with patch("execution.alpaca_broker.ALPACA_ENABLED", True), \
             patch("execution.alpaca_broker.ALPACA_API_KEY", None), \
             patch("execution.alpaca_broker.ALPACA_SECRET_KEY", "test-secret"):
            broker = AlpacaBroker()
            assert broker._client is None

    def test_init_disabled_when_secret_key_missing(self):
        """Broker skips initialization when Secret key env var is missing."""
        with patch("execution.alpaca_broker.ALPACA_ENABLED", True), \
             patch("execution.alpaca_broker.ALPACA_API_KEY", "test-key"), \
             patch("execution.alpaca_broker.ALPACA_SECRET_KEY", None):
            broker = AlpacaBroker()
            assert broker._client is None


# ---------------------------------------------------------------------------
# Order Submission
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestSubmitLimitOrder:

    async def test_buy_limit_order_params(self, mock_trading_client):
        """Verify BUY limit order is constructed with correct agent-tagged metadata."""
        broker = AlpacaBroker()
        broker._client = mock_trading_client

        trade_id = uuid4()
        await broker.submit_limit_order(
            trade_id=trade_id,
            ticker="AAPL",
            quantity=10,
            signal="BUY",
            limit_price=150.00,
            agent_id="gpt-5.4-nano",
        )

        call_args = mock_trading_client.submit_order.call_args
        request = call_args[0][0]  # positional arg

        assert request.symbol == "AAPL"
        assert request.qty == 10
        assert request.side == OrderSide.BUY
        assert request.limit_price == 150.00
        assert request.time_in_force == TimeInForce.DAY
        assert request.client_order_id == f"gpt-5.4-nano__AAPL__BUY__{trade_id}"

    async def test_sell_limit_order_params(self, mock_trading_client):
        """Verify SELL limit order uses correct side and metadata."""
        broker = AlpacaBroker()
        broker._client = mock_trading_client

        trade_id = uuid4()
        await broker.submit_limit_order(
            trade_id=trade_id,
            ticker="TSLA",
            quantity=5,
            signal="SELL",
            limit_price=250.00,
            agent_id="claude-haiku-4-5",
        )

        request = mock_trading_client.submit_order.call_args[0][0]
        assert request.side == OrderSide.SELL
        assert request.client_order_id == f"claude-haiku-4-5__TSLA__SELL__{trade_id}"

    async def test_no_op_when_client_none(self):
        """submit_limit_order is a no-op if _client is None (disabled/missing keys)."""
        broker = AlpacaBroker()
        broker._client = None

        # Should not raise
        await broker.submit_limit_order(
            trade_id=uuid4(),
            ticker="AAPL",
            quantity=1,
            signal="BUY",
            limit_price=100.0,
            agent_id="test",
        )

    async def test_failure_does_not_propagate(self, mock_trading_client):
        """Alpaca API exceptions are caught and logged; trade flow is NOT interrupted."""
        mock_trading_client.submit_order.side_effect = Exception("Alpaca API down")
        broker = AlpacaBroker()
        broker._client = mock_trading_client

        with patch.object(broker, "_update_trade", new_callable=AsyncMock) as mock_update:
            # Should NOT raise despite Alpaca failure
            await broker.submit_limit_order(
                trade_id=uuid4(),
                ticker="AAPL",
                quantity=1,
                signal="BUY",
                limit_price=100.0,
                agent_id="test",
            )
            mock_update.assert_awaited_once()
            # _update_trade receives (trade_id, order_id, status) as positional args
            assert mock_update.call_args[0][2] == "ERROR"

    async def test_limit_price_rounded_to_two_decimals(self, mock_trading_client):
        """Limit prices with excess precision are rounded to 2 decimal places."""
        broker = AlpacaBroker()
        broker._client = mock_trading_client

        await broker.submit_limit_order(
            trade_id=uuid4(),
            ticker="AAPL",
            quantity=1,
            signal="BUY",
            limit_price=150.9999,
            agent_id="test",
        )

        request = mock_trading_client.submit_order.call_args[0][0]
        assert request.limit_price == 151.00


# ---------------------------------------------------------------------------
# Supabase Update (_update_trade)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestUpdateTrade:

    async def test_update_trade_with_order_id(self, mock_supabase_table):
        """Supabase row is updated with string order_id and PENDING status."""
        mock_table, mock_eq, mock_execute = mock_supabase_table

        with patch("execution.alpaca_broker.get_supabase_client") as mock_get_client:
            mock_get_client.return_value.table.return_value = mock_table

            broker = AlpacaBroker()
            trade_id = uuid4()
            await broker._update_trade(trade_id, "alpaca-order-456", "PENDING")

            # Verify update payload
            update_call = mock_table.update.call_args[0][0]
            assert update_call["alpaca_status"] == "PENDING"
            assert update_call["alpaca_submitted_at"] == "now()"
            assert update_call["alpaca_order_id"] == "alpaca-order-456"

            # Verify WHERE clause uses stringified UUID
            mock_eq.assert_called_once_with("id", str(trade_id))

    async def test_update_trade_without_order_id(self, mock_supabase_table):
        """Error state update omits alpaca_order_id from payload."""
        mock_table, mock_eq, mock_execute = mock_supabase_table

        with patch("execution.alpaca_broker.get_supabase_client") as mock_get_client:
            mock_get_client.return_value.table.return_value = mock_table

            broker = AlpacaBroker()
            trade_id = uuid4()
            await broker._update_trade(trade_id, None, "ERROR")

            update_call = mock_table.update.call_args[0][0]
            assert update_call["alpaca_status"] == "ERROR"
            assert "alpaca_order_id" not in update_call

    async def test_update_trade_failure_logged(self, mock_supabase_table):
        """Supabase errors during update are caught and logged, not propagated."""
        mock_table, mock_eq, mock_execute = mock_supabase_table
        mock_eq.side_effect = Exception("Supabase connection timeout")

        with patch("execution.alpaca_broker.get_supabase_client") as mock_get_client:
            mock_get_client.return_value.table.return_value = mock_table

            broker = AlpacaBroker()
            trade_id = uuid4()
            # Should NOT raise
            await broker._update_trade(trade_id, "order-123", "PENDING")


# ---------------------------------------------------------------------------
# End-to-End Smoke (asyncio.create_task behavior)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestFireAndForget:

    async def test_submit_is_fire_and_forget_compatible(self, mock_trading_client):
        """The broker method can be wrapped in asyncio.create_task without blocking."""
        broker = AlpacaBroker()
        broker._client = mock_trading_client

        trade_id = uuid4()
        task = asyncio.create_task(
            broker.submit_limit_order(
                trade_id=trade_id,
                ticker="AAPL",
                quantity=1,
                signal="BUY",
                limit_price=200.0,
                agent_id="test",
            )
        )

        # Immediate return — task is running in background
        assert not task.done()
        await task  # Clean up
