"""Tests for 30-day and 90-day systematic sector predictor portfolios (Benchify standard)."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from execution.sector_trading import (
    execute_system_sector_entry,
    execute_system_sector_exit,
    get_sector_portfolios_status,
)
from execution.system_portfolios import (
    ALL_SECTOR_LS_OWNER_IDS,
    SYS_SECTOR_LS_30D_OWNER_ID,
    SYS_SECTOR_LS_90D_OWNER_ID,
    SYS_SECTOR_LS_OWNER_ID,
    resolve_horizon_predictions,
)


def test_horizon_constants_and_registry():
    """Verify owner IDs for 30d and 90d sector portfolios are defined and registered."""
    assert SYS_SECTOR_LS_30D_OWNER_ID == "sys-sector-ls-30d"
    assert SYS_SECTOR_LS_90D_OWNER_ID == "sys-sector-ls-90d"
    assert SYS_SECTOR_LS_OWNER_ID in ALL_SECTOR_LS_OWNER_IDS
    assert SYS_SECTOR_LS_30D_OWNER_ID in ALL_SECTOR_LS_OWNER_IDS
    assert SYS_SECTOR_LS_90D_OWNER_ID in ALL_SECTOR_LS_OWNER_IDS


def test_resolve_horizon_predictions_scoping():
    """Verify resolve_horizon_predictions strictly isolates predictions by timeframe."""
    mixed_preds = [
        {
            "prediction_date": "2026-08-17",
            "timeframe": "7d",
            "predicted_sector": "XLK",
            "predicted_worst_sector": "XLE",
        },
        {
            "prediction_date": "2026-08-17",
            "timeframe": "30d",
            "predicted_sector": "XLV",
            "predicted_worst_sector": "XLI",
        },
        {
            "prediction_date": "2026-08-17",
            "timeframe": "30d",
            "predicted_sector": "XLF",
            "predicted_worst_sector": "XLU",
        },
        {
            "prediction_date": "2026-08-17",
            "timeframe": "90d",
            "predicted_sector": "XLE",
            "predicted_worst_sector": "XLK",
        },
    ]

    preds_30d = resolve_horizon_predictions(mixed_preds, "30d")
    assert len(preds_30d) == 2
    assert all(p["timeframe"] == "30d" for p in preds_30d)
    assert {p["predicted_sector"] for p in preds_30d} == {"XLV", "XLF"}

    preds_90d = resolve_horizon_predictions(mixed_preds, "90d")
    assert len(preds_90d) == 1
    assert preds_90d[0]["predicted_sector"] == "XLE"
    assert preds_90d[0]["predicted_worst_sector"] == "XLK"


@pytest.mark.asyncio
async def test_30d_sector_entry_and_alpaca_mirror():
    """Verify that execute_system_sector_entry with SYS_SECTOR_LS_30D_OWNER_ID executes correctly."""
    mock_client = MagicMock()
    mock_chain = MagicMock()
    mock_chain.select.return_value = mock_chain
    mock_chain.insert.return_value = mock_chain
    mock_chain.update.return_value = mock_chain
    mock_chain.upsert.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain
    mock_chain.execute.return_value = MagicMock(data=[])
    mock_client.table.return_value = mock_chain

    mock_portfolio = MagicMock()
    mock_portfolio.id = uuid4()
    mock_portfolio.cash_balance = 10000.0

    predictions = [
        {"predicted_sector": "XLV", "predicted_worst_sector": "XLI", "timeframe": "30d"},
    ]
    price_map = {"XLV": 100.0, "XLI": 50.0}

    with (
        patch("execution.sector_trading.get_supabase_client", return_value=mock_client),
        patch("execution.sector_trading.get_or_create_system_portfolio", return_value=mock_portfolio),
        patch("execution.alpaca_broker.AlpacaBroker.submit_limit_order", new_callable=AsyncMock) as mock_alpaca_order,
    ):
        res = await execute_system_sector_entry(
            week_start_date="2026-08-17",
            predictions=predictions,
            price_map=price_map,
            owner_id=SYS_SECTOR_LS_30D_OWNER_ID,
            dry_run=False,
        )

    assert res["status"] == "success"
    assert res["owner_id"] == SYS_SECTOR_LS_30D_OWNER_ID
    # Long leg XLV submitted to Alpaca
    assert mock_alpaca_order.call_count == 1
    assert mock_alpaca_order.call_args.kwargs["ticker"] == "XLV"
    assert mock_alpaca_order.call_args.kwargs["signal"] == "BUY"
    assert mock_alpaca_order.call_args.kwargs["agent_id"] == SYS_SECTOR_LS_30D_OWNER_ID


@pytest.mark.asyncio
async def test_90d_sector_exit_and_alpaca_mirror():
    """Verify that execute_system_sector_exit with SYS_SECTOR_LS_90D_OWNER_ID executes correctly."""
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

    mock_portfolio = MagicMock()
    mock_portfolio.id = uuid4()
    mock_portfolio.cash_balance = 5000.0

    mock_open_trades = [
        {
            "id": "t-90d-1",
            "portfolio_id": str(mock_portfolio.id),
            "ticker": "XLE",
            "signal": "BUY",
            "quantity": 50,
            "price": 80.0,
            "total_cost": 4000.0,
            "executed_at": "2026-08-17T13:30:00Z",
            "realized_pnl": None,
        }
    ]
    mock_chain.execute.return_value = MagicMock(data=mock_open_trades)
    mock_client.table.return_value = mock_chain

    with (
        patch("execution.sector_trading.get_supabase_client", return_value=mock_client),
        patch("execution.sector_trading.get_or_create_system_portfolio", return_value=mock_portfolio),
        patch("execution.alpaca_broker.AlpacaBroker.submit_limit_order", new_callable=AsyncMock) as mock_alpaca_order,
    ):
        res = await execute_system_sector_exit(
            week_end_date="2026-11-15",
            price_map={"XLE": 90.0},
            owner_id=SYS_SECTOR_LS_90D_OWNER_ID,
            dry_run=False,
        )

    assert res["status"] == "success"
    assert res["owner_id"] == SYS_SECTOR_LS_90D_OWNER_ID
    assert res["total_realized_pnl"] > 0
    assert mock_alpaca_order.call_count == 1
    assert mock_alpaca_order.call_args.kwargs["ticker"] == "XLE"
    assert mock_alpaca_order.call_args.kwargs["signal"] == "SELL"
    assert mock_alpaca_order.call_args.kwargs["agent_id"] == SYS_SECTOR_LS_90D_OWNER_ID


@pytest.mark.asyncio
async def test_get_sector_portfolios_status_includes_30d_and_90d():
    """Verify get_sector_portfolios_status inspects all 7 sector portfolios (7d, 30d, 90d + 4 mechanical)."""
    mock_client = MagicMock()
    mock_chain = MagicMock()
    mock_chain.select.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain
    mock_chain.is_.return_value = mock_chain
    mock_chain.execute.return_value = MagicMock(data=[])
    mock_client.table.return_value = mock_chain

    mock_port = MagicMock()
    mock_port.id = uuid4()
    mock_port.cash_balance = 10000.0
    mock_port.total_equity = 10000.0

    with (
        patch("execution.sector_trading.get_supabase_client", return_value=mock_client),
        patch("execution.sector_trading.get_or_create_system_portfolio", return_value=mock_port),
    ):
        status = await get_sector_portfolios_status()

    assert "sys-sector-ls-consensus" in status
    assert "sys-sector-ls-30d" in status
    assert "sys-sector-ls-90d" in status
    assert len(status) == 7


@pytest.mark.asyncio
async def test_execute_horizon_sector_entries_skips_when_open_and_enters_when_empty():
    """Verify execute_horizon_sector_entries skips if positions exist, and enters if clean."""
    from execution.sector_horizon_trading import execute_horizon_sector_entries

    mock_client = MagicMock()
    mock_chain = MagicMock()
    mock_chain.select.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain
    mock_chain.lte.return_value = mock_chain
    mock_chain.order.return_value = mock_chain
    mock_chain.limit.return_value = mock_chain
    mock_chain.is_.return_value = mock_chain
    mock_chain.execute.return_value = MagicMock(data=[])
    mock_client.table.return_value = mock_chain

    mock_port = MagicMock()
    mock_port.id = uuid4()
    mock_port.cash_balance = 10000.0

    mock_preds = [
        {
            "prediction_date": "2026-08-17",
            "timeframe": "30d",
            "predicted_sector": "XLK",
            "predicted_worst_sector": "XLE",
        },
    ]

    with (
        patch("execution.sector_horizon_trading.get_supabase_client", return_value=mock_client),
        patch("execution.sector_horizon_trading.get_or_create_system_portfolio", return_value=mock_port),
        patch("execution.sector_trading.execute_system_sector_entry", new_callable=AsyncMock) as mock_entry,
    ):
        mock_chain.execute.side_effect = [
            MagicMock(data=[]),  # pos_res for 30d
            MagicMock(data=[]),  # open_trades_res for 30d
            MagicMock(data=mock_preds),  # preds_res for 30d
            MagicMock(data=[{"ticker": "XLF"}]),  # pos_res for 90d (already has position)
            MagicMock(data=[]),  # open_trades_res for 90d
        ]
        mock_entry.return_value = {"status": "success"}

        res = await execute_horizon_sector_entries(
            today_str="2026-08-17",
            price_map={"XLK": 100.0, "XLE": 50.0},
            dry_run=False,
        )

        assert mock_entry.call_count == 1
        assert res["sys-sector-ls-30d"]["status"] == "success"
        assert res["sys-sector-ls-90d"]["status"] == "skipped"


@pytest.mark.asyncio
async def test_execute_horizon_sector_exits_holds_until_maturity():
    """Verify execute_horizon_sector_exits holds positions until maturity date has arrived."""
    from execution.sector_horizon_trading import execute_horizon_sector_exits

    mock_client = MagicMock()
    mock_chain = MagicMock()
    mock_chain.select.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain
    mock_chain.is_.return_value = mock_chain
    mock_client.table.return_value = mock_chain

    mock_port = MagicMock()
    mock_port.id = uuid4()

    # Open trade entered on 2026-08-17 (30d maturity is 2026-09-16)
    open_trades = [{"id": "t1", "executed_at": "2026-08-17T13:30:00Z", "ticker": "XLK", "signal": "BUY"}]

    with (
        patch("execution.sector_horizon_trading.get_supabase_client", return_value=mock_client),
        patch("execution.sector_horizon_trading.get_or_create_system_portfolio", return_value=mock_port),
        patch("execution.sector_trading.execute_system_sector_exit", new_callable=AsyncMock) as mock_exit,
    ):
        mock_chain.execute.return_value = MagicMock(data=open_trades)

        # 1. On 2026-08-25 (only 8 days in), should hold, not exit
        res_early = await execute_horizon_sector_exits(
            today_str="2026-08-25",
            price_map={"XLK": 105.0},
        )
        assert res_early["sys-sector-ls-30d"]["status"] == "holding"
        assert mock_exit.call_count == 0

        # 2. On 2026-09-16 (30 days reached), should exit
        mock_exit.return_value = {"status": "success"}
        res_mature = await execute_horizon_sector_exits(
            today_str="2026-09-16",
            price_map={"XLK": 105.0},
        )
        assert res_mature["sys-sector-ls-30d"]["status"] == "success"
        assert mock_exit.call_count >= 1
