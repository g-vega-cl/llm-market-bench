"""Hermetic unit tests for live intraday agent daemon runner."""

from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from trading.runner import (
    _create_clients,
    calculate_seconds_to_market_open,
    is_market_session_active,
    main,
    run_daemon_turn,
    run_loop,
)


def test_is_market_session_active():
    with patch("trading.runner.datetime") as mock_dt:
        mock_now = MagicMock()
        mock_now.weekday.return_value = 2  # Wednesday
        mock_now.hour = 10
        mock_now.minute = 15
        mock_dt.now.return_value = mock_now
        assert is_market_session_active() is True

        # Sunday -> Inactive
        mock_now.weekday.return_value = 6
        assert is_market_session_active() is False

        # Wednesday 08:00 AM ET (pre-market) -> Inactive
        mock_now.weekday.return_value = 2
        mock_now.hour = 8
        assert is_market_session_active() is False


def test_calculate_seconds_to_market_open():
    with patch("trading.runner.datetime") as mock_dt:
        mock_now = MagicMock()
        mock_now.weekday.return_value = 2  # Wednesday 08:30 AM ET
        mock_now.hour = 8
        mock_now.minute = 30
        mock_now.second = 0
        mock_dt.now.return_value = mock_now

        secs = calculate_seconds_to_market_open()
        assert secs == 3600.0

        # Friday after close (weekday 4, 17:00)
        mock_now.weekday.return_value = 4
        mock_now.hour = 17
        mock_now.minute = 0
        mock_now.second = 0
        secs_weekend = calculate_seconds_to_market_open()
        assert secs_weekend > 86400

        # Saturday (weekday 5)
        mock_now.weekday.return_value = 5
        secs_sat = calculate_seconds_to_market_open()
        assert secs_sat > 0


@pytest.mark.asyncio
async def test_run_daemon_turn_calls_step_and_candle():
    mock_alpaca_data = MagicMock()
    mock_alpaca_trade = MagicMock()
    mock_sb = MagicMock()

    with (
        patch("trading.runner.fetch_active_candle", new=AsyncMock(return_value={"close": 582.5})) as mock_candle,
        patch(
            "trading.runner.execute_intraday_agent_step",
            new=AsyncMock(return_value={"action": "BUY", "conviction": 80, "thought": "Bullish trend"}),
        ) as mock_step,
    ):
        result = await run_daemon_turn(
            alpaca_data_client=mock_alpaca_data,
            alpaca_trading_client=mock_alpaca_trade,
            sb_client=mock_sb,
            ticker="SPY",
            strata_url="http://primary-workstation:8080/v1",
            cheap_proxy_url="https://llm.clvg.uk/v1",
        )

        assert mock_step.called
        assert mock_candle.called
        assert result["action"] == "BUY"
        assert result["active_candle"]["close"] == 582.5


def test_create_clients_handles_missing_keys():
    with (
        patch("trading.runner.ALPACA_API_KEY", ""),
        patch("trading.runner.ALPACA_SECRET_KEY", ""),
        patch("trading.runner.get_supabase_client", return_value=MagicMock()),
    ):
        data, trade, sb = _create_clients()
        assert data is None
        assert trade is None
        assert sb is not None


def test_create_clients_initializes_when_keys_present():
    with (
        patch("trading.runner.ALPACA_API_KEY", "test_key"),
        patch("trading.runner.ALPACA_SECRET_KEY", "test_secret"),
        patch("trading.runner.get_supabase_client", return_value=MagicMock()),
        patch("alpaca.data.historical.StockHistoricalDataClient") as mock_data_cls,
        patch("alpaca.trading.client.TradingClient") as mock_trade_cls,
    ):
        data, trade, sb = _create_clients()
        assert mock_data_cls.called
        assert mock_trade_cls.called
        assert sb is not None


@pytest.mark.asyncio
async def test_run_loop_executes_turn_when_open():
    mock_data = MagicMock()
    mock_trade = MagicMock()
    mock_sb = MagicMock()

    loop_count = 0

    async def mock_sleep(_duration):
        nonlocal loop_count
        loop_count += 1
        if loop_count >= 2:
            raise asyncio.CancelledError()

    with (
        patch("trading.runner._create_clients", return_value=(mock_data, mock_trade, mock_sb)),
        patch("trading.runner.is_market_session_active", side_effect=[False, True]),
        patch("trading.runner.calculate_seconds_to_market_open", return_value=120.0),
        patch("trading.runner.run_daemon_turn", new=AsyncMock(return_value={"action": "HOLD", "conviction": 50})),
        patch("asyncio.sleep", side_effect=mock_sleep),
        pytest.raises(asyncio.CancelledError),
    ):
        await run_loop(ticker="SPY", interval_seconds=10, continuous_24_7=False)


@pytest.mark.asyncio
async def test_run_loop_executes_in_24_7_off_hours_mode():
    mock_data = MagicMock()
    mock_trade = MagicMock()
    mock_sb = MagicMock()

    loop_count = 0

    async def mock_sleep(_duration):
        nonlocal loop_count
        loop_count += 1
        if loop_count >= 1:
            raise asyncio.CancelledError()

    with (
        patch("trading.runner._create_clients", return_value=(mock_data, mock_trade, mock_sb)),
        patch("trading.runner.is_market_session_active", return_value=False),
        patch(
            "trading.runner.run_daemon_turn", new=AsyncMock(return_value={"action": "HOLD", "conviction": 50})
        ) as mock_turn,
        patch("asyncio.sleep", side_effect=mock_sleep),
        pytest.raises(asyncio.CancelledError),
    ):
        await run_loop(ticker="SPY", interval_seconds=10, continuous_24_7=True)

        assert mock_turn.called
        # Verify trading client was passed as None during off hours
        call_kwargs = mock_turn.call_args[1]
        assert call_kwargs["alpaca_trading_client"] is None


@pytest.mark.asyncio
async def test_run_tape_poller_loop_polls_and_publishes():
    from trading.runner import run_tape_poller_loop

    mock_alpaca = MagicMock()
    mock_sb = MagicMock()
    mock_broadcaster = MagicMock()

    sample_bars = [{"time": "2026-10-30T16:00:00Z", "close": 582.0}]

    async def mock_sleep(_dur):
        raise asyncio.CancelledError()

    with (
        patch("trading.runner.is_market_session_active", return_value=True),
        patch("trading.live_intraday_agent.fetch_intraday_bars", new=AsyncMock(return_value=sample_bars)) as mock_bars,
        patch("trading.runner.update_latest_tape_in_db", new=AsyncMock(return_value=True)) as mock_db,
        patch("asyncio.sleep", side_effect=mock_sleep),
        pytest.raises(asyncio.CancelledError),
    ):
        await run_tape_poller_loop(
            alpaca_data_client=mock_alpaca,
            sb_client=mock_sb,
            broadcaster=mock_broadcaster,
            ticker="SPY",
            tape_interval_seconds=10,
        )

        assert mock_bars.called
        assert mock_broadcaster.publish_bars.called
        assert mock_db.called


def test_main_cli_once():
    with (
        patch.object(sys, "argv", ["runner.py", "--once", "--ticker", "SPY"]),
        patch("trading.runner._create_clients", return_value=(None, None, MagicMock())),
        patch(
            "trading.runner.run_daemon_turn",
            new=AsyncMock(return_value={"action": "BUY", "conviction": 75}),
        ),
    ):
        main()


def test_main_cli_loop():
    with (
        patch.object(sys, "argv", ["runner.py", "--loop", "--interval", "60"]),
        patch("trading.runner.run_loop", new=AsyncMock()) as mock_run_loop,
    ):
        main()
        assert mock_run_loop.called
