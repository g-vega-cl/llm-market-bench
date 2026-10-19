"""Hermetic unit tests for analytics.trend_profile.

Verifies mathematical accuracy, strict avoidance of hallucinated SMAs when history is insufficient,
and strict zero-lookahead filtering.
"""

from __future__ import annotations

import pytest

from analytics.trend_profile import compute_trend_profile


def test_compute_trend_profile_full_history():
    """Verify accurate calculation of 5-day return, 20-day SMA, and 3-day sequence with 25 bars."""
    # 25 days: 500.0, 501.0, ..., 524.0
    mock_history = [
        {
            "price": 500.0 + i,
            "open": 499.5 + i,
            "close": 500.0 + i,
            "fetched_at": f"2026-09-{i + 1:02d}T16:00:00Z",
        }
        for i in range(25)
    ]

    profile = compute_trend_profile(mock_history, target_date="2026-09-26")

    assert profile.is_available is True
    assert profile.prior_date == "2026-09-25"
    assert profile.prior_close == 524.0

    # 5-day return: from day 20 (index -6, price 519.0) to day 25 (index -1, price 524.0)
    expected_5d = ((524.0 - 519.0) / 519.0) * 100.0
    assert profile.return_5d_pct is not None
    assert pytest.approx(profile.return_5d_pct, rel=1e-3) == expected_5d

    # 20-day SMA: average of last 20 prices: 505.0 to 524.0 -> average = 514.5
    expected_sma_20 = sum(500.0 + i for i in range(5, 25)) / 20.0
    assert profile.sma_20 is not None
    assert pytest.approx(profile.sma_20, rel=1e-3) == expected_sma_20

    # Distance to SMA20
    expected_dist = ((524.0 - expected_sma_20) / expected_sma_20) * 100.0
    assert profile.sma_20_dist_pct is not None
    assert pytest.approx(profile.sma_20_dist_pct, rel=1e-3) == expected_dist

    # Check summary representation
    summary = profile.summary
    assert "Previous Trading Session (2026-09-25) Close: $524.00" in summary
    assert "5-Day Return" in summary
    assert "20-Day Simple Moving Average (SMA20): $514.50" in summary
    assert "3-Day Direction Sequence" in summary


def test_compute_trend_profile_insufficient_history_for_sma_no_hallucination():
    """Verify that when fewer than 20 bars exist, SMA20 is strictly None and NOT hallucinated."""
    # 12 bars: sufficient for 5-day return, but NOT sufficient for 20-day SMA
    mock_history = [
        {
            "price": 600.0 + i,
            "open": 599.0 + i,
            "close": 600.0 + i,
            "fetched_at": f"2026-10-{i + 1:02d}T16:00:00Z",
        }
        for i in range(12)
    ]

    profile = compute_trend_profile(mock_history, target_date="2026-10-15")

    assert profile.is_available is True
    assert profile.prior_close == 611.0
    assert profile.return_5d_pct is not None

    # CRITICAL: SMA20 must be None to prevent hallucinating non-existent metrics
    assert profile.sma_20 is None
    assert profile.sma_20_dist_pct is None
    assert "20-Day Simple Moving Average" not in profile.summary


def test_compute_trend_profile_insufficient_history_for_5d_return():
    """Verify that when fewer than 5 bars exist, 5-day return is strictly None."""
    mock_history = [
        {"price": 580.0, "open": 579.0, "close": 580.0, "fetched_at": "2026-10-01T16:00:00Z"},
        {"price": 582.0, "open": 580.0, "close": 582.0, "fetched_at": "2026-10-02T16:00:00Z"},
    ]

    profile = compute_trend_profile(mock_history, target_date="2026-10-05")

    assert profile.is_available is True
    assert profile.prior_close == 582.0
    assert profile.return_5d_pct is None
    assert profile.sma_20 is None
    assert "5-Day Return" not in profile.summary
    assert "20-Day Simple Moving Average" not in profile.summary


def test_compute_trend_profile_empty_or_malformed():
    """Verify handling of empty or invalid price histories."""
    assert compute_trend_profile([]).is_available is False
    assert compute_trend_profile([{"price": None}]).is_available is False
    assert compute_trend_profile([{"price": "invalid"}]).is_available is False


def test_compute_trend_profile_zero_lookahead():
    """Verify that bars on or after target_date are strictly filtered out to prevent lookahead."""
    mock_history = [
        {"price": 500.0, "open": 499.0, "close": 500.0, "fetched_at": "2026-10-10T16:00:00Z"},
        {"price": 505.0, "open": 501.0, "close": 505.0, "fetched_at": "2026-10-11T16:00:00Z"},
        {"price": 999.0, "open": 990.0, "close": 999.0, "fetched_at": "2026-10-12T16:00:00Z"},  # Future bar
    ]

    # Target date is 2026-10-12 morning pre-market; bar from 2026-10-12 must be ignored
    profile = compute_trend_profile(mock_history, target_date="2026-10-12")

    assert profile.is_available is True
    assert profile.prior_date == "2026-10-11"
    assert profile.prior_close == 505.0
    assert "999.0" not in profile.summary
