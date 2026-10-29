"""30-minute comprehensive live trader audit harness.

Executes consecutive 5-minute turns against live market feeds (Alpaca, Benzinga,
Polygon, FMP stable, Supabase, and multi-tier LLM inference), recording metrics,
latencies, decision fidelity, and database persistence.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from dotenv import load_dotenv

# Ensure repo root and apps/engine are in path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENGINE_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
REPO_ROOT = os.path.abspath(os.path.join(ENGINE_ROOT, "../.."))
if ENGINE_ROOT not in sys.path:
    sys.path.insert(0, ENGINE_ROOT)

load_dotenv(os.path.join(ENGINE_ROOT, ".env"))

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
from trading.runner import is_market_session_active


def _init_clients() -> tuple[Any, Any, Any]:
    """Initialize Alpaca and Supabase clients."""
    data_client = None
    trading_client = None

    if ALPACA_API_KEY and ALPACA_SECRET_KEY:
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.trading.client import TradingClient

        data_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)
        trading_client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)

    sb_client = get_supabase_client()
    return data_client, trading_client, sb_client


async def run_single_audit_turn(
    turn_idx: int,
    total_turns: int,
    ticker: str,
    data_client: Any,
    trading_client: Any,
    sb_client: Any,
    http_client: httpx.AsyncClient,
    strata_url: str,
    cheap_proxy_url: str,
) -> dict[str, Any]:
    """Execute one instrumented audit turn and collect granular metrics."""
    now_et = datetime.now(ZoneInfo("America/New_York"))
    now_utc = datetime.now(UTC)
    time_str = now_et.strftime("%H:%M:%S ET")

    print(f"\n[{turn_idx}/{total_turns}] ════ Starting 5-Minute Turn at {time_str} ════")

    # 1. Active Candle
    t0_candle = time.perf_counter()
    active_candle = await fetch_active_candle(data_client, ticker=ticker)
    dur_candle_ms = (time.perf_counter() - t0_candle) * 1000

    last_price = active_candle.get("close") if active_candle else "N/A"
    candle_time = active_candle.get("time") if active_candle else "N/A"
    print(f"  • Tape: {ticker} Price=${last_price} (Bar: {candle_time}, Fetch: {dur_candle_ms:.1f}ms)")

    # 2. Execute Full Trading Step
    t0_step = time.perf_counter()
    step_result = await execute_intraday_agent_step(
        alpaca_data_client=data_client,
        alpaca_trading_client=trading_client,
        sb_client=sb_client,
        http_client=http_client,
        ticker=ticker,
        strata_url=strata_url,
        cheap_proxy_url=cheap_proxy_url,
    )
    dur_step = time.perf_counter() - t0_step

    action = step_result.get("action", "HOLD")
    conviction = step_result.get("conviction", 50)
    thought = step_result.get("thought", "")
    order_id = step_result.get("order_id")
    technicals = step_result.get("technicals", {})

    print(f"  • Decision: Action={action} | Conviction={conviction}% | Turn Latency={dur_step:.2f}s")
    print(
        f"  • Technicals: VWAP=${technicals.get('vwap')} | RSI-14={technicals.get('rsi_14')} | Trend={technicals.get('trend')}"
    )
    print(f'  • Rationale: "{thought[:140]}..."' if len(thought) > 140 else f'  • Rationale: "{thought}"')
    if order_id:
        print(f"  • Order Placed: Alpaca Order ID {order_id}")

    # 3. Verify Database Persistence
    t0_db = time.perf_counter()
    db_ok = False
    try:
        latest = (
            sb_client.table("market_feeling")
            .select("id, created_at, market_direction, sentiment_label, model_used")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if latest.data:
            rec = latest.data[0]
            db_ok = True
            dur_db_ms = (time.perf_counter() - t0_db) * 1000
            print(f"  • Supabase Verification: ID={rec.get('id')} ({rec.get('sentiment_label')}, {dur_db_ms:.1f}ms)")
    except Exception as e:
        print(f"  • Supabase Verification Failed: {e}")

    return {
        "turn": turn_idx,
        "timestamp_et": now_et.isoformat(),
        "timestamp_utc": now_utc.isoformat(),
        "ticker": ticker,
        "active_candle": active_candle,
        "step_duration_seconds": round(dur_step, 2),
        "action": action,
        "conviction": conviction,
        "thought": thought,
        "order_id": order_id,
        "technicals": technicals,
        "db_verified": db_ok,
    }


async def run_30min_audit(
    total_minutes: int = 30,
    turn_interval: int = 300,
    ticker: str = "SPY",
    output_path: str = "audit_30min_results.json",
    strata_url: str = DEFAULT_STRATA_URL,
    cheap_proxy_url: str = DEFAULT_CHEAP_PROXY_URL,
) -> list[dict[str, Any]]:
    """Run consecutive turns across the audit window."""
    total_turns = max(1, total_minutes * 60 // turn_interval)

    print("═════════════════════════════════════════════════════════════════")
    print("  30-MINUTE AUTONOMOUS TRADER AUDIT HARNESS")
    print(f"  Duration: {total_minutes}m ({total_turns} turns @ {turn_interval}s interval)")
    print(f"  Ticker: {ticker} | Regular Market Hours: {is_market_session_active()}")
    print(f"  Tier 1 Strata: {strata_url}")
    print(f"  Tier 2 Free Proxy: {cheap_proxy_url}")
    print("═════════════════════════════════════════════════════════════════")

    data_client, trading_client, sb_client = _init_clients()
    results: list[dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=35.0) as http_client:
        for turn_idx in range(1, total_turns + 1):
            try:
                turn_res = await run_single_audit_turn(
                    turn_idx=turn_idx,
                    total_turns=total_turns,
                    ticker=ticker,
                    data_client=data_client,
                    trading_client=trading_client,
                    sb_client=sb_client,
                    http_client=http_client,
                    strata_url=strata_url,
                    cheap_proxy_url=cheap_proxy_url,
                )
                results.append(turn_res)

                # Save intermediate results
                with open(output_path, "w") as f:
                    json.dump(results, f, indent=2)

            except Exception:
                logger.exception(f"Turn {turn_idx} encountered an unhandled exception")
                results.append(
                    {
                        "turn": turn_idx,
                        "timestamp_utc": datetime.now(UTC).isoformat(),
                        "error": "Unhandled exception in turn",
                    }
                )

            if turn_idx < total_turns:
                print(f"\n  Sleeping {turn_interval}s until next turn...")
                await asyncio.sleep(float(turn_interval))

    # Print Summary Table
    print("\n═════════════════════════════════════════════════════════════════")
    print(f"  30-MINUTE AUDIT COMPLETE ({len(results)} turns recorded)")
    print("═════════════════════════════════════════════════════════════════")
    print(f"{'Turn':<6}{'Time ET':<12}{'Price':<10}{'Trend':<10}{'Action':<8}{'Conv':<6}{'Latency':<10}{'DB':<6}")
    print("─────────────────────────────────────────────────────────────────")
    for r in results:
        t_et = r.get("timestamp_et", "")
        time_display = t_et[11:19] if len(t_et) >= 19 else "N/A"
        price = r.get("active_candle", {}).get("close", "N/A") if r.get("active_candle") else "N/A"
        price_str = f"${price:.2f}" if isinstance(price, (int, float)) else str(price)
        trend = r.get("technicals", {}).get("trend", "N/A")
        act = r.get("action", "ERR")
        conv = f"{r.get('conviction', 0)}%"
        lat = f"{r.get('step_duration_seconds', 0.0):.2f}s"
        db = "OK" if r.get("db_verified") else "FAIL"
        print(f"{r.get('turn', 0):<6}{time_display:<12}{price_str:<10}{trend:<10}{act:<8}{conv:<6}{lat:<10}{db:<6}")

    print("─────────────────────────────────────────────────────────────────")
    print(f"Results persisted to: {output_path}")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="30-Minute Live Trader Audit Harness")
    parser.add_argument("--total-minutes", type=int, default=30, help="Total audit duration in minutes (default: 30)")
    parser.add_argument("--turn-interval", type=int, default=300, help="Seconds between turns (default: 300)")
    parser.add_argument("--ticker", default="SPY", help="Ticker symbol (default: SPY)")
    parser.add_argument("--output", default="audit_30min_results.json", help="Output JSON path")
    parser.add_argument("--strata-url", default=DEFAULT_STRATA_URL, help="Tier 1 Strata URL")
    parser.add_argument("--cheap-proxy-url", default=DEFAULT_CHEAP_PROXY_URL, help="Tier 2 Proxy URL")

    args = parser.parse_args()

    asyncio.run(
        run_30min_audit(
            total_minutes=args.total_minutes,
            turn_interval=args.turn_interval,
            ticker=args.ticker,
            output_path=args.output,
            strata_url=args.strata_url,
            cheap_proxy_url=args.cheap_proxy_url,
        )
    )


if __name__ == "__main__":
    main()
