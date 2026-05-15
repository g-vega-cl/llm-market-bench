import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from execution.market_data import MarketDataManager
from execution.reg_t_validation import calculate_reg_t_metrics


@pytest.mark.asyncio
async def test_market_data_ancient_price_rejection():
    """
    REPRODUCTION TEST: Ancient prices in history should not be returned as valid quotes.
    """
    mdm = MarketDataManager()
    ticker = "CSCO"

    # Mock supabase client to return an ancient price (e.g., from 2024)
    mock_supabase = MagicMock()
    mdm.client = mock_supabase

    ancient_date = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=365)).isoformat()
    mock_supabase.table().select().eq().order().limit().execute.return_value = MagicMock(
        data=[{"ticker": ticker, "price": 81.85, "market_cap": 300e9, "fetched_at": ancient_date}]
    )

    # Mock provider fetch to fail so it falls back to last known
    mdm._fetch_with_backoff = AsyncMock(return_value=None)
    mdm._get_from_cache = MagicMock(return_value=None)

    # EXECUTE: Fetch quote
    quote = await mdm.get_quote(ticker)

    # ASSERT: Should NOT use the ancient price
    # Currently, it WILL return the ancient price (the bug)
    assert quote is None or quote.price != 81.85, (
        "Should not return ancient price from history as a valid current quote"
    )


@pytest.mark.asyncio
async def test_margin_inflation_from_negative_positions():
    """
    REPRODUCTION TEST: Negative position values (e.g. from corruption) should not inflate buying power.
    """
    # GIVEN: A portfolio with 10k cash but a large corrupted negative position
    # If the bug exists:
    # stock_value = -5000
    # total_equity = 10000 - 5000 = 5000
    # initial_margin_req = -5000 * 0.57 = -2850
    # available_funds = 5000 - (-2850) = 7850
    # buying_power = 7850 * 4 = 31400
    # BUT: 4x Total Equity (5000) is only 20000.

    cash = 10000.0
    positions = {"CSCO": {"quantity": -50, "average_cost_basis": 100.0}}
    current_prices = {"CSCO": 100.0}

    # EXECUTE: Calculate metrics
    metrics = calculate_reg_t_metrics(
        cash_balance=cash, positions=positions, current_prices=current_prices, previous_sma=10000.0
    )

    theoretical_max_bp = max(0.0, metrics.total_equity * 4.0)

    assert metrics.buying_power <= theoretical_max_bp, (
        f"Buying power ({metrics.buying_power:,.2f}) inflated beyond 4x Total Equity "
        f"({theoretical_max_bp:,.2f}) due to negative position value."
    )
