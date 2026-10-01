"""Reproduction and contract tests for CLI decomposition and entry point LOC limits.

Validates that:
1. apps/engine/main.py entry point is under 200 LOC.
2. apps/engine/cli/ sub-command routers exist and each is under 200 LOC.
3. Subcommand routing accurately dispatches all CLI commands.
"""

from pathlib import Path


def test_main_py_loc_under_200():
    """Verify apps/engine/main.py is under 200 LOC (entry point ceiling)."""
    main_py = Path(__file__).resolve().parent.parent / "main.py"
    assert main_py.exists(), "apps/engine/main.py must exist"
    lines = main_py.read_text(encoding="utf-8").splitlines()
    loc = len(lines)
    assert loc <= 200, f"apps/engine/main.py has {loc} LOC, expected <= 200 LOC"


def test_cli_routers_exist_and_under_200_loc():
    """Verify apps/engine/cli/ exists and all router files are under 200 LOC."""
    cli_dir = Path(__file__).resolve().parent.parent / "cli"
    assert cli_dir.exists(), "apps/engine/cli/ directory must exist"

    expected_routers = [
        "parser.py",
        "router.py",
        "ingest.py",
        "predictions.py",
        "trading.py",
        "autoresearch.py",
        "audit.py",
    ]

    for router_name in expected_routers:
        router_path = cli_dir / router_name
        assert router_path.exists(), f"Router {router_name} must exist in apps/engine/cli/"
        loc = len(router_path.read_text(encoding="utf-8").splitlines())
        assert loc <= 200, f"apps/engine/cli/{router_name} has {loc} LOC, expected <= 200 LOC"


def test_cli_router_dispatch_map_complete():
    """Verify cli.router defines handlers for all 26 COMMAND_* constants."""
    from cli.router import DISPATCH_MAP
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

    all_commands = [
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
        COMMAND_DAILY_TRADE,
        COMMAND_GAINERS_POSTMORTEM,
        COMMAND_HISTORICAL_ANALOG,
        COMMAND_AUDIT_PORTFOLIOS,
    ]

    for cmd in all_commands:
        assert cmd in DISPATCH_MAP, f"Command '{cmd}' must be registered in cli.router.DISPATCH_MAP"
        assert callable(DISPATCH_MAP[cmd]), f"Handler for '{cmd}' must be callable"
