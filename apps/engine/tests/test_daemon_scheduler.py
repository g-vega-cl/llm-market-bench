"""MiniPC daemon scheduling: it is the single owner of prices, marks and strategy hooks."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from trading.runner import _is_price_refresh_window, run_market_data_loop, run_systematic_hooks_loop

ET = ZoneInfo("America/New_York")


def test_price_refresh_window_bounds():
    assert _is_price_refresh_window(datetime(2026, 11, 18, 9, 29, tzinfo=ET)) is False
    assert _is_price_refresh_window(datetime(2026, 11, 18, 9, 30, tzinfo=ET)) is True
    assert _is_price_refresh_window(datetime(2026, 11, 18, 15, 59, tzinfo=ET)) is True
    assert _is_price_refresh_window(datetime(2026, 11, 18, 16, 5, tzinfo=ET)) is True
    assert _is_price_refresh_window(datetime(2026, 11, 18, 16, 6, tzinfo=ET)) is False
    assert _is_price_refresh_window(datetime(2026, 11, 14, 11, 0, tzinfo=ET)) is False  # Saturday


async def _stop_after_first_tick(_seconds):
    raise asyncio.CancelledError


@pytest.mark.asyncio
async def test_hooks_loop_runs_hook_once_during_session():
    calls = []

    async def fake_hook(now_et, dry_run=False):
        calls.append(now_et)

    with (
        patch("trading.runner._is_hooks_window", return_value=True),
        patch("scripts.update_prices.run_systematic_strategy_hooks", new=fake_hook),
        patch("trading.runner.asyncio.sleep", new=_stop_after_first_tick),
    ):
        with pytest.raises(asyncio.CancelledError):
            await run_systematic_hooks_loop(interval_seconds=300)

    assert len(calls) == 1
    assert calls[0].tzinfo is not None


@pytest.mark.asyncio
async def test_hooks_loop_skips_hook_when_market_closed():
    calls = []

    async def fake_hook(now_et, dry_run=False):
        calls.append(now_et)

    with (
        patch("trading.runner._is_hooks_window", return_value=False),
        patch("scripts.update_prices.run_systematic_strategy_hooks", new=fake_hook),
        patch("trading.runner.asyncio.sleep", new=_stop_after_first_tick),
    ):
        with pytest.raises(asyncio.CancelledError):
            await run_systematic_hooks_loop(interval_seconds=300)

    assert calls == []


@pytest.mark.asyncio
async def test_market_data_loop_marks_and_refreshes_history():
    with (
        patch("trading.runner._is_price_refresh_window", return_value=True),
        patch("trading.runner.get_supabase_client", return_value=MagicMock()),
        patch("execution.market_data.MarketDataManager", return_value=MagicMock()),
        patch("scripts.update_prices.refresh_portfolio_marks", new_callable=AsyncMock) as marks,
        patch("scripts.update_prices.fetch_benchmark_history", new_callable=AsyncMock) as history,
        patch("trading.runner.asyncio.sleep", new=_stop_after_first_tick),
    ):
        with pytest.raises(asyncio.CancelledError):
            await run_market_data_loop(interval_seconds=900, history_interval_seconds=1800)

    marks.assert_awaited_once()
    history.assert_awaited_once()


@pytest.mark.asyncio
async def test_market_data_loop_refreshes_history_on_first_tick_regardless_of_uptime():
    """The first tick must refresh history even on a freshly booted host.

    `time.monotonic()` is seconds since boot, not wall-clock time. Seeding the
    history cursor with 0.0 makes the first refresh depend on host uptime: it
    fires on a long-running workstation but is skipped on a fresh CI runner
    whose monotonic clock is still below the interval.
    """
    with (
        patch("trading.runner._is_price_refresh_window", return_value=True),
        patch("trading.runner.get_supabase_client", return_value=MagicMock()),
        patch("execution.market_data.MarketDataManager", return_value=MagicMock()),
        patch("scripts.update_prices.refresh_portfolio_marks", new_callable=AsyncMock),
        patch("scripts.update_prices.fetch_benchmark_history", new_callable=AsyncMock) as history,
        patch("trading.runner.asyncio.sleep", new=_stop_after_first_tick),
    ):
        with pytest.raises(asyncio.CancelledError):
            await run_market_data_loop(interval_seconds=900, history_interval_seconds=10**9)

    history.assert_awaited_once()


@pytest.mark.asyncio
async def test_market_data_loop_skips_outside_window():
    with (
        patch("trading.runner._is_price_refresh_window", return_value=False),
        patch("trading.runner.get_supabase_client", return_value=MagicMock()),
        patch("execution.market_data.MarketDataManager", return_value=MagicMock()),
        patch("scripts.update_prices.refresh_portfolio_marks", new_callable=AsyncMock) as marks,
        patch("scripts.update_prices.fetch_benchmark_history", new_callable=AsyncMock) as history,
        patch("trading.runner.asyncio.sleep", new=_stop_after_first_tick),
    ):
        with pytest.raises(asyncio.CancelledError):
            await run_market_data_loop(interval_seconds=900)

    marks.assert_not_awaited()
    history.assert_not_awaited()


def test_hooks_window_reaches_closing_print():
    """The hooks loop must tick once after 16:00 so close-print exits can run."""
    from trading.runner import _is_hooks_window

    assert _is_hooks_window(datetime(2026, 11, 19, 9, 29, tzinfo=ET)) is False
    assert _is_hooks_window(datetime(2026, 11, 19, 9, 30, tzinfo=ET)) is True
    assert _is_hooks_window(datetime(2026, 11, 19, 16, 4, tzinfo=ET)) is True
    assert _is_hooks_window(datetime(2026, 11, 19, 16, 6, tzinfo=ET)) is False
    assert _is_hooks_window(datetime(2026, 11, 21, 11, 0, tzinfo=ET)) is False  # Saturday
