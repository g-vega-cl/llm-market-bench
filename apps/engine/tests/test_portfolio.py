"""Tests for Portfolio management and Reg T4 calculations."""

from unittest.mock import MagicMock, patch

import pytest

from execution.portfolio import Portfolio, Position, RegTMetrics

# --- Reg T Scenario Tests ---


def test_reg_t_scenario_1_no_leverage():
    """
    Scenario 1: Basic Cash-Backed Purchase
    Cash: 49.76. Buy $9,950.24 stock.
    Cash-Only Model:
    - Equity: 10,000
    - Maint Margin: 0.0
    - Excess Liquidity: 49.76
    - Available Funds: 49.76
    - Buying Power: 49.76 (Cash Balance)
    """
    p = Portfolio("test_agent")
    p.cash_balance = 49.76
    p.positions = {"QQQ": Position("QQQ", 16, 621.89)}

    current_prices = {"QQQ": 621.89}

    metrics = p.calculate_reg_t_metrics(current_prices)

    assert metrics.total_equity == pytest.approx(10000.00, abs=0.10)
    assert metrics.maintenance_margin_req == 0.0
    assert metrics.excess_liquidity == pytest.approx(49.76, abs=0.10)
    assert metrics.buying_power == pytest.approx(49.76, abs=0.10)
    assert metrics.realized == pytest.approx(10000.00, abs=0.10)


def test_reg_t_scenario_2_leveraged_profitable():
    """
    Scenario 2: Negative Cash Boundary (Overdraft / Legacy Deficit)
    Cash: -2000. Stock Value: 12437.80.
    In Cash-Only: Buying power is 0.0 when cash is negative. Margin requirements are 0.0.
    """
    p = Portfolio("test_agent")
    p.cash_balance = -2000.00
    p.positions = {"QQQ": Position("QQQ", 20, 600.00)}

    current_prices = {"QQQ": 621.89}

    metrics = p.calculate_reg_t_metrics(current_prices)

    assert metrics.total_equity == pytest.approx(10437.80, abs=0.10)
    assert metrics.maintenance_margin_req == 0.0
    assert metrics.excess_liquidity == 0.0
    assert metrics.buying_power == 0.0
    assert metrics.realized == pytest.approx(10000.00, abs=0.10)


def test_reg_t_scenario_3_leveraged_loss():
    """
    Scenario 3: Negative Cash Deficit at a Loss
    Cash: -3000. Stock Value: 12437.80.
    In Cash-Only: Buying power is 0.0.
    """
    p = Portfolio("test_agent")
    p.cash_balance = -3000.00
    p.positions = {"QQQ": Position("QQQ", 20, 650.00)}

    current_prices = {"QQQ": 621.89}

    metrics = p.calculate_reg_t_metrics(current_prices)

    assert metrics.total_equity == pytest.approx(9437.80, abs=0.10)
    assert metrics.maintenance_margin_req == 0.0
    assert metrics.excess_liquidity == 0.0
    assert metrics.buying_power == 0.0
    assert metrics.realized == pytest.approx(10000.00, abs=0.10)


def test_reg_t_scenario_5_liquidation():
    """
    Scenario 5: High Deficit Boundary Test
    Cash: -28000. Stock Value: 30400.
    Expected:
    - Equity: 2,400.00
    - Maint Margin: 0.0
    - Excess: 0.0
    - BP: 0.00
    """
    p = Portfolio("test_agent")
    p.cash_balance = -28000.00
    p.positions = {"STK": Position("STK", 380, 100.00)}

    current_prices = {"STK": 80.00}

    metrics = p.calculate_reg_t_metrics(current_prices)

    assert metrics.total_equity == pytest.approx(2400.00, abs=0.10)
    assert metrics.maintenance_margin_req == 0.0
    assert metrics.excess_liquidity == 0.0
    assert metrics.buying_power == 0.00


# --- Persistence Tests ---


@pytest.mark.asyncio
async def test_initialize_existing_portfolio():
    """Test loading a portfolio that already exists in DB."""
    p = Portfolio("existing_agent")

    # Mock supabase response
    mock_db = MagicMock()
    mock_res_portfolio = MagicMock()
    mock_res_portfolio.data = [
        {"id": "uuid-123", "cash_balance": 15000.00, "buying_power": 45000.00, "sma": 15000.00, "realized": 10000.00}
    ]

    mock_res_positions = MagicMock()
    mock_res_positions.data = [{"ticker": "AAPL", "quantity": 10, "average_cost_basis": 150.00}]

    # Setup chain for portfolios select
    mock_db.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
        mock_res_portfolio,
        mock_res_positions,
    ]

    with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
        await p.initialize()

    assert p.id == "uuid-123"
    assert p.cash_balance == 15000.00
    assert "AAPL" in p.positions
    assert p.positions["AAPL"].quantity == 10

    # Verify metrics hydration
    assert p.metrics is not None
    assert p.metrics.buying_power == 45000.00
    assert p.metrics.sma == 15000.00
    assert p.metrics.realized == 10000.00


@pytest.mark.asyncio
async def test_initialize_existing_portfolio_with_null_metrics_fields():
    """Test loading a portfolio where margin metrics columns in DB are NULL (None)."""
    p = Portfolio("null_metrics_agent")

    mock_db = MagicMock()
    mock_res_portfolio = MagicMock()
    mock_res_portfolio.data = [
        {
            "id": "uuid-null-fields",
            "cash_balance": 10000.00,
            "buying_power": 40000.00,
            "total_equity": None,
            "maintenance_margin": None,
            "excess_liquidity": None,
            "sma": None,
            "realized": None,
        }
    ]

    mock_res_positions = MagicMock()
    mock_res_positions.data = []

    mock_db.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
        mock_res_portfolio,
        mock_res_positions,
    ]

    with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
        await p.initialize()

    assert p.id == "uuid-null-fields"
    assert p.cash_balance == 10000.00
    assert p.sma == 0.0
    assert p.metrics is not None
    assert p.metrics.buying_power == 40000.00
    assert p.metrics.maintenance_margin_req == 0.0
    assert p.metrics.total_equity == 0.0
    assert p.metrics.excess_liquidity == 0.0
    assert p.metrics.realized == 10000.00


@pytest.mark.asyncio
async def test_initialize_new_portfolio():
    """Test creating a new portfolio if none exists."""
    p = Portfolio("new_agent")

    mock_db = MagicMock()

    # First select returns empty
    mock_res_empty = MagicMock()
    mock_res_empty.data = []

    # Insert returns new row
    mock_res_insert = MagicMock()
    mock_res_insert.data = [{"id": "uuid-new", "cash_balance": 10000.00}]

    # Setup chain
    # 1. select portfolios -> empty
    # 2. insert portfolios -> data

    # Use side_effect carefully.
    # calling .execute() on the first chain returns empty.
    # calling .execute() on the insert chain (second db call) returns new.

    # A cleaner mock might be needed if the calls overlap, but linear assumption holds here.

    # We can mock the table object differently but let's try strict ordering
    select_mock = MagicMock()
    select_mock.execute.return_value = mock_res_empty

    insert_mock = MagicMock()
    insert_mock.execute.return_value = mock_res_insert

    # table("portfolios").select... -> select_mock
    # table("portfolios").insert... -> insert_mock

    # This requires more complex mocking due to method chaining.
    # Simplified approach:

    mock_table = MagicMock()
    mock_db.table.return_value = mock_table

    # Scenario: select returns empty, then insert happens
    mock_table.select.return_value.eq.return_value.execute.return_value = mock_res_empty
    mock_table.insert.return_value.execute.return_value = mock_res_insert

    with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
        await p.initialize()

        # Verify insert was called with full $10k initial metrics
        mock_table.insert.assert_called_with(
            {
                "owner_id": "new_agent",
                "cash_balance": 10000.00,
                "sma": 10000.00,
                "total_equity": 10000.00,
                "buying_power": 10000.00,
                "excess_liquidity": 10000.00,
                "maintenance_margin": 0.0,
                "realized": 10000.00,
            }
        )

    assert p.id == "uuid-new"
    assert p.cash_balance == 10000.00
    assert p.total_equity == 10000.00
    assert p.metrics is not None
    assert p.metrics.buying_power == 10000.00


@pytest.mark.asyncio
async def test_initialize_existing_portfolio_with_null_metrics():
    """Verify that loading an existing portfolio with NULL total_equity falls back to cash_balance."""
    p = Portfolio("existing_agent")

    mock_db = MagicMock()
    mock_table = MagicMock()
    mock_db.table.return_value = mock_table

    # Existing row where total_equity and buying_power are NULL
    mock_res_existing = MagicMock(
        data=[
            {
                "id": "uuid-existing",
                "owner_id": "existing_agent",
                "cash_balance": 10000.00,
                "sma": 10000.00,
                "total_equity": None,
                "buying_power": None,
                "excess_liquidity": None,
                "maintenance_margin": None,
                "realized": 10000.00,
            }
        ]
    )
    mock_table.select.return_value.eq.return_value.execute.return_value = mock_res_existing
    mock_table.select.return_value.eq.return_value.execute.return_value.data = mock_res_existing.data
    # Positions select returns empty
    pos_mock = MagicMock(data=[])
    mock_table.select.return_value.eq.return_value.execute.side_effect = [mock_res_existing, pos_mock]

    with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
        await p.initialize()

    assert p.id == "uuid-existing"
    assert p.cash_balance == 10000.00
    assert p.total_equity == 10000.00
    assert p.metrics is not None
    assert p.metrics.total_equity == 10000.00
    assert p.metrics.buying_power == 10000.00


@pytest.mark.asyncio
async def test_save_metrics():
    """Test that save_metrics persists calculated metrics to the portfolios table."""
    p = Portfolio("test_agent")
    p.id = "portfolio-123"
    p.metrics = RegTMetrics(
        total_equity=12000.0,
        initial_margin_req=5000.0,
        maintenance_margin_req=2500.0,
        available_funds=7000.0,
        excess_liquidity=9500.0,
        sma=10000.0,
        realized=11000.0,
        buying_power=28000.0,
    )

    mock_db = MagicMock()
    mock_table = MagicMock()
    mock_db.table.return_value = mock_table

    with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
        await p.save_metrics()

        # Verify update call
        mock_table.update.assert_called_once()
        update_payload = mock_table.update.call_args[0][0]

        assert update_payload["total_equity"] == 12000.0
        assert update_payload["maintenance_margin"] == 2500.0
        assert update_payload["buying_power"] == 28000.0
        assert update_payload["sma"] == 10000.0
        assert update_payload["realized"] == 11000.0

        # Verify filtering
        mock_table.update.return_value.eq.assert_called_with("id", "portfolio-123")


def test_calculate_reg_t_metrics_with_positions():
    """Test that calculate_reg_t_metrics works with Position objects."""
    p = Portfolio("test_agent")
    p.cash_balance = 5000.0
    p.positions = {"AAPL": Position("AAPL", 10, 150.0), "MSFT": Position("MSFT", 5, 300.0)}

    current_prices = {
        "AAPL": 160.0,  # Value: 1600
        "MSFT": 320.0,  # Value: 1600
    }
    # Total Stock Value: 3200
    # Total Equity: 5000 + 3200 = 8200
    # Maintenance Margin (33%): 3200 * 0.33 = 1056

    metrics = p.calculate_reg_t_metrics(current_prices)

    assert metrics.total_equity == 8200.0
    assert metrics.maintenance_margin_req == 0.0
    assert metrics.buying_power == 5000.0


class _AtomicTradeRpcDB:
    """Hermetic Supabase RPC stub mimicking `execute_portfolio_trade` ACID semantics."""

    def __init__(
        self,
        *,
        cash_balance: float = 10000.0,
        sma: float = 10000.0,
        positions: dict[str, tuple[int, float]] | None = None,
        rpc_errors: list[Exception] | None = None,
    ):
        self.portfolio = {
            "id": "port-atomic-1",
            "cash_balance": cash_balance,
            "sma": sma,
            "total_equity": cash_balance,
            "buying_power": cash_balance,
            "excess_liquidity": cash_balance,
            "maintenance_margin": 0.0,
            "realized": cash_balance,
        }
        self.positions: dict[str, dict] = {
            t: {"portfolio_id": "port-atomic-1", "ticker": t, "quantity": q, "average_cost_basis": c}
            for t, (q, c) in (positions or {}).items()
        }
        self.trades: list[dict] = []
        self.rpc_errors = list(rpc_errors or [])
        self.seen_idempotency_keys: list[str] = []
        self._trade_seq = 0

    def rpc(self, name: str, params: dict):
        assert name == "execute_portfolio_trade"
        return _RpcCallStub(self, params)


class _RpcCallStub:
    def __init__(self, db: _AtomicTradeRpcDB, params: dict):
        self.db = db
        self.params = params

    def execute(self):
        idem_key = self.params.get("p_idempotency_key")
        if idem_key:
            self.db.seen_idempotency_keys.append(idem_key)

        if self.db.rpc_errors:
            raise self.db.rpc_errors.pop(0)

        for existing in self.db.trades:
            if idem_key and existing.get("idempotency_key") == idem_key:
                pos = self.db.positions.get(existing["ticker"], {})
                return MagicMock(
                    data={
                        "trade_id": existing["id"],
                        "cash_balance": self.db.portfolio["cash_balance"],
                        "sma": self.db.portfolio["sma"],
                        "quantity": existing["quantity"],
                        "total_cost": existing["total_cost"],
                        "realized_pnl": existing.get("realized_pnl"),
                        "realized_pnl_pct": existing.get("realized_pnl_pct"),
                        "position_quantity": pos.get("quantity", 0),
                        "position_avg_cost": pos.get("average_cost_basis", 0.0),
                        "idempotent_replay": True,
                    }
                )

        ticker = self.params["p_ticker"]
        sig = self.params["p_signal"]
        qty = int(self.params["p_quantity"])
        price = float(self.params["p_price"])
        cost = qty * price

        if sig == "BUY":
            if cost > self.db.portfolio["cash_balance"]:
                raise RuntimeError("Insufficient cash balance")
            self.db.portfolio["cash_balance"] -= cost
            if ticker in self.db.positions:
                cur = self.db.positions[ticker]
                new_qty = cur["quantity"] + qty
                cur["average_cost_basis"] = ((cur["average_cost_basis"] * cur["quantity"]) + cost) / new_qty
                cur["quantity"] = new_qty
            else:
                self.db.positions[ticker] = {
                    "portfolio_id": "port-atomic-1",
                    "ticker": ticker,
                    "quantity": qty,
                    "average_cost_basis": price,
                }
            realized_pnl = None
            realized_pnl_pct = None
        else:
            cur = self.db.positions[ticker]
            qty = min(qty, cur["quantity"])
            cost = qty * price
            avg_cost = cur["average_cost_basis"]
            realized_pnl = (price - avg_cost) * qty
            realized_pnl_pct = ((price / avg_cost) - 1) * 100 if avg_cost > 0 else 0.0
            self.db.portfolio["cash_balance"] += cost
            cur["quantity"] -= qty
            if cur["quantity"] == 0:
                self.db.positions.pop(ticker)

        self.db.portfolio["sma"] = max(0.0, self.db.portfolio["cash_balance"])
        self.db._trade_seq += 1
        trade_id = f"trade-{self.db._trade_seq}"
        self.db.trades.append(
            {
                "id": trade_id,
                "ticker": ticker,
                "signal": sig,
                "quantity": qty,
                "price": price,
                "total_cost": cost,
                "realized_pnl": realized_pnl,
                "realized_pnl_pct": realized_pnl_pct,
                "idempotency_key": idem_key,
            }
        )
        pos = self.db.positions.get(ticker, {})
        return MagicMock(
            data={
                "trade_id": trade_id,
                "cash_balance": self.db.portfolio["cash_balance"],
                "sma": self.db.portfolio["sma"],
                "quantity": qty,
                "total_cost": cost,
                "realized_pnl": realized_pnl,
                "realized_pnl_pct": realized_pnl_pct,
                "position_quantity": pos.get("quantity", 0),
                "position_avg_cost": pos.get("average_cost_basis", 0.0),
                "idempotent_replay": False,
            }
        )


@pytest.mark.asyncio
async def test_execute_trade_rolls_back_positions_and_trade_when_cash_update_fails():
    """If atomic RPC fails, neither DB nor in-memory portfolio state is partially mutated."""
    p = Portfolio("sys-sentiment-fader")
    p.id = "port-atomic-1"
    p.cash_balance = 5211.91
    p.sma = 5211.91
    p.positions = {"SPY": Position("SPY", 6, 718.16)}

    db = _AtomicTradeRpcDB(
        cash_balance=5211.91,
        sma=5211.91,
        positions={"SPY": (6, 718.16)},
        rpc_errors=[RuntimeError("PostgREST write failed")],
    )

    with (
        patch("execution.portfolio.get_supabase_client", return_value=db),
        patch("execution.alpaca_broker.AlpacaBroker") as mock_broker,
    ):
        trade_id = await p.execute_trade(
            ticker="QQQ",
            quantity=7,
            price=647.34,
            signal="BUY",
            current_prices={"SPY": 718.16, "QQQ": 647.34},
            skip_alpaca_mirror=False,
        )

    assert trade_id is None
    assert p.cash_balance == pytest.approx(5211.91)
    assert "QQQ" not in p.positions
    assert db.portfolio["cash_balance"] == pytest.approx(5211.91)
    assert "QQQ" not in db.positions
    assert db.trades == []
    mock_broker.assert_not_called()


@pytest.mark.asyncio
async def test_execute_trade_retries_transient_cash_update_error():
    """Transient 502/504 errors on execute_portfolio_trade RPC retry with the same idempotency_key."""
    p = Portfolio("sys-sentiment-fader")
    p.id = "port-atomic-1"
    p.cash_balance = 5211.91
    p.sma = 5211.91

    db = _AtomicTradeRpcDB(
        cash_balance=5211.91,
        sma=5211.91,
        rpc_errors=[Exception("502 Bad Gateway")],
    )

    with (
        patch("execution.portfolio.get_supabase_client", return_value=db),
        patch("core.db.asyncio.sleep", return_value=None),
    ):
        trade_id = await p.execute_trade(
            ticker="QQQ",
            quantity=7,
            price=647.34,
            signal="BUY",
            current_prices={"QQQ": 647.34},
            skip_alpaca_mirror=True,
        )

    assert trade_id == "trade-1"
    assert db.portfolio["cash_balance"] == pytest.approx(5211.91 - 7 * 647.34)
    assert "QQQ" in db.positions
    assert len(db.trades) == 1
    assert len(db.seen_idempotency_keys) == 2
    assert db.seen_idempotency_keys[0] == db.seen_idempotency_keys[1]


@pytest.mark.asyncio
async def test_execute_trade_sell_rollback_restores_deleted_position():
    """If a SELL RPC fails, in-memory and DB positions/cash remain completely unchanged."""
    p = Portfolio("sys-sentiment-fader")
    p.id = "port-atomic-1"
    p.cash_balance = 186.63
    p.sma = 186.63
    p.positions = {"SPY": Position("SPY", 13, 729.13)}

    db = _AtomicTradeRpcDB(
        cash_balance=186.63,
        sma=186.63,
        positions={"SPY": (13, 729.13)},
        rpc_errors=[RuntimeError("PostgREST write failed")],
    )

    with patch("execution.portfolio.get_supabase_client", return_value=db):
        trade_id = await p.execute_trade(
            ticker="SPY",
            quantity=13,
            price=718.02,
            signal="SELL",
            current_prices={"SPY": 718.02},
            skip_alpaca_mirror=True,
        )

    assert trade_id is None
    assert p.cash_balance == pytest.approx(186.63)
    assert p.positions["SPY"].quantity == 13
    assert p.positions["SPY"].average_cost_basis == pytest.approx(729.13)
    assert db.portfolio["cash_balance"] == pytest.approx(186.63)
    assert db.positions["SPY"]["quantity"] == 13
    assert db.positions["SPY"]["average_cost_basis"] == pytest.approx(729.13)
    assert db.trades == []


@pytest.mark.asyncio
async def test_execute_trade_rejects_invalid_signal():
    """Invalid trade signals (anything other than BUY/SELL) must fail closed before DB RPC."""
    p = Portfolio("sys-sentiment-fader")
    p.id = "port-atomic-1"
    p.cash_balance = 10000.0
    db = _AtomicTradeRpcDB()

    with patch("execution.portfolio.get_supabase_client", return_value=db):
        res = await p.execute_trade(
            ticker="SPY",
            quantity=5,
            price=500.0,
            signal="HOLD",
            skip_alpaca_mirror=True,
        )

    assert res is None
    assert p.cash_balance == pytest.approx(10000.0)
    assert db.seen_idempotency_keys == []


@pytest.mark.asyncio
async def test_execute_trade_idempotent_replay_after_commit_timeout():
    """If DB committed on attempt 1 before a 504 timeout, retry replays without double-charging."""
    p = Portfolio("sys-sentiment-fader")
    p.id = "port-atomic-1"
    p.cash_balance = 5211.91
    p.sma = 5211.91

    db = _AtomicTradeRpcDB(cash_balance=5211.91, sma=5211.91)
    real_rpc = db.rpc
    attempts = {"n": 0}

    def commit_then_timeout(name: str, params: dict):
        call = real_rpc(name, params)
        orig_execute = call.execute

        def flaky_execute():
            attempts["n"] += 1
            res = orig_execute()
            if attempts["n"] == 1:
                raise Exception("504 Gateway Timeout after commit")
            return res

        call.execute = flaky_execute
        return call

    db.rpc = commit_then_timeout

    with (
        patch("execution.portfolio.get_supabase_client", return_value=db),
        patch("core.db.asyncio.sleep", return_value=None),
    ):
        trade_id = await p.execute_trade(
            ticker="QQQ",
            quantity=7,
            price=647.34,
            signal="BUY",
            current_prices={"QQQ": 647.34},
            skip_alpaca_mirror=True,
        )

    assert trade_id == "trade-1"
    assert attempts["n"] == 2
    assert len(db.trades) == 1
    assert db.portfolio["cash_balance"] == pytest.approx(5211.91 - 7 * 647.34)
    assert p.cash_balance == pytest.approx(5211.91 - 7 * 647.34)


def test_backtest_sandbox_rpc_executes_locally_in_sqlite(tmp_path):
    """Portfolio.execute_trade via MockSimulatedSupabaseClient must run locally in SQLite and block unknown RPCs."""
    import asyncio
    import sqlite3
    from datetime import UTC, datetime

    from tasks import backtest_autoresearch

    db_file = tmp_path / "backtest_test.db"
    real_client = MagicMock()
    t_sim = datetime(2026, 11, 19, 15, 0, tzinfo=UTC)

    with patch.object(backtest_autoresearch, "DB_PATH", str(db_file)):
        backtest_autoresearch.init_backtest_db()
        conn = sqlite3.connect(str(db_file))
        conn.execute(
            "INSERT INTO portfolios (id, owner_id, cash_balance, sma, total_equity, buying_power, excess_liquidity, maintenance_margin, realized) "
            "VALUES ('p-sim-1', 'sim-agent', 10000.0, 10000.0, 10000.0, 10000.0, 10000.0, 0.0, 10000.0)"
        )
        conn.commit()
        conn.close()

        sim_client = backtest_autoresearch.MockSimulatedSupabaseClient(real_client, t_sim)
        p = Portfolio("sim-agent")
        p.id = "p-sim-1"
        p.cash_balance = 10000.0
        p.sma = 10000.0

        with patch("execution.portfolio.get_supabase_client", return_value=sim_client):
            trade_id = asyncio.run(
                p.execute_trade(
                    ticker="SPY",
                    quantity=5,
                    price=500.0,
                    signal="BUY",
                    current_prices={"SPY": 500.0},
                    skip_alpaca_mirror=True,
                )
            )

        replay = sim_client.rpc(
            "execute_portfolio_trade",
            {
                "p_portfolio_id": "p-sim-1",
                "p_ticker": "SPY",
                "p_signal": "BUY",
                "p_quantity": 5,
                "p_price": 500.0,
                "p_idempotency_key": "idem-sim-1",
            },
        ).execute()
        replay_again = sim_client.rpc(
            "execute_portfolio_trade",
            {
                "p_portfolio_id": "p-sim-1",
                "p_ticker": "SPY",
                "p_signal": "BUY",
                "p_quantity": 5,
                "p_price": 500.0,
                "p_idempotency_key": "idem-sim-1",
            },
        ).execute()

        with pytest.raises(ValueError, match="not allowlisted"):
            sim_client.rpc("some_mutating_rpc", {})

    assert trade_id is not None
    assert p.cash_balance == pytest.approx(7500.0)
    assert p.positions["SPY"].quantity == 5
    assert replay_again.data["idempotent_replay"] is True
    assert replay_again.data["trade_id"] == replay.data["trade_id"]
    real_client.rpc.assert_not_called()


def test_is_transient_supabase_error_ignores_business_digits_and_p0001():
    """Business/SQL errors containing digits like 4290 or UUID 504 must fail fast, not retry."""
    from core.db import is_transient_supabase_error

    assert is_transient_supabase_error(RuntimeError("Insufficient cash balance: need 4290, available 1502")) is False
    assert is_transient_supabase_error(RuntimeError("Price $502.34 invalid")) is False
    assert (
        is_transient_supabase_error(RuntimeError("Portfolio a1b2c3d4-504a-4000-8000-000000000001 not found")) is False
    )
    assert is_transient_supabase_error(RuntimeError("{'code': 'P0001', 'message': '503 insufficient cash'}")) is False

    assert is_transient_supabase_error(Exception("502 Bad Gateway")) is True
    assert is_transient_supabase_error(Exception("HTTP 429 Too Many Requests")) is True
    err_with_status = RuntimeError("upstream error")
    err_with_status.status_code = 503
    assert is_transient_supabase_error(err_with_status) is True


@pytest.mark.asyncio
async def test_execute_trade_is_single_atomic_rpc_without_post_save_metrics():
    """execute_trade must pass p_mark_prices to the atomic RPC and not run an unlocked post-RPC save_metrics."""
    p = Portfolio("sys-sentiment-fader")
    p.id = "port-atomic-1"
    p.cash_balance = 10000.0
    db = _AtomicTradeRpcDB(cash_balance=10000.0, sma=10000.0)

    with (
        patch("execution.portfolio.get_supabase_client", return_value=db),
        patch.object(p, "save_metrics") as mock_save_metrics,
    ):
        trade_id = await p.execute_trade(
            ticker="QQQ",
            quantity=5,
            price=500.0,
            signal="BUY",
            current_prices={"QQQ": 500.0},
            skip_alpaca_mirror=True,
        )

    assert trade_id == "trade-1"
    mock_save_metrics.assert_not_called()


@pytest.mark.asyncio
async def test_execute_trade_rejects_nan_and_infinite_prices():
    """NaN and Infinity prices must fail preflight validation before touching DB."""
    p = Portfolio("sys-sentiment-fader")
    p.id = "port-atomic-1"
    p.cash_balance = 10000.0
    db = _AtomicTradeRpcDB(cash_balance=10000.0, sma=10000.0)

    with patch("execution.portfolio.get_supabase_client", return_value=db):
        assert await p.execute_trade("SPY", 5, float("nan"), "BUY", skip_alpaca_mirror=True) is None
        assert await p.execute_trade("SPY", 5, float("inf"), "BUY", skip_alpaca_mirror=True) is None

    assert db.trades == []
