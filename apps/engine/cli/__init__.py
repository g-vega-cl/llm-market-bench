"""Command line interface package for the AI Wall Street Engine."""

from cli.parser import build_parser
from cli.router import DISPATCH_MAP, dispatch, run_cli

__all__ = ["build_parser", "dispatch", "run_cli", "DISPATCH_MAP"]
