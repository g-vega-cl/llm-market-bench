"""Quantitative Analytics, Sized Return Optimization, and Feature Conditioning for Autoresearch."""

from __future__ import annotations

import math
from typing import Any


def calculate_sized_trading_pnl(records: list[dict[str, Any]]) -> dict[str, float]:
    """Calculate position-sized daily trading PnL, Sharpe ratio, and drawdown metrics."""
    if not records:
        return {
            "trade_count": 0,
            "cumulative_return_pct": 0.0,
            "unweighted_return_pct": 0.0,
            "mean_daily_return_pct": 0.0,
            "daily_return_std": 0.0,
            "annualized_sharpe": 0.0,
            "win_loss_payoff_ratio": 0.0,
            "profit_factor": 0.0,
            "max_drawdown_pct": 0.0,
        }

    sized_returns: list[float] = []
    unweighted_returns: list[float] = []
    gains: list[float] = []
    losses: list[float] = []

    for r in records:
        open_p = float(r.get("open_price") or 0.0)
        close_p = float(r.get("close_price") or 0.0)
        if open_p <= 0.0:
            continue

        raw_ret = (close_p - open_p) / open_p
        pred_dir = str(r.get("predicted_direction", "UP")).upper()
        sign = 1.0 if pred_dir == "UP" else -1.0

        # Position size scales with confidence: 50% -> 0.0 (no edge), 100% -> 1.0 (full Kelly size)
        conf = float(r.get("confidence", 50.0))
        size = max(0.0, min(1.0, (conf - 50.0) / 50.0))

        sized_ret = sign * raw_ret * size
        unweighted_ret = sign * raw_ret

        sized_returns.append(sized_ret)
        unweighted_returns.append(unweighted_ret)

        if sized_ret > 0:
            gains.append(sized_ret)
        elif sized_ret < 0:
            losses.append(abs(sized_ret))

    if not sized_returns:
        return {
            "trade_count": 0,
            "cumulative_return_pct": 0.0,
            "unweighted_return_pct": 0.0,
            "mean_daily_return_pct": 0.0,
            "daily_return_std": 0.0,
            "annualized_sharpe": 0.0,
            "win_loss_payoff_ratio": 0.0,
            "profit_factor": 0.0,
            "max_drawdown_pct": 0.0,
        }

    n = len(sized_returns)
    cum_ret = sum(sized_returns) * 100.0
    unw_ret = sum(unweighted_returns) * 100.0
    mean_ret = sum(sized_returns) / n

    variance = sum((r - mean_ret) ** 2 for r in sized_returns) / n if n > 1 else 0.0
    std_ret = math.sqrt(variance)

    # Annualized Sharpe (assuming 252 trading days)
    sharpe = (mean_ret / std_ret * math.sqrt(252.0)) if std_ret > 1e-8 else 0.0

    # Profit Factor & Payoff Ratio
    total_gains = sum(gains)
    total_losses = sum(losses)
    profit_factor = (total_gains / total_losses) if total_losses > 0 else (99.0 if total_gains > 0 else 0.0)

    mean_win = (total_gains / len(gains)) if gains else 0.0
    mean_loss = (total_losses / len(losses)) if losses else 0.0
    payoff_ratio = (mean_win / mean_loss) if mean_loss > 0 else (99.0 if mean_win > 0 else 0.0)

    # Maximum Drawdown of Sized Equity Curve
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    for r in sized_returns:
        equity *= 1.0 + r
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd

    return {
        "trade_count": n,
        "cumulative_return_pct": round(cum_ret, 2),
        "unweighted_return_pct": round(unw_ret, 2),
        "mean_daily_return_pct": round(mean_ret * 100.0, 4),
        "daily_return_std": round(std_ret, 6),
        "annualized_sharpe": round(sharpe, 2),
        "win_loss_payoff_ratio": round(payoff_ratio, 2),
        "profit_factor": round(profit_factor, 2),
        "max_drawdown_pct": round(max_dd * 100.0, 2),
    }


def format_normalized_quant_vector(session: dict[str, Any]) -> str:
    """Format a standardized quantitative tabular summary from session point-in-time data."""
    quotes = session.get("quotes") or {}
    options = session.get("options") or {}

    lines = [
        "=== STANDARDIZED QUANTITATIVE FEATURE VECTOR ===",
    ]

    # 1. Overnight Gaps & Cross-Asset Delta
    spy_gap = quotes.get("SPY", {}).get("gap_pct")
    qqq_gap = quotes.get("QQQ", {}).get("gap_pct")
    tlt_gap = quotes.get("TLT", {}).get("gap_pct")

    if spy_gap is not None:
        lines.append(f"- SPY Gap: {spy_gap:+.2f}%")
    else:
        lines.append("- SPY Gap: Not Provided / N/A")

    if qqq_gap is not None and spy_gap is not None:
        spread = qqq_gap - spy_gap
        lines.append(f"- QQQ vs SPY Gap Spread: {spread:+.2f}%")
    elif qqq_gap is not None:
        lines.append(f"- QQQ Gap: {qqq_gap:+.2f}%")

    if tlt_gap is not None:
        lines.append(f"- Bond Yield Proxy (TLT Gap): {tlt_gap:+.2f}%")

    # 2. Options Positioning & Skew
    pc_vol = options.get("put_call_volume_ratio")
    pc_oi = options.get("put_call_oi_ratio")
    max_pain = options.get("max_pain_strike")
    atm_iv = options.get("atm_implied_vol")

    if pc_vol is not None:
        lines.append(f"- Options Put/Call Volume Ratio: {pc_vol:.2f}")
    if pc_oi is not None:
        lines.append(f"- Options Put/Call Open Interest Ratio: {pc_oi:.2f}")

    if max_pain is not None:
        open_p = float(session.get("open_price") or 0.0)
        dist_str = ""
        if open_p > 0:
            dist_pct = (open_p - max_pain) / open_p * 100.0
            dist_str = f" ({dist_pct:+.2f}% vs open)"
        lines.append(f"- Options Max Pain Strike: {max_pain:.2f}{dist_str}")

    if atm_iv is not None:
        lines.append(f"- ATM Implied Volatility: {atm_iv:.2f}%")

    if len(lines) == 1:
        lines.append("- Point-in-time quantitative indicators: Not Provided / N/A")

    return "\n".join(lines)


def create_walk_forward_splits(
    sessions: list[dict[str, Any]],
    n_splits: int = 3,
    min_train_size: int = 10,
) -> list[tuple[list[dict[str, Any]], list[dict[str, Any]]]]:
    """Generate expanding-window walk-forward cross validation folds."""
    if len(sessions) < min_train_size + n_splits:
        # Not enough data for meaningful walk-forward
        return [(sessions, [])]

    # Ensure chronological order
    sorted_sessions = sorted(sessions, key=lambda s: str(s.get("target_date", "")))
    total = len(sorted_sessions)

    test_pool_size = total - min_train_size
    test_chunk_size = max(1, test_pool_size // n_splits)

    folds: list[tuple[list[dict[str, Any]], list[dict[str, Any]]]] = []

    for i in range(n_splits):
        train_end = min_train_size + i * test_chunk_size
        test_end = total if i == n_splits - 1 else min(total, train_end + test_chunk_size)

        train_fold = sorted_sessions[:train_end]
        test_fold = sorted_sessions[train_end:test_end]

        if train_fold and test_fold:
            folds.append((train_fold, test_fold))

    return folds


def passes_two_sided_gate_discrete(
    bal_metrics: dict[str, float],
    min_recall_up: float = 54.0,
    min_recall_down: float = 54.0,
    min_bal_acc: float = 58.0,
    min_mcc: float = 0.20,
) -> tuple[bool, str]:
    """Validate that candidate exhibits genuine two-sided predictive edge with discrete sample boundary awareness."""
    rec_up = bal_metrics.get("recall_up_pct", 0.0)
    rec_down = bal_metrics.get("recall_down_pct", 0.0)
    bal_acc = bal_metrics.get("balanced_accuracy_pct", 0.0)
    mcc = bal_metrics.get("mcc", 0.0)

    if rec_up < min_recall_up:
        return False, f"Recall UP {rec_up:.1f}% < {min_recall_up:.1f}% (Bear-biased)"
    if rec_down < min_recall_down:
        return False, f"Recall DOWN {rec_down:.1f}% < {min_recall_down:.1f}% (Bull-biased)"
    if bal_acc < min_bal_acc:
        return False, f"Balanced Acc {bal_acc:.1f}% < {min_bal_acc:.1f}%"
    if mcc < min_mcc:
        return False, f"MCC {mcc:.3f} < {min_mcc:.3f}"

    return True, "Passed two-sided gate"
