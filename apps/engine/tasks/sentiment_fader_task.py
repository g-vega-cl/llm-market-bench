"""Contrarian Options Sentiment Fader Scheduled Task.

Executes the Sentiment Fader systematic strategy:
1. Gathers options sentiment snapshots (Put/Call volume ratio, OI ratio, skew) for liquid index ETFs (SPY, QQQ).
2. Detects extreme crowd panic (Put/Call Volume Ratio >= 1.30) to generate oversold bounce entries.
3. Detects extreme euphoria (Put/Call Volume Ratio <= 0.60), stop-loss breaches (1.5%), or 3-day max holding horizon for exits.
4. Executes rebalance orders against `sys-sentiment-fader` portfolio with 1 bps friction.
"""

import argparse
import asyncio
import os
import sys
from datetime import UTC, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

# Ensure apps/engine is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import logger
from core.db import async_with_retry, get_supabase_client
from execution.market_data import MarketDataManager
from execution.portfolio import Portfolio
from execution.providers.massive import (
    MassiveOptionsClient,
    calculate_options_sentiment,
)
from execution.sentiment_fader import (
    DEFAULT_EUPHORIA_THRESHOLD_PC,
    DEFAULT_FADER_MAX_HOLDING_DAYS,
    DEFAULT_FADER_SLIPPAGE_BPS,
    DEFAULT_FADER_STOP_LOSS_PCT,
    DEFAULT_PANIC_THRESHOLD_PC,
    DEFAULT_SENTIMENT_UNIVERSE,
    SYS_SENTIMENT_FADER_OWNER_ID,
    compute_sentiment_fader_rebalance_orders,
    evaluate_sentiment_holding_exit,
    evaluate_sentiment_signal,
)


async def fetch_ticker_price(ticker: str) -> float:
    """Fetch current price for a ticker using MarketDataManager."""
    try:
        manager = MarketDataManager()
        quote = await manager.get_quote(ticker)
        if quote and quote.exists and quote.price > 0:
            return float(quote.price)
    except Exception as e:
        logger.debug(f"Failed to fetch price for {ticker}: {e}")
    return 0.0


async def fetch_sentiment_snapshot(
    ticker: str,
    current_price: float | None = None,
    client: MassiveOptionsClient | None = None,
) -> dict[str, Any] | None:
    """Fetch and calculate options sentiment metrics for a ticker."""
    try:
        massive_client = client or MassiveOptionsClient()
        snapshot = await massive_client.get_options_snapshot(ticker, current_price=current_price)
        if snapshot.get("status") != "OK" or not snapshot.get("contracts"):
            logger.info(f"Sentiment Fader skip {ticker}: no options data returned")
            return None

        contracts = snapshot.get("contracts", [])
        metrics = calculate_options_sentiment(ticker, contracts, current_price=current_price)
        if metrics:
            metrics["pv_ratio"] = metrics.get("put_call_volume_ratio")
        return metrics
    except Exception as e:
        logger.warning(f"Failed to fetch options snapshot for {ticker}: {e}")
        return None


async def _load_recent_trade_state(portfolio_id: str) -> tuple[dict[str, int], set[str]]:
    """Load holding days per ticker and same-day ET exited tickers in a single query.

    Fails closed (raises) if the trade ledger cannot be read so intraday ticks never
    bypass stop-loss re-entry cooldown or holding-horizon checks on transient DB errors.
    """
    if not portfolio_id:
        return {}, set()

    sb = get_supabase_client()
    now_utc = datetime.now(UTC)
    now_et = now_utc.astimezone(ZoneInfo("America/New_York"))
    start_of_day_utc = datetime.combine(now_et.date(), time.min, tzinfo=ZoneInfo("America/New_York")).astimezone(UTC)

    res = await async_with_retry(
        lambda: (
            sb.table("trades")
            .select("ticker, signal, executed_at")
            .eq("portfolio_id", portfolio_id)
            .order("executed_at", desc=True)
            .limit(500)
            .execute()
        ),
        f"sentiment_fader_trade_state_{portfolio_id}",
    )

    rows = res.data if isinstance(res.data, list) else []
    holding_days: dict[str, int] = {}
    same_day_exited: set[str] = set()

    for row in rows:
        if not isinstance(row, dict):
            continue
        sym = str(row.get("ticker") or "").upper()
        sig = str(row.get("signal") or "").upper()
        raw_ts = row.get("executed_at")
        if not sym or not raw_ts:
            continue

        exec_time = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
        if exec_time.tzinfo is None:
            exec_time = exec_time.replace(tzinfo=UTC)

        if sig == "BUY" and sym not in holding_days:
            holding_days[sym] = max(0, (now_utc - exec_time).days)
        elif sig == "SELL" and exec_time >= start_of_day_utc:
            same_day_exited.add(sym)

    return holding_days, same_day_exited


async def _gather_universe_data(
    tickers: tuple[str, ...] | list[str], massive_client: MassiveOptionsClient
) -> tuple[dict[str, float], dict[str, dict[str, Any]]]:
    """Fetch current spot prices and options sentiment snapshots for the universe."""
    current_prices: dict[str, float] = {}
    sentiment_cache: dict[str, dict[str, Any]] = {}
    for raw_sym in tickers:
        sym = str(raw_sym).upper()
        price = await fetch_ticker_price(sym)
        if price > 0:
            current_prices[sym] = price
            sent = await fetch_sentiment_snapshot(sym, current_price=price, client=massive_client)
            if sent:
                sentiment_cache[sym] = sent
    return current_prices, sentiment_cache


def _evaluate_holdings(
    positions: dict[str, Any],
    current_prices: dict[str, float],
    sentiment_cache: dict[str, dict[str, Any]],
    holding_days_by_ticker: dict[str, int],
    *,
    stop_loss_pct: float,
    max_holding_days: int,
    euphoria_threshold: float,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Evaluate exit rules across all currently held positions.

    Fails closed (raises ValueError) if any held ticker lacks a positive live spot price
    so positions are never liquidated or marked at historical cost basis.
    """
    current_holdings: list[dict[str, Any]] = []
    holding_evaluations: dict[str, dict[str, Any]] = {}

    for sym_key, pos in positions.items():
        sym = str(sym_key).upper()
        spot_px = current_prices.get(sym, 0.0)
        if spot_px <= 0:
            raise ValueError(f"Missing live spot price for held position {sym}")

        holding_info = {
            "ticker": sym,
            "shares": pos.quantity,
            "cost_basis": float(pos.average_cost_basis),
            "entry_price": float(pos.average_cost_basis),
            "current_price": spot_px,
        }
        current_holdings.append(holding_info)

        should_exit, reason = evaluate_sentiment_holding_exit(
            holding_info=holding_info,
            current_price=spot_px,
            current_sentiment=sentiment_cache.get(sym),
            days_held=holding_days_by_ticker.get(sym, 0),
            stop_loss_pct=stop_loss_pct,
            max_holding_days=max_holding_days,
            euphoria_threshold=euphoria_threshold,
        )
        holding_evaluations[sym] = {"should_exit": should_exit, "reason": reason}

    return current_holdings, holding_evaluations


def _collect_qualified_candidates(
    action: str,
    tickers: tuple[str, ...] | list[str],
    current_prices: dict[str, float],
    sentiment_cache: dict[str, dict[str, Any]],
    *,
    panic_threshold: float,
    euphoria_threshold: float,
) -> list[dict[str, Any]]:
    """Evaluate universe tickers for extreme panic BUY entries."""
    if action not in ("evaluate", "entry", "rebalance"):
        return []

    qualified: list[dict[str, Any]] = []
    for raw_sym in tickers:
        sym = str(raw_sym).upper()
        sent = sentiment_cache.get(sym)
        spot_px = current_prices.get(sym, 0.0)
        if not sent or spot_px <= 0:
            continue

        sig, reason = evaluate_sentiment_signal(
            metrics=sent,
            panic_threshold=panic_threshold,
            euphoria_threshold=euphoria_threshold,
        )
        if sig == "BUY":
            logger.info(f"Sentiment Fader qualified candidate {sym}: {reason}")
            qualified.append(
                {
                    "ticker": sym,
                    "price": spot_px,
                    "pv_ratio": sent.get("pv_ratio"),
                    "reason": reason,
                }
            )
    return qualified


async def _execute_rebalance_plan(
    portfolio: Portfolio,
    plan: dict[str, Any],
    current_prices: dict[str, float],
) -> list[str]:
    """Execute planned sales then buys, returning error messages if any order fails."""
    errors: list[str] = []

    for sale in plan["sales"]:
        sym = sale["ticker"]
        shares = sale["shares"]
        exec_p = sale["execution_price"]
        trade_id = await portfolio.execute_trade(
            ticker=sym,
            quantity=shares,
            price=exec_p,
            signal="SELL",
            current_prices=current_prices,
            skip_alpaca_mirror=False,
            reason=sale["reason"],
        )
        if not trade_id:
            msg = f"SELL {shares} {sym} failed; aborting dependent buys for this tick"
            logger.error(f"Sentiment Fader {msg}")
            errors.append(msg)
            return errors
        logger.info(f"Sentiment Fader executed SELL {shares} {sym} @ {exec_p:.2f} ({sale['reason']})")

    for buy in plan["buys"]:
        sym = buy["ticker"]
        shares = buy["shares"]
        exec_p = buy["execution_price"]
        current_prices[sym] = exec_p
        trade_id = await portfolio.execute_trade(
            ticker=sym,
            quantity=shares,
            price=exec_p,
            signal="BUY",
            current_prices=current_prices,
            skip_alpaca_mirror=False,
            reason=f"Contrarian Panic Entry (P/C: {buy['pv_ratio']})",
        )
        if not trade_id:
            msg = f"BUY {shares} {sym} failed"
            logger.error(f"Sentiment Fader {msg}")
            errors.append(msg)
            continue
        logger.info(f"Sentiment Fader executed BUY {shares} {sym} @ {exec_p:.2f} (P/C: {buy['pv_ratio']})")

    if plan["sales"] or plan["buys"]:
        await portfolio.record_performance_snapshot(current_prices)
    return errors


async def run_sentiment_fader_task(
    dry_run: bool = False,
    action: str = "evaluate",
    tickers: tuple[str, ...] | list[str] = DEFAULT_SENTIMENT_UNIVERSE,
    panic_threshold: float = DEFAULT_PANIC_THRESHOLD_PC,
    euphoria_threshold: float = DEFAULT_EUPHORIA_THRESHOLD_PC,
    stop_loss_pct: float = DEFAULT_FADER_STOP_LOSS_PCT,
    max_holding_days: int = DEFAULT_FADER_MAX_HOLDING_DAYS,
    slippage_bps: float = DEFAULT_FADER_SLIPPAGE_BPS,
) -> dict[str, Any]:
    """Runs the systematic Contrarian Options Sentiment Fader strategy."""
    logger.info(
        f"Starting Sentiment Fader Task (Action: {action}, Dry Run: {dry_run}, "
        f"Tickers: {tickers}, Panic Threshold: {panic_threshold}, Euphoria: {euphoria_threshold})"
    )

    try:
        portfolio = Portfolio(SYS_SENTIMENT_FADER_OWNER_ID)
        await portfolio.initialize()
    except Exception as e:
        logger.exception(f"Failed to initialize portfolio for {SYS_SENTIMENT_FADER_OWNER_ID}: {e}")
        return {"status": "error", "error": f"Portfolio initialization failed: {e}"}

    try:
        holding_days_by_ticker, cooldown_tickers = await _load_recent_trade_state(
            str(portfolio.id) if portfolio.id else ""
        )
    except Exception as e:
        logger.exception(f"Failed to load trade state for {SYS_SENTIMENT_FADER_OWNER_ID}; failing closed")
        return {"status": "error", "error": f"Trade state lookup failed: {e}"}

    quote_symbols = list(
        dict.fromkeys([str(t).upper() for t in tickers] + [str(k).upper() for k in portfolio.positions])
    )
    current_prices, sentiment_cache = await _gather_universe_data(quote_symbols, MassiveOptionsClient())

    try:
        current_holdings, holding_evaluations = _evaluate_holdings(
            portfolio.positions,
            current_prices,
            sentiment_cache,
            holding_days_by_ticker,
            stop_loss_pct=stop_loss_pct,
            max_holding_days=max_holding_days,
            euphoria_threshold=euphoria_threshold,
        )
    except ValueError as e:
        logger.exception(f"Aborting Sentiment Fader tick due to missing quote: {e}")
        return {"status": "error", "error": str(e)}

    qualified_candidates = _collect_qualified_candidates(
        action,
        tickers,
        current_prices,
        sentiment_cache,
        panic_threshold=panic_threshold,
        euphoria_threshold=euphoria_threshold,
    )

    plan = compute_sentiment_fader_rebalance_orders(
        current_holdings=current_holdings,
        holding_evaluations=holding_evaluations,
        qualified_candidates=qualified_candidates,
        available_cash=portfolio.cash_balance,
        max_holdings=len(tickers),
        slippage_bps=slippage_bps,
        cooldown_tickers=cooldown_tickers,
    )

    if not dry_run and portfolio.id:
        exec_errors = await _execute_rebalance_plan(portfolio, plan, current_prices)
        if exec_errors:
            return {
                "status": "error",
                "error": "; ".join(exec_errors),
                "dry_run": dry_run,
                "action": action,
                "sales": plan["sales"],
                "retained": plan["retained"],
                "buys": plan["buys"],
                "remaining_cash": plan["remaining_cash"],
            }

    return {
        "status": "success",
        "dry_run": dry_run,
        "action": action,
        "sales": plan["sales"],
        "retained": plan["retained"],
        "buys": plan["buys"],
        "remaining_cash": plan["remaining_cash"],
    }


def main():
    parser = argparse.ArgumentParser(description="Contrarian Options Sentiment Fader Task")
    parser.add_argument("--dry-run", action="store_true", help="Simulate execution without modifying DB")
    parser.add_argument("--action", choices=["evaluate", "entry", "rebalance"], default="evaluate")
    parser.add_argument("--panic-threshold", type=float, default=DEFAULT_PANIC_THRESHOLD_PC)
    parser.add_argument("--euphoria-threshold", type=float, default=DEFAULT_EUPHORIA_THRESHOLD_PC)
    args = parser.parse_args()

    asyncio.run(
        run_sentiment_fader_task(
            dry_run=args.dry_run,
            action=args.action,
            panic_threshold=args.panic_threshold,
            euphoria_threshold=args.euphoria_threshold,
        )
    )


if __name__ == "__main__":
    main()
