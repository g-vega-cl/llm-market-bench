from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from execution.system_portfolios import (
    SYS_SECTOR_MEAN_REV_OWNER_ID,
    SYS_SECTOR_NAIVE_MOM_OWNER_ID,
    SYS_SECTOR_UNCORR_7D_OWNER_ID,
    SYS_SECTOR_UNCORR_20D_OWNER_ID,
    execute_all_system_mechanical_sector_rebalances,
    execute_mechanical_sector_rebalance,
    resolve_mechanical_sectors,
)


def test_resolve_mechanical_sectors():
    """Test selection of sectors for all 4 mechanical strategies."""
    universe = ["XLK", "SMH", "XLE", "XLV", "XLU"]

    # Sample rows from correlation_data
    # XLK and SMH: highly correlated (0.9), high 30d returns
    # XLE: moderate 30d, but uncorrelated with XLV (-0.2)
    # XLV: moderate 30d
    # XLU: worst 7d return (-5.0), SMH second worst (-3.0)
    correlation_rows = [
        {
            "ticker_a": "XLK",
            "ticker_b": "SMH",
            "pearson_corr": 0.92,
            "returns_a_7d": 1.0,
            "returns_b_7d": -3.0,
            "returns_a_30d": 12.0,
            "returns_b_30d": 10.0,
        },
        {
            "ticker_a": "XLK",
            "ticker_b": "XLE",
            "pearson_corr": 0.15,
            "returns_a_7d": 1.0,
            "returns_b_7d": 4.0,
            "returns_a_30d": 12.0,
            "returns_b_30d": 5.0,
        },
        {
            "ticker_a": "XLK",
            "ticker_b": "XLV",
            "pearson_corr": 0.35,
            "returns_a_7d": 1.0,
            "returns_b_7d": 2.0,
            "returns_a_30d": 12.0,
            "returns_b_30d": 6.0,
        },
        {
            "ticker_a": "XLK",
            "ticker_b": "XLU",
            "pearson_corr": -0.10,
            "returns_a_7d": 1.0,
            "returns_b_7d": -5.0,
            "returns_a_30d": 12.0,
            "returns_b_30d": 1.0,
        },
        {
            "ticker_a": "SMH",
            "ticker_b": "XLE",
            "pearson_corr": 0.20,
            "returns_a_7d": -3.0,
            "returns_b_7d": 4.0,
            "returns_a_30d": 10.0,
            "returns_b_30d": 5.0,
        },
        {
            "ticker_a": "SMH",
            "ticker_b": "XLV",
            "pearson_corr": 0.40,
            "returns_a_7d": -3.0,
            "returns_b_7d": 2.0,
            "returns_a_30d": 10.0,
            "returns_b_30d": 6.0,
        },
        {
            "ticker_a": "SMH",
            "ticker_b": "XLU",
            "pearson_corr": -0.05,
            "returns_a_7d": -3.0,
            "returns_b_7d": -5.0,
            "returns_a_30d": 10.0,
            "returns_b_30d": 1.0,
        },
        {
            "ticker_a": "XLE",
            "ticker_b": "XLV",
            "pearson_corr": -0.22,
            "returns_a_7d": 4.0,
            "returns_b_7d": 2.0,
            "returns_a_30d": 5.0,
            "returns_b_30d": 6.0,
        },
        {
            "ticker_a": "XLE",
            "ticker_b": "XLU",
            "pearson_corr": 0.05,
            "returns_a_7d": 4.0,
            "returns_b_7d": -5.0,
            "returns_a_30d": 5.0,
            "returns_b_30d": 1.0,
        },
        {
            "ticker_a": "XLV",
            "ticker_b": "XLU",
            "pearson_corr": 0.28,
            "returns_a_7d": 2.0,
            "returns_b_7d": -5.0,
            "returns_a_30d": 6.0,
            "returns_b_30d": 1.0,
        },
    ]

    picks = resolve_mechanical_sectors(correlation_rows, universe)

    # 1. Uncorr 20d/30d: XLK (12.0) and XLE (5.0) have corr 0.15 < 0.3, avg = 8.5
    # (XLK+SMH is corr 0.92 > 0.3; XLK+XLV is corr 0.35 > 0.3)
    assert set(picks[SYS_SECTOR_UNCORR_20D_OWNER_ID]) == {"XLK", "XLE"}

    # 2. Uncorr 7d: XLE (4.0) and XLV (2.0) have corr -0.22 < 0.3, avg = 3.0
    # (XLE+XLK is corr 0.15, avg = 2.5)
    assert set(picks[SYS_SECTOR_UNCORR_7D_OWNER_ID]) == {"XLE", "XLV"}

    # 3. Naive Momentum (any corr): Top 2 by 30d are XLK (12.0) and SMH (10.0)
    assert set(picks[SYS_SECTOR_NAIVE_MOM_OWNER_ID]) == {"XLK", "SMH"}

    # 4. Mean Reversion: Bottom 2 by 7d are XLU (-5.0) and SMH (-3.0)
    assert set(picks[SYS_SECTOR_MEAN_REV_OWNER_ID]) == {"XLU", "SMH"}


@pytest.mark.asyncio
async def test_execute_mechanical_sector_rebalance_skip_before_start():
    """Verify that rebalance skips windows starting before SYS_SECTOR_START_DATE."""
    res = await execute_mechanical_sector_rebalance(
        owner_id=SYS_SECTOR_UNCORR_20D_OWNER_ID,
        sectors=["XLK", "XLE"],
        week_start_date="2026-08-10",
        week_end_date="2026-08-17",
        price_map={"XLK": {"start_price": 100.0, "end_price": 105.0}},
    )
    assert res["status"] == "skipped"


@pytest.mark.asyncio
async def test_execute_mechanical_sector_rebalance_execution():
    """Verify order logging, slippage, and portfolio equity updates for mechanical rebalance."""
    mock_portfolio_id = uuid4()

    mock_client = MagicMock()
    mock_chain = MagicMock()
    mock_chain.insert.return_value = mock_chain
    mock_chain.update.return_value = mock_chain
    mock_chain.upsert.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain
    mock_chain.execute.return_value = MagicMock(data=[{"id": str(mock_portfolio_id)}])
    mock_client.table.return_value = mock_chain

    price_map = {
        "XLK": {"start_price": 100.0, "end_price": 110.0},
        "XLE": {"start_price": 50.0, "end_price": 45.0},
    }

    with (
        patch("execution.system_portfolios.get_supabase_client", return_value=mock_client),
        patch("execution.system_portfolios.get_or_create_system_portfolio") as mock_get_port,
    ):
        mock_port = MagicMock()
        mock_port.id = mock_portfolio_id
        mock_port.cash_balance = 10000.00
        mock_get_port.return_value = mock_port

        res = await execute_mechanical_sector_rebalance(
            owner_id=SYS_SECTOR_UNCORR_20D_OWNER_ID,
            sectors=["XLK", "XLE"],
            week_start_date="2026-08-17",
            week_end_date="2026-08-24",
            price_map=price_map,
            slippage_bps=5.0,  # 0.05%
        )

        assert res["status"] == "success"
        assert len(res["trades"]) == 2
        # XLK: long gained from 100 to 110
        # XLE: long dropped from 50 to 45
        assert res["trades"][0]["ticker"] == "XLK"
        assert res["trades"][0]["pnl"] > 0
        assert res["trades"][1]["ticker"] == "XLE"
        assert res["trades"][1]["pnl"] < 0
        assert "new_equity" in res


@pytest.mark.asyncio
async def test_execute_all_system_mechanical_sector_rebalances():
    """Verify execute_all_system_mechanical_sector_rebalances queries correlation run and executes all 4 portfolios."""
    mock_client = MagicMock()
    mock_chain = MagicMock()

    # Correlation runs return
    run_data = [{"id": "run-uuid-1", "tickers": ["XLK", "SMH", "XLE", "XLV", "XLU"]}]
    corr_rows = [
        {
            "ticker_a": "XLK",
            "ticker_b": "XLE",
            "pearson_corr": 0.1,
            "returns_a_7d": 1.0,
            "returns_b_7d": 2.0,
            "returns_a_30d": 5.0,
            "returns_b_30d": 6.0,
        },
        {
            "ticker_a": "XLK",
            "ticker_b": "SMH",
            "pearson_corr": 0.9,
            "returns_a_7d": 1.0,
            "returns_b_7d": -1.0,
            "returns_a_30d": 5.0,
            "returns_b_30d": 8.0,
        },
    ]

    mock_chain.select.return_value = mock_chain
    mock_chain.lte.return_value = mock_chain
    mock_chain.order.return_value = mock_chain
    mock_chain.limit.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain

    # Mock execute returns depending on table queried
    def mock_table_side_effect(table_name):
        chain = MagicMock()
        chain.select.return_value = chain
        chain.lte.return_value = chain
        chain.order.return_value = chain
        chain.limit.return_value = chain
        chain.eq.return_value = chain
        if table_name == "correlation_runs":
            chain.execute.return_value = MagicMock(data=run_data)
        elif table_name == "correlation_data":
            chain.execute.return_value = MagicMock(data=corr_rows)
        return chain

    mock_client.table.side_effect = mock_table_side_effect

    price_map = {
        "XLK": {"start_price": 100.0, "end_price": 105.0},
        "XLE": {"start_price": 50.0, "end_price": 52.0},
        "SMH": {"start_price": 200.0, "end_price": 210.0},
        "XLV": {"start_price": 130.0, "end_price": 132.0},
        "XLU": {"start_price": 60.0, "end_price": 59.0},
    }

    with (
        patch("execution.system_portfolios.get_supabase_client", return_value=mock_client),
        patch(
            "execution.system_portfolios.execute_mechanical_sector_rebalance", new_callable=AsyncMock
        ) as mock_exec_one,
    ):
        mock_exec_one.return_value = {"status": "success"}

        results = await execute_all_system_mechanical_sector_rebalances(
            week_start_date="2026-08-17",
            week_end_date="2026-08-24",
            price_map=price_map,
        )

        assert len(results) == 4
        assert mock_exec_one.call_count == 4
