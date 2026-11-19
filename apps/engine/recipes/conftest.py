"""Shared fixtures for the strategy-recipe test package.

Live-turn tests exercise `run_push_live`, which now mirrors fills to Alpaca. The
engine `.env` ships real paper credentials, so without this guard a unit test would
build a `TradingClient` and attempt an outbound HTTP call. Tests that assert on the
mirror pass their own fake client explicitly.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _no_live_alpaca_broker(monkeypatch):
    from recipes import alpaca_mirror

    monkeypatch.setattr(alpaca_mirror, "_build_client", lambda: None)
    yield
