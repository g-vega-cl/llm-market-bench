"""Unit tests for Small/Mid-Cap Quality Compounder analytics and exit rules.

Pure unit tests with zero external network calls, verifying:
1. GAAP net income and profitability filtering (weeding out zombies).
2. Free cash flow generation and Sloan accrual anomaly protection.
3. ROIC and balance sheet solvency checks.
4. Momentum (12-month relative strength) calculation from daily bars.
5. Exit conditions: Zero-ceiling hold rule vs. fundamental zombie liquidation.
"""

import pytest

from analytics.smid_quality import (
    calculate_momentum_12m,
    evaluate_exit_condition,
    evaluate_quality_metrics,
)


def _make_sample_income_statements(quarterly_net_income: list[float]) -> list[dict]:
    """Helper to generate FMP /stable/income-statement fixture."""
    return [
        {
            "date": f"2026-0{i+1}-30",
            "netIncome": ni,
            "operatingIncome": ni * 1.2,
            "revenue": ni * 5.0 if ni > 0 else 50000000.0,
            "incomeTaxExpense": ni * 0.2 if ni > 0 else 0.0,
        }
        for i, ni in enumerate(quarterly_net_income)
    ]


def _make_sample_cash_flow_statements(quarterly_fcf: list[float]) -> list[dict]:
    """Helper to generate FMP /stable/cash-flow-statement fixture."""
    return [
        {
            "date": f"2026-0{i+1}-30",
            "freeCashFlow": fcf,
            "operatingCashFlow": fcf + 1000000.0,
            "capitalExpenditure": -1000000.0,
        }
        for i, fcf in enumerate(quarterly_fcf)
    ]


def _make_sample_balance_sheets(
    equity: float = 100000000.0,
    debt: float = 20000000.0,
    cash: float = 10000000.0,
) -> list[dict]:
    """Helper to generate FMP /stable/balance-sheet-statement fixture."""
    return [
        {
            "date": "2026-06-30",
            "totalStockholdersEquity": equity,
            "totalDebt": debt,
            "cashAndCashEquivalents": cash,
        }
    ]


def test_quality_metrics_pass_profitable_firm():
    """A company with 4 profitable quarters and positive FCF must pass the quality screen."""
    income_stmts = _make_sample_income_statements([25000000.0, 30000000.0, 28000000.0, 35000000.0])
    cf_stmts = _make_sample_cash_flow_statements([20000000.0, 22000000.0, 25000000.0, 30000000.0])
    balance_sheets = _make_sample_balance_sheets(equity=200000000.0, debt=30000000.0, cash=40000000.0)

    result = evaluate_quality_metrics(income_stmts, cf_stmts, balance_sheets)

    assert result["is_quality_pass"] is True
    assert result["ttm_net_income"] == pytest.approx(118000000.0)
    assert result["ttm_fcf"] == pytest.approx(97000000.0)
    assert result["roic"] > 0.10  # > 10% ROIC requirement


def test_quality_metrics_rejects_unprofitable_zombie():
    """A company with negative TTM net income must be rejected as a zombie firm."""
    income_stmts = _make_sample_income_statements([-50000000.0, 10000000.0, 5000000.0, 2000000.0])
    cf_stmts = _make_sample_cash_flow_statements([5000000.0, 5000000.0, 5000000.0, 5000000.0])
    balance_sheets = _make_sample_balance_sheets()

    result = evaluate_quality_metrics(income_stmts, cf_stmts, balance_sheets)

    assert result["is_quality_pass"] is False
    assert result["ttm_net_income"] < 0
    assert "negative_ttm_net_income" in result["rejection_reasons"]


def test_quality_metrics_rejects_negative_fcf():
    """A company with positive paper income but negative cumulative cash flow must fail."""
    income_stmts = _make_sample_income_statements([10000000.0, 12000000.0, 15000000.0, 11000000.0])
    cf_stmts = _make_sample_cash_flow_statements([-30000000.0, -20000000.0, -10000000.0, 5000000.0])
    balance_sheets = _make_sample_balance_sheets()

    result = evaluate_quality_metrics(income_stmts, cf_stmts, balance_sheets)

    assert result["is_quality_pass"] is False
    assert result["ttm_fcf"] < 0
    assert "negative_ttm_fcf" in result["rejection_reasons"]


def test_quality_metrics_rejects_excessive_debt():
    """A company with extreme debt leverage must fail solvency checks."""
    income_stmts = _make_sample_income_statements([5000000.0, 5000000.0, 5000000.0, 5000000.0])
    cf_stmts = _make_sample_cash_flow_statements([4000000.0, 4000000.0, 4000000.0, 4000000.0])
    # Equity = $10M, Debt = $100M -> Debt/Equity = 10.0 (unsafe)
    balance_sheets = _make_sample_balance_sheets(equity=10000000.0, debt=100000000.0, cash=5000000.0)

    result = evaluate_quality_metrics(income_stmts, cf_stmts, balance_sheets)

    assert result["is_quality_pass"] is False
    assert "excessive_leverage" in result["rejection_reasons"]


def test_quality_metrics_insufficient_quarters_graceful():
    """A company with fewer than 4 quarters of reporting must be skipped without crashing."""
    income_stmts = _make_sample_income_statements([10000000.0, 15000000.0])
    cf_stmts = _make_sample_cash_flow_statements([8000000.0, 12000000.0])
    balance_sheets = _make_sample_balance_sheets()

    result = evaluate_quality_metrics(income_stmts, cf_stmts, balance_sheets)

    assert result["is_quality_pass"] is False
    assert "insufficient_history" in result["rejection_reasons"]


def test_calculate_momentum_12m_valid():
    """Verifies 12-month momentum calculation from daily candlestick bars."""
    bars = [{"c": 100.0 + (i * 0.5)} for i in range(252)]
    # First close = 100.0, Last close = 100.0 + 251 * 0.5 = 225.5
    # Return = (225.5 - 100.0) / 100.0 * 100 = 125.5%
    mom = calculate_momentum_12m(bars)
    assert mom == pytest.approx(125.5)


def test_calculate_momentum_12m_insufficient_bars():
    """Fewer than 120 trading days should return None to prevent spurious ranking."""
    bars = [{"c": 100.0} for _ in range(50)]
    assert calculate_momentum_12m(bars) is None


# Exit Condition Tests


def test_exit_condition_zero_ceiling_retention():
    """Holding grew from $3B to $35B, now a large cap. Positive FCF and earnings. Must NOT be sold."""
    holding_info = {
        "ticker": "DECK",
        "entry_market_cap": 3000000000.0,
        "current_market_cap": 35000000000.0,  # Now a $35B large-cap!
    }
    income_stmts = _make_sample_income_statements([50000000.0, 60000000.0, 55000000.0, 70000000.0])
    cf_stmts = _make_sample_cash_flow_statements([45000000.0, 50000000.0, 48000000.0, 65000000.0])
    balance_sheets = _make_sample_balance_sheets()

    should_sell, reason = evaluate_exit_condition(holding_info, income_stmts, cf_stmts, balance_sheets)

    assert should_sell is False
    assert reason == "hold_quality_winner"


def test_exit_condition_liquidate_when_unprofitable_zombie():
    """Holding suffered a collapse in earnings and TTM net income turned negative. Must be sold."""
    holding_info = {
        "ticker": "FAIL",
        "entry_market_cap": 2000000000.0,
        "current_market_cap": 1500000000.0,
    }
    # TTM net income = -80M + 5M + 5M + 10M = -60M
    income_stmts = _make_sample_income_statements([-80000000.0, 5000000.0, 5000000.0, 10000000.0])
    cf_stmts = _make_sample_cash_flow_statements([1000000.0, 2000000.0, 1000000.0, 2000000.0])
    balance_sheets = _make_sample_balance_sheets()

    should_sell, reason = evaluate_exit_condition(holding_info, income_stmts, cf_stmts, balance_sheets)

    assert should_sell is True
    assert reason == "unprofitable_zombie"


def test_exit_condition_liquidate_on_two_consecutive_negative_fcf():
    """Holding produced negative free cash flow for 2 consecutive quarters. Must be sold."""
    holding_info = {
        "ticker": "BURN",
        "entry_market_cap": 4000000000.0,
        "current_market_cap": 3800000000.0,
    }
    income_stmts = _make_sample_income_statements([5000000.0, 5000000.0, 5000000.0, 5000000.0])
    # Most recent two quarters had negative FCF
    cf_stmts = _make_sample_cash_flow_statements([-15000000.0, -10000000.0, 5000000.0, 5000000.0])
    balance_sheets = _make_sample_balance_sheets()

    should_sell, reason = evaluate_exit_condition(holding_info, income_stmts, cf_stmts, balance_sheets)

    assert should_sell is True
    assert reason == "cash_burn_two_quarters"


def test_exit_condition_liquidate_on_debt_spike():
    """Holding's leverage spiked to dangerous distress levels. Must be sold."""
    holding_info = {
        "ticker": "LEVG",
        "entry_market_cap": 2500000000.0,
        "current_market_cap": 2100000000.0,
    }
    income_stmts = _make_sample_income_statements([2000000.0, 2000000.0, 2000000.0, 2000000.0])
    cf_stmts = _make_sample_cash_flow_statements([1000000.0, 1000000.0, 1000000.0, 1000000.0])
    balance_sheets = _make_sample_balance_sheets(equity=10000000.0, debt=120000000.0, cash=2000000.0)

    should_sell, reason = evaluate_exit_condition(holding_info, income_stmts, cf_stmts, balance_sheets)

    assert should_sell is True
    assert reason == "debt_distress"
