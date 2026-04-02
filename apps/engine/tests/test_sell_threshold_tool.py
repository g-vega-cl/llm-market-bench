"""Tests for the sell_if_below_10_percent_threshold tool."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from core.llm import tools


@pytest.fixture
def mock_supabase_and_market_data():
    """Setup mock Supabase client and MarketDataManager."""
    with patch("core.llm.tools.get_supabase_client") as mock_get_client, \
         patch("core.llm.tools.MarketDataManager") as MockMDM:
        
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        mock_mdm = MockMDM.return_value
        mock_mdm.get_quote = AsyncMock()
        
        yield {
            "client": mock_client,
            "mdm": mock_mdm
        }


def setup_position_mock(client, quantity, avg_cost, portfolio_id):
    """Helper to setup position query mock."""
    position_data = [{"quantity": quantity, "average_cost_basis": avg_cost, "portfolio_id": portfolio_id}]
    client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = position_data
    return position_data


def setup_portfolio_mock(client, total_equity):
    """Helper to setup portfolio equity query mock."""
    portfolio_data = [{"total_equity": total_equity}]
    # Need to chain the calls differently for the second query
    client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = portfolio_data
    return portfolio_data


@pytest.mark.asyncio
async def test_sell_if_below_10_percent_threshold_below_limit(mock_supabase_and_market_data):
    """Verify tool returns SELL recommendation when position is below 10% threshold."""
    mocks = mock_supabase_and_market_data
    client = mocks["client"]
    
    # Setup mocks with side_effect for sequential calls
    position_data = [{"quantity": 5, "average_cost_basis": 100.0, "portfolio_id": "port-123"}]
    portfolio_data = [{"total_equity": 10000.0}]
    
    # Configure table().select() to return different results based on context
    mock_table = client.table.return_value
    mock_select = mock_table.select.return_value
    
    # First call (position): .eq("ticker", ticker).eq("portfolio_id", owner_id)
    # Second call (portfolio): .eq("id", portfolio_id)
    mock_eq_ticker = mock_select.eq.return_value
    mock_eq_portfolio = MagicMock()
    mock_eq_ticker.eq.return_value.execute.return_value.data = position_data
    mock_eq_portfolio.execute.return_value.data = portfolio_data
    mock_eq_ticker.eq.return_value = mock_eq_portfolio
    
    # Mock market price: $100
    quote = MagicMock()
    quote.exists = True
    quote.price = 100.0
    mocks["mdm"].get_quote.return_value = quote
    
    result = await tools.execute_sell_if_below_10_percent_threshold_tool("AAPL", "test-agent")
    
    assert "BELOW THRESHOLD" in result
    assert "SELL ALL 5 shares" in result
    assert "Position Value: $500.00" in result
    assert "10% Threshold: $1,000.00" in result


@pytest.mark.asyncio
async def test_sell_if_below_10_percent_threshold_above_limit(mock_supabase_and_market_data):
    """Verify tool returns no action when position is above 10% threshold."""
    mocks = mock_supabase_and_market_data
    client = mocks["client"]
    
    # Mock position: 100 shares @ $150 = $15,000 value
    position_data = [{"quantity": 100, "average_cost_basis": 150.0, "portfolio_id": "port-123"}]
    portfolio_data = [{"total_equity": 10000.0}]
    
    mock_table = client.table.return_value
    mock_select = mock_table.select.return_value
    mock_eq_ticker = mock_select.eq.return_value
    mock_eq_portfolio = MagicMock()
    mock_eq_ticker.eq.return_value.execute.return_value.data = position_data
    mock_eq_portfolio.execute.return_value.data = portfolio_data
    mock_eq_ticker.eq.return_value = mock_eq_portfolio
    
    # Mock market price: $150
    quote = MagicMock()
    quote.exists = True
    quote.price = 150.0
    mocks["mdm"].get_quote.return_value = quote
    
    result = await tools.execute_sell_if_below_10_percent_threshold_tool("AAPL", "test-agent")
    
    assert "ABOVE THRESHOLD" in result
    assert "No action required" in result
    assert "Position Value: $15,000.00" in result


@pytest.mark.asyncio
async def test_sell_if_below_10_percent_threshold_no_position(mock_supabase_and_market_data):
    """Verify tool handles case where position doesn't exist."""
    mocks = mock_supabase_and_market_data
    client = mocks["client"]
    
    # Mock no position
    mock_table = client.table.return_value
    mock_select = mock_table.select.return_value
    mock_eq_ticker = mock_select.eq.return_value
    mock_eq_portfolio = MagicMock()
    mock_eq_ticker.eq.return_value.execute.return_value.data = []
    mock_eq_portfolio.execute.return_value.data = [{"total_equity": 10000.0}]
    mock_eq_ticker.eq.return_value = mock_eq_portfolio
    
    result = await tools.execute_sell_if_below_10_percent_threshold_tool("AAPL", "test-agent")
    
    assert "do not currently own" in result


@pytest.mark.asyncio
async def test_sell_if_below_10_percent_threshold_zero_quantity(mock_supabase_and_market_data):
    """Verify tool handles zero quantity position."""
    mocks = mock_supabase_and_market_data
    client = mocks["client"]
    
    # Mock zero quantity
    position_data = [{"quantity": 0, "average_cost_basis": 100.0, "portfolio_id": "port-123"}]
    
    mock_table = client.table.return_value
    mock_select = mock_table.select.return_value
    mock_eq_ticker = mock_select.eq.return_value
    mock_eq_portfolio = MagicMock()
    mock_eq_ticker.eq.return_value.execute.return_value.data = position_data
    mock_eq_portfolio.execute.return_value.data = [{"total_equity": 10000.0}]
    mock_eq_ticker.eq.return_value = mock_eq_portfolio
    
    result = await tools.execute_sell_if_below_10_percent_threshold_tool("AAPL", "test-agent")
    
    assert "own 0 shares" in result


@pytest.mark.asyncio
async def test_sell_if_below_10_percent_threshold_market_data_error(mock_supabase_and_market_data):
    """Verify tool handles market data fetch error."""
    mocks = mock_supabase_and_market_data
    client = mocks["client"]
    
    # Mock position exists
    position_data = [{"quantity": 5, "average_cost_basis": 100.0, "portfolio_id": "port-123"}]
    
    mock_table = client.table.return_value
    mock_select = mock_table.select.return_value
    mock_eq_ticker = mock_select.eq.return_value
    mock_eq_portfolio = MagicMock()
    mock_eq_ticker.eq.return_value.execute.return_value.data = position_data
    mock_eq_portfolio.execute.return_value.data = [{"total_equity": 10000.0}]
    mock_eq_ticker.eq.return_value = mock_eq_portfolio
    
    # Mock market data error
    mocks["mdm"].get_quote.return_value = None
    
    result = await tools.execute_sell_if_below_10_percent_threshold_tool("AAPL", "test-agent")
    
    assert "Error" in result
    assert "Could not fetch current price" in result


@pytest.mark.asyncio
async def test_sell_if_below_10_percent_threshold_portfolio_error(mock_supabase_and_market_data):
    """Verify tool handles portfolio equity fetch error."""
    mocks = mock_supabase_and_market_data
    client = mocks["client"]
    
    # Mock position exists
    position_data = [{"quantity": 5, "average_cost_basis": 100.0, "portfolio_id": "port-123"}]
    
    mock_table = client.table.return_value
    mock_select = mock_table.select.return_value
    mock_eq_ticker = mock_select.eq.return_value
    mock_eq_portfolio = MagicMock()
    mock_eq_ticker.eq.return_value.execute.return_value.data = position_data
    mock_eq_portfolio.execute.return_value.data = []  # Empty = error
    mock_eq_ticker.eq.return_value = mock_eq_portfolio
    
    # Mock market price
    quote = MagicMock()
    quote.exists = True
    quote.price = 100.0
    mocks["mdm"].get_quote.return_value = quote
    
    result = await tools.execute_sell_if_below_10_percent_threshold_tool("AAPL", "test-agent")
    
    assert "Error" in result
    assert "Could not fetch portfolio equity" in result


@pytest.mark.asyncio
async def test_sell_if_below_10_percent_threshold_exact_threshold(mock_supabase_and_market_data):
    """Verify tool behavior when position is exactly at 10% threshold."""
    mocks = mock_supabase_and_market_data
    client = mocks["client"]
    
    # Mock position: 10 shares @ $100 = $1,000 value (exactly 10% of $10k)
    position_data = [{"quantity": 10, "average_cost_basis": 100.0, "portfolio_id": "port-123"}]
    portfolio_data = [{"total_equity": 10000.0}]
    
    mock_table = client.table.return_value
    mock_select = mock_table.select.return_value
    mock_eq_ticker = mock_select.eq.return_value
    mock_eq_portfolio = MagicMock()
    mock_eq_ticker.eq.return_value.execute.return_value.data = position_data
    mock_eq_portfolio.execute.return_value.data = portfolio_data
    mock_eq_ticker.eq.return_value = mock_eq_portfolio
    
    # Mock market price: $100
    quote = MagicMock()
    quote.exists = True
    quote.price = 100.0
    mocks["mdm"].get_quote.return_value = quote
    
    result = await tools.execute_sell_if_below_10_percent_threshold_tool("AAPL", "test-agent")
    
    # At exactly 10%, should be considered ABOVE threshold (not below)
    assert "ABOVE THRESHOLD" in result
    assert "No action required" in result
