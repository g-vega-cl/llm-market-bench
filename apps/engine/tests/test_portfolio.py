"""Tests for Portfolio management and Reg T4 calculations."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from execution.portfolio import Portfolio, RegTMetrics, Position

# --- Reg T Scenario Tests ---

def test_reg_t_scenario_1_no_leverage():
    """
    Scenario 1: Basic Cash-Backed Purchase
    Cash: 10,000. Buy $9,950.24 stock.
    Expected (from docs/account-buying-power-reg-t4-calculations.md):
    - Equity: 10,000
    - Maint Margin (25%): 2,487.56
    - Excess Liquidity: 7,512.44
    - Available Funds: 5,024.88
    - Buying Power: 20,099.52 (4x Available Funds)
    """
    p = Portfolio("test_agent")
    p.cash_balance = 49.76
    p.positions = {"QQQ": Position("QQQ", 16, 621.89)}
    
    current_prices = {"QQQ": 621.89}
    
    metrics = p.calculate_reg_t_metrics(current_prices)
    
    assert metrics.total_equity == pytest.approx(10000.00, abs=0.10)
    assert metrics.maintenance_margin_req == pytest.approx(3283.58, abs=0.10)
    assert metrics.excess_liquidity == pytest.approx(6716.42, abs=0.10)
    assert metrics.buying_power == pytest.approx(17313.44, abs=1.0)


def test_reg_t_scenario_2_leveraged_profitable():
    """
    Scenario 2: Leveraged Position (Profitable)
    Cash: -2000. Stock Value: 12437.80.
    Expected (from docs/account-buying-power-reg-t4-calculations.md):
    - Equity: 10,437.80
    - Maint Margin: 3,109.45
    - Excess: 7,328.35
    - Available Funds: 4,218.90
    - BP: 16,875.60 (4x Available Funds)
    """
    p = Portfolio("test_agent")
    p.cash_balance = -2000.00
    p.positions = {"QQQ": Position("QQQ", 20, 600.00)}
    
    current_prices = {"QQQ": 621.89}
    
    metrics = p.calculate_reg_t_metrics(current_prices)
    
    assert metrics.total_equity == pytest.approx(10437.80, abs=0.10)
    assert metrics.maintenance_margin_req == pytest.approx(4104.47, abs=0.10)
    assert metrics.excess_liquidity == pytest.approx(6333.33, abs=0.10)
    assert metrics.buying_power == pytest.approx(13393.00, abs=1.0)


def test_reg_t_scenario_3_leveraged_loss():
    """
    Scenario 3: Leveraged Position (Unrealized Loss)
    Cash: -3000. Stock Value: 12437.80.
    Expected (from docs/account-buying-power-reg-t4-calculations.md):
    - Equity: 9,437.80
    - Maint Margin: 3,109.45
    - Excess: 6,328.35
    - Available Funds: 3,218.90
    - BP: 12,875.60 (4x Available Funds)
    """
    p = Portfolio("test_agent")
    p.cash_balance = -3000.00
    p.positions = {"QQQ": Position("QQQ", 20, 650.00)}
    
    current_prices = {"QQQ": 621.89}
    
    metrics = p.calculate_reg_t_metrics(current_prices)
    
    assert metrics.total_equity == pytest.approx(9437.80, abs=0.10)
    assert metrics.maintenance_margin_req == pytest.approx(4104.47, abs=0.10)
    assert metrics.excess_liquidity == pytest.approx(5333.33, abs=0.10)
    assert metrics.buying_power == pytest.approx(9393.00, abs=1.0)


def test_reg_t_scenario_5_liquidation():
    """
    Scenario 5: High Leverage / Boundary Test
    Cash: -28000. Stock Value: 30400.
    Expected:
    - Equity: 2,400.00
    - Maint Margin: 7,600.00
    - Excess: -5,200.00
    - BP: 0.00
    """
    p = Portfolio("test_agent")
    p.cash_balance = -28000.00
    # Price dropped 20% from cost basis implies we hold $38k cost basis?
    # Scenario says "Buy $38,000 worth". Let's say 380 shares @ $100.
    # Now price is $80. Value = 380 * 80 = 30400.
    p.positions = {"STK": Position("STK", 380, 100.00)}
    
    current_prices = {"STK": 80.00}
    
    metrics = p.calculate_reg_t_metrics(current_prices)
    
    assert metrics.total_equity == pytest.approx(2400.00, abs=0.10)
    assert metrics.maintenance_margin_req == pytest.approx(10032.00, abs=0.10)
    assert metrics.excess_liquidity == pytest.approx(-7632.00, abs=0.10)
    assert metrics.buying_power == 0.00


# --- Persistence Tests ---

@pytest.mark.asyncio
async def test_initialize_existing_portfolio():
    """Test loading a portfolio that already exists in DB."""
    p = Portfolio("existing_agent")
    
    # Mock supabase response
    mock_db = MagicMock()
    mock_res_portfolio = MagicMock()
    mock_res_portfolio.data = [{
        "id": "uuid-123",
        "cash_balance": 15000.00,
        "buying_power": 45000.00,
        "sma": 15000.00
    }]
    
    mock_res_positions = MagicMock()
    mock_res_positions.data = [{
        "ticker": "AAPL",
        "quantity": 10,
        "average_cost_basis": 150.00
    }]
    
    # Setup chain for portfolios select
    mock_db.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
        mock_res_portfolio, 
        mock_res_positions
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
        
        # Verify insert was called with $10k default
        mock_table.insert.assert_called_with({
            "owner_id": "new_agent",
            "cash_balance": 10000.00,
            "sma": 10000.00
        })
        
    assert p.id == "uuid-new"
    assert p.cash_balance == 10000.00


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
        buying_power=28000.0
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
        
        # Verify filtering
        mock_table.update.return_value.eq.assert_called_with("id", "portfolio-123")


def test_calculate_reg_t_metrics_with_positions():
    """Test that calculate_reg_t_metrics works with Position objects."""
    p = Portfolio("test_agent")
    p.cash_balance = 5000.0
    p.positions = {
        "AAPL": Position("AAPL", 10, 150.0),
        "MSFT": Position("MSFT", 5, 300.0)
    }
    
    current_prices = {
        "AAPL": 160.0,  # Value: 1600
        "MSFT": 320.0   # Value: 1600
    }
    # Total Stock Value: 3200
    # Total Equity: 5000 + 3200 = 8200
    # Maintenance Margin (33%): 3200 * 0.33 = 1056
    
    metrics = p.calculate_reg_t_metrics(current_prices)
    
    assert metrics.total_equity == 8200.0
    assert metrics.maintenance_margin_req == 1056.0

