"""Unit tests for the Contrarian Options Sentiment Fader scheduled task.

Hermetic tests with zero live network calls.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
    mock_portfolio.positions = []
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
    """Verify live trade execution and Reg T calculations."""
    mock_portfolio = MagicMock()
    mock_portfolio.id = "mock-port-id"
    mock_portfolio.cash_balance = 10000.0
    mock_portfolio.positions = []
    mock_portfolio.total_equity = 10000.0
    mock_portfolio.unrealized_pnl = 0.0
    mock_portfolio.buying_power = 20000.0
    mock_portfolio.excess_liquidity = 10000.0
    mock_portfolio.sma = 10000.0
    mock_portfolio.metrics = MagicMock(realized=10000.0)
    mock_portfolio.initialize = AsyncMock()
    mock_portfolio.execute_trade = AsyncMock()
    mock_portfolio.calculate_reg_t_metrics = MagicMock()
    mock_portfolio.save_metrics = AsyncMock()

    mock_sentiment = {
        "ticker": "SPY",
        "pv_ratio": 1.50,
    }

    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_sb.table.return_value = mock_table
    mock_table.upsert.return_value = mock_table
    mock_table.execute.return_value = MagicMock()

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
        mock_portfolio.calculate_reg_t_metrics.assert_called_once()
        mock_portfolio.save_metrics.assert_called_once()
