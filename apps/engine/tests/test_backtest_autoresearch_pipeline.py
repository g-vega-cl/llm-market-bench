import sqlite3
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from tasks.backtest_autoresearch import DB_PATH, MockSimulatedSupabaseClient, SQLiteTable, init_backtest_db


@pytest.mark.asyncio
async def test_temporal_sandbox_query_interception():
    """Verify that simulated client select queries are intercepted and filtered by current t_sim."""
    t_sim = datetime(2026, 4, 27, 11, 0, 0, tzinfo=UTC)
    
    mock_postgrest_builder = MagicMock()
    mock_postgrest_builder.lte.return_value = mock_postgrest_builder
    mock_postgrest_builder.execute = MagicMock(return_value=MagicMock(data=[]))
    
    mock_real_table = MagicMock()
    mock_real_table.select.return_value = mock_postgrest_builder
    
    mock_real_client = MagicMock()
    mock_real_client.table.return_value = mock_real_table
    
    simulated_client = MockSimulatedSupabaseClient(mock_real_client, t_sim)
    
    # Query memories
    simulated_client.table("memories").select("*").execute()
    
    # Verify temporal filter lte("created_at", t_sim) was applied
    mock_postgrest_builder.lte.assert_called_once_with("created_at", t_sim.isoformat())


def test_sqlite_table_insert_and_select():
    """Verify SQLiteTable mock operations write and read from local backtest db."""
    init_backtest_db()
    
    # Clear portfolios for test isolation
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM portfolios")
    conn.commit()
    conn.close()

    table = SQLiteTable("portfolios")
    
    # Insert new test portfolio
    portfolio_data = {
        "id": "test-uuid-123",
        "owner_id": "test-model-owner",
        "cash_balance": 10000.0,
        "sma": 10000.0,
        "total_equity": 10000.0,
        "buying_power": 10000.0,
        "excess_liquidity": 10000.0,
        "maintenance_margin": 0.0,
        "realized": 10000.0,
        "last_updated_at": "2026-07-23T12:00:00"
    }
    table.insert(portfolio_data)
    
    # Read back using eq filter
    res = table.select("*").eq("owner_id", "test-model-owner").execute()
    assert len(res.data) == 1
    assert res.data[0]["id"] == "test-uuid-123"
    assert res.data[0]["cash_balance"] == 10000.0
    
    # Test update
    table.update({"cash_balance": 9500.0}).eq("id", "test-uuid-123").execute()
    
    res2 = table.select("*").eq("owner_id", "test-model-owner").execute()
    assert res2.data[0]["cash_balance"] == 9500.0


@pytest.mark.asyncio
async def test_portfolio_performance_sandbox_redirection():
    """Verify that portfolio_performance is sandboxed and redirected to SQLiteTable."""
    mock_real_client = MagicMock()
    simulated_client = MockSimulatedSupabaseClient(mock_real_client, datetime.now(UTC))
    
    # Get table object
    table_obj = simulated_client.table("portfolio_performance")
    assert isinstance(table_obj, SQLiteTable)
    assert table_obj.table_name == "portfolio_performance"


@pytest.mark.asyncio
async def test_evaluate_backtest_week_return_calculation():
    """Verify that evaluate_backtest_week calculates returns using total_equity instead of cash_balance."""
    from tasks.backtest_autoresearch import evaluate_backtest_week
    init_backtest_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM portfolios")
    
    # Insert two test portfolios with negative cash but positive equity (margin loan case)
    cursor.execute(
        "INSERT INTO portfolios (id, owner_id, cash_balance, total_equity, sma, buying_power, excess_liquidity, maintenance_margin, realized, last_updated_at) "
        "VALUES ('id-1', 'model-1', -5000.0, 9500.0, 9500.0, 9500.0, 9500.0, 0.0, 9500.0, datetime('now'))"
    )
    cursor.execute(
        "INSERT INTO portfolios (id, owner_id, cash_balance, total_equity, sma, buying_power, excess_liquidity, maintenance_margin, realized, last_updated_at) "
        "VALUES ('id-2', 'model-2', -3000.0, 10500.0, 10500.0, 10500.0, 10500.0, 0.0, 10500.0, datetime('now'))"
    )
    conn.commit()
    conn.close()
    
    report, metrics = await evaluate_backtest_week(datetime.now(UTC), datetime.now(UTC))
    
    # model-1 equity = 9500 (-5.0% return)
    # model-2 equity = 10500 (+5.0% return)
    # Average model return should be 0.0%
    assert metrics["portfolio_return"] == 0.0

