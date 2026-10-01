"""Command dispatcher routing CLI subcommands to domain handlers."""

import argparse
from collections.abc import Callable

from cli.audit import handle_audit, handle_audit_alpaca, handle_audit_portfolios, handle_cleanup
from cli.autoresearch import (
    handle_autoresearch,
    handle_backtest_daily_autoresearch,
    handle_bootstrap_autoresearch,
    handle_daily_autoresearch,
)
from cli.ingest import (
    handle_calendar,
    handle_cause_and_effect,
    handle_government,
    handle_ingest,
    handle_lin_renko,
    handle_post_analysis,
    handle_weekend_ingest,
)
from cli.parser import build_parser
from cli.predictions import (
    handle_daily_postmortem,
    handle_daily_predictor,
    handle_evaluate_daily_predictions,
    handle_gainers_postmortem,
    handle_generate_newsletter,
    handle_historical_analog,
    handle_seed_daily_predictor,
)
from cli.trading import (
    handle_daily_trade,
    handle_frontier_tech,
    handle_future_forces,
    handle_sector_trade,
)
from core.config import (
    COMMAND_AUDIT,
    COMMAND_AUDIT_ALPACA,
    COMMAND_AUDIT_PORTFOLIOS,
    COMMAND_AUTORESEARCH,
    COMMAND_BACKTEST_DAILY_AUTORESEARCH,
    COMMAND_BOOTSTRAP_AUTORESEARCH,
    COMMAND_CALENDAR,
    COMMAND_CAUSE_AND_EFFECT,
    COMMAND_CLEANUP,
    COMMAND_DAILY_AUTORESEARCH,
    COMMAND_DAILY_POSTMORTEM,
    COMMAND_DAILY_PREDICTOR,
    COMMAND_DAILY_TRADE,
    COMMAND_EVALUATE_DAILY_PREDICTIONS,
    COMMAND_FRONTIER_TECH,
    COMMAND_FUTURE_FORCES,
    COMMAND_GAINERS_POSTMORTEM,
    COMMAND_GENERATE_NEWSLETTER,
    COMMAND_GOVERNMENT,
    COMMAND_HISTORICAL_ANALOG,
    COMMAND_INGEST,
    COMMAND_LIN_RENKO,
    COMMAND_POST_ANALYSIS,
    COMMAND_SECTOR_TRADE,
    COMMAND_SEED_DAILY_PREDICTOR,
    COMMAND_WEEKEND_INGEST,
)

DISPATCH_MAP: dict[str, Callable[[argparse.Namespace], None]] = {
    COMMAND_INGEST: handle_ingest,
    COMMAND_WEEKEND_INGEST: handle_weekend_ingest,
    COMMAND_POST_ANALYSIS: handle_post_analysis,
    COMMAND_GOVERNMENT: handle_government,
    COMMAND_CALENDAR: handle_calendar,
    COMMAND_CAUSE_AND_EFFECT: handle_cause_and_effect,
    COMMAND_AUDIT: handle_audit,
    COMMAND_AUTORESEARCH: handle_autoresearch,
    COMMAND_BOOTSTRAP_AUTORESEARCH: handle_bootstrap_autoresearch,
    COMMAND_CLEANUP: handle_cleanup,
    COMMAND_DAILY_PREDICTOR: handle_daily_predictor,
    COMMAND_EVALUATE_DAILY_PREDICTIONS: handle_evaluate_daily_predictions,
    COMMAND_DAILY_AUTORESEARCH: handle_daily_autoresearch,
    COMMAND_DAILY_POSTMORTEM: handle_daily_postmortem,
    COMMAND_BACKTEST_DAILY_AUTORESEARCH: handle_backtest_daily_autoresearch,
    COMMAND_SEED_DAILY_PREDICTOR: handle_seed_daily_predictor,
    COMMAND_GENERATE_NEWSLETTER: handle_generate_newsletter,
    COMMAND_LIN_RENKO: handle_lin_renko,
    COMMAND_AUDIT_ALPACA: handle_audit_alpaca,
    COMMAND_FRONTIER_TECH: handle_frontier_tech,
    COMMAND_FUTURE_FORCES: handle_future_forces,
    COMMAND_SECTOR_TRADE: handle_sector_trade,
    COMMAND_DAILY_TRADE: handle_daily_trade,
    COMMAND_GAINERS_POSTMORTEM: handle_gainers_postmortem,
    COMMAND_HISTORICAL_ANALOG: handle_historical_analog,
    COMMAND_AUDIT_PORTFOLIOS: handle_audit_portfolios,
}


def dispatch(args: argparse.Namespace) -> None:
    """Dispatches parsed arguments to the registered subcommand handler."""
    handler = DISPATCH_MAP.get(args.command)
    if handler:
        handler(args)
    else:
        raise ValueError(f"Unknown command: {args.command}")


def run_cli(args_list: list[str] | None = None) -> None:
    """Main CLI entry point function."""
    parser = build_parser()
    args = parser.parse_args(args_list)
    dispatch(args)
