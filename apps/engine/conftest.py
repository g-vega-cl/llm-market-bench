"""Shared pytest fixtures for the engine suite."""

import pytest

from trading.market_calendar import configure_market_calendar


@pytest.fixture(autouse=True)
def _reset_market_calendar():
    """The session gate is a module-level singleton: isolate it per test.

    ``trading.runner.run_loop`` installs a clock-backed calendar into
    ``trading.market_calendar``; without this reset a test that ran the daemon
    would leak its (possibly mocked) client into every test that follows.
    """
    yield
    configure_market_calendar(None)
