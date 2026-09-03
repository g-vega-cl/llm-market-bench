"""Small/Mid-Cap Quality and Momentum Analytics.

Implements empirical factor logic based on:
1. Asness, Frazzini, Israel, Moskowitz, & Pedersen (2018): Quality-controlled size factor (eliminating unprofitable zombies).
2. Sloan (1996): Cash-flow accrual validation (avoiding paper earnings without cash flow).
3. Jegadeesh & Titman (1993): 12-month relative strength momentum.
4. The Zero-Ceiling Exit Model: Holding compounding winners indefinitely unless fundamentals fail.
"""

from typing import Any

DEFAULT_CORPORATE_TAX_RATE = 0.21
MIN_ACCEPTABLE_ROIC = 0.10  # 10% ROIC
MAX_SAFE_DEBT_TO_EQUITY = 3.0
MIN_BARS_FOR_MOMENTUM = 120


def evaluate_quality_metrics(
    income_stmts: list[dict],
    cash_flow_stmts: list[dict],
    balance_sheets: list[dict],
) -> dict[str, Any]:
    """Evaluates trailing 4 quarters of fundamentals to filter out unprofitable or distressed firms."""
    if len(income_stmts) < 4 or len(cash_flow_stmts) < 4 or not balance_sheets:
        return {
            "is_quality_pass": False,
            "ttm_net_income": 0.0,
            "ttm_fcf": 0.0,
            "roic": 0.0,
            "debt_to_equity": 0.0,
            "rejection_reasons": ["insufficient_history"],
        }

    rejection_reasons: list[str] = []

    # 1. TTM GAAP Net Income (S&P 600 rule: eliminate zombies)
    ttm_net_income = sum(float(q.get("netIncome") or 0.0) for q in income_stmts[:4])
    if ttm_net_income <= 0:
        rejection_reasons.append("negative_ttm_net_income")

    # 2. TTM Free Cash Flow (Sloan accrual check)
    ttm_fcf = sum(float(q.get("freeCashFlow") or 0.0) for q in cash_flow_stmts[:4])
    if ttm_fcf <= 0:
        rejection_reasons.append("negative_ttm_fcf")

    # 3. ROIC Calculation: (Operating Income * (1 - tax_rate)) / Invested Capital
    ttm_op_income = sum(float(q.get("operatingIncome") or 0.0) for q in income_stmts[:4])
    ttm_tax = sum(float(q.get("incomeTaxExpense") or 0.0) for q in income_stmts[:4])

    tax_rate = (
        max(0.0, min(0.35, ttm_tax / ttm_op_income))
        if ttm_op_income > 0 and ttm_tax > 0
        else DEFAULT_CORPORATE_TAX_RATE
    )

    bs = balance_sheets[0]
    equity = float(bs.get("totalStockholdersEquity") or 0.0)
    debt = float(bs.get("totalDebt") or 0.0)
    cash = float(bs.get("cashAndCashEquivalents") or 0.0)

    debt_to_equity = (debt / equity) if equity > 0 else (999.0 if debt > 0 else 0.0)
    if debt_to_equity > MAX_SAFE_DEBT_TO_EQUITY:
        rejection_reasons.append("excessive_leverage")

    invested_capital = max(1.0, equity + debt - cash)
    nopat = ttm_op_income * (1.0 - tax_rate)
    roic = nopat / invested_capital

    if roic < MIN_ACCEPTABLE_ROIC and "negative_ttm_net_income" not in rejection_reasons:
        rejection_reasons.append("insufficient_roic")

    is_quality_pass = len(rejection_reasons) == 0

    return {
        "is_quality_pass": is_quality_pass,
        "ttm_net_income": ttm_net_income,
        "ttm_fcf": ttm_fcf,
        "roic": roic,
        "debt_to_equity": debt_to_equity,
        "rejection_reasons": rejection_reasons,
    }


def calculate_momentum_12m(daily_bars: list[dict]) -> float | None:
    """Computes 12-month relative strength return from daily price bars."""
    if len(daily_bars) < MIN_BARS_FOR_MOMENTUM:
        return None

    first_close = float(daily_bars[0].get("c") or 0.0)
    last_close = float(daily_bars[-1].get("c") or 0.0)

    if first_close <= 0:
        return None

    return ((last_close - first_close) / first_close) * 100.0


def evaluate_exit_condition(
    holding_info: dict,
    income_stmts: list[dict],
    cash_flow_stmts: list[dict],
    balance_sheets: list[dict],
) -> tuple[bool, str]:
    """Evaluates whether an existing holding should be sold.

    Invariant: We NEVER sell because a company grew too large (Zero-Ceiling Rule).
    We only sell if fundamentals break:
    1. TTM GAAP Net Income < 0 (Unprofitable Zombie).
    2. Negative Free Cash Flow for two consecutive quarters (Cash Bleed).
    3. Severe Debt Distress (Debt / Equity > 3.0).
    """
    if len(income_stmts) < 4:
        return False, "insufficient_data_hold"

    # 1. Unprofitable Zombie check
    ttm_net_income = sum(float(q.get("netIncome") or 0.0) for q in income_stmts[:4])
    if ttm_net_income < 0:
        return True, "unprofitable_zombie"

    # 2. Consecutive Cash Burn check (last 2 quarters)
    if len(cash_flow_stmts) >= 2:
        q0_fcf = float(cash_flow_stmts[0].get("freeCashFlow") or 0.0)
        q1_fcf = float(cash_flow_stmts[1].get("freeCashFlow") or 0.0)
        if q0_fcf < 0 and q1_fcf < 0:
            return True, "cash_burn_two_quarters"

    # 3. Debt distress check
    if balance_sheets:
        bs = balance_sheets[0]
        equity = float(bs.get("totalStockholdersEquity") or 0.0)
        debt = float(bs.get("totalDebt") or 0.0)
        debt_to_equity = (debt / equity) if equity > 0 else (999.0 if debt > 0 else 0.0)
        if debt_to_equity > MAX_SAFE_DEBT_TO_EQUITY:
            return True, "debt_distress"

    return False, "hold_quality_winner"


def rank_and_select_candidates(
    candidates: list[dict],
    target_count: int = 10,
) -> list[dict]:
    """Filters candidate stocks for quality and positive momentum, ranking by composite factor score."""
    eligible: list[dict] = []

    for cand in candidates:
        qual = cand.get("quality") or {}
        if not qual.get("is_quality_pass"):
            continue

        mom = cand.get("momentum_12m")
        if mom is None or mom <= 0:
            continue

        roic = float(qual.get("roic") or 0.0)
        # Composite score: 40% weight to ROIC (scaled by 100), 60% weight to 12M momentum
        composite_score = (roic * 100.0 * 0.4) + (mom * 0.6)
        cand_copy = dict(cand)
        cand_copy["composite_score"] = composite_score
        eligible.append(cand_copy)

    # Sort descending by composite score
    eligible.sort(key=lambda x: x["composite_score"], reverse=True)
    return eligible[:target_count]
