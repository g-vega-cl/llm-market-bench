"""Pytest configuration for the engine package.

Skip live IBKR API tests by default so the suite stays offline-friendly.
"""

from __future__ import annotations

from pathlib import Path

import pytest


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip live IBKR API tests regardless of where they are collected from."""
    skip_ibkr = pytest.mark.skip(reason="Skipping live IBKR API tests by default.")

    for item in items:
        path = Path(str(item.path))
        if path.name.startswith("test_ibkr") or path.name == "test_ibkr.py":
            item.add_marker(skip_ibkr)
