"""Continuous runner and daemon coordinator for the autonomous intraday trader.

Polls active tape, executes 5-minute reasoning turns directly via the centralized CLVG
proxy (`auto-go`), routes paper orders to Alpaca, and respects US regular market session hours.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import time
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from core.config import (
    ALPACA_API_KEY,
    ALPACA_ENABLED,
    ALPACA_SECRET_KEY,
    logger,
)
from core.db import get_supabase_client
from execution.alpaca_broker import AlpacaBroker
from trading.conversational_explainer import process_pending_queue_item
from trading.live_intraday_agent import (
    DEFAULT_CHEAP_PROXY_URL,
    DEFAULT_STRATA_URL,
    execute_intraday_agent_step,
    fetch_active_candle,
    fetch_intraday_bars,
    query_multi_tier_llm,
    set_latest_news_synthesis,
)
from trading.market_calendar import configure_market_calendar, get_market_calendar
from trading.tape_stream import (
    TapeBroadcaster,
    seed_broadcaster_from_db,
    start_tape_server,
    update_latest_tape_in_db,
)


def is_market_session_active(now_dt: datetime | None = None) -> bool:
    """Check if the current time falls within US regular equity market hours.

    Delegates to the configured MarketCalendar: Alpaca's /v2/clock when a client
    is wired (holidays, half-days, ad-hoc closures), weekday/time arithmetic
    otherwise. A client whose clock cannot be read counts as closed.
    """
    return get_market_calendar().is_open(now_dt)


def calculate_seconds_to_market_open(now_dt: datetime | None = None) -> float:
    """Seconds until the next regular session open (holiday-aware when wired)."""
    return get_market_calendar().seconds_to_next_open(now_dt)


async def run_daemon_turn(
    alpaca_data_client: Any = None,
    alpaca_broker: Any = None,
    sb_client: Any = None,
    http_client: httpx.AsyncClient | None = None,
    ticker: str = "SPY",
    strata_url: str = DEFAULT_STRATA_URL,
    cheap_proxy_url: str = DEFAULT_CHEAP_PROXY_URL,
    is_market_open: bool = True,
) -> dict[str, Any]:
    """Execute a single intraday agent cycle: active candle poll + trading step."""
    active_candle = await fetch_active_candle(alpaca_data_client, ticker=ticker)

    step_result = await execute_intraday_agent_step(
        alpaca_data_client=alpaca_data_client,
        alpaca_broker=alpaca_broker,
        sb_client=sb_client,
        http_client=http_client,
        ticker=ticker,
        strata_url=strata_url,
        cheap_proxy_url=cheap_proxy_url,
        is_market_open=is_market_open,
    )

    return {
        **step_result,
        "active_candle": active_candle,
    }


def _create_clients() -> tuple[Any, Any, Any]:
    """Instantiate the Alpaca data client, the paper broker, and the Supabase client.

    The trading client is constructed here — once, with `paper=True`, and only when
    `ALPACA_ENABLED` — then injected. Constructing it inside AlpacaBroker instead would
    skip the kill switch, because the broker returns early on an injected-or-built client
    before it checks `ALPACA_ENABLED`. AlpacaBroker's own construction path is still used
    by the other trading callers, so this makes the daemon's path explicit rather than
    eliminating the duplication repo-wide.
    """
    data_client = None
    trading_client = None

    if ALPACA_API_KEY and ALPACA_SECRET_KEY:
        try:
            from alpaca.data.historical import StockHistoricalDataClient

            data_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)
        except Exception:
            logger.exception("Failed to initialize Alpaca data client")

        if ALPACA_ENABLED:
            try:
                from alpaca.trading.client import TradingClient

                trading_client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)
            except Exception:
                logger.exception("Failed to initialize Alpaca trading client; mirror will report DISABLED")

    sb_client = get_supabase_client()
    return data_client, AlpacaBroker(client=trading_client, sb_client=sb_client), sb_client


async def run_tape_poller_loop(
    alpaca_data_client: Any,
    sb_client: Any,
    broadcaster: TapeBroadcaster,
    ticker: str = "SPY",
    tape_interval_seconds: int = 10,
) -> None:
    """Continuously poll active tape from Alpaca, push to broadcaster, and update DB."""
    logger.info(f"Starting tape poller loop for {ticker} (interval={tape_interval_seconds}s)")
    if sb_client:
        try:
            await seed_broadcaster_from_db(sb_client, broadcaster)
        except Exception:
            logger.debug("Initial tape broadcaster DB seed failed", exc_info=True)

    while True:
        try:
            if alpaca_data_client and await asyncio.to_thread(is_market_session_active):
                bars = await fetch_intraday_bars(alpaca_data_client, ticker=ticker, window_minutes=60)
                if bars:
                    broadcaster.publish_bars(bars)
                    await update_latest_tape_in_db(sb_client, bars)
            elif not broadcaster.latest_bars and sb_client:
                # Outside market hours, ensure initial snapshot is seeded
                await seed_broadcaster_from_db(sb_client, broadcaster)
            broadcaster.record_loop_ok("tape", tape_interval_seconds)
        except Exception as exc:
            logger.exception("Error in tape poller loop")
            broadcaster.record_loop_error("tape", type(exc).__name__, tape_interval_seconds)
        await asyncio.sleep(float(tape_interval_seconds))


async def _run_agent_loop(
    ticker: str,
    interval_seconds: int,
    strata_url: str,
    cheap_proxy_url: str,
    continuous_24_7: bool,
    data_client: Any,
    broker: Any,
    sb_client: Any,
    broadcaster: TapeBroadcaster | None = None,
) -> None:
    """Run the 5-minute autonomous LLM reasoning turn loop."""
    async with httpx.AsyncClient(timeout=90.0) as http_client:
        while True:
            try:
                is_open = await asyncio.to_thread(is_market_session_active)
                if not is_open and not continuous_24_7:
                    secs_to_open = await asyncio.to_thread(calculate_seconds_to_market_open)
                    sleep_dur = min(secs_to_open, 300.0)
                    logger.info(
                        f"Regular market closed. Sleeping {sleep_dur:.0f}s (next open in {secs_to_open / 3600:.1f}h)"
                    )
                    if broadcaster:
                        broadcaster.record_loop_ok("agent", sleep_dur)
                    await asyncio.sleep(sleep_dur)
                    continue

                # In 24/7 off-hours mode, trading is disabled (paper orders skipped) but Q&A and analysis run
                effective_broker = broker if is_open else None
                mode_str = "Market open" if is_open else "24/7 Off-hours"
                logger.info(f"{mode_str}. Running evaluation turn for {ticker}...")
                turn_result = await run_daemon_turn(
                    alpaca_data_client=data_client,
                    alpaca_broker=effective_broker,
                    sb_client=sb_client,
                    http_client=http_client,
                    ticker=ticker,
                    strata_url=strata_url,
                    cheap_proxy_url=cheap_proxy_url,
                    is_market_open=is_open,
                )
                logger.info(
                    f"Turn complete: Action={turn_result.get('action')} Conviction={turn_result.get('conviction')}%"
                )

                if broadcaster:
                    action = turn_result.get("action", "HOLD")
                    agent_turn_payload = {
                        "action": action,
                        "conviction": turn_result.get("conviction", 50),
                        "thought": turn_result.get("thought", ""),
                        "marketDirection": "BULLISH"
                        if action == "BUY"
                        else "BEARISH"
                        if action == "SELL"
                        else "NEUTRAL",
                        "sentimentLabel": "Accumulating Dips"
                        if action == "BUY"
                        else "Defensive Cash"
                        if action == "HOLD"
                        else "Reducing Risk",
                        "lastUpdated": datetime.now(ZoneInfo("America/New_York")).strftime("%H:%M ET"),
                        "technicals": turn_result.get("technicals"),
                        "portfolio": turn_result.get("portfolio"),
                    }
                    broadcaster.publish_agent_turn(agent_turn_payload)
                    broadcaster.record_loop_ok("agent", interval_seconds)
            except Exception as exc:
                logger.exception("Unexpected error in daemon turn loop")
                if broadcaster:
                    broadcaster.record_loop_error("agent", type(exc).__name__, interval_seconds)

            await asyncio.sleep(float(interval_seconds))


async def run_qa_worker_loop(
    sb_client: Any,
    strata_url: str = DEFAULT_STRATA_URL,
    cheap_proxy_url: str = DEFAULT_CHEAP_PROXY_URL,
    interval_seconds: int = 300,
    broadcaster: TapeBroadcaster | None = None,
) -> None:
    """Run the 5-minute background worker answering audience questions with conversational explainer."""
    logger.info(f"Starting Conversational Desk QA worker loop (interval={interval_seconds}s)")
    async with httpx.AsyncClient(timeout=120.0) as http_client:
        while True:
            try:
                if sb_client:
                    result = await process_pending_queue_item(
                        sb_client=sb_client,
                        http_client=http_client,
                        strata_url=strata_url,
                        cheap_proxy_url=cheap_proxy_url,
                    )
                    if result:
                        logger.info(
                            f"Answered audience inquiry from @{result.get('author')}: {result.get('message', '')[:60]}"
                        )
                if broadcaster:
                    broadcaster.record_loop_ok("qa", interval_seconds)
            except Exception as exc:
                logger.exception("Unexpected error in QA worker loop")
                if broadcaster:
                    broadcaster.record_loop_error("qa", type(exc).__name__, interval_seconds)

            await asyncio.sleep(float(interval_seconds))


async def synthesize_recent_news(
    sb_client: Any = None,
    http_client: httpx.AsyncClient | None = None,
    strata_url: str = DEFAULT_STRATA_URL,
    cheap_proxy_url: str = DEFAULT_CHEAP_PROXY_URL,
    limit: int = 15,
) -> str | None:
    """Synthesize recent breaking news items into a concise market intelligence brief.

    Uses Tier 1 (local Strata) with fallback to Tier 2 (auto-strata free proxy).
    Updates market_feeling.news_summary with the resulting text.
    """
    sb = sb_client or get_supabase_client()
    if not sb:
        return None

    try:
        resp = (
            sb.table("intraday_market_news")
            .select("headline, source, event_timestamp")
            .eq("jev_choice", "MARKET_MOVING")
            .order("event_timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        news_rows = resp.data or []
    except Exception as e:
        logger.warning(f"Failed to fetch recent intraday news for synthesis: {e}")
        return None

    if not news_rows:
        return None

    bullets = "\n".join(
        [f"- [{r.get('source', 'Wire')}] {r.get('headline', '').strip()}" for r in news_rows if r.get("headline")]
    )
    if not bullets:
        return None

    prompt = (
        "You are an institutional macro research analyst. "
        "Synthesize the following recent breaking market news and macro headlines into a concise 2-3 sentence "
        "intelligence summary highlighting dominant market themes, sector rotation, or immediate risk catalysts. "
        "Avoid fluff or buzzwords; be direct, factual, and quantitative.\n\n"
        f"### BREAKING HEADLINES (LAST 30 MINUTES):\n{bullets}\n\n"
        "Summary:"
    )

    summary_text = await query_multi_tier_llm(
        messages=[
            {"role": "system", "content": "You are a concise institutional market analyst."},
            {"role": "user", "content": prompt},
        ],
        strata_url=strata_url,
        cheap_proxy_url=cheap_proxy_url,
        http_client=http_client,
        max_tokens=4096,
        purpose="homepage-news-synthesis",
    )

    clean_summary = summary_text.strip().strip('"').strip("'")
    if not clean_summary or "All LLM endpoints currently unavailable" in clean_summary:
        return None

    set_latest_news_synthesis(clean_summary)

    try:
        latest_feeling = sb.table("market_feeling").select("id").order("created_at", desc=True).limit(1).execute()
        if latest_feeling.data:
            fid = latest_feeling.data[0]["id"]
            sb.table("market_feeling").update({"news_summary": clean_summary}).eq("id", fid).execute()
            logger.info(f"Updated market_feeling id={fid} with fresh 30m AI news synthesis.")
    except Exception as e:
        logger.warning(f"Failed to update latest market_feeling with news summary: {e}")

    return clean_summary


async def run_news_synthesis_worker_loop(
    sb_client: Any,
    strata_url: str = DEFAULT_STRATA_URL,
    cheap_proxy_url: str = DEFAULT_CHEAP_PROXY_URL,
    interval_seconds: int = 1800,
    broadcaster: TapeBroadcaster | None = None,
) -> None:
    """Run the 30-minute background worker synthesizing recent breaking news using auto-strata."""
    logger.info(f"Starting 30-minute AI News Synthesis worker loop (interval={interval_seconds}s)")
    async with httpx.AsyncClient(timeout=90.0) as http_client:
        while True:
            try:
                if sb_client:
                    summary = await synthesize_recent_news(
                        sb_client=sb_client,
                        http_client=http_client,
                        strata_url=strata_url,
                        cheap_proxy_url=cheap_proxy_url,
                    )
                    if summary:
                        logger.info(f"AI News Synthesis complete: {summary[:80]}...")
                if broadcaster:
                    broadcaster.record_loop_ok("news", interval_seconds)
            except Exception as exc:
                logger.exception("Unexpected error in news synthesis worker loop")
                if broadcaster:
                    broadcaster.record_loop_error("news", type(exc).__name__, interval_seconds)

            await asyncio.sleep(float(interval_seconds))


def _is_price_refresh_window(now_dt: datetime | None = None) -> bool:
    """Regular session plus the post-close print window, from the exchange calendar.

    Same window as the strategy hooks: marks and the closing print both belong to
    a real session day, so holidays and half days are excluded identically.
    """
    return _is_hooks_window(now_dt)


def _is_hooks_window(now_dt: datetime | None = None) -> bool:
    """True inside the regular session, plus the closing-print tail.

    Derived from the exchange calendar rather than the clock: strategies need
    "is today a session day and when does it close", which /v2/clock cannot
    answer after the bell (is_open is already False at 16:01 while the daily
    picks legs still exit on the official closing print at 16:00-16:05).
    Holidays return no session, so no hook runs; half days end at 13:00 and the
    tail moves with them.
    """
    now_dt = now_dt or datetime.now(ZoneInfo("America/New_York"))
    if now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=ZoneInfo("America/New_York"))
    session = get_market_calendar().session_for(now_dt.date())
    if session is None:
        return False
    open_at, close_at = session
    return open_at <= now_dt <= close_at + timedelta(minutes=5)


async def run_systematic_hooks_loop(
    interval_seconds: int = 300,
    strategy_lock: asyncio.Lock | None = None,
    broadcaster: TapeBroadcaster | None = None,
) -> None:
    """Run every time-gated systematic strategy hook while the market is open.

    This daemon is the single owner of deterministic strategy execution. The price
    update script no longer invokes the hooks, so max pain, PEAD, the sentiment fader
    and the sector/horizon exits can never be executed by two callers at once.
    """
    from scripts.update_prices import run_systematic_strategy_hooks

    lock = strategy_lock or asyncio.Lock()
    logger.info(f"Starting systematic strategy hooks loop (interval={interval_seconds}s)")
    while True:
        try:
            now_et = datetime.now(ZoneInfo("America/New_York"))
            if await asyncio.to_thread(_is_hooks_window, now_et):
                async with lock:
                    await run_systematic_strategy_hooks(now_et)
            if broadcaster:
                broadcaster.record_loop_ok("hooks", interval_seconds)
        except Exception as exc:
            logger.exception("Systematic strategy hooks loop failed")
            if broadcaster:
                broadcaster.record_loop_error("hooks", type(exc).__name__, interval_seconds)
        await asyncio.sleep(float(interval_seconds))


async def run_market_data_loop(
    interval_seconds: int = 900,
    history_interval_seconds: int = 1800,
    strategy_lock: asyncio.Lock | None = None,
    broadcaster: TapeBroadcaster | None = None,
) -> None:
    """Refresh portfolio marks on every tick and benchmark/macro history less often.

    Marks are cheap (one batch quote plus one snapshot per portfolio); rebuilding
    90-day histories for every benchmark and macro ticker is not, so it runs at its
    own slower cadence. Both share the strategy lock so a mark never snapshots a
    portfolio mid-execution.
    """
    from execution.market_data import MarketDataManager
    from scripts.update_prices import fetch_benchmark_history, refresh_portfolio_marks

    lock = strategy_lock or asyncio.Lock()
    sb_client = get_supabase_client()
    mdm = MarketDataManager()
    # `None` means "never refreshed this process". Seeding with 0.0 compares the
    # interval against seconds-since-boot, so a freshly booted host (CI runner)
    # would skip the first history refresh for up to history_interval_seconds.
    last_history_at: float | None = None
    logger.info(f"Starting market data loop (marks={interval_seconds}s, history={history_interval_seconds}s)")
    while True:
        try:
            now_et = datetime.now(ZoneInfo("America/New_York"))
            if await asyncio.to_thread(_is_price_refresh_window, now_et):
                async with lock:
                    await refresh_portfolio_marks(sb_client, mdm)
                if last_history_at is None or (time.monotonic() - last_history_at) >= history_interval_seconds:
                    await fetch_benchmark_history(mdm)
                    last_history_at = time.monotonic()
            if broadcaster:
                broadcaster.record_loop_ok("marks", interval_seconds)
        except Exception as exc:
            logger.exception("Market data loop failed")
            if broadcaster:
                broadcaster.record_loop_error("marks", type(exc).__name__, interval_seconds)
        await asyncio.sleep(float(interval_seconds))


async def run_loop(
    ticker: str = "SPY",
    interval_seconds: int = 300,
    tape_interval_seconds: int = 10,
    news_interval_seconds: int = 1800,
    marks_interval_seconds: int = 900,
    history_interval_seconds: int = 1800,
    tape_port: int = 8090,
    enable_tape_server: bool = True,
    strata_url: str = DEFAULT_STRATA_URL,
    cheap_proxy_url: str = DEFAULT_CHEAP_PROXY_URL,
    continuous_24_7: bool = True,
) -> None:
    """Run the continuous 24/7 daemon loop with concurrent 10s tape polling, 5m trader, & 5m QA worker."""
    logger.info(
        f"Starting Live SPY Trader Daemon (ticker={ticker}, interval={interval_seconds}s, tape_interval={tape_interval_seconds}s, 24/7={continuous_24_7})"
    )
    logger.info(f"LLM Inference: {cheap_proxy_url} (model={os.getenv('FREE_PROXY_MODEL', 'auto-go')})")

    data_client, broker, sb_client = _create_clients()
    configure_market_calendar(getattr(broker, "client", None))
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
                broker=broker,
                sb_client=sb_client,
                broadcaster=broadcaster,
            )
        )
        qa_task = asyncio.create_task(
            run_qa_worker_loop(
                sb_client=sb_client,
                strata_url=strata_url,
                cheap_proxy_url=cheap_proxy_url,
                interval_seconds=interval_seconds,
                broadcaster=broadcaster,
            )
        )
        news_synth_task = asyncio.create_task(
            run_news_synthesis_worker_loop(
                sb_client=sb_client,
                strata_url=strata_url,
                cheap_proxy_url=cheap_proxy_url,
                interval_seconds=news_interval_seconds,
                broadcaster=broadcaster,
            )
        )
        strategy_lock = asyncio.Lock()
        systematic_task = asyncio.create_task(
            run_systematic_hooks_loop(
                interval_seconds=interval_seconds,
                strategy_lock=strategy_lock,
                broadcaster=broadcaster,
            )
        )
        market_data_task = asyncio.create_task(
            run_market_data_loop(
                interval_seconds=marks_interval_seconds,
                history_interval_seconds=history_interval_seconds,
                strategy_lock=strategy_lock,
                broadcaster=broadcaster,
            )
        )
        await asyncio.gather(
            tape_task,
            agent_task,
            qa_task,
            news_synth_task,
            systematic_task,
            market_data_task,
        )
    finally:
        if server:
            server.close()
            try:
                await server.wait_closed()
            except Exception:
                logger.debug("Error waiting for tape server close", exc_info=True)


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
        default=10,
        help="Tape polling cadence in seconds (default: 10)",
    )
    parser.add_argument(
        "--news-interval",
        type=int,
        default=1800,
        help="Cadence for AI news synthesis in seconds (default: 1800)",
    )
    parser.add_argument(
        "--marks-interval",
        type=int,
        default=900,
        help="Cadence for portfolio quotes/marks in seconds (default: 900)",
    )
    parser.add_argument(
        "--history-interval",
        type=int,
        default=1800,
        help="Cadence for benchmark/macro history refresh in seconds (default: 1800)",
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
        data_client, broker, sb_client = _create_clients()
        configure_market_calendar(getattr(broker, "client", None))
        result = asyncio.run(
            run_daemon_turn(
                alpaca_data_client=data_client,
                alpaca_broker=broker,
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
                news_interval_seconds=args.news_interval,
                marks_interval_seconds=args.marks_interval,
                history_interval_seconds=args.history_interval,
                tape_port=args.tape_port,
                enable_tape_server=not args.no_tape_server,
                strata_url=args.strata_url,
                cheap_proxy_url=args.cheap_proxy_url,
                continuous_24_7=not args.no_24_7,
            )
        )


if __name__ == "__main__":
    main()
