"""Unit tests for the Intraday Movement Profile and Tape Matrix analytics module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from analytics.intraday_profile import (
    build_hourly_tape_matrix,
    calculate_intraday_metrics,
    filter_regular_trading_hours,
    format_intraday_movement_markdown,
    get_intraday_movement_report,
)


def _make_bar(time_str: str, open_p: float, high_p: float, low_p: float, close_p: float, vol: int = 1_000_000):
    return {
        "date": f"2026-09-21 {time_str}",
        "open": open_p,
        "high": high_p,
        "low": low_p,
        "close": close_p,
        "volume": vol,
    }


def test_filter_regular_trading_hours():
    """Ensure pre-market and post-market bars are stripped, leaving only 09:30 to 16:00."""
    bars = [
        _make_bar("04:00:00", 575.0, 576.0, 575.0, 576.0),
        _make_bar("09:00:00", 578.0, 579.0, 578.0, 578.5),
        _make_bar("09:30:00", 579.0, 580.5, 578.5, 580.0),
        _make_bar("12:00:00", 580.0, 581.0, 579.8, 580.5),
        _make_bar("16:00:00", 582.0, 583.0, 581.5, 582.5),
        _make_bar("16:30:00", 582.5, 582.8, 582.0, 582.1),
    ]
    rth = filter_regular_trading_hours(bars)
    assert len(rth) == 3
    assert rth[0]["date"].endswith("09:30:00")
    assert rth[-1]["date"].endswith("16:00:00")


def test_trend_day_up_metrics():
    """Bullish trend day with higher highs, higher lows, and close near high."""
    bars = [
        _make_bar("09:30:00", 580.0, 581.5, 579.5, 581.0, 5_000_000),
        _make_bar("10:30:00", 581.0, 582.5, 580.8, 582.2, 4_000_000),
        _make_bar("11:30:00", 582.2, 583.5, 582.0, 583.0, 3_000_000),
        _make_bar("12:30:00", 583.0, 584.0, 582.8, 583.8, 2_000_000),
        _make_bar("13:30:00", 583.8, 585.0, 583.5, 584.8, 3_000_000),
        _make_bar("14:30:00", 584.8, 586.0, 584.5, 585.5, 4_000_000),
        _make_bar("15:30:00", 585.5, 586.5, 585.0, 586.2, 6_000_000),
    ]
    metrics = calculate_intraday_metrics(bars)
    assert metrics is not None
    assert metrics["open"] == 580.0
    assert metrics["high"] == 586.5
    assert metrics["low"] == 579.5
    assert metrics["close"] == 586.2
    assert metrics["intraday_return_pct"] > 1.0
    assert metrics["clv"] > 0.7
    assert metrics["archetype"] == "TREND_DAY_UP"
    assert metrics["ib_high"] == 581.5
    assert metrics["ib_low"] == 579.5
    assert metrics["ib_broken"] == "HIGH"


def test_trend_day_down_metrics():
    """Bearish trend day with lower lows, lower highs, and close near low."""
    bars = [
        _make_bar("09:30:00", 586.0, 586.5, 584.5, 585.0, 5_000_000),
        _make_bar("10:30:00", 585.0, 585.2, 583.5, 583.8, 4_000_000),
        _make_bar("11:30:00", 583.8, 584.0, 582.5, 582.7, 3_000_000),
        _make_bar("12:30:00", 582.7, 583.0, 581.5, 581.8, 2_000_000),
        _make_bar("13:30:00", 581.8, 582.0, 580.5, 580.8, 3_000_000),
        _make_bar("14:30:00", 580.8, 581.0, 579.5, 579.8, 4_000_000),
        _make_bar("15:30:00", 579.8, 580.0, 578.5, 578.8, 6_000_000),
    ]
    metrics = calculate_intraday_metrics(bars)
    assert metrics is not None
    assert metrics["open"] == 586.0
    assert metrics["close"] == 578.8
    assert metrics["intraday_return_pct"] < -1.0
    assert metrics["clv"] < -0.7
    assert metrics["archetype"] == "TREND_DAY_DOWN"
    assert metrics["ib_broken"] == "LOW"


def test_morning_dip_and_rip():
    """Morning dump below initial balance followed by steady reclaim closing green."""
    bars = [
        _make_bar("09:30:00", 580.0, 581.0, 577.0, 577.5, 6_000_000),  # Morning flush to 577.0
        _make_bar("10:30:00", 577.5, 579.0, 577.2, 578.8, 4_000_000),
        _make_bar("11:30:00", 578.8, 580.5, 578.5, 580.2, 3_000_000),  # Reclaiming Open
        _make_bar("12:30:00", 580.2, 581.5, 580.0, 581.3, 2_000_000),  # Breaking IB High
        _make_bar("13:30:00", 581.3, 582.2, 581.0, 582.0, 3_000_000),
        _make_bar("14:30:00", 582.0, 582.8, 581.8, 582.5, 3_000_000),
        _make_bar("15:30:00", 582.5, 583.2, 582.2, 583.0, 5_000_000),
    ]
    metrics = calculate_intraday_metrics(bars)
    assert metrics is not None
    assert metrics["archetype"] == "MORNING_DIP_AND_RIP"
    assert metrics["close"] > metrics["open"]
    assert metrics["clv"] > 0.5


def test_gap_and_crap():
    """Morning spike that fails and rolls over into a red close."""
    bars = [
        _make_bar("09:30:00", 580.0, 584.0, 579.8, 583.5, 6_000_000),  # Morning spike to 584.0
        _make_bar("10:30:00", 583.5, 583.8, 581.5, 581.8, 4_000_000),
        _make_bar("11:30:00", 581.8, 582.0, 580.2, 580.5, 3_000_000),
        _make_bar("12:30:00", 580.5, 580.8, 579.5, 579.6, 2_000_000),
        _make_bar("13:30:00", 579.6, 579.8, 578.5, 578.6, 3_000_000),
        _make_bar("14:30:00", 578.6, 578.8, 577.8, 578.0, 3_000_000),
        _make_bar("15:30:00", 578.0, 578.2, 576.8, 577.0, 5_000_000),
    ]
    metrics = calculate_intraday_metrics(bars)
    assert metrics is not None
    assert metrics["archetype"] == "GAP_AND_CRAP"
    assert metrics["close"] < metrics["open"]
    assert metrics["clv"] < -0.5


def test_range_bound_churn():
    """Price stays inside initial balance with low range and close near midpoint."""
    bars = [
        _make_bar("09:30:00", 580.0, 581.5, 579.0, 580.5, 4_000_000),
        _make_bar("10:30:00", 580.5, 581.2, 579.5, 580.0, 2_000_000),
        _make_bar("11:30:00", 580.0, 580.8, 579.8, 580.3, 2_000_000),
        _make_bar("12:30:00", 580.3, 580.9, 579.7, 580.1, 1_500_000),
        _make_bar("13:30:00", 580.1, 580.7, 579.9, 580.4, 1_800_000),
        _make_bar("14:30:00", 580.4, 581.0, 580.0, 580.2, 2_200_000),
        _make_bar("15:30:00", 580.2, 580.8, 579.8, 580.2, 3_500_000),
    ]
    metrics = calculate_intraday_metrics(bars)
    assert metrics is not None
    assert metrics["archetype"] == "RANGE_BOUND_CHURN"
    assert abs(metrics["intraday_return_pct"]) < 0.2
    assert abs(metrics["clv"]) < 0.4
    assert metrics["ib_broken"] == "NONE"


def test_build_hourly_tape_matrix():
    """Verify ascii tape matrix table generation."""
    bars = [
        _make_bar("09:30:00", 580.0, 582.0, 579.5, 581.5, 5_000_000),
        _make_bar("10:30:00", 581.5, 583.0, 581.0, 582.5, 4_000_000),
    ]
    matrix = build_hourly_tape_matrix(bars)
    assert "Time (ET)" in matrix
    assert "09:30" in matrix
    assert "10:30" in matrix
    assert "[" in matrix and "]" in matrix  # ASCII map


def test_format_intraday_movement_markdown():
    """Verify markdown output formatting."""
    bars = [
        _make_bar("09:30:00", 580.0, 582.0, 579.5, 581.5, 5_000_000),
        _make_bar("10:30:00", 581.5, 583.0, 581.0, 582.5, 4_000_000),
    ]
    metrics = calculate_intraday_metrics(bars)
    md = format_intraday_movement_markdown("SPY", "2026-09-21", metrics, bars, include_hourly_tape=True)
    assert "SPY INTRADAY MOVEMENT PROFILE" in md
    assert "Regular Trading Hours:" in md
    assert "True Intraday Return:" in md
    assert "HOURLY TAPE MATRIX" in md


@pytest.mark.asyncio
async def test_get_intraday_movement_report_hermetic():
    """Hermetic test with mocked MarketDataManager and provider."""
    mock_bars = [
        {"date": "2026-09-21 09:30:00", "open": 580.0, "high": 582.0, "low": 579.0, "close": 581.5, "volume": 5000000},
        {"date": "2026-09-21 15:30:00", "open": 581.5, "high": 583.5, "low": 581.0, "close": 583.0, "volume": 8000000},
    ]

    mock_provider = MagicMock()
    mock_provider.get_hourly_history = AsyncMock(return_value=mock_bars)

    with patch("execution.market_data.MarketDataManager") as mock_mdm_cls:
        instance = MagicMock()
        instance.provider = mock_provider
        mock_mdm_cls.return_value = instance

        report = await get_intraday_movement_report(ticker="SPY", date_str="2026-09-21", include_hourly_tape=True)
        assert "markdown" in report
        assert "SPY INTRADAY MOVEMENT PROFILE" in report["markdown"]
        assert report["metrics"]["archetype"] == "TREND_DAY_UP"


@pytest.mark.asyncio
async def test_execute_get_intraday_movement_profile_tool():
    """Verify tool execution wrapper and dispatcher integration."""
    from core.llm.handlers.base import execute_tool
    from core.llm.tools import CANONICAL_TOOLS_REGISTRY, execute_get_intraday_movement_profile_tool

    assert "get_intraday_movement_profile" in CANONICAL_TOOLS_REGISTRY
    tool_def = CANONICAL_TOOLS_REGISTRY["get_intraday_movement_profile"]
    assert tool_def["type"] == "function"
    assert tool_def["function"]["name"] == "get_intraday_movement_profile"

    with patch(
        "analytics.intraday_profile.get_intraday_movement_report",
        AsyncMock(return_value={"markdown": "=== MOCKED INTRADAY PROFILE ==="}),
    ):
        res1 = await execute_get_intraday_movement_profile_tool(ticker="SPY", date="2026-09-21")
        assert "MOCKED INTRADAY PROFILE" in res1

        res2 = await execute_tool(
            "get_intraday_movement_profile",
            {"ticker": "SPY", "date": "2026-09-21", "include_hourly_tape": True},
            model_name="deepseek-v4-flash",
        )
        assert "MOCKED INTRADAY PROFILE" in res2
