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
    mock_db.rpc.return_value.execute.side_effect = RuntimeError("DB Insert Error")

    with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
        # The trade should fail and return None
        trade_id = await p.execute_trade("AAPL", 10, 150.0, "BUY", skip_alpaca_mirror=True)

    assert trade_id is None
    assert p.cash_balance == 10000.00
    assert p.positions == {}
    mock_db.table.assert_not_called()

    print("\n[PASS] Atomic trade Settlement: Portfolio cash not deducted on ledger failure.")


if __name__ == "__main__":
    asyncio.run(test_atomic_trade_failure_reversal())
