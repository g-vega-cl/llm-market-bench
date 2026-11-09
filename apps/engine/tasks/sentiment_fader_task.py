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
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

# Ensure apps/engine is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import logger
from core.db import get_supabase_client
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


async def _get_holding_days(portfolio_id: str, ticker: str) -> int:
    """Determine days held for a position based on most recent BUY trade timestamp."""
    try:
        sb = get_supabase_client()
        res = (
            sb.table("trades")
            .select("executed_at")
            .eq("portfolio_id", portfolio_id)
            .eq("ticker", ticker.upper())
            .eq("signal", "BUY")
            .order("executed_at", desc=True)
            .limit(1)
            .execute()
        )
        if res.data:
            exec_time = datetime.fromisoformat(res.data[0]["executed_at"].replace("Z", "+00:00"))
            return max(0, (datetime.now(UTC) - exec_time).days)
    except Exception as e:
        logger.debug(f"Could not determine holding days for {ticker}: {e}")
    return 0


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

    massive_client = MassiveOptionsClient()
    current_prices: dict[str, float] = {}
    sentiment_cache: dict[str, dict[str, Any]] = {}

    # 1. Fetch current prices & sentiment for universe tickers
    for sym in tickers:
        p = await fetch_ticker_price(sym)
        if p > 0:
            current_prices[sym] = p
            sent = await fetch_sentiment_snapshot(sym, current_price=p, client=massive_client)
            if sent:
                sentiment_cache[sym] = sent

    # 2. Evaluate current active holdings
    current_holdings: list[dict[str, Any]] = []
    holding_evaluations: dict[str, dict[str, Any]] = {}

    for pos in portfolio.positions:
        sym = pos.ticker.upper()
        spot_px = current_prices.get(sym) or float(pos.current_price or pos.cost_basis)
        current_prices[sym] = spot_px

        sent = sentiment_cache.get(sym)
        days_held = await _get_holding_days(str(portfolio.id), sym) if portfolio.id else 0

        holding_info = {
            "ticker": sym,
            "shares": pos.shares,
            "cost_basis": float(pos.cost_basis),
            "entry_price": float(pos.cost_basis),
            "current_price": spot_px,
        }
        current_holdings.append(holding_info)

        should_exit, reason = evaluate_sentiment_holding_exit(
            holding_info=holding_info,
            current_price=spot_px,
            current_sentiment=sent,
            days_held=days_held,
            stop_loss_pct=stop_loss_pct,
            max_holding_days=max_holding_days,
            euphoria_threshold=euphoria_threshold,
        )
        holding_evaluations[sym] = {"should_exit": should_exit, "reason": reason}

    # 3. Evaluate candidate universe for extreme panic entries
    qualified_candidates: list[dict[str, Any]] = []
    if action in ("evaluate", "entry", "rebalance"):
        for sym in tickers:
            sent = sentiment_cache.get(sym)
            if not sent:
                continue

            spot_px = current_prices.get(sym, 0.0)
            if spot_px <= 0:
                continue

            sig, reason = evaluate_sentiment_signal(
                metrics=sent,
                panic_threshold=panic_threshold,
                euphoria_threshold=euphoria_threshold,
            )

            if sig == "BUY":
                logger.info(f"Sentiment Fader qualified candidate {sym}: {reason}")
                qualified_candidates.append(
                    {
                        "ticker": sym,
                        "price": spot_px,
                        "pv_ratio": sent.get("pv_ratio"),
                        "reason": reason,
                    }
                )

    # 4. Compute rebalance plan
    plan = compute_sentiment_fader_rebalance_orders(
        current_holdings=current_holdings,
        holding_evaluations=holding_evaluations,
        qualified_candidates=qualified_candidates,
        available_cash=portfolio.cash_balance,
        max_holdings=len(tickers),
        slippage_bps=slippage_bps,
    )

    # 5. Execute orders if live (not dry run)
    if not dry_run and portfolio.id:
        for sale in plan["sales"]:
            sym = sale["ticker"]
            shares = sale["shares"]
            exec_p = sale["execution_price"]
            await portfolio.execute_trade(
                ticker=sym,
                quantity=shares,
                price=exec_p,
                signal="SELL",
                current_prices=current_prices,
                skip_alpaca_mirror=False,
            )
            logger.info(f"Sentiment Fader executed SELL {shares} {sym} @ {exec_p:.2f} ({sale['reason']})")

        for buy in plan["buys"]:
            sym = buy["ticker"]
            shares = buy["shares"]
            exec_p = buy["execution_price"]
            current_prices[sym] = exec_p
            await portfolio.execute_trade(
                ticker=sym,
                quantity=shares,
                price=exec_p,
                signal="BUY",
                current_prices=current_prices,
                skip_alpaca_mirror=False,
            )
            logger.info(f"Sentiment Fader executed BUY {shares} {sym} @ {exec_p:.2f} (P/C: {buy['pv_ratio']})")

        portfolio.calculate_reg_t_metrics(current_prices)
        await portfolio.save_metrics()

        try:
            today_et = datetime.now(ZoneInfo("America/New_York")).date().isoformat()
            sb = get_supabase_client()
            total_equity = portfolio.total_equity
            sb.table("portfolio_performance").upsert(
                {
                    "portfolio_id": str(portfolio.id),
                    "date": today_et,
                    "total_equity": total_equity,
                    "cash_balance": portfolio.cash_balance,
                    "unrealized_pnl": portfolio.unrealized_pnl,
                    "realized_pnl": portfolio.metrics.realized if portfolio.metrics else total_equity,
                    "buying_power": portfolio.buying_power,
                    "excess_liquidity": portfolio.excess_liquidity,
                    "sma": portfolio.sma,
                    "cash": portfolio.cash_balance,
                    "equity": total_equity,
                    "realized": portfolio.metrics.realized if portfolio.metrics else total_equity,
                },
                on_conflict="portfolio_id,date",
            ).execute()
        except Exception as e:
            logger.warning(f"Failed to upsert portfolio_performance for {SYS_SENTIMENT_FADER_OWNER_ID}: {e}")

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
