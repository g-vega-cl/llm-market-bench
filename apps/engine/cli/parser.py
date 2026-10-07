"""Argument parsing schema and configuration for AI Wall Street Engine CLI."""

import argparse

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
    COMMAND_EARNINGS_PREDICTOR,
    COMMAND_EVALUATE_DAILY_PREDICTIONS,
    COMMAND_EVALUATE_EARNINGS_PREDICTIONS,
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


def build_parser() -> argparse.ArgumentParser:
    """Builds and returns the top-level CLI argument parser."""
    parser = argparse.ArgumentParser(description="AI Wall Street Engine")
    parser.add_argument(
        "command",
        choices=[
            COMMAND_INGEST,
            COMMAND_WEEKEND_INGEST,
            COMMAND_POST_ANALYSIS,
            COMMAND_GOVERNMENT,
            COMMAND_CALENDAR,
            COMMAND_CAUSE_AND_EFFECT,
            COMMAND_AUDIT,
            COMMAND_AUTORESEARCH,
            COMMAND_BOOTSTRAP_AUTORESEARCH,
            COMMAND_CLEANUP,
            COMMAND_DAILY_PREDICTOR,
            COMMAND_EVALUATE_DAILY_PREDICTIONS,
            COMMAND_EARNINGS_PREDICTOR,
            COMMAND_EVALUATE_EARNINGS_PREDICTIONS,
            COMMAND_DAILY_AUTORESEARCH,
            COMMAND_DAILY_POSTMORTEM,
            COMMAND_BACKTEST_DAILY_AUTORESEARCH,
            COMMAND_SEED_DAILY_PREDICTOR,
            COMMAND_GENERATE_NEWSLETTER,
            COMMAND_LIN_RENKO,
            COMMAND_AUDIT_ALPACA,
            COMMAND_FRONTIER_TECH,
            COMMAND_FUTURE_FORCES,
            COMMAND_SECTOR_TRADE,
            COMMAND_GAINERS_POSTMORTEM,
            COMMAND_HISTORICAL_ANALOG,
            COMMAND_DAILY_TRADE,
            COMMAND_AUDIT_PORTFOLIOS,
        ],
        help="Action to perform",
    )

    parser.add_argument("--fix", action="store_true", help="Auto-heal and backfill missing systematic trades")
    parser.add_argument("--lookback-days", type=int, default=5, help="Number of trading days to look back for audit")
    parser.add_argument("--force", action="store_true", help="Force ingestion even outside market hours")
    parser.add_argument("--dry-run", action="store_true", help="Run auto-research without writing to database")
    parser.add_argument(
        "--track-id",
        "--track",
        type=str,
        default="all",
        help="Track ID for multi-track autoresearch ('all' to run all tracks)",
    )
    parser.add_argument("--cold-start", action="store_true", help="Trigger a cold-start reset for autoresearch")
    parser.add_argument("--ticker", type=str, default="SPY", help="Ticker for daily predictor (default: SPY)")
    parser.add_argument(
        "--model",
        type=str,
        default="MiniMax-M3",
        help="Target model name for audit/tasks (default: MiniMax-M3)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Lookback period in days for audit (default: 7)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output audit results in JSON format",
    )
    parser.add_argument(
        "--session",
        type=str,
        choices=["open", "close"],
        default="open",
        help="Session window for generated newsletter (open or close)",
    )
    parser.add_argument(
        "--action",
        type=str,
        choices=["entry", "open", "exit", "close", "status", "target-orders"],
        default="entry",
        help="Action for sector trade (entry, exit, status)",
    )
    parser.add_argument("--start-date", type=str, default="2026-04-27", help="Backtest start date (YYYY-MM-DD)")
    parser.add_argument(
        "--target-date", type=str, default=None, help="Target date for daily predictor evaluation (YYYY-MM-DD)"
    )
    parser.add_argument("--weeks", type=int, default=1, help="Number of backtest weeks")
    parser.add_argument(
        "--mode",
        type=str,
        default="auto",
        choices=["auto", "rebalance", "health_check", "bootstrap", "sentinel", "all"],
        help="Execution mode for tasks (default: auto)",
    )
    parser.add_argument(
        "--force-market",
        action="store_true",
        help="Bypass market hours check for scheduled tasks (for testing/simulations)",
    )
    parser.add_argument(
        "--target-weight",
        type=float,
        default=0.03,
        help="Target position weight for portfolio tasks (default: 0.03)",
    )
    parser.add_argument(
        "--timeframe",
        type=str,
        default="all",
        choices=["daily", "weekly", "monthly", "all"],
        help="Target timeframe for gainers post-mortem (daily, weekly, monthly, all)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=3,
        help="Number of top gainers to audit per timeframe (default: 3)",
    )
    parser.add_argument(
        "--no-save-memory",
        action="store_true",
        help="Skip saving post-mortem results into Supabase memories table",
    )
    parser.add_argument(
        "--situation",
        "--query",
        type=str,
        default=None,
        help="Market situation or query for historical analog research",
    )
    parser.add_argument(
        "--assets",
        type=str,
        default=None,
        help="Comma-separated focus assets (e.g. TLT,GLD,BTCUSD)",
    )
    parser.add_argument(
        "--horizon",
        type=str,
        default="1m",
        help="Reaction horizon for historical analog (default: 1m)",
    )

    return parser
