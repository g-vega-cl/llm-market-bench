"""Tests for Daily Performance Snapshotting."""

from unittest.mock import MagicMock, patch

import pytest

from execution.portfolio import Portfolio, Position


@pytest.mark.asyncio
async def test_record_performance_snapshot():
    """Test recording a performance snapshot to the DB."""
    p = Portfolio("test_agent")
    p.id = "portfolio-123"
    p.cash_balance = 5000.00
    p.positions = {"AAPL": Position("AAPL", 10, 150.00)}

    current_prices = {"AAPL": 200.00}

    # Expected Equity: 5000 + (10 * 200) = 7000.00

    mock_db = MagicMock()
    mock_table = MagicMock()
    mock_db.table.return_value = mock_table

    # Mock upsert success
    mock_res = MagicMock()
    mock_res.data = [{"id": "snapshot-123"}]
    mock_table.upsert.return_value.execute.return_value = mock_res

    with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
        await p.record_performance_snapshot(current_prices)

        # Verify upsert call
        mock_table.upsert.assert_called_once()
        call_args = mock_table.upsert.call_args[0][0]

        assert call_args["portfolio_id"] == "portfolio-123"
        assert call_args["total_equity"] == pytest.approx(7000.00)
        assert call_args["cash_balance"] == 5000.00
        # Stock Value = 2000. IM (57%) = 1140. Equity = 7000. Avail = 5860. BP = 23440.
        assert call_args["buying_power"] == pytest.approx(23440.00)
        assert call_args["initial_margin_req"] == 1140.00
        assert call_args["maintenance_margin_req"] == 660.00
        assert call_args["available_funds"] == 5860.00
        assert call_args["excess_liquidity"] == 6340.00
        from datetime import date
        today = date.today().isoformat()
        assert call_args["date"] == today


@pytest.mark.asyncio
async def test_record_performance_snapshot_idempotency():
    """Test that upsert is used for idempotency."""
    p = Portfolio("test_agent")
    p.id = "portfolio-123"

    mock_db = MagicMock()
    mock_table = MagicMock()
    mock_db.table.return_value = mock_table

    with patch("execution.portfolio.get_supabase_client", return_value=mock_db):
        await p.record_performance_snapshot({})

        # Upsert should be called once
        assert mock_table.upsert.called


@pytest.mark.asyncio
async def test_stage_snapshots_skips_portfolios_without_positions():
    """Only portfolios that hold positions should get a performance snapshot.

    Empty portfolios (cash-only, never traded) don't change between runs
    and don't need daily snapshots. The pipeline has ~11 portfolios but
    only ~5 are active in any given run.
    """
    from unittest.mock import AsyncMock

    from main import _stage_snapshots_and_pca

    # Portfolio 1: has positions → SHOULD be snapshotted
    p1 = Portfolio("active_trader")
    p1.id = "portfolio-1"
    p1.positions = {"AAPL": Position("AAPL", 10, 150.0)}
    p1.initialize = AsyncMock()
    p1.record_performance_snapshot = AsyncMock()
    p1.save_metrics = AsyncMock()

    # Portfolio 2: no positions → should be SKIPPED
    p2 = Portfolio("idle_cash")
    p2.id = "portfolio-2"
    p2.positions = {}
    p2.initialize = AsyncMock()
    p2.record_performance_snapshot = AsyncMock()
    p2.save_metrics = AsyncMock()

    mock_db = MagicMock()
    # DB query returns both portfolio owner_ids
    mock_db.table.return_value.select.return_value.execute.return_value = MagicMock(
        data=[{"owner_id": "active_trader"}, {"owner_id": "idle_cash"}]
    )

    with patch("main.get_supabase_client", return_value=mock_db), \
         patch("main.Portfolio", side_effect=[p1, p2]), \
         patch("execution.market_data.MarketDataManager") as MockMDM, \
         patch("main.update_pca_coordinates"):

        mock_mdm = MockMDM.return_value
        mock_mdm.get_quotes = AsyncMock(return_value={"AAPL": MagicMock(price=150.0)})

        await _stage_snapshots_and_pca(mock_db)

        # p1 should have been snapshotted (has AAPL position)
        p1.record_performance_snapshot.assert_awaited()
        p1.save_metrics.assert_awaited()

        # p2 should NOT have been snapshotted (empty portfolio)
        p2.record_performance_snapshot.assert_not_awaited()
        p2.save_metrics.assert_not_awaited()


@pytest.mark.asyncio
async def test_stage_snapshots_uses_batch_get_quotes():
    """_stage_snapshots_and_pca must use get_quotes() (batch), not get_quote().

    Individual get_quote() calls are sequential and each checks the cache
    independently. With a short cache TTL, this means 20+ sequential FMP API
    calls. Batch get_quotes() fetches all missing tickers in one call.
    """
    from unittest.mock import AsyncMock

    from main import _stage_snapshots_and_pca

    p = Portfolio("trader")
    p.id = "portfolio-1"
    p.positions = {"AAPL": Position("AAPL", 10, 150.0), "GOOGL": Position("GOOGL", 5, 200.0)}
    p.initialize = AsyncMock()
    p.record_performance_snapshot = AsyncMock()
    p.save_metrics = AsyncMock()

    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.execute.return_value = MagicMock(
        data=[{"owner_id": "trader"}]
    )

    with patch("main.get_supabase_client", return_value=mock_db), \
         patch("main.Portfolio", return_value=p), \
         patch("execution.market_data.MarketDataManager") as MockMDM, \
         patch("main.update_pca_coordinates"):

        mock_mdm = MockMDM.return_value
        mock_quote_data = MagicMock(price=150.0)
        mock_mdm.get_quote = AsyncMock(return_value=mock_quote_data)
        mock_mdm.get_quotes = AsyncMock(
            return_value={"AAPL": mock_quote_data, "GOOGL": mock_quote_data}
        )

        await _stage_snapshots_and_pca(mock_db)

        # MUST use batch get_quotes, not individual get_quote
        mock_mdm.get_quotes.assert_awaited_once()
        # Should be called with both tickers at once
        args = mock_mdm.get_quotes.await_args[0][0]
        assert sorted(args) == ["AAPL", "GOOGL"], \
            f"Expected ['AAPL', 'GOOGL'], got {args}"

        # Individual get_quote should NOT be called
        mock_mdm.get_quote.assert_not_awaited()