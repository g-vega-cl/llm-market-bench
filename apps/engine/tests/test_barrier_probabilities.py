"""Tests for the Triple Barrier Method and regime-conditional touch probabilities."""

import pytest

from analytics.barrier_probabilities import (
    calculate_atr,
    calculate_barrier_probabilities,
    calculate_sma,
    classify_market_regime,
    format_barrier_report_markdown,
)


def _generate_synthetic_bars(count: int = 100, trend: float = 0.0, vol: float = 1.0) -> list[dict]:
    """Generate synthetic daily bars for deterministic testing."""
    bars = []
    base_price = 100.0
    for i in range(count):
        close_price = base_price + (i * trend)
        high_price = close_price + vol
        low_price = close_price - vol
        open_price = close_price
        bars.append(
            {
                "date": f"2025-01-{(i % 28) + 1:02d}",
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
            }
        )
    return bars


def test_calculate_atr():
    """Verify ATR computes expected values on known prices."""
    bars = [
        {"high": 105.0, "low": 95.0, "close": 100.0},
        {"high": 110.0, "low": 98.0, "close": 108.0},
        {"high": 112.0, "low": 106.0, "close": 110.0},
    ]
    highs = [b["high"] for b in bars]
    lows = [b["low"] for b in bars]
    closes = [b["close"] for b in bars]

    atrs = calculate_atr(highs, lows, closes, period=2)
    assert len(atrs) == 3
    assert atrs[0] is None
    assert atrs[1] is not None
    # TR0 = 10, TR1 = max(12, 10, 2) = 12 -> avg = 11.0
    assert pytest.approx(atrs[1], 0.1) == 11.0


def test_calculate_sma():
    """Verify SMA calculation handles lookback correctly."""
    values = [10.0, 20.0, 30.0, 40.0, 50.0]
    smas = calculate_sma(values, period=3)
    assert smas[0] is None
    assert smas[1] is None
    assert smas[2] == 20.0
    assert smas[3] == 30.0
    assert smas[4] == 40.0


def test_classify_market_regime():
    """Verify regime classifier detects trend and volatility tiers."""
    # Bullish trend with high volatility
    regime = classify_market_regime(
        current_close=120.0,
        current_sma=110.0,
        prev_sma=108.0,
        current_atr_pct=3.5,
        historical_atr_pcts=[1.0, 1.5, 2.0, 2.5, 3.0, 3.5],
    )
    assert regime["trend"] == "BULLISH_TREND"
    assert regime["volatility"] == "HIGH_VOLATILITY"

    # Bearish trend with low volatility
    regime_bear = classify_market_regime(
        current_close=90.0,
        current_sma=100.0,
        prev_sma=102.0,
        current_atr_pct=1.1,
        historical_atr_pcts=[1.0, 1.5, 2.0, 2.5, 3.0, 3.5],
    )
    assert regime_bear["trend"] == "BEARISH_TREND"
    assert regime_bear["volatility"] == "LOW_VOLATILITY"


def test_barrier_probabilities_pure_uptrend():
    """In a strong upward trend, upper barrier should dominate."""
    bars = _generate_synthetic_bars(count=60, trend=1.5, vol=0.5)

    result = calculate_barrier_probabilities(
        bars,
        target_pct=2.0,
        stop_pct=2.0,
        horizon_bars=5,
        lookback_days=50,
    )

    assert result["sample_count"] > 0
    assert result["upper_hit_pct"] > result["lower_hit_pct"]
    assert result["expected_value_pct"] > 0
    assert "BULLISH" in result["current_regime"]["trend"]


def test_barrier_probabilities_pure_downtrend():
    """In a strong downward trend, lower barrier should dominate."""
    bars = _generate_synthetic_bars(count=60, trend=-1.5, vol=0.5)

    result = calculate_barrier_probabilities(
        bars,
        target_pct=2.0,
        stop_pct=2.0,
        horizon_bars=5,
        lookback_days=50,
    )

    assert result["sample_count"] > 0
    assert result["lower_hit_pct"] > result["upper_hit_pct"]
    assert "BEARISH" in result["current_regime"]["trend"]


def test_barrier_probabilities_dynamic_atr_scaling():
    """When target_pct and stop_pct are omitted, dynamic ATR scaling applies."""
    bars = _generate_synthetic_bars(count=60, trend=0.2, vol=1.0)

    result = calculate_barrier_probabilities(
        bars,
        target_pct=None,
        stop_pct=None,
        horizon_bars=5,
        lookback_days=50,
    )

    assert result["target_pct"] > 0
    assert result["stop_pct"] > 0
    assert result["target_pct"] >= result["stop_pct"]


def test_format_barrier_report_markdown():
    """Markdown formatter produces structured tables and unslop output."""
    mock_data = {
        "ticker": "SPY",
        "current_price": 500.0,
        "current_regime": {
            "trend": "BULLISH_TREND",
            "volatility": "NORMAL_VOLATILITY",
            "combined": "BULLISH_TREND + NORMAL_VOLATILITY",
        },
        "target_pct": 2.0,
        "stop_pct": 1.5,
        "horizon_bars": 5,
        "sample_count": 42,
        "upper_hit_count": 25,
        "upper_hit_pct": 59.5,
        "lower_hit_count": 10,
        "lower_hit_pct": 23.8,
        "vertical_exit_count": 7,
        "vertical_exit_pct": 16.7,
        "avg_bars_to_upper": 2.1,
        "avg_bars_to_lower": 1.8,
        "avg_return_on_vertical_pct": 0.45,
        "friction_bps": 10.0,
        "expected_value_pct": 0.81,
        "verdict": "FAVORABLE_LONG",
    }

    markdown = format_barrier_report_markdown(mock_data)
    assert "Triple Barrier Touch Probabilities: SPY" in markdown
    assert "FAVORABLE_LONG" in markdown
    assert "59.5%" in markdown
    assert "23.8%" in markdown
    assert "0.81%" in markdown


@pytest.mark.asyncio
async def test_execute_barrier_touch_probabilities_tool(monkeypatch):
    """Verify tool execution dispatcher with mocked market data."""
    from unittest.mock import AsyncMock, MagicMock

    from core.llm.handlers.base import execute_tool

    mock_bars = _generate_synthetic_bars(count=60, trend=0.5, vol=0.5)

    mock_mdm = MagicMock()
    mock_mdm.get_history = AsyncMock(return_value=list(reversed(mock_bars)))

    monkeypatch.setattr("execution.market_data.MarketDataManager", lambda: mock_mdm)

    result = await execute_tool(
        "get_barrier_touch_probabilities",
        {"ticker": "SPY", "target_pct": 2.0, "stop_pct": 1.5, "horizon_bars": 5},
        model_name="test_model",
    )

    assert "Triple Barrier Touch Probabilities: SPY" in result
    assert "Take Profit" in result
    assert "Stop Loss" in result
    assert "Time Stop" in result
