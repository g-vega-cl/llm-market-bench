"""CLI sub-command router for trade execution, sector rebalancing, and thematic portfolios."""

import argparse
import asyncio

from core.config import logger
from pipeline.resolver import resolve_dep


def handle_sector_trade(args: argparse.Namespace) -> None:
    """Execute systematic sector rotation entry, exit, or status check."""
    from execution.sector_trading import run_sector_trade

    asyncio.run(
        run_sector_trade(
            action=args.action,
            target_date_str=args.target_date,
            dry_run=args.dry_run,
        )
    )


def handle_daily_trade(args: argparse.Namespace) -> None:
    """Execute daily systematic SPY MOO entries, target orders, or close exits."""
    from execution.daily_trading import (
        execute_daily_close_exits,
        execute_daily_moo_entries,
        place_daily_target_limit_orders,
    )

    log = resolve_dep("logger", logger)

    if args.action in ("entry", "open"):
        asyncio.run(execute_daily_moo_entries(target_date=args.target_date, dry_run=args.dry_run))
    elif args.action == "target-orders":
        asyncio.run(place_daily_target_limit_orders(target_date=args.target_date, dry_run=args.dry_run))
    elif args.action in ("exit", "close"):
        asyncio.run(execute_daily_close_exits(target_date=args.target_date, dry_run=args.dry_run))
    else:
        log.error(f"Unknown action '{args.action}' for daily-trade.")


def handle_frontier_tech(args: argparse.Namespace) -> None:
    """Run Frontier Tech systematic thematic portfolio execution."""
    from tasks.frontier_tech_task import run_frontier_tech_task

    asyncio.run(
        run_frontier_tech_task(
            mode=args.mode,
            dry_run=args.dry_run,
            target_weight=args.target_weight,
        )
    )


def handle_future_forces(args: argparse.Namespace) -> None:
    """Run Future Forces thematic portfolio rebalancing and sentinel auditing."""
    from tasks.future_forces_task import run_future_forces_task

    asyncio.run(
        run_future_forces_task(
            mode=args.mode,
            dry_run=args.dry_run,
            force_market=args.force_market,
            target_weight=args.target_weight,
        )
    )
