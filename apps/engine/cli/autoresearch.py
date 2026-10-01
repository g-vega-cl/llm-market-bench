"""CLI sub-command router for autoresearch optimization loops and backtests."""

import argparse
import asyncio


def handle_autoresearch(args: argparse.Namespace) -> None:
    """Run continuous prompt autoresearch loop across tracks."""
    from autoresearch.runner import run, run_all

    forced_cold = True if args.cold_start else None
    if args.track_id == "all":
        asyncio.run(run_all(dry_run=args.dry_run, cold_start=forced_cold))
    else:
        asyncio.run(run(dry_run=args.dry_run, track_id=args.track_id, cold_start=forced_cold))


def handle_bootstrap_autoresearch(args: argparse.Namespace) -> None:
    """Bootstrap initial autoresearch prompt blocks and baseline programs."""
    from autoresearch.bootstrap import bootstrap

    asyncio.run(bootstrap())


def handle_daily_autoresearch(args: argparse.Namespace) -> None:
    """Run daily autoresearch session."""
    from tasks.daily_autoresearch import run_daily_autoresearch

    forced_cold = True if args.cold_start else None
    asyncio.run(run_daily_autoresearch(dry_run=args.dry_run, cold_start=forced_cold))


def handle_backtest_daily_autoresearch(args: argparse.Namespace) -> None:
    """Run multi-week historical backtest of daily autoresearch prompts."""
    from tasks.backtest_daily_autoresearch import run_backtest_daily_autoresearch

    asyncio.run(run_backtest_daily_autoresearch(start_date_str=args.start_date, weeks=args.weeks))
