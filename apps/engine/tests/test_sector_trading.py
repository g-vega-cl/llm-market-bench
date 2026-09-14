"""Tests for live weekly sector portfolio trade execution and position lifecycle."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from execution.sector_trading import (
    execute_mechanical_sector_entry,
    execute_mechanical_sector_exit,
    execute_system_sector_entry,
    execute_system_sector_exit,
    run_sector_trade,
)
from execution.system_portfolios import (
    SYS_SECTOR_UNCORR_20D_OWNER_ID,
)


@pytest.mark.asyncio
async def test_execute_system_sector_entry_creates_trades_and_positions():
    """Verify that live sector entry logs BUY/SHORT trades and creates long positions."""
    mock_client = MagicMock()
    mock_chain = MagicMock()
    mock_chain.select.return_value = mock_chain
    mock_chain.insert.return_value = mock_chain
    mock_chain.update.return_value = mock_chain
    mock_chain.delete.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain
    mock_chain.order.return_value = mock_chain
    mock_chain.in_.return_value = mock_chain
    mock_chain.gte.return_value = mock_chain
    mock_chain.lte.return_value = mock_chain
    mock_chain.upsert.return_value = mock_chain
    mock_chain.execute.return_value = MagicMock(data=[])

    def mock_table(table_name):
        return mock_chain

    mock_client.table.side_effect = mock_table

    mock_portfolio = MagicMock()
    mock_portfolio.id = "port-sector-ls-123"
    mock_portfolio.cash_balance = 10000.0

    predictions = [
        {"predicted_sector": "XLK", "predicted_worst_sector": "XLE"},
    ]
    price_map = {
        "XLK": 100.0,
        "XLE": 50.0,
    }

    with (
        patch("execution.sector_trading.get_supabase_client", return_value=mock_client),
        patch("execution.sector_trading.get_or_create_system_portfolio", return_value=mock_portfolio),
    ):
        res = await execute_system_sector_entry(
            week_start_date="2026-09-14",
            predictions=predictions,
            price_map=price_map,
        )

    assert res["status"] == "success"
    assert res["long_sectors"] == ["XLK"]
    assert res["short_sectors"] == ["XLE"]

    # Verify trades inserted: 1 BUY and 1 SHORT
    inserted_trades = [call[0][0] for call in mock_chain.insert.call_args_list if "signal" in call[0][0]]
    assert len(inserted_trades) == 2
    signals = {t["signal"]: t for t in inserted_trades}
    assert "BUY" in signals
    assert "SHORT" in signals
    assert signals["BUY"]["ticker"] == "XLK"
    assert signals["SHORT"]["ticker"] == "XLE"

    # Verify long position upserted in portfolio_positions
    upserted_positions = [call[0][0] for call in mock_chain.upsert.call_args_list if "average_cost_basis" in call[0][0]]
    assert len(upserted_positions) >= 1
    assert upserted_positions[0]["ticker"] == "XLK"
    assert upserted_positions[0]["quantity"] > 0


@pytest.mark.asyncio
async def test_execute_mechanical_sector_entry_and_exit_lifecycle():
    """Verify that mechanical sector portfolio entries create positions and exits clear them with realized PnL."""
    mock_client = MagicMock()
    mock_chain = MagicMock()
    mock_chain.select.return_value = mock_chain
    mock_chain.insert.return_value = mock_chain
    mock_chain.update.return_value = mock_chain
    mock_chain.delete.return_value = mock_chain
    mock_chain.match.return_value = mock_chain
    mock_chain.order.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain
    mock_chain.in_.return_value = mock_chain
    mock_chain.gte.return_value = mock_chain
    mock_chain.lte.return_value = mock_chain
    mock_chain.upsert.return_value = mock_chain
    mock_chain.execute.return_value = MagicMock(data=[])

    mock_client.table.return_value = mock_chain

    mock_portfolio = MagicMock()
    mock_portfolio.id = "port-uncorr-20d-123"
    mock_portfolio.cash_balance = 10000.0

    entry_prices = {"XLK": 100.0, "XLV": 50.0}

    # 1. Entry
    with (
        patch("execution.sector_trading.get_supabase_client", return_value=mock_client),
        patch("execution.sector_trading.get_or_create_system_portfolio", return_value=mock_portfolio),
    ):
        res_entry = await execute_mechanical_sector_entry(
            owner_id=SYS_SECTOR_UNCORR_20D_OWNER_ID,
            sectors=["XLK", "XLV"],
            week_start_date="2026-09-14",
            price_map=entry_prices,
        )

    assert res_entry["status"] == "success"
    assert res_entry["sectors"] == ["XLK", "XLV"]

    # 2. Exit
    exit_prices = {"XLK": 110.0, "XLV": 55.0}  # Both gained 10%
    mock_open_trades = [
        {
            "id": "t1",
            "portfolio_id": "port-uncorr-20d-123",
            "ticker": "XLK",
            "signal": "BUY",
            "quantity": 50,
            "price": 100.05,
            "total_cost": 5002.5,
            "executed_at": "2026-09-14T13:30:00Z",
            "realized_pnl": None,
        },
        {
            "id": "t2",
            "portfolio_id": "port-uncorr-20d-123",
            "ticker": "XLV",
            "signal": "BUY",
            "quantity": 100,
            "price": 50.025,
            "total_cost": 5002.5,
            "executed_at": "2026-09-14T13:30:00Z",
            "realized_pnl": None,
        },
    ]

    mock_chain.execute.return_value = MagicMock(data=mock_open_trades)

    with (
        patch("execution.sector_trading.get_supabase_client", return_value=mock_client),
        patch("execution.sector_trading.get_or_create_system_portfolio", return_value=mock_portfolio),
    ):
        res_exit = await execute_mechanical_sector_exit(
            owner_id=SYS_SECTOR_UNCORR_20D_OWNER_ID,
            week_end_date="2026-09-18",
            price_map=exit_prices,
        )

    assert res_exit["status"] == "success"
    assert res_exit["total_realized_pnl"] > 0
    assert mock_chain.delete.called


@pytest.mark.asyncio
async def test_execute_system_sector_exit_consensus():
    """Verify that consensus sector portfolio exit handles both SELL for longs and COVER for shorts."""
    mock_client = MagicMock()
    mock_chain = MagicMock()
    mock_chain.select.return_value = mock_chain
    mock_chain.insert.return_value = mock_chain
    mock_chain.update.return_value = mock_chain
    mock_chain.delete.return_value = mock_chain
    mock_chain.match.return_value = mock_chain
    mock_chain.order.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain
    mock_chain.upsert.return_value = mock_chain

    mock_client.table.return_value = mock_chain

    mock_portfolio = MagicMock()
    mock_portfolio.id = "port-sector-ls-123"
    mock_portfolio.cash_balance = 10000.0

    mock_open_trades = [
        {
            "id": "t1",
            "portfolio_id": "port-sector-ls-123",
            "ticker": "XLK",
            "signal": "BUY",
            "quantity": 50,
            "price": 100.05,
            "total_cost": 5002.5,
            "executed_at": "2026-09-14T13:30:00Z",
            "realized_pnl": None,
        },
        {
            "id": "t2",
            "portfolio_id": "port-sector-ls-123",
            "ticker": "XLE",
            "signal": "SHORT",
            "quantity": 100,
            "price": 50.00,
            "total_cost": 5000.0,
            "executed_at": "2026-09-14T13:30:00Z",
            "realized_pnl": None,
        },
    ]
    mock_chain.execute.return_value = MagicMock(data=mock_open_trades)

    exit_prices = {"XLK": 110.0, "XLE": 45.0}  # Long gained, Short dropped (both profitable)

    with (
        patch("execution.sector_trading.get_supabase_client", return_value=mock_client),
        patch("execution.sector_trading.get_or_create_system_portfolio", return_value=mock_portfolio),
    ):
        res_exit = await execute_system_sector_exit(
            week_end_date="2026-09-18",
            price_map=exit_prices,
        )

    assert res_exit["status"] == "success"
    assert res_exit["total_realized_pnl"] > 0
    # Both trades should be profitable
    assert len(res_exit["trades"]) == 2
    sides = {t["side"]: t for t in res_exit["trades"]}
    assert "SELL" in sides
    assert "COVER" in sides
    assert sides["SELL"]["pnl"] > 0
    assert sides["COVER"]["pnl"] > 0


@pytest.mark.asyncio
async def test_run_sector_trade_orchestrator():
    """Verify high-level orchestration of run_sector_trade for entry and exit actions."""
    mock_client = MagicMock()
    mock_chain = MagicMock()
    mock_chain.select.return_value = mock_chain
    mock_chain.order.return_value = mock_chain
    mock_chain.limit.return_value = mock_chain
    mock_chain.lte.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain

    # Mock predictions
    mock_preds = [{"predicted_sector": "XLK", "predicted_worst_sector": "XLE"}]
    # Mock correlation run
    mock_corr_run = [{"id": "run-1", "tickers": ["XLK", "XLE", "XLV"]}]
    # Mock correlation data
    mock_corr_data = [
        {"ticker_a": "XLK", "ticker_b": "XLV", "pearson_corr": 0.1, "returns_a_7d": 2.0, "returns_b_7d": 1.0}
    ]

    def mock_table_routing(table_name):
        c = MagicMock()
        c.select.return_value = c
        c.order.return_value = c
        c.limit.return_value = c
        c.lte.return_value = c
        c.eq.return_value = c
        if table_name == "sector_predictions":
            c.execute.return_value = MagicMock(data=mock_preds)
        elif table_name == "correlation_runs":
            c.execute.return_value = MagicMock(data=mock_corr_run)
        elif table_name == "correlation_data":
            c.execute.return_value = MagicMock(data=mock_corr_data)
        else:
            c.execute.return_value = MagicMock(data=[])
        return c

    mock_client.table.side_effect = mock_table_routing

    mock_mdm = MagicMock()
    quote_mock = MagicMock()
    quote_mock.price = 100.0
    quote_mock.open = 99.5
    mock_mdm.get_quotes = AsyncMock(return_value={"XLK": quote_mock, "XLE": quote_mock, "XLV": quote_mock})

    with (
        patch("execution.sector_trading.get_supabase_client", return_value=mock_client),
        patch("execution.market_data.MarketDataManager", return_value=mock_mdm),
        patch("execution.sector_trading.execute_system_sector_entry", new_callable=AsyncMock) as mock_sys_entry,
        patch("execution.sector_trading.execute_mechanical_sector_entry", new_callable=AsyncMock) as mock_mech_entry,
    ):
        mock_sys_entry.return_value = {"status": "success"}
        mock_mech_entry.return_value = {"status": "success"}

        res = await run_sector_trade(action="entry", target_date_str="2026-09-14")

    assert res["status"] == "success"
    assert res["action"] == "entry"
    assert mock_sys_entry.called
    assert mock_mech_entry.called


@pytest.mark.asyncio
async def test_execute_system_sector_entry_idempotency():
    """Verify that running entry twice on the same start date skips re-entry."""
    mock_client = MagicMock()
    mock_chain = MagicMock()
    mock_chain.select.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain
    # Simulate existing entry trades returned from trades table query
    mock_chain.execute.return_value = MagicMock(data=[{"id": "existing-t1", "ticker": "XLK", "signal": "BUY"}])
    mock_client.table.return_value = mock_chain

    mock_port = MagicMock(id="port-123", cash_balance=10000.0)

    with (
        patch("execution.sector_trading.get_supabase_client", return_value=mock_client),
        patch("execution.sector_trading.get_or_create_system_portfolio", return_value=mock_port),
    ):
        res = await execute_system_sector_entry(
            week_start_date="2026-09-14",
            predictions=[{"predicted_sector": "XLK", "predicted_worst_sector": "XLE"}],
            price_map={"XLK": 100.0, "XLE": 50.0},
        )

    assert res["status"] == "skipped"
    assert "Already entered" in res["reason"]


@pytest.mark.asyncio
async def test_execute_mechanical_sector_entry_idempotency():
    """Verify that running mechanical entry twice on the same start date skips re-entry."""
    mock_client = MagicMock()
    mock_chain = MagicMock()
    mock_chain.select.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain
    mock_chain.execute.return_value = MagicMock(data=[{"id": "existing-m1"}])
    mock_client.table.return_value = mock_chain

    mock_port = MagicMock(id="port-mech-123", cash_balance=10000.0)

    with (
        patch("execution.sector_trading.get_supabase_client", return_value=mock_client),
        patch("execution.sector_trading.get_or_create_system_portfolio", return_value=mock_port),
    ):
        res = await execute_mechanical_sector_entry(
            owner_id=SYS_SECTOR_UNCORR_20D_OWNER_ID,
            sectors=["XLK", "XLV"],
            week_start_date="2026-09-14",
            price_map={"XLK": 100.0, "XLV": 50.0},
        )

    assert res["status"] == "skipped"
    assert "Already entered" in res["reason"]


@pytest.mark.asyncio
async def test_execute_sector_entry_before_start_date():
    """Verify that windows before SYS_SECTOR_START_DATE (2026-08-17) are cleanly skipped."""
    res = await execute_system_sector_entry(
        week_start_date="2026-08-01",
        predictions=[{"predicted_sector": "XLK"}],
        price_map={"XLK": 100.0},
    )
    assert res["status"] == "skipped"
    assert "Before start date" in res["reason"]


@pytest.mark.asyncio
async def test_execute_system_sector_exit_dry_run():
    """Verify that dry_run skips DB deletions and insertions during exit."""
    mock_client = MagicMock()
    mock_chain = MagicMock()
    mock_chain.select.return_value = mock_chain
    mock_chain.insert.return_value = mock_chain
    mock_chain.update.return_value = mock_chain
    mock_chain.delete.return_value = mock_chain
    mock_chain.match.return_value = mock_chain
    mock_chain.order.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain
    mock_chain.upsert.return_value = mock_chain

    mock_client.table.return_value = mock_chain
    mock_portfolio = MagicMock(id="port-sector-ls-123", cash_balance=10000.0)

    mock_open_trades = [
        {
            "id": "t1",
            "portfolio_id": "port-sector-ls-123",
            "ticker": "XLK",
            "signal": "BUY",
            "quantity": 50,
            "price": 100.0,
            "total_cost": 5000.0,
            "executed_at": "2026-09-14T13:30:00Z",
            "realized_pnl": None,
        },
    ]
    mock_chain.execute.return_value = MagicMock(data=mock_open_trades)

    with (
        patch("execution.sector_trading.get_supabase_client", return_value=mock_client),
        patch("execution.sector_trading.get_or_create_system_portfolio", return_value=mock_portfolio),
    ):
        res = await execute_system_sector_exit(
            week_end_date="2026-09-18",
            price_map={"XLK": 105.0},
            dry_run=True,
        )

    assert res["status"] == "success"
    assert res["dry_run"] is True
    assert not mock_chain.insert.called
    assert not mock_chain.delete.called
    assert not mock_chain.update.called


@pytest.mark.asyncio
async def test_run_sector_trade_status():
    """Verify that action='status' queries all 5 portfolios and returns summary without trading."""
    mock_client = MagicMock()
    mock_chain = MagicMock()
    mock_chain.select.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain
    mock_chain.is_.return_value = mock_chain
    mock_chain.execute.return_value = MagicMock(data=[])
    mock_client.table.return_value = mock_chain

    mock_portfolio = MagicMock(id="p-1", cash_balance=10000.0, total_equity=10000.0)

    with (
        patch("execution.sector_trading.get_supabase_client", return_value=mock_client),
        patch("execution.sector_trading.get_or_create_system_portfolio", return_value=mock_portfolio),
    ):
        res = await run_sector_trade(action="status")

    assert res["status"] == "success"
    assert res["action"] == "status"
    assert len(res["portfolios"]) == 5

