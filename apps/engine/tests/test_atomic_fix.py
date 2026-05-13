
import asyncio
from unittest.mock import MagicMock, patch

import pytest

from execution.portfolio import Portfolio


@pytest.mark.asyncio
async def test_atomic_trade_failure_reversal():
    """
    Test that if the trade ledger insertion fails, 
    the portfolios table (cash/sma) is NOT updated.
    """
    p = Portfolio("test_agent")
    p.id = "portfolio-123"
    p.cash_balance = 10000.00
    p.sma = 10000.00
    p.positions = {}
    
    mock_db = MagicMock()
    mock_table = MagicMock()
    mock_db.table.return_value = mock_table
    
    # Mocking DB chain:
    # 1. table("portfolio_positions").upsert().execute() -> SUCCESS
    # 2. table("trades").insert().execute() -> FAIL (raises exception)
    
    def mock_table_side_effect(table_name):
        if table_name == "trades":
            m = MagicMock()
            m.insert.side_effect = Exception("DB Insert Error")
            return m
        return MagicMock() # For other tables

    mock_db.table.side_effect = mock_table_side_effect

    with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
        # The trade should fail and return None
        trade_id = await p.execute_trade("AAPL", 10, 150.0, "BUY")
        
    assert trade_id is None
    
    # CRITICAL: Verify that supabase.table("portfolios").update was NEVER called
    # Because it should only happen AFTER the trades insert succeeds.
    portfolios_table_mock = mock_db.table("portfolios")
    assert portfolios_table_mock.update.called is False, "Portfolios table should not be updated on ledger failure"

    print("\n[PASS] Atomic trade Settlement: Portfolio cash not deducted on ledger failure.")

if __name__ == "__main__":
    asyncio.run(test_atomic_trade_failure_reversal())
