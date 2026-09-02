"""Pure mathematical analytics for Post-Earnings Announcement Drift (PEAD), SUE, and Sloan accruals."""

from dataclasses import dataclass

import numpy as np


@dataclass
class EarningsAlphaMetrics:
    """Calculated metrics for an earnings announcement."""

    eps_surprise: float
    sue_score: float
    is_top_decile_sue: bool
    quarters_analyzed_count: int
    has_sufficient_earnings_history: bool
    has_zero_variance_guard: bool


def calculate_sue(
    actual_eps: float,
    estimated_eps: float,
    historical_surprises: list[float],
    min_epsilon_std: float = 0.01,
    min_required_quarters: int = 4,
    top_decile_sue_threshold: float = 2.0,
) -> EarningsAlphaMetrics:
    """Calculate Standardized Unexpected Earnings (SUE).

    SUE = (Actual EPS - Estimated EPS) / StdDev(Historical Surprises)
    """
    eps_surprise = actual_eps - estimated_eps
    quarters_count = len(historical_surprises)
    has_sufficient_history = quarters_count >= min_required_quarters

    if quarters_count == 0:
        return EarningsAlphaMetrics(
            eps_surprise=eps_surprise,
            sue_score=0.0,
            is_top_decile_sue=False,
            quarters_analyzed_count=0,
            has_sufficient_earnings_history=False,
            has_zero_variance_guard=False,
        )

    std_surprise = float(np.std(historical_surprises))
    has_zero_variance_guard = False

    if std_surprise <= 0.0:
        std_surprise = min_epsilon_std
        has_zero_variance_guard = True

    sue_score = eps_surprise / std_surprise
    is_top_decile = has_sufficient_history and (sue_score >= top_decile_sue_threshold) and (eps_surprise > 0)

    return EarningsAlphaMetrics(
        eps_surprise=eps_surprise,
        sue_score=sue_score,
        is_top_decile_sue=is_top_decile,
        quarters_analyzed_count=quarters_count,
        has_sufficient_earnings_history=has_sufficient_history,
        has_zero_variance_guard=has_zero_variance_guard,
    )


def calculate_sloan_accrual_quality(
    net_income: float,
    operating_cash_flow: float,
    total_assets: float,
    max_clean_accrual_ratio: float = 0.10,
) -> tuple[float, bool]:
    """Calculate the Sloan Accrual Quality ratio.

    Accrual Ratio = (Net Income - Operating Cash Flow) / Total Assets
    If total_assets is 0 or negative, falls back to Net Income normalization.
    Returns (accrual_ratio, is_sloan_accrual_clean).
    """
    denominator = total_assets if total_assets > 0 else (abs(net_income) if net_income != 0 else 1.0)
    accrual_ratio = (net_income - operating_cash_flow) / denominator
    is_clean = accrual_ratio <= max_clean_accrual_ratio
    return accrual_ratio, is_clean


def calculate_post_earnings_drift(
    stock_report_close: float,
    stock_current_price: float,
    spy_report_close: float,
    spy_current_price: float,
) -> tuple[float, float]:
    """Calculate post-earnings price drift % and benchmark alpha % vs S&P 500 (SPY).

    Returns (post_earnings_drift_pct, post_earnings_alpha_vs_spy).
    """
    if stock_report_close <= 0 or spy_report_close <= 0:
        return 0.0, 0.0

    drift_pct = ((stock_current_price - stock_report_close) / stock_report_close) * 100.0
    spy_return_pct = ((spy_current_price - spy_report_close) / spy_report_close) * 100.0
    alpha_pct = drift_pct - spy_return_pct

    return drift_pct, alpha_pct


def check_pre_earnings_runup(
    price_20d_prior: float,
    price_at_earnings: float,
    max_clean_runup_pct: float = 25.0,
) -> tuple[float, bool]:
    """Check if the stock had an extreme parabolic run-up before the announcement.

    Returns (pre_earnings_20d_return_pct, has_extreme_pre_earnings_runup).
    """
    if price_20d_prior <= 0:
        return 0.0, False

    runup_pct = ((price_at_earnings - price_20d_prior) / price_20d_prior) * 100.0
    has_extreme_runup = runup_pct > max_clean_runup_pct
    return runup_pct, has_extreme_runup
