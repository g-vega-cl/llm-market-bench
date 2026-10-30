"""Continuous runner and daemon coordinator for the autonomous intraday trader.

Polls active tape, executes 5-minute reasoning turns via local Strata with fallback
to the centralized CLVG proxy, routes paper orders to Alpaca, and respects US regular
market session hours.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import os
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from core.config import (
    ALPACA_API_KEY,
    ALPACA_SECRET_KEY,
    logger,
)
from core.db import get_supabase_client
from trading.live_intraday_agent import (
    DEFAULT_CHEAP_PROXY_URL,
    DEFAULT_STRATA_URL,
    execute_intraday_agent_step,
    fetch_active_candle,
    fetch_intraday_bars,
)
from trading.tape_stream import (
    TapeBroadcaster,
    start_tape_server,
    update_latest_tape_in_db,
)


def is_market_session_active(now_dt: datetime | None = None) -> bool:
    """Check if the current time falls within US regular equity market hours.

    Regular hours: Monday through Friday, 09:30 AM to 04:00 PM Eastern Time.
    """
    if now_dt is None:
        now_dt = datetime.now(ZoneInfo("America/New_York"))

    weekday = now_dt.weekday() if callable(getattr(now_dt, "weekday", None)) else getattr(now_dt, "weekday", 0)
    if weekday >= 5:
        return False

    hour = getattr(now_dt, "hour", 0)
    minute = getattr(now_dt, "minute", 0)
    total_minutes = hour * 60 + minute
    return 570 <= total_minutes < 960


def calculate_seconds_to_market_open(now_dt: datetime | None = None) -> float:
    """Calculate the number of seconds until the next 09:30 AM ET market open."""
    if now_dt is None:
        now_dt = datetime.now(ZoneInfo("America/New_York"))

    weekday = now_dt.weekday() if callable(getattr(now_dt, "weekday", None)) else getattr(now_dt, "weekday", 0)
    hour = getattr(now_dt, "hour", 0)
    minute = getattr(now_dt, "minute", 0)
    second = getattr(now_dt, "second", 0)

    current_secs = hour * 3600 + minute * 60 + second
    target_open_secs = 9 * 3600 + 30 * 60

    if weekday < 5 and current_secs < target_open_secs:
        return float(target_open_secs - current_secs)

    days_ahead = 1
    if weekday == 4:
        days_ahead = 3
    elif weekday == 5:
        days_ahead = 2
    elif weekday == 6:
        days_ahead = 1

    secs_remaining_today = max(0, 86400 - current_secs)
    return float(secs_remaining_today + (days_ahead - 1) * 86400 + target_open_secs)


async def run_daemon_turn(
    alpaca_data_client: Any = None,
    alpaca_trading_client: Any = None,
    sb_client: Any = None,
    http_client: httpx.AsyncClient | None = None,
    ticker: str = "SPY",
    strata_url: str = DEFAULT_STRATA_URL,
    cheap_proxy_url: str = DEFAULT_CHEAP_PROXY_URL,
) -> dict[str, Any]:
    """Execute a single intraday agent cycle: active candle poll + trading step."""
    active_candle = await fetch_active_candle(alpaca_data_client, ticker=ticker)

    step_result = await execute_intraday_agent_step(
        alpaca_data_client=alpaca_data_client,
        alpaca_trading_client=alpaca_trading_client,
        sb_client=sb_client,
        http_client=http_client,
        ticker=ticker,
        strata_url=strata_url,
        cheap_proxy_url=cheap_proxy_url,
    )

    return {
        **step_result,
        "active_candle": active_candle,
    }


def _create_clients() -> tuple[Any, Any, Any]:
    """Instantiate Alpaca data/trading clients and Supabase client."""
    data_client = None
    trading_client = None

    if ALPACA_API_KEY and ALPACA_SECRET_KEY:
        try:
            from alpaca.data.historical import StockHistoricalDataClient
            from alpaca.trading.client import TradingClient

            data_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)
            trading_client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)
        except Exception:
            logger.exception("Failed to initialize Alpaca clients")

    sb_client = get_supabase_client()
    return data_client, trading_client, sb_client


async def run_tape_poller_loop(
    alpaca_data_client: Any,
    sb_client: Any,
    broadcaster: TapeBroadcaster,
    ticker: str = "SPY",
    tape_interval_seconds: int = 20,
) -> None:
    """Continuously poll active tape from Alpaca, push to broadcaster, and update DB."""
    logger.info(f"Starting tape poller loop for {ticker} (interval={tape_interval_seconds}s)")
    while True:
        try:
            if alpaca_data_client and is_market_session_active():
                bars = await fetch_intraday_bars(alpaca_data_client, ticker=ticker, window_minutes=60)
                if bars:
                    broadcaster.publish_bars(bars)
                    await update_latest_tape_in_db(sb_client, bars)
        except Exception:
            logger.exception("Error in tape poller loop")
        await asyncio.sleep(float(tape_interval_seconds))


async def _run_agent_loop(
    ticker: str,
    interval_seconds: int,
    strata_url: str,
    cheap_proxy_url: str,
    continuous_24_7: bool,
    data_client: Any,
    trading_client: Any,
    sb_client: Any,
    broadcaster: TapeBroadcaster | None = None,
) -> None:
    """Run the 5-minute autonomous LLM reasoning turn loop."""
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        while True:
            try:
                is_open = is_market_session_active()
                if not is_open and not continuous_24_7:
                    secs_to_open = calculate_seconds_to_market_open()
                    sleep_dur = min(secs_to_open, 300.0)
                    logger.info(
                        f"Regular market closed. Sleeping {sleep_dur:.0f}s (next open in {secs_to_open / 3600:.1f}h)"
                    )
                    await asyncio.sleep(sleep_dur)
                    continue

                # In 24/7 off-hours mode, trading is disabled (paper orders skipped) but Q&A and analysis run
                effective_trading_client = trading_client if is_open else None
                mode_str = "Market open" if is_open else "24/7 Off-hours"
                logger.info(f"{mode_str}. Running evaluation turn for {ticker}...")
                turn_result = await run_daemon_turn(
                    alpaca_data_client=data_client,
                    alpaca_trading_client=effective_trading_client,
                    sb_client=sb_client,
                    http_client=http_client,
                    ticker=ticker,
                    strata_url=strata_url,
                    cheap_proxy_url=cheap_proxy_url,
                )
                logger.info(
                    f"Turn complete: Action={turn_result.get('action')} Conviction={turn_result.get('conviction')}%"
                )
            except Exception:
                logger.exception("Unexpected error in daemon turn loop")

            await asyncio.sleep(float(interval_seconds))


async def run_loop(
    ticker: str = "SPY",
    interval_seconds: int = 300,
    tape_interval_seconds: int = 20,
    tape_port: int = 8090,
    enable_tape_server: bool = True,
    strata_url: str = DEFAULT_STRATA_URL,
    cheap_proxy_url: str = DEFAULT_CHEAP_PROXY_URL,
    continuous_24_7: bool = True,
) -> None:
    """Run the continuous 24/7 daemon loop with concurrent 20s tape polling & SSE server."""
    logger.info(
        f"Starting Live SPY Trader Daemon (ticker={ticker}, interval={interval_seconds}s, tape_interval={tape_interval_seconds}s, 24/7={continuous_24_7})"
    )
    logger.info(f"Tier 1 Inference: {strata_url}")
    logger.info(f"Tier 2 Inference: {cheap_proxy_url}")

    data_client, trading_client, sb_client = _create_clients()
    broadcaster = TapeBroadcaster()

    server = None
    if enable_tape_server:
        try:
            server, bound_port = await start_tape_server(broadcaster, host="0.0.0.0", port=tape_port)
            logger.info(f"Tape SSE server running on port {bound_port}")
        except Exception:
            logger.exception(f"Failed to start tape SSE server on port {tape_port}")

    try:
        tape_task = asyncio.create_task(
            run_tape_poller_loop(
                alpaca_data_client=data_client,
                sb_client=sb_client,
                broadcaster=broadcaster,
                ticker=ticker,
                tape_interval_seconds=tape_interval_seconds,
            )
        )
        agent_task = asyncio.create_task(
            _run_agent_loop(
                ticker=ticker,
                interval_seconds=interval_seconds,
                strata_url=strata_url,
                cheap_proxy_url=cheap_proxy_url,
                continuous_24_7=continuous_24_7,
                data_client=data_client,
                trading_client=trading_client,
                sb_client=sb_client,
                broadcaster=broadcaster,
            )
        )
        await asyncio.gather(tape_task, agent_task)
    finally:
        if server:
            server.close()
            with contextlib.suppress(Exception):
                await server.wait_closed()


def main() -> None:
    """CLI entrypoint for running the intraday agent trader."""
    parser = argparse.ArgumentParser(description="Live Intraday SPY Trader Daemon")
    parser.add_argument("--loop", action="store_true", help="Run continuously as background daemon")
    parser.add_argument("--once", action="store_true", help="Run a single trading turn and exit")
    parser.add_argument("--ticker", default="SPY", help="Ticker symbol to trade (default: SPY)")
    parser.add_argument("--interval", type=int, default=300, help="Cadence in seconds (default: 300)")
    parser.add_argument(
        "--tape-interval",
        type=int,
        default=20,
        help="Tape polling cadence in seconds (default: 20)",
    )
    parser.add_argument(
        "--tape-port",
        type=int,
        default=8090,
        help="Port for SSE tape server (default: 8090)",
    )
    parser.add_argument(
        "--no-tape-server",
        action="store_true",
        help="Disable the SSE tape server",
    )
    parser.add_argument(
        "--no-24-7",
        action="store_true",
        help="Disable 24/7 off-hours loop (sleep when regular market closes)",
    )
    parser.add_argument(
        "--strata-url",
        default=os.getenv("STRATA_BASE_URL", DEFAULT_STRATA_URL),
        help="Tier 1 Strata LLM endpoint",
    )
    parser.add_argument(
        "--cheap-proxy-url",
        default=os.getenv("FREE_LLM_PROXY_URL", DEFAULT_CHEAP_PROXY_URL),
        help="Tier 2 Centralized CLVG fallback endpoint",
    )

    args = parser.parse_args()

    if args.once:
        data_client, trading_client, sb_client = _create_clients()
        result = asyncio.run(
            run_daemon_turn(
                alpaca_data_client=data_client,
                alpaca_trading_client=trading_client,
                sb_client=sb_client,
                ticker=args.ticker,
                strata_url=args.strata_url,
                cheap_proxy_url=args.cheap_proxy_url,
            )
        )
        print(
            f"Executed single turn for {args.ticker}: {result.get('action')} (Conviction: {result.get('conviction')}%)"
        )
    else:
        asyncio.run(
            run_loop(
                ticker=args.ticker,
                interval_seconds=args.interval,
                tape_interval_seconds=args.tape_interval,
                tape_port=args.tape_port,
                enable_tape_server=not args.no_tape_server,
                strata_url=args.strata_url,
                cheap_proxy_url=args.cheap_proxy_url,
                continuous_24_7=not args.no_24_7,
            )
        )


if __name__ == "__main__":
    main()
