"""Hermetic tests for technical indicator computation and tool formatting."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

import core.llm.tools  # noqa: F401 - initialize core.llm before tools.* to avoid circular import
from tools.technicals import compute_technical_snapshot, execute_technical_indicators_tool


def _make_history(count: int = 60, start_price: float = 100.0, step: float = 0.5) -> list[dict]:
    base = datetime(2026, 1, 1, 21, 0, tzinfo=UTC)
    rows = []
    # Return recent-first like MarketDataManager.get_history
    for i in range(count - 1, -1, -1):
        dt = base + timedelta(days=i)
        rows.append(
            {
                "price": round(start_price + i * step, 2),
                "volume": 1_000_000 + (i % 5) * 100_000,
                "fetched_at": dt.isoformat(),
            }
        )
    return rows


def test_compute_technical_snapshot_math():
    history = _make_history(60, start_price=100.0, step=1.0)
    snap = compute_technical_snapshot(history)

    assert snap["latest_price"] == 159.0
    assert snap["rsi_14"] > 90.0  # Monotonic uptrend
    assert snap["sma_20"] is not None and snap["sma_20"] < snap["latest_price"]
    assert snap["sma_50"] is not None and snap["sma_50"] < snap["sma_20"]
    assert snap["macd"] is not None and snap["macd"] > 0
    assert snap["macd_signal"] is not None
    assert snap["vwap_20d"] is not None
    assert snap["rvol_20d"] is not None and snap["rvol_20d"] > 0
    assert snap["price_52w_pct"] == 100.0
    assert snap["pct_from_52w_high"] == 0.0


def test_compute_technical_snapshot_cutoff_date_prevents_lookahead():
    history = _make_history(60, start_price=100.0, step=1.0)
    cutoff = "2026-01-25"
    snap = compute_technical_snapshot(history, cutoff_date=cutoff)
    assert snap["latest_date"].startswith("2026-01-25")
    assert snap["latest_price"] == 124.0


@pytest.mark.asyncio
async def test_execute_technical_indicators_tool_formats_output():
    history = _make_history(45, start_price=200.0, step=0.25)
    with patch("tools.technicals.MarketDataManager") as mock_cls:
        instance = mock_cls.return_value
        instance.get_history = AsyncMock(return_value=history)

        output = await execute_technical_indicators_tool("NVDA", cutoff_date="2026-02-10")

    assert "NVDA" in output
    assert "RSI (14)" in output
    assert "MACD" in output
    assert "VWAP" in output
    assert "52W Range Position" in output
    assert "cutoff: 2026-02-10" in output


@pytest.mark.asyncio
async def test_execute_technical_indicators_tool_handles_empty_data():
    with patch("tools.technicals.MarketDataManager") as mock_cls:
        instance = mock_cls.return_value
        instance.get_history = AsyncMock(return_value=[])

        output = await execute_technical_indicators_tool("UNKNOWN")

    assert "No price history available" in output
