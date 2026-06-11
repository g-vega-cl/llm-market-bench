"""Tests for Alpaca paper trading broker integration.

Verifies:
- AlpacaBroker initialization logic (enabled/disabled, missing keys)
- submit_limit_order success path with mocked TradingClient
- submit_limit_order failure handling (fire-and-forget isolation)
- submit_limit_order SELL guardrails (skip when no position, cap when under-held)
- get_alpaca_position returns correct quantities and handles 404 gracefully
- _update_trade Supabase persistence with UUID serialization
- Order parameter correctness (DAY limit, agent-tagged client_order_id)

NO real API keys or network calls are used. All external dependencies are mocked.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
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
        with (
            patch("execution.alpaca_broker.ALPACA_ENABLED", True),
            patch("execution.alpaca_broker.ALPACA_API_KEY", "test-key"),
            patch("execution.alpaca_broker.ALPACA_SECRET_KEY", "test-secret"),
        ):
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
        with (
            patch("execution.alpaca_broker.ALPACA_ENABLED", True),
            patch("execution.alpaca_broker.ALPACA_API_KEY", None),
            patch("execution.alpaca_broker.ALPACA_SECRET_KEY", "test-secret"),
        ):
            broker = AlpacaBroker()
            assert broker._client is None

    def test_init_disabled_when_secret_key_missing(self):
        """Broker skips initialization when Secret key env var is missing."""
        with (
            patch("execution.alpaca_broker.ALPACA_ENABLED", True),
            patch("execution.alpaca_broker.ALPACA_API_KEY", "test-key"),
            patch("execution.alpaca_broker.ALPACA_SECRET_KEY", None),
        ):
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
# SELL Guardrails — prevent shorting in Alpaca
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestSellGuardrails:
    async def test_sell_skipped_when_no_alpaca_position(self, mock_trading_client):
        """SELL order is skipped when Alpaca holds 0 shares and Supabase also shows 0."""
        broker = AlpacaBroker()
        broker._client = mock_trading_client

        with (
            patch.object(broker, "get_alpaca_position", return_value=0.0) as mock_pos,
            patch.object(broker, "_get_supabase_position", return_value=0) as mock_sup,
            patch.object(broker, "_update_trade", new_callable=AsyncMock) as mock_update,
        ):
            trade_id = uuid4()
            await broker.submit_limit_order(
                trade_id=trade_id,
                ticker="TSLA",
                quantity=10,
                signal="SELL",
                limit_price=250.00,
                agent_id="test",
            )

            mock_pos.assert_called_once_with("TSLA")
            mock_sup.assert_called_once_with("TSLA", "test")
            mock_trading_client.submit_order.assert_not_called()
            mock_update.assert_awaited_once_with(trade_id, None, "SKIPPED_NO_POSITION")

    async def test_sell_proceeds_when_supabase_has_position_but_alpaca_does_not(self, mock_trading_client):
        """SELL order proceeds when Alpaca shows 0 but Supabase ledger shows the position."""
        broker = AlpacaBroker()
        broker._client = mock_trading_client

        with (
            patch.object(broker, "get_alpaca_position", return_value=0.0) as mock_pos,
            patch.object(broker, "_get_supabase_position", return_value=15) as mock_sup,
        ):
            trade_id = uuid4()
            await broker.submit_limit_order(
                trade_id=trade_id,
                ticker="JPM",
                quantity=5,
                signal="SELL",
                limit_price=200.00,
                agent_id="contrarian_agent",
            )

            mock_pos.assert_called_once_with("JPM")
            mock_sup.assert_called_once_with("JPM", "contrarian_agent")
            request = mock_trading_client.submit_order.call_args[0][0]
            assert request.qty == 5
            assert request.side == OrderSide.SELL

    async def test_sell_quantity_capped_when_under_held(self, mock_trading_client):
        """SELL quantity is reduced to actual Alpaca holdings when fewer shares held."""
        broker = AlpacaBroker()
        broker._client = mock_trading_client

        with patch.object(broker, "get_alpaca_position", return_value=7.0) as mock_pos:
            trade_id = uuid4()
            await broker.submit_limit_order(
                trade_id=trade_id,
                ticker="TSLA",
                quantity=10,
                signal="SELL",
                limit_price=250.00,
                agent_id="test",
            )

            mock_pos.assert_called_once_with("TSLA")
            request = mock_trading_client.submit_order.call_args[0][0]
            assert request.qty == 7
            assert request.side == OrderSide.SELL

    async def test_sell_proceeds_normally_when_fully_held(self, mock_trading_client):
        """SELL order is submitted unchanged when Alpaca holds >= requested quantity."""
        broker = AlpacaBroker()
        broker._client = mock_trading_client

        with patch.object(broker, "get_alpaca_position", return_value=15.0) as mock_pos:
            trade_id = uuid4()
            await broker.submit_limit_order(
                trade_id=trade_id,
                ticker="TSLA",
                quantity=10,
                signal="SELL",
                limit_price=250.00,
                agent_id="test",
            )

            mock_pos.assert_called_once_with("TSLA")
            request = mock_trading_client.submit_order.call_args[0][0]
            assert request.qty == 10
            assert request.side == OrderSide.SELL

    async def test_buy_orders_not_checked_for_position(self, mock_trading_client):
        """BUY orders bypass the position guardrail entirely."""
        broker = AlpacaBroker()
        broker._client = mock_trading_client

        with patch.object(broker, "get_alpaca_position", return_value=0.0) as mock_pos:
            await broker.submit_limit_order(
                trade_id=uuid4(),
                ticker="AAPL",
                quantity=5,
                signal="BUY",
                limit_price=150.00,
                agent_id="test",
            )

            mock_pos.assert_not_called()
            request = mock_trading_client.submit_order.call_args[0][0]
            assert request.side == OrderSide.BUY


# ---------------------------------------------------------------------------
# Position Query (get_alpaca_position)
# ---------------------------------------------------------------------------


class TestGetAlpacaPosition:
    def test_returns_quantity_for_existing_position(self):
        """get_alpaca_position returns the quantity when a position exists."""
        broker = AlpacaBroker()
        mock_pos = MagicMock()
        mock_pos.qty = "42"
        mock_client = MagicMock()
        mock_client.get_open_position.return_value = mock_pos
        broker._client = mock_client

        qty = broker.get_alpaca_position("AAPL")
        assert qty == 42.0
        mock_client.get_open_position.assert_called_once_with("AAPL")

    def test_returns_zero_for_404_api_error(self):
        """get_alpaca_position returns 0.0 when Alpaca raises a 404 APIError."""
        from alpaca.common.exceptions import APIError

        broker = AlpacaBroker()
        mock_client = MagicMock()
        # APIError reads status_code from http_error.response.status_code
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_http_error = MagicMock()
        mock_http_error.response = mock_response
        exc = APIError(error={"message": "position does not exist"}, http_error=mock_http_error)
        mock_client.get_open_position.side_effect = exc
        broker._client = mock_client

        qty = broker.get_alpaca_position("AAPL")
        assert qty == 0.0

    def test_returns_zero_for_unexpected_exception(self):
        """get_alpaca_position returns 0.0 on any unexpected exception."""
        broker = AlpacaBroker()
        mock_client = MagicMock()
        mock_client.get_open_position.side_effect = RuntimeError("boom")
        broker._client = mock_client

        qty = broker.get_alpaca_position("AAPL")
        assert qty == 0.0

    def test_returns_zero_when_client_none(self):
        """get_alpaca_position returns 0.0 when broker client is not initialized."""
        broker = AlpacaBroker()
        broker._client = None
        assert broker.get_alpaca_position("AAPL") == 0.0


# ---------------------------------------------------------------------------
# Supabase Position Lookup (_get_supabase_position)
# ---------------------------------------------------------------------------


class TestGetSupabasePosition:
    def test_returns_quantity_when_position_exists(self):
        """_get_supabase_position returns the quantity from Supabase ledger."""
        broker = AlpacaBroker()

        mock_positions = MagicMock()
        mock_positions.data = [{"quantity": 15}]

        mock_portfolio = MagicMock()
        mock_portfolio.data = [{"id": "pf-123"}]

        # Chainable builder mock: .select/.eq/.eq all return self, .execute returns response
        def make_builder(execute_response):
            b = MagicMock()
            b.select.return_value = b
            b.eq.return_value = b
            b.execute.return_value = execute_response
            return b

        portfolios_builder = make_builder(mock_portfolio)
        positions_builder = make_builder(mock_positions)

        def table_side_effect(name):
            if name == "portfolios":
                return portfolios_builder
            if name == "portfolio_positions":
                return positions_builder
            return MagicMock()

        mock_client = MagicMock()
        mock_client.table.side_effect = table_side_effect

        with patch("execution.alpaca_broker.get_supabase_client", return_value=mock_client):
            qty = broker._get_supabase_position("JPM", "contrarian_agent")
            assert qty == 15

    def test_returns_zero_when_no_portfolio_found(self):
        """Returns 0 when the agent has no portfolio entry."""
        broker = AlpacaBroker()

        mock_portfolio = MagicMock()
        mock_portfolio.data = []

        b = MagicMock()
        b.select.return_value = b
        b.eq.return_value = b
        b.execute.return_value = mock_portfolio

        mock_client = MagicMock()
        mock_client.table.return_value = b

        with patch("execution.alpaca_broker.get_supabase_client", return_value=mock_client):
            qty = broker._get_supabase_position("JPM", "unknown_agent")
            assert qty == 0

    def test_returns_zero_when_no_position_for_ticker(self):
        """Returns 0 when portfolio exists but ticker is not held."""
        broker = AlpacaBroker()

        mock_positions = MagicMock()
        mock_positions.data = []

        mock_portfolio = MagicMock()
        mock_portfolio.data = [{"id": "pf-123"}]

        def make_builder(execute_response):
            b = MagicMock()
            b.select.return_value = b
            b.eq.return_value = b
            b.execute.return_value = execute_response
            return b

        def table_side_effect(name):
            if name == "portfolios":
                return make_builder(mock_portfolio)
            if name == "portfolio_positions":
                return make_builder(mock_positions)
            return MagicMock()

        mock_client = MagicMock()
        mock_client.table.side_effect = table_side_effect

        with patch("execution.alpaca_broker.get_supabase_client", return_value=mock_client):
            qty = broker._get_supabase_position("UNKNOWN", "test_agent")
            assert qty == 0

    def test_returns_zero_on_supabase_error(self):
        """Returns 0 and logs warning when Supabase query fails."""
        broker = AlpacaBroker()

        mock_client = MagicMock()
        mock_client.table.side_effect = RuntimeError("connection timeout")

        with patch("execution.alpaca_broker.get_supabase_client", return_value=mock_client):
            qty = broker._get_supabase_position("JPM", "test_agent")
            assert qty == 0


# ---------------------------------------------------------------------------
# Supabase Update (_update_trade)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestUpdateTrade:
    async def test_update_trade_with_order_id(self, mock_supabase_table):
        """Supabase row is updated with string order_id and SUBMITTED status."""
        mock_table, mock_eq, mock_execute = mock_supabase_table

        with patch("execution.alpaca_broker.get_supabase_client") as mock_get_client:
            mock_get_client.return_value.table.return_value = mock_table

            broker = AlpacaBroker()
            trade_id = uuid4()
            await broker._update_trade(trade_id, "alpaca-order-456", "SUBMITTED")

            # Verify update payload
            update_call = mock_table.update.call_args[0][0]
            assert update_call["alpaca_status"] == "SUBMITTED"
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
            await broker._update_trade(trade_id, "order-123", "SUBMITTED")


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
