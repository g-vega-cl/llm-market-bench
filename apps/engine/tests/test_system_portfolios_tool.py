"""Unit tests for get_system_portfolios tool and its integration with trading agents and autoresearch."""

from unittest.mock import MagicMock, patch

import pytest

from core.llm.tools import (
    CANONICAL_TOOLS_REGISTRY,
    GET_SYSTEM_PORTFOLIOS_TOOL,
    execute_get_system_portfolios_tool,
)


def test_get_system_portfolios_tool_registration():
    """Verify that get_system_portfolios is properly declared and in CANONICAL_TOOLS_REGISTRY."""
    assert "get_system_portfolios" in CANONICAL_TOOLS_REGISTRY
    assert CANONICAL_TOOLS_REGISTRY["get_system_portfolios"] == GET_SYSTEM_PORTFOLIOS_TOOL
    assert GET_SYSTEM_PORTFOLIOS_TOOL["function"]["name"] == "get_system_portfolios"
    params = GET_SYSTEM_PORTFOLIOS_TOOL["function"]["parameters"]["properties"]
    assert "category" in params
    assert "include_positions" in params
    assert "lookback_days" in params


@pytest.mark.asyncio
async def test_execute_get_system_portfolios_tool_all():
    """Verify execute_get_system_portfolios_tool formats all system portfolios with holdings and performance."""
    mock_portfolios = [
        {
            "id": "port-1",
            "owner_id": "sys-sector-mean-reversion",
            "cash_balance": 5000.0,
            "total_equity": 10500.0,
            "buying_power": 10000.0,
        },
        {
            "id": "port-2",
            "owner_id": "sys-sector-naive-momentum",
            "cash_balance": 1000.0,
            "total_equity": 11200.0,
            "buying_power": 2000.0,
        },
    ]

    mock_positions = [
        {
            "portfolio_id": "port-1",
            "owner_id": "sys-sector-mean-reversion",
            "ticker": "XLRE",
            "quantity": 50,
            "average_cost_basis": 40.0,
            "current_price": 42.0,
            "unrealized_pnl_usd": 100.0,
            "unrealized_pnl_pct": 5.0,
        },
        {
            "portfolio_id": "port-1",
            "owner_id": "sys-sector-mean-reversion",
            "ticker": "XLU",
            "quantity": 60,
            "average_cost_basis": 50.0,
            "current_price": 49.0,
            "unrealized_pnl_usd": -60.0,
            "unrealized_pnl_pct": -2.0,
        },
        {
            "portfolio_id": "port-2",
            "owner_id": "sys-sector-naive-momentum",
            "ticker": "XLK",
            "quantity": 40,
            "average_cost_basis": 200.0,
            "current_price": 210.0,
            "unrealized_pnl_usd": 400.0,
            "unrealized_pnl_pct": 5.0,
        },
    ]

    mock_performance = [
        {"portfolio_id": "port-1", "date": "2026-09-27", "total_equity": 10500.0},
        {"portfolio_id": "port-1", "date": "2026-09-20", "total_equity": 10200.0},
        {"portfolio_id": "port-2", "date": "2026-09-27", "total_equity": 11200.0},
        {"portfolio_id": "port-2", "date": "2026-09-20", "total_equity": 10800.0},
    ]

    mock_sb = MagicMock()
    mock_p_query = MagicMock()
    mock_p_query.select.return_value.like.return_value.execute.return_value = MagicMock(data=mock_portfolios)
    mock_pos_query = MagicMock()
    mock_pos_query.select.return_value.execute.return_value = MagicMock(data=mock_positions)
    mock_perf_query = MagicMock()
    mock_perf_query.select.return_value.gte.return_value.order.return_value.execute.return_value = MagicMock(
        data=mock_performance
    )

    table_map = {
        "portfolios": mock_p_query,
        "position_pnl": mock_pos_query,
        "portfolio_performance": mock_perf_query,
    }
    mock_sb.table.side_effect = lambda name: table_map.get(name, MagicMock())

    with patch("analytics.system_portfolios_report.get_supabase_client", return_value=mock_sb):
        res = await execute_get_system_portfolios_tool(category="all", include_positions=True)

    assert "SYSTEM PORTFOLIOS & MECHANICAL BENCHMARKS" in res
    assert "sys-sector-mean-reversion" in res
    assert "XLRE: 50 shares" in res
    assert "sys-sector-naive-momentum" in res
    assert "XLK: 40 shares" in res
    assert "+2.94%" in res or "Total Equity: $10,500.00" in res


@pytest.mark.asyncio
async def test_execute_get_system_portfolios_tool_mean_reversion_filter():
    """Verify category='mean_reversion' only selects mean-reversion portfolios."""
    mock_portfolios = [
        {
            "id": "port-1",
            "owner_id": "sys-sector-mean-reversion",
            "cash_balance": 5000.0,
            "total_equity": 10500.0,
            "buying_power": 10000.0,
        },
        {
            "id": "port-2",
            "owner_id": "sys-sector-naive-momentum",
            "cash_balance": 1000.0,
            "total_equity": 11200.0,
            "buying_power": 2000.0,
        },
    ]

    mock_sb = MagicMock()
    mock_p_query = MagicMock()
    mock_p_query.select.return_value.like.return_value.execute.return_value = MagicMock(data=mock_portfolios)
    mock_pos_query = MagicMock()
    mock_pos_query.select.return_value.execute.return_value = MagicMock(data=[])
    mock_perf_query = MagicMock()
    mock_perf_query.select.return_value.gte.return_value.order.return_value.execute.return_value = MagicMock(data=[])

    table_map = {
        "portfolios": mock_p_query,
        "position_pnl": mock_pos_query,
        "portfolio_performance": mock_perf_query,
    }
    mock_sb.table.side_effect = lambda name: table_map.get(name, MagicMock())

    with patch("analytics.system_portfolios_report.get_supabase_client", return_value=mock_sb):
        res = await execute_get_system_portfolios_tool(category="mean_reversion", include_positions=False)

    assert "sys-sector-mean-reversion" in res
    assert "sys-sector-naive-momentum" not in res
    assert "Holdings: omitted" in res


@pytest.mark.asyncio
async def test_execute_get_system_portfolios_tool_empty():
    """Verify execute_get_system_portfolios_tool gracefully handles empty DB results."""
    mock_sb = MagicMock()
    mock_sb.table.return_value.select.return_value.like.return_value.execute.return_value = MagicMock(data=[])

    with patch("analytics.system_portfolios_report.get_supabase_client", return_value=mock_sb):
        res = await execute_get_system_portfolios_tool()

    assert "No system portfolios found" in res


@pytest.mark.asyncio
async def test_base_handler_dispatches_get_system_portfolios():
    """Verify that base handler routes get_system_portfolios correctly."""
    from core.llm.handlers.base import execute_tool

    with patch("core.llm.tools.execute_get_system_portfolios_tool", return_value="Mock system portfolios"):
        res = await execute_tool(
            "get_system_portfolios",
            {"category": "momentum", "include_positions": True},
            model_name="test_model",
        )
    assert res == "Mock system portfolios"


@pytest.mark.asyncio
async def test_autoresearch_query_system_portfolios_audit():
    """Verify autoresearch tools query_system_portfolios_audit helper."""
    from autoresearch.tools import query_system_portfolios_audit

    with patch("core.llm.tools.execute_get_system_portfolios_tool", return_value="Mock audit portfolios"):
        res = await query_system_portfolios_audit(category="all")
    assert "Mock audit portfolios" in res


@pytest.mark.asyncio
async def test_execute_get_system_portfolios_tool_with_open_shorts():
    """Verify execute_get_system_portfolios_tool surfaces open shorts with [SHORT] tag."""
    mock_portfolios = [
        {
            "id": "port-ls",
            "owner_id": "sys-sector-ls-30d",
            "cash_balance": 5000.0,
            "total_equity": 10000.0,
            "buying_power": 20000.0,
        },
    ]

    mock_positions = [
        {
            "portfolio_id": "port-ls",
            "owner_id": "sys-sector-ls-30d",
            "ticker": "XLK",
            "quantity": 10,
            "average_cost_basis": 150.0,
            "current_price": 160.0,
            "unrealized_pnl_usd": 100.0,
            "unrealized_pnl_pct": 6.67,
        },
    ]

    mock_trades = [
        {
            "portfolio_id": "port-ls",
            "ticker": "XLE",
            "quantity": 25,
            "price": 80.0,
            "executed_at": "2026-10-01T13:30:00Z",
            "signal": "SHORT",
            "realized_pnl": None,
        },
    ]

    mock_cache = [
        {"ticker": "XLE", "price": 76.0},
    ]

    mock_sb = MagicMock()
    mock_p_query = MagicMock()
    mock_p_query.select.return_value.like.return_value.execute.return_value = MagicMock(data=mock_portfolios)
    mock_pos_query = MagicMock()
    mock_pos_query.select.return_value.execute.return_value = MagicMock(data=mock_positions)
    mock_perf_query = MagicMock()
    mock_perf_query.select.return_value.gte.return_value.order.return_value.execute.return_value = MagicMock(data=[])

    mock_trades_query = MagicMock()
    mock_trades_query.select.return_value.eq.return_value.is_.return_value.execute.return_value = MagicMock(
        data=mock_trades
    )

    mock_cache_query = MagicMock()
    mock_cache_query.select.return_value.in_.return_value.execute.return_value = MagicMock(data=mock_cache)

    table_map = {
        "portfolios": mock_p_query,
        "position_pnl": mock_pos_query,
        "portfolio_performance": mock_perf_query,
        "trades": mock_trades_query,
        "market_data_cache": mock_cache_query,
    }
    mock_sb.table.side_effect = lambda name: table_map.get(name, MagicMock())

    with patch("analytics.system_portfolios_report.get_supabase_client", return_value=mock_sb):
        res = await execute_get_system_portfolios_tool(category="sector_ls", include_positions=True)

    assert "sys-sector-ls-30d" in res
    assert "XLK: 10 shares" in res
    assert "XLE [SHORT]: 25 shares" in res
    assert "Short Entry: $80.00" in res
    assert "Current Price: $76.00" in res
    # (80 - 76) * 25 = +100 USD
    assert "Unrealized PnL: $+100.00" in res
