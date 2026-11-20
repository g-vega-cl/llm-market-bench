"""Unit tests for the Contrarian Options Sentiment Fader scheduled task.

Hermetic tests with zero live network calls.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from execution.portfolio import Position
from tasks.sentiment_fader_task import (
    fetch_sentiment_snapshot,
    fetch_ticker_price,
    run_sentiment_fader_task,
)


@pytest.mark.asyncio
async def test_fetch_ticker_price_success():
    """Verify fetch_ticker_price extracts price cleanly from MarketDataManager."""
    mock_quote = MagicMock()
    mock_quote.exists = True
    mock_quote.price = 550.25

    with patch("tasks.sentiment_fader_task.MarketDataManager") as mock_mgr_cls:
        mock_mgr = MagicMock()
        mock_mgr.get_quote = AsyncMock(return_value=mock_quote)
        mock_mgr_cls.return_value = mock_mgr

        price = await fetch_ticker_price("SPY")
        assert price == 550.25


@pytest.mark.asyncio
async def test_fetch_sentiment_snapshot_success():
    """Verify fetch_sentiment_snapshot passes contracts to calculate_options_sentiment."""
    mock_snapshot = {
        "status": "OK",
        "contracts": [
            {
                "details": {"contract_type": "call", "strike_price": 550.0},
                "day": {"volume": 1000},
                "open_interest": 500,
            },
            {
                "details": {"contract_type": "put", "strike_price": 550.0},
                "day": {"volume": 1500},
                "open_interest": 600,
            },
        ],
    }
    mock_client = MagicMock()
    mock_client.get_options_snapshot = AsyncMock(return_value=mock_snapshot)

    sent = await fetch_sentiment_snapshot("SPY", current_price=550.0, client=mock_client)
    assert sent is not None
    assert sent["ticker"] == "SPY"
    assert sent["pv_ratio"] == 1.5


@pytest.mark.asyncio
async def test_fetch_sentiment_snapshot_empty():
    """Verify fetch_sentiment_snapshot returns None when no contracts found."""
    mock_client = MagicMock()
    mock_client.get_options_snapshot = AsyncMock(return_value={"status": "ERROR", "contracts": []})

    sent = await fetch_sentiment_snapshot("SPY", current_price=550.0, client=mock_client)
    assert sent is None


@pytest.mark.asyncio
async def test_run_sentiment_fader_task_dry_run():
    """Verify run_sentiment_fader_task dry-run plan generation."""
    mock_portfolio = MagicMock()
    mock_portfolio.id = "mock-port-id"
    mock_portfolio.cash_balance = 10000.0
    mock_portfolio.positions = {}
    mock_portfolio.initialize = AsyncMock()

    mock_sentiment_spy = {
        "ticker": "SPY",
        "pv_ratio": 1.45,  # Panic buy signal
    }
    mock_sentiment_qqq = {
        "ticker": "QQQ",
        "pv_ratio": 0.90,  # Neutral
    }

    async def mock_fetch_sent(ticker, current_price=None, client=None):
        if ticker == "SPY":
            return mock_sentiment_spy
        return mock_sentiment_qqq

    async def mock_fetch_px(ticker):
        return 500.0 if ticker == "SPY" else 400.0

    with (
        patch("tasks.sentiment_fader_task.Portfolio", return_value=mock_portfolio),
        patch("tasks.sentiment_fader_task.fetch_ticker_price", side_effect=mock_fetch_px),
        patch("tasks.sentiment_fader_task.fetch_sentiment_snapshot", side_effect=mock_fetch_sent),
        patch(
            "tasks.sentiment_fader_task._load_recent_trade_state",
            new=AsyncMock(return_value=({}, set())),
        ),
    ):
        result = await run_sentiment_fader_task(
            dry_run=True,
            action="evaluate",
            tickers=["SPY", "QQQ"],
        )

        assert result["status"] == "success"
        assert result["dry_run"] is True
        assert len(result["buys"]) == 1
        assert result["buys"][0]["ticker"] == "SPY"
        assert result["buys"][0]["shares"] > 0
        mock_portfolio.execute_trade.assert_not_called()


@pytest.mark.asyncio
async def test_run_sentiment_fader_task_live_execution():
    """Verify live trade execution calls execute_trade, save_metrics, and record_performance_snapshot."""
    mock_portfolio = MagicMock()
    mock_portfolio.id = "mock-port-id"
    mock_portfolio.cash_balance = 10000.0
    mock_portfolio.positions = {}
    mock_portfolio.metrics = MagicMock(realized=10000.0)
    mock_portfolio.initialize = AsyncMock()
    mock_portfolio.execute_trade = AsyncMock(return_value="trade-uuid-1")
    mock_portfolio.calculate_reg_t_metrics = MagicMock()
    mock_portfolio.save_metrics = AsyncMock()
    mock_portfolio.record_performance_snapshot = AsyncMock()

    mock_sentiment = {
        "ticker": "SPY",
        "pv_ratio": 1.50,
    }

    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_sb.table.return_value = mock_table
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.gte.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.limit.return_value = mock_table
    mock_table.execute.return_value = MagicMock(data=[])

    with (
        patch("tasks.sentiment_fader_task.Portfolio", return_value=mock_portfolio),
        patch("tasks.sentiment_fader_task.fetch_ticker_price", new=AsyncMock(return_value=500.0)),
        patch("tasks.sentiment_fader_task.fetch_sentiment_snapshot", new=AsyncMock(return_value=mock_sentiment)),
        patch("tasks.sentiment_fader_task.get_supabase_client", return_value=mock_sb),
    ):
        result = await run_sentiment_fader_task(
            dry_run=False,
            action="evaluate",
            tickers=["SPY"],
        )

        assert result["status"] == "success"
        assert result["dry_run"] is False
        mock_portfolio.execute_trade.assert_called_once()
        assert "reason" in mock_portfolio.execute_trade.call_args.kwargs
        mock_portfolio.save_metrics.assert_not_called()
        mock_portfolio.record_performance_snapshot.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_sentiment_fader_task_blocks_same_day_reentry():
    """Verify tickers sold earlier the same ET day cannot be re-bought on subsequent ticks."""
    mock_portfolio = MagicMock()
    mock_portfolio.id = "mock-port-id"
    mock_portfolio.cash_balance = 9520.87
    mock_portfolio.positions = {}
    mock_portfolio.initialize = AsyncMock()

    now_iso = datetime.now(UTC).isoformat()
    mock_sb = MagicMock()
    mock_trades_tbl = MagicMock()
    mock_sb.table.return_value = mock_trades_tbl
    mock_trades_tbl.select.return_value = mock_trades_tbl
    mock_trades_tbl.eq.return_value = mock_trades_tbl
    mock_trades_tbl.gte.return_value = mock_trades_tbl
    mock_trades_tbl.order.return_value = mock_trades_tbl
    mock_trades_tbl.limit.return_value = mock_trades_tbl
    mock_trades_tbl.execute.return_value = MagicMock(data=[{"ticker": "SPY", "signal": "SELL", "executed_at": now_iso}])

    async def mock_fetch_sent(ticker, current_price=None, client=None):
        return {"ticker": ticker, "pv_ratio": 1.60}

    with (
        patch("tasks.sentiment_fader_task.Portfolio", return_value=mock_portfolio),
        patch("tasks.sentiment_fader_task.fetch_ticker_price", new=AsyncMock(return_value=500.0)),
        patch("tasks.sentiment_fader_task.fetch_sentiment_snapshot", side_effect=mock_fetch_sent),
        patch("tasks.sentiment_fader_task.get_supabase_client", return_value=mock_sb),
    ):
        result = await run_sentiment_fader_task(
            dry_run=True,
            action="evaluate",
            tickers=["SPY", "QQQ"],
        )

    assert result["status"] == "success"
    assert [b["ticker"] for b in result["buys"]] == ["QQQ"]


@pytest.mark.asyncio
async def test_run_sentiment_fader_task_fails_closed_when_trade_state_lookup_fails():
    """If the trade ledger cannot be read, fail closed instead of bypassing re-entry cooldown."""
    mock_portfolio = MagicMock()
    mock_portfolio.id = "mock-port-id"
    mock_portfolio.cash_balance = 10000.0
    mock_portfolio.positions = {}
    mock_portfolio.initialize = AsyncMock()
    mock_portfolio.execute_trade = AsyncMock()

    mock_sb = MagicMock()
    mock_sb.table.side_effect = RuntimeError("PostgREST unavailable")

    with (
        patch("tasks.sentiment_fader_task.Portfolio", return_value=mock_portfolio),
        patch("tasks.sentiment_fader_task.get_supabase_client", return_value=mock_sb),
    ):
        result = await run_sentiment_fader_task(dry_run=False, action="evaluate", tickers=["SPY"])

    assert result["status"] == "error"
    mock_portfolio.execute_trade.assert_not_called()


@pytest.mark.asyncio
async def test_run_sentiment_fader_task_aborts_buys_when_sell_fails():
    """If a planned SELL fails in execute_trade, dependent BUYs must be aborted."""
    mock_portfolio = MagicMock()
    mock_portfolio.id = "mock-port-id"
    mock_portfolio.cash_balance = 100.0
    mock_portfolio.positions = {"SPY": Position(ticker="SPY", quantity=10, average_cost_basis=500.0)}
    mock_portfolio.initialize = AsyncMock()
    mock_portfolio.execute_trade = AsyncMock(return_value=None)
    mock_portfolio.calculate_reg_t_metrics = MagicMock()
    mock_portfolio.save_metrics = AsyncMock()
    mock_portfolio.record_performance_snapshot = AsyncMock()

    async def mock_fetch_px(ticker):
        return 490.0 if ticker == "SPY" else 400.0  # SPY triggers -2% stop-loss

    async def mock_fetch_sent(ticker, current_price=None, client=None):
        return {"ticker": ticker, "pv_ratio": 1.60}

    with (
        patch("tasks.sentiment_fader_task.Portfolio", return_value=mock_portfolio),
        patch("tasks.sentiment_fader_task.fetch_ticker_price", side_effect=mock_fetch_px),
        patch("tasks.sentiment_fader_task.fetch_sentiment_snapshot", side_effect=mock_fetch_sent),
        patch(
            "tasks.sentiment_fader_task._load_recent_trade_state",
            new=AsyncMock(return_value=({"SPY": 1}, set())),
        ),
    ):
        result = await run_sentiment_fader_task(
            dry_run=False,
            action="evaluate",
            tickers=["SPY", "QQQ"],
        )

    assert result["status"] == "error"
    # Only the SELL was attempted; QQQ BUY was aborted when SELL returned None
    mock_portfolio.execute_trade.assert_awaited_once()
    assert mock_portfolio.execute_trade.call_args.kwargs["signal"] == "SELL"


@pytest.mark.asyncio
async def test_run_sentiment_fader_task_fails_closed_on_missing_held_quote():
    """If a held ticker lacks a live quote (0.0), abort tick instead of liquidating at cost basis."""
    mock_portfolio = MagicMock()
    mock_portfolio.id = "mock-port-id"
    mock_portfolio.cash_balance = 500.0
    mock_portfolio.positions = {"SPY": Position(ticker="SPY", quantity=10, average_cost_basis=500.0)}
    mock_portfolio.initialize = AsyncMock()
    mock_portfolio.execute_trade = AsyncMock()
    mock_portfolio.record_performance_snapshot = AsyncMock()

    with (
        patch("tasks.sentiment_fader_task.Portfolio", return_value=mock_portfolio),
        patch("tasks.sentiment_fader_task.fetch_ticker_price", new=AsyncMock(return_value=0.0)),
        patch(
            "tasks.sentiment_fader_task._load_recent_trade_state",
            new=AsyncMock(return_value=({"SPY": 5}, set())),  # Would trigger max holding days if cost basis used
        ),
    ):
        result = await run_sentiment_fader_task(dry_run=False, action="evaluate", tickers=["SPY"])

    assert result["status"] == "error"
    assert "Missing live spot price" in result["error"]
    mock_portfolio.execute_trade.assert_not_called()
    mock_portfolio.record_performance_snapshot.assert_not_called()
