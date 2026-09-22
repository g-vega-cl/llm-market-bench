"""Tests for real-time sector trading: single-cycle prediction scoping, cash balance updates, and Alpaca paper execution."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from execution.sector_trading import (
    execute_mechanical_sector_entry,
    execute_mechanical_sector_exit,
    execute_system_sector_entry,
    run_sector_trade,
)
from execution.system_portfolios import (
    SYS_SECTOR_UNCORR_20D_OWNER_ID,
)


@pytest.mark.asyncio
async def test_sector_prediction_single_cycle_scoping():
    """Verify that run_sector_trade(entry) only uses predictions from the latest prediction_date."""
    mock_client = MagicMock()
    mock_chain = MagicMock()
    mock_chain.select.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain
    mock_chain.lte.return_value = mock_chain
    mock_chain.order.return_value = mock_chain
    mock_chain.limit.return_value = mock_chain

    # Mock 3 different dates in the returned sector_predictions
    mock_predictions = [
        {"prediction_date": "2026-09-20", "predicted_sector": "XLK", "predicted_worst_sector": "XLE"},
        {"prediction_date": "2026-09-20", "predicted_sector": "XLE", "predicted_worst_sector": "XLV"},
        {"prediction_date": "2026-09-13", "predicted_sector": "XLF", "predicted_worst_sector": "XLI"},
        {"prediction_date": "2026-09-06", "predicted_sector": "XME", "predicted_worst_sector": "XLU"},
    ]
    mock_chain.execute.return_value = MagicMock(data=mock_predictions)
    mock_client.table.return_value = mock_chain

    with (
        patch("execution.sector_trading.get_supabase_client", return_value=mock_client),
        patch("execution.market_data.MarketDataManager.get_quotes", new_callable=AsyncMock) as mock_quotes,
        patch("execution.sector_trading.execute_system_sector_entry", new_callable=AsyncMock) as mock_sys_entry,
        patch("execution.sector_trading.execute_mechanical_sector_entry", new_callable=AsyncMock),
    ):
        mock_quote = MagicMock(open=100.0, price=100.0)
        mock_quotes.return_value = {"XLK": mock_quote, "XLE": mock_quote, "XLV": mock_quote}

        await run_sector_trade(action="entry", target_date_str="2026-09-21")

        # execute_system_sector_entry must only receive predictions from 2026-09-20
        assert mock_sys_entry.called
        passed_preds = mock_sys_entry.call_args.kwargs["predictions"]
        dates = {p["prediction_date"] for p in passed_preds}
        assert dates == {"2026-09-20"}
        assert len(passed_preds) == 2


@pytest.mark.asyncio
async def test_mechanical_entry_deducts_cash_and_submits_alpaca():
    """Verify that mechanical entry updates cash_balance in DB and mirrors BUY limit orders to Alpaca."""
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
    mock_portfolio.id = "port-uncorr-123"
    mock_portfolio.cash_balance = 10000.0

    entry_prices = {"XLK": 100.0, "XLV": 50.0}

    with (
        patch("execution.sector_trading.get_supabase_client", return_value=mock_client),
        patch("execution.sector_trading.get_or_create_system_portfolio", return_value=mock_portfolio),
        patch("execution.alpaca_broker.AlpacaBroker.submit_limit_order", new_callable=AsyncMock) as mock_alpaca_order,
    ):
        res = await execute_mechanical_sector_entry(
            owner_id=SYS_SECTOR_UNCORR_20D_OWNER_ID,
            sectors=["XLK", "XLV"],
            week_start_date="2026-09-21",
            price_map=entry_prices,
            dry_run=False,
        )

    assert res["status"] == "success"
    # Budget per sector: 5000. XLK: 49 shares @ ~100.05 = ~4902.45; XLV: 99 shares @ ~50.025 = ~4952.47
    total_spent = sum(t["shares"] * t["entry_price"] for t in res["trades"])
    assert total_spent > 9000.0

    # Verify that portfolio cash_balance was deducted
    update_calls = [call[0][0] for call in mock_chain.update.call_args_list if "cash_balance" in call[0][0]]
    assert len(update_calls) >= 1
    new_cash = update_calls[0]["cash_balance"]
    assert pytest.approx(new_cash, abs=1.0) == 10000.0 - total_spent

    # Verify Alpaca order was called for both tickers
    assert mock_alpaca_order.call_count == 2
    tickers_called = {call.kwargs["ticker"] for call in mock_alpaca_order.call_args_list}
    assert tickers_called == {"XLK", "XLV"}
    signals_called = {call.kwargs["signal"] for call in mock_alpaca_order.call_args_list}
    assert signals_called == {"BUY"}


@pytest.mark.asyncio
async def test_mechanical_exit_credits_cash_and_submits_alpaca():
    """Verify that mechanical exit credits proceeds to cash_balance and mirrors SELL orders to Alpaca."""
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

    # Open entries
    mock_open_trades = [
        {
            "id": "t1",
            "portfolio_id": "port-uncorr-123",
            "ticker": "XLK",
            "signal": "BUY",
            "quantity": 50,
            "price": 100.0,
            "total_cost": 5000.0,
            "executed_at": "2026-09-21T13:30:00Z",
            "realized_pnl": None,
        },
    ]
    mock_chain.execute.return_value = MagicMock(data=mock_open_trades)
    mock_client.table.return_value = mock_chain

    # Portfolio cash after entry was 5000.0
    mock_portfolio = MagicMock()
    mock_portfolio.id = "port-uncorr-123"
    mock_portfolio.cash_balance = 5000.0

    exit_prices = {"XLK": 110.0}  # Proceeds: 50 * 109.945 = 5497.25

    with (
        patch("execution.sector_trading.get_supabase_client", return_value=mock_client),
        patch("execution.sector_trading.get_or_create_system_portfolio", return_value=mock_portfolio),
        patch("execution.alpaca_broker.AlpacaBroker.submit_limit_order", new_callable=AsyncMock) as mock_alpaca_order,
    ):
        res = await execute_mechanical_sector_exit(
            owner_id=SYS_SECTOR_UNCORR_20D_OWNER_ID,
            week_end_date="2026-09-25",
            price_map=exit_prices,
            dry_run=False,
        )

    assert res["status"] == "success"
    # Cash must be credited with total proceeds (5000 initial remaining + ~5497.25 proceeds)
    update_calls = [call[0][0] for call in mock_chain.update.call_args_list if "cash_balance" in call[0][0]]
    assert len(update_calls) >= 1
    new_cash = update_calls[0]["cash_balance"]
    assert new_cash > 10000.0

    # Alpaca SELL order submitted
    assert mock_alpaca_order.call_count == 1
    assert mock_alpaca_order.call_args.kwargs["ticker"] == "XLK"
    assert mock_alpaca_order.call_args.kwargs["signal"] == "SELL"


@pytest.mark.asyncio
async def test_system_sector_entry_deducts_cash_and_mirrors_longs_to_alpaca():
    """Verify that consensus sector entry deducts cash for long purchases and mirrors ONLY longs to Alpaca."""
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
    mock_portfolio.id = "port-ls-123"
    mock_portfolio.cash_balance = 10000.0

    predictions = [
        {"predicted_sector": "XLK", "predicted_worst_sector": "XLE"},
    ]
    price_map = {"XLK": 100.0, "XLE": 50.0}

    with (
        patch("execution.sector_trading.get_supabase_client", return_value=mock_client),
        patch("execution.sector_trading.get_or_create_system_portfolio", return_value=mock_portfolio),
        patch("execution.alpaca_broker.AlpacaBroker.submit_limit_order", new_callable=AsyncMock) as mock_alpaca_order,
    ):
        res = await execute_system_sector_entry(
            week_start_date="2026-09-21",
            predictions=predictions,
            price_map=price_map,
            dry_run=False,
        )

    assert res["status"] == "success"
    # Verify cash deduction for long leg
    update_calls = [call[0][0] for call in mock_chain.update.call_args_list if "cash_balance" in call[0][0]]
    assert len(update_calls) >= 1
    new_cash = update_calls[0]["cash_balance"]
    assert new_cash < 10000.0

    # Verify Alpaca only received order for XLK (BUY), NOT for XLE (SHORT)
    assert mock_alpaca_order.call_count == 1
    assert mock_alpaca_order.call_args.kwargs["ticker"] == "XLK"
    assert mock_alpaca_order.call_args.kwargs["signal"] == "BUY"


@pytest.mark.asyncio
async def test_evaluate_predictions_zero_backfill():
    """Verify evaluate_predictions scores predictions without triggering retroactive portfolio rebalances."""
    from tasks.evaluate_predictions import run_evaluation

    mock_client = MagicMock()
    mock_chain = MagicMock()
    mock_chain.select.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain
    mock_chain.lte.return_value = mock_chain
    mock_chain.order.return_value = mock_chain
    mock_chain.execute.return_value = MagicMock(data=[])
    mock_pending = [
        {
            "id": "pred-1",
            "prediction_date": "2026-09-13",
            "target_date": "2026-09-20",
            "timeframe": "7d",
            "predicted_sector": "XLK",
            "predicted_worst_sector": "XLE",
            "predicted_pair": ["XLK", "XLV"],
            "confidence": 80.0,
            "status": "pending",
        }
    ]

    def mock_table_routing(table_name):
        c = MagicMock()
        c.select.return_value = c
        c.eq.return_value = c
        c.lte.return_value = c
        c.order.return_value = c
        c.update.return_value = c
        if table_name == "sector_predictions":
            c.execute.return_value = MagicMock(data=mock_pending)
        else:
            c.execute.return_value = MagicMock(data=[])
        return c

    mock_client.table.side_effect = mock_table_routing

    mock_provider = MagicMock()
    mock_provider.get_history = AsyncMock(
        return_value=[
            {"date": "2026-09-13", "close": 100.0},
            {"date": "2026-09-20", "close": 105.0},
        ]
    )

    with (
        patch("tasks.evaluate_predictions.get_supabase_client", return_value=mock_client),
        patch("tasks.evaluate_predictions.get_financial_provider", return_value=mock_provider),
    ):
        await run_evaluation()

    # Verify sector_predictions was updated, but trades/portfolios were never touched
    table_names_called = [call[0][0] for call in mock_client.table.call_args_list]
    assert "sector_predictions" in table_names_called
    assert "trades" not in table_names_called
    assert "portfolios" not in table_names_called
    assert "portfolio_positions" not in table_names_called


@pytest.mark.asyncio
async def test_sector_exit_preserves_positions_until_after_alpaca_order():
    """Verify that portfolio_positions is NOT deleted before Alpaca limit order is submitted.

    This ensures that AlpacaBroker's _get_supabase_position fallback finds the position
    in Supabase when Alpaca reports 0 shares.
    """
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

    mock_open_trades = [
        {
            "id": "t-1",
            "portfolio_id": "port-123",
            "ticker": "XLK",
            "signal": "BUY",
            "quantity": 10,
            "price": 100.0,
            "total_cost": 1000.0,
            "executed_at": "2026-09-21T13:30:00Z",
            "realized_pnl": None,
        }
    ]
    mock_chain.execute.return_value = MagicMock(data=mock_open_trades)
    mock_client.table.return_value = mock_chain

    mock_portfolio = MagicMock()
    mock_portfolio.id = "port-123"
    mock_portfolio.cash_balance = 5000.0

    delete_called_at_alpaca_time = []

    async def mock_submit(*args, **kwargs):
        # Record whether portfolio_positions delete was called BEFORE Alpaca submit
        delete_called_at_alpaca_time.append(mock_chain.delete.called)

    with (
        patch("execution.sector_trading.get_supabase_client", return_value=mock_client),
        patch("execution.sector_trading.get_or_create_system_portfolio", return_value=mock_portfolio),
        patch("execution.alpaca_broker.AlpacaBroker.submit_limit_order", side_effect=mock_submit),
    ):
        await execute_mechanical_sector_exit(
            owner_id=SYS_SECTOR_UNCORR_20D_OWNER_ID,
            week_end_date="2026-09-25",
            price_map={"XLK": 110.0},
            dry_run=False,
        )

    assert len(delete_called_at_alpaca_time) == 1
    # MUST be False: portfolio_positions must NOT have been deleted before Alpaca order was submitted
    assert delete_called_at_alpaca_time[0] is False, (
        "portfolio_positions was prematurely deleted before Alpaca order submission!"
    )
    # MUST be True: portfolio_positions must be deleted after Alpaca order was submitted
    assert mock_chain.delete.called is True


@pytest.mark.asyncio
async def test_system_sector_exit_preserves_positions_until_after_alpaca_order():
    """Verify that execute_system_sector_exit does NOT delete portfolio_positions before Alpaca submit."""
    from execution.sector_trading import execute_system_sector_exit

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

    mock_open_trades = [
        {
            "id": "t-sys-1",
            "portfolio_id": "port-sys-123",
            "ticker": "XLK",
            "signal": "BUY",
            "quantity": 10,
            "price": 100.0,
            "total_cost": 1000.0,
            "executed_at": "2026-09-21T13:30:00Z",
            "realized_pnl": None,
        }
    ]
    mock_chain.execute.return_value = MagicMock(data=mock_open_trades)
    mock_client.table.return_value = mock_chain

    mock_portfolio = MagicMock()
    mock_portfolio.id = "port-sys-123"
    mock_portfolio.cash_balance = 5000.0

    delete_called_at_alpaca_time = []

    async def mock_submit(*args, **kwargs):
        delete_called_at_alpaca_time.append(mock_chain.delete.called)

    with (
        patch("execution.sector_trading.get_supabase_client", return_value=mock_client),
        patch("execution.sector_trading.get_or_create_system_portfolio", return_value=mock_portfolio),
        patch("execution.alpaca_broker.AlpacaBroker.submit_limit_order", side_effect=mock_submit),
    ):
        await execute_system_sector_exit(
            week_end_date="2026-09-25",
            price_map={"XLK": 110.0},
            dry_run=False,
        )

    assert len(delete_called_at_alpaca_time) == 1
    assert delete_called_at_alpaca_time[0] is False
    assert mock_chain.delete.called is True


@pytest.mark.asyncio
async def test_friday_exit_hook_in_update_prices():
    """Verify that update_prices triggers sector exit on Friday at or after 3:25 PM ET."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from scripts.update_prices import update_prices

    # Mock datetime to a Friday at 3:30 PM ET (2026-09-25 15:30:00 ET)
    friday_330pm = datetime(2026, 9, 25, 15, 30, 0, tzinfo=ZoneInfo("America/New_York"))

    mock_client = MagicMock()
    mock_chain = MagicMock()
    mock_chain.select.return_value = mock_chain
    mock_chain.execute.return_value = MagicMock(data=[])
    mock_client.table.return_value = mock_chain

    with (
        patch("execution.market_data.MarketDataManager.is_market_open", new_callable=AsyncMock, return_value=True),
        patch("scripts.update_prices.get_supabase_client", return_value=mock_client),
        patch("scripts.update_prices.datetime") as mock_dt,
        patch("execution.sector_trading.run_sector_trade", new_callable=AsyncMock) as mock_sector_exit,
    ):
        mock_dt.now.return_value = friday_330pm
        await update_prices()

    assert mock_sector_exit.called
    assert mock_sector_exit.call_args.kwargs["action"] == "exit"


@pytest.mark.asyncio
async def test_friday_exit_hook_in_main_ingest():
    """Verify that main.run_ingest triggers sector exit on Friday at or after 3:00 PM ET."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    import main

    friday_330pm = datetime(2026, 9, 25, 15, 30, 0, tzinfo=ZoneInfo("America/New_York"))

    mock_client = MagicMock()
    mock_chain = MagicMock()
    mock_chain.select.return_value = mock_chain
    mock_chain.execute.return_value = MagicMock(data=[])
    mock_client.table.return_value = mock_chain

    with (
        patch("main.get_supabase_client", return_value=mock_client),
        patch("main.datetime") as mock_dt,
        patch("main._stage_dust_cleanup", new_callable=AsyncMock),
        patch("main._stage_ingest_and_snapshot", new_callable=AsyncMock, return_value=({"test": "data"}, mock_client)),
        patch("main._stage_analysis_and_consensus", new_callable=AsyncMock, return_value=([], [], {}, {})),
        patch("main._stage_decision_processing", new_callable=AsyncMock),
        patch("main._stage_snapshots_and_pca", new_callable=AsyncMock),
        patch("main.analyze_market_feeling", new_callable=AsyncMock, return_value=None),
        patch("execution.sector_trading.run_sector_trade", new_callable=AsyncMock) as mock_sector_exit,
    ):
        mock_dt.now.return_value = friday_330pm
        await main.run_ingest(force=True)

    assert mock_sector_exit.called
    assert mock_sector_exit.call_args.kwargs["action"] == "exit"
