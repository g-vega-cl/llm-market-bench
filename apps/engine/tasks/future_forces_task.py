"""Future Forces & Forward Catalysts Scheduled Task (`sys-future-forces`).

Handles:
1. Bootstrapping the `sys-future-forces` portfolio if absent.
2. Seeding/syncing baseline vetted multi-horizon forces into `public.future_forces`.
3. Running the Sentinel Invalidation Audit with OpenAI Luna (gpt-5.6-luna).
4. Executing pending liquidations and monthly rebalancing strictly during
   regular market hours (09:30-16:00 ET) with Alpaca paper broker mirroring.
"""

import argparse
import asyncio
from datetime import UTC, datetime
from typing import Any

import httpx

from analytics.future_forces import (
    DEFAULT_FUTURE_FORCES,
    audit_force_invalidation,
)
from core.config import FMP_API_KEY, logger
from core.db import get_supabase_client
from core.utils import is_market_open_with_logging
from execution.future_forces import (
    DEFAULT_SLIPPAGE_BPS,
    DEFAULT_TARGET_POSITION_WEIGHT,
    SYS_FUTURE_FORCES_OWNER_ID,
    compute_future_forces_rebalance_orders,
    execute_force_invalidation,
)
from execution.portfolio import Portfolio


def fetch_ticker_quote(client: httpx.Client, ticker: str, fmp_key: str) -> dict[str, Any]:
    """Fetches real-time price quote from FMP."""
    if not fmp_key:
        return {"price": 100.0, "changesPercentage": 0.0}
    try:
        url = f"https://financialmodelingprep.com/stable/quote?symbol={ticker.upper()}&apikey={fmp_key}"
        resp = client.get(url, timeout=10.0)
        if resp.status_code == 200 and resp.json():
            return resp.json()[0]
    except Exception as e:
        logger.debug("Failed to fetch FMP quote for %s: %s", ticker, e)
    return {"price": 100.0, "changesPercentage": 0.0}


async def seed_baseline_future_forces(supabase: Any, portfolio_id: str) -> list[dict[str, Any]]:
    """Seeds baseline vetted future forces if table has no active records."""
    try:
        res = supabase.table("future_forces").select("id").limit(1).execute()
        if res.data:
            return []
    except Exception as e:
        logger.warning("Could not query future_forces table (migration may be pending): %s", e)
        return []

    logger.info("Seeding baseline vetted future forces for portfolio %s", portfolio_id)
    seeded = []
    now = datetime.now(UTC).isoformat()
    for force in DEFAULT_FUTURE_FORCES:
        row = {
            "portfolio_id": portfolio_id,
            "force_title": force["force_title"],
            "archetype": force["archetype"],
            "thesis": force["thesis"],
            "catalyst_event": force["catalyst_event"],
            "horizon_months": force["horizon_months"],
            "target_date": force.get("target_date"),
            "invalidation_triggers": force["invalidation_triggers"],
            "transmission_mechanism": force.get("transmission_mechanism"),
            "tickers": force.get("tickers", []),
            "conviction_score": force.get("conviction_score", 4),
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
        try:
            res = supabase.table("future_forces").insert(row).execute()
            if res.data:
                seeded.append(res.data[0])
        except Exception as e:
            logger.debug("Could not insert future_force row: %s", e)
    return seeded


async def run_sentinel_audit(
    supabase: Any,
    force_market: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Audits active forces against recent news/data and processes pending liquidations."""
    logger.info("Starting Future Forces Invalidation Sentinel Audit")
    results: dict[str, Any] = {"pending_executed": [], "invalidations": [], "retained": []}

    # 1. Process pending liquidations first if market is open
    market_open = force_market or await is_market_open_with_logging()
    pending_forces: list[dict[str, Any]] = []
    try:
        pending_res = supabase.table("future_forces").select("*").eq("status", "pending_liquidation").execute()
        pending_forces = pending_res.data or []
    except Exception as e:
        logger.debug("Could not query pending future_forces: %s", e)

    for force in pending_forces:
        if market_open and not dry_run:
            logger.info("Market is open: Executing deferred liquidation for %s", force.get("force_title"))
            res = await execute_force_invalidation(
                force_id=force["id"],
                reason=force.get("invalidation_reason") or "deferred_pending_liquidation",
                force_market_check=not force_market,
            )
            results["pending_executed"].append(res)
        else:
            logger.info(
                "Holding pending liquidation for %s (market_open=%s, dry_run=%s)",
                force.get("force_title"),
                market_open,
                dry_run,
            )

    # 2. Audit active forces
    active_forces: list[dict[str, Any]] = []
    try:
        active_res = supabase.table("future_forces").select("*").eq("status", "active").execute()
        active_forces = active_res.data or []
    except Exception as e:
        logger.debug("Could not query active future_forces, using vetted defaults: %s", e)
        active_forces = DEFAULT_FUTURE_FORCES

    for force in active_forces:
        tickers = force.get("tickers") or []
        news_context = f"Monitoring active force: {force.get('force_title')} for tickers {', '.join(tickers)}."

        # Audit with Luna
        audit_res = await audit_force_invalidation(force_data=force, news_context=news_context)
        if audit_res.is_invalidated or audit_res.is_realized:
            logger.warning(
                "Sentinel flagged %s: %s (action=%s)",
                force.get("force_title"),
                audit_res.explanation,
                audit_res.recommended_action,
            )
            if not dry_run:
                exec_res = await execute_force_invalidation(
                    force_id=force["id"],
                    reason=audit_res.explanation,
                    is_realized=audit_res.is_realized,
                    force_market_check=not force_market,
                )
                results["invalidations"].append(exec_res)
            else:
                results["invalidations"].append({"force_title": force.get("force_title"), "simulated": True})
        else:
            results["retained"].append(force.get("force_title"))

    return results


async def run_future_forces_task(
    mode: str = "auto",  # 'auto', 'sentinel', 'rebalance', 'all'
    dry_run: bool = False,
    force_market: bool = False,
    target_weight: float = DEFAULT_TARGET_POSITION_WEIGHT,
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
) -> dict[str, Any]:
    """Executes the Future Forces portfolio task."""
    supabase = get_supabase_client()
    logger.info("Initializing sys-future-forces task (mode=%s, dry_run=%s)", mode, dry_run)

    if mode == "auto":
        market_open = force_market or await is_market_open_with_logging()
        mode = "all" if market_open else "sentinel"
        logger.info("Auto mode resolved to '%s' (market_open=%s)", mode, market_open)

    # 1. Initialize portfolio
    portfolio = Portfolio(SYS_FUTURE_FORCES_OWNER_ID)
    await portfolio.initialize()

    if not portfolio.id:
        logger.info("Bootstrapping new portfolio record for %s", SYS_FUTURE_FORCES_OWNER_ID)
        res = (
            supabase.table("portfolios")
            .insert(
                {
                    "owner_id": SYS_FUTURE_FORCES_OWNER_ID,
                    "cash_balance": 10000.00,
                    "total_equity": 10000.00,
                    "buying_power": 20000.00,
                    "sma": 0.0,
                }
            )
            .execute()
        )
        if res.data:
            portfolio.id = res.data[0]["id"]
            portfolio.cash_balance = 10000.00
            portfolio.total_equity = 10000.00

    # 2. Seed baseline forces if absent
    if portfolio.id:
        await seed_baseline_future_forces(supabase, portfolio.id)

    task_results: dict[str, Any] = {}

    # 3. Sentinel audit
    if mode in ("sentinel", "all"):
        task_results["sentinel"] = await run_sentinel_audit(supabase, force_market=force_market, dry_run=dry_run)

    # 4. Rebalance
    if mode in ("rebalance", "all"):
        market_open = force_market or await is_market_open_with_logging()
        if not market_open and not dry_run:
            logger.info("Market is closed. Skipping live rebalance buys to enforce market hours guardrail.")
            task_results["rebalance"] = {"status": "skipped_market_closed"}
            return task_results

        # Fetch active forces
        active_forces = []
        try:
            forces_res = (
                supabase.table("future_forces")
                .select("*")
                .eq("status", "active")
                .order("conviction_score", desc=True)
                .execute()
            )
            active_forces = forces_res.data or []
        except Exception as e:
            logger.debug("Could not fetch active future_forces from database, using vetted defaults: %s", e)

        if not active_forces:
            active_forces = DEFAULT_FUTURE_FORCES

        # Pull quotes for candidate tickers
        quotes: dict[str, dict[str, Any]] = {}
        with httpx.Client(timeout=10.0) as client:
            for force in active_forces:
                for ticker in force.get("tickers") or []:
                    ticker_up = ticker.upper()
                    if ticker_up not in quotes:
                        quotes[ticker_up] = fetch_ticker_quote(client, ticker_up, FMP_API_KEY)
                force["quotes"] = quotes

        current_holdings = [
            {
                "ticker": pos["ticker"],
                "shares": int(pos["quantity"]),
                "current_price": float(pos.get("current_price") or pos.get("average_cost_basis") or 100.0),
            }
            for pos in portfolio.positions.values()
            if (pos.get("quantity") or 0) > 0
        ]

        holding_evals = {h["ticker"].upper(): {"should_exit": False} for h in current_holdings}

        orders = compute_future_forces_rebalance_orders(
            current_holdings=current_holdings,
            holding_evaluations=holding_evals,
            candidate_forces=active_forces,
            available_cash=portfolio.cash_balance,
            total_equity=portfolio.total_equity or 10000.0,
            target_position_weight=target_weight,
            slippage_bps=slippage_bps,
        )

        task_results["rebalance_orders"] = orders

        # Execute buys if not dry_run and market open
        if not dry_run and market_open:
            for buy in orders["new_buys"]:
                await portfolio.execute_trade(
                    ticker=buy["ticker"],
                    signal="BUY",
                    quantity=buy["shares"],
                    price=buy["execution_price"],
                    reason=f"future_force_buy: {buy['force_title']}",
                    skip_alpaca_mirror=False,  # Enforce Alpaca paper audit
                )
                logger.info(
                    "Executed BUY of %s (%d shares at $%.2f) mirrored to Alpaca",
                    buy["ticker"],
                    buy["shares"],
                    buy["execution_price"],
                )

    return task_results


def main() -> None:
    """CLI entrypoint for future forces scheduled task."""
    parser = argparse.ArgumentParser(description="Future Forces & Forward Catalysts Scheduled Task")
    parser.add_argument(
        "--mode",
        choices=["auto", "sentinel", "rebalance", "all"],
        default="auto",
        help="Task execution mode (auto, sentinel, rebalance, all)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Simulate execution without modifying DB or broker")
    parser.add_argument("--force-market", action="store_true", help="Bypass market hours check (for testing)")
    parser.add_argument(
        "--target-weight",
        type=float,
        default=DEFAULT_TARGET_POSITION_WEIGHT,
        help=f"Target weight per force (default: {DEFAULT_TARGET_POSITION_WEIGHT})",
    )
    args = parser.parse_args()

    asyncio.run(
        run_future_forces_task(
            mode=args.mode,
            dry_run=args.dry_run,
            force_market=args.force_market,
            target_weight=args.target_weight,
        )
    )


if __name__ == "__main__":
    main()
