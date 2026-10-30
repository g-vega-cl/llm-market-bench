"""Continuous runner and daemon coordinator for the autonomous intraday trader.

Polls active tape, executes 5-minute reasoning turns via local Strata with fallback
to the centralized CLVG proxy, routes paper orders to Alpaca, and respects US regular
market session hours.
"""

from __future__ import annotations

import argparse
import asyncio
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


async def run_loop(
    ticker: str = "SPY",
    interval_seconds: int = 300,
    strata_url: str = DEFAULT_STRATA_URL,
    cheap_proxy_url: str = DEFAULT_CHEAP_PROXY_URL,
    continuous_24_7: bool = True,
) -> None:
    """Run the continuous 24/7 daemon loop."""
    logger.info(
        f"Starting Live SPY Trader Daemon (ticker={ticker}, interval={interval_seconds}s, 24/7={continuous_24_7})"
    )
    logger.info(f"Tier 1 Inference: {strata_url}")
    logger.info(f"Tier 2 Inference: {cheap_proxy_url}")

    data_client, trading_client, sb_client = _create_clients()

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


def main() -> None:
    """CLI entrypoint for running the intraday agent trader."""
    parser = argparse.ArgumentParser(description="Live Intraday SPY Trader Daemon")
    parser.add_argument("--loop", action="store_true", help="Run continuously as background daemon")
    parser.add_argument("--once", action="store_true", help="Run a single trading turn and exit")
    parser.add_argument("--ticker", default="SPY", help="Ticker symbol to trade (default: SPY)")
    parser.add_argument("--interval", type=int, default=300, help="Cadence in seconds (default: 300)")
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
                strata_url=args.strata_url,
                cheap_proxy_url=args.cheap_proxy_url,
                continuous_24_7=not args.no_24_7,
            )
        )


if __name__ == "__main__":
    main()
