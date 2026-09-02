"""Unit tests for the earnings alpha and PEAD mathematical analytics engine."""

import pytest

from analytics.earnings_alpha import (
    calculate_post_earnings_drift,
    calculate_sloan_accrual_quality,
    calculate_sue,
    check_pre_earnings_runup,
)


def test_sue_standard_calculation():
    """Verify SUE calculation for standard 8-quarter history."""
    # 8 historical quarters of surprise: [0.05, 0.03, 0.07, 0.05, 0.04, 0.06, 0.05, 0.05]
    # std dev = ~0.01118
    # Recent report: actual=1.20, est=1.15 => surprise = +0.05
    # Historical surprises:
    historical_surprises = [0.05, 0.03, 0.07, 0.05, 0.04, 0.06, 0.05, 0.05]
    actual_eps = 1.20
    estimated_eps = 1.15

    result = calculate_sue(
        actual_eps=actual_eps,
        estimated_eps=estimated_eps,
        historical_surprises=historical_surprises,
    )

    assert result.eps_surprise == pytest.approx(0.05, rel=1e-3)
    assert result.sue_score > 2.0
    assert result.is_top_decile_sue is True
    assert result.quarters_analyzed_count == 8
    assert result.has_sufficient_earnings_history is True
    assert result.has_zero_variance_guard is False


def test_sue_zero_variance_epsilon_guard():
    """Verify division by zero protection when historical surprise is constant."""
    historical_surprises = [0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05]
    actual_eps = 1.20
    estimated_eps = 1.15

    result = calculate_sue(
        actual_eps=actual_eps,
        estimated_eps=estimated_eps,
        historical_surprises=historical_surprises,
        min_epsilon_std=0.01,
    )

    # Standard deviation is 0.0, so it uses 0.01
    assert result.eps_surprise == pytest.approx(0.05, rel=1e-3)
    assert result.sue_score == pytest.approx(5.0, rel=1e-3)
    assert result.has_zero_variance_guard is True
    assert result.has_sufficient_earnings_history is True


def test_sue_insufficient_history():
    """Verify insufficient history flag when fewer than 4 quarters exist."""
    historical_surprises = [0.05, 0.03]
    actual_eps = 1.20
    estimated_eps = 1.15

    result = calculate_sue(
        actual_eps=actual_eps,
        estimated_eps=estimated_eps,
        historical_surprises=historical_surprises,
    )

    assert result.quarters_analyzed_count == 2
    assert result.has_sufficient_earnings_history is False
    assert result.is_top_decile_sue is False


def test_sue_negative_miss_filtered():
    """Verify negative earnings surprise produces negative SUE and is not top decile."""
    historical_surprises = [0.05, 0.03, 0.07, 0.05, 0.04, 0.06, 0.05, 0.05]
    actual_eps = 1.10
    estimated_eps = 1.15

    result = calculate_sue(
        actual_eps=actual_eps,
        estimated_eps=estimated_eps,
        historical_surprises=historical_surprises,
    )

    assert result.eps_surprise == pytest.approx(-0.05, rel=1e-3)
    assert result.sue_score < 0
    assert result.is_top_decile_sue is False


def test_sloan_accrual_quality_clean():
    """Verify high cash-conversion (low accrual) passes clean quality check."""
    # Net Income: 100M, Operating Cash Flow: 110M, Total Assets: 1000M
    # Accrual = (Net Income - OCF) / Total Assets = (100 - 110) / 1000 = -0.01 (-1%)
    accrual_ratio, is_clean = calculate_sloan_accrual_quality(
        net_income=100_000_000,
        operating_cash_flow=110_000_000,
        total_assets=1_000_000_000,
    )

    assert accrual_ratio == pytest.approx(-0.01, rel=1e-3)
    assert is_clean is True


def test_sloan_accrual_quality_flagged():
    """Verify high non-cash accounting accruals are flagged as low quality."""
    # Net Income: 100M, Operating Cash Flow: 20M, Total Assets: 500M
    # Accrual = (100 - 20) / 500 = 80 / 500 = +0.16 (+16% of assets)
    accrual_ratio, is_clean = calculate_sloan_accrual_quality(
        net_income=100_000_000,
        operating_cash_flow=20_000_000,
        total_assets=500_000_000,
        max_clean_accrual_ratio=0.10,
    )

    assert accrual_ratio == pytest.approx(0.16, rel=1e-3)
    assert is_clean is False


def test_post_earnings_drift_and_alpha():
    """Verify post-earnings drift calculation and SPY benchmark alpha."""
    # Stock entry post-print: $100.00, current: $106.00 => +6.0%
    # SPY entry: $500.00, current: $510.00 => +2.0%
    # Alpha = +6.0% - +2.0% = +4.0%
    drift_pct, alpha_pct = calculate_post_earnings_drift(
        stock_report_close=100.0,
        stock_current_price=106.0,
        spy_report_close=500.0,
        spy_current_price=510.0,
    )

    assert drift_pct == pytest.approx(6.0, rel=1e-3)
    assert alpha_pct == pytest.approx(4.0, rel=1e-3)


def test_pre_earnings_runup_detection():
    """Verify extreme pre-announcement rally triggers runup risk flag."""
    # Stock rallied from $80 to $104 in the 20 days leading up to earnings (+30%)
    runup_pct, has_extreme_runup = check_pre_earnings_runup(
        price_20d_prior=80.0,
        price_at_earnings=104.0,
        max_clean_runup_pct=25.0,
    )

    assert runup_pct == pytest.approx(30.0, rel=1e-3)
    assert has_extreme_runup is True
