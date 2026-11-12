"""Data models and trade closing helpers for recipe timeline backtesting."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from recipes.indicators import Bar


@dataclass
class Position:
    ticker: str
    entry_time: datetime
    entry_price: float
    entry_bar_idx: int
    action: str  # BUY or SELL
    shares: int
    stop_loss_price: float
    target_price: float
    max_hold_bars: int
    exit_on_session_close: bool
    catalyst_headline: str = ""
    confidence: float = 100.0


@dataclass
class CompletedTrade:
    ticker: str
    entry_time: str
    entry_price: float
    exit_time: str
    exit_price: float
    action: str
    shares: int
    pnl_midpoint: float
    pnl_net: float
    return_pct_midpoint: float
    return_pct_net: float
    exit_reason: str
    catalyst_headline: str = ""
    confidence: float = 100.0


@dataclass
class SkippedTrade:
    time: str
    reason: str
    skip_type: str  # TECHNICAL_BLOCKED, NO_CATALYST, LLM_REJECTED, BUDGET_EXCEEDED
    headline: str = ""


def close_position(
    pos: Position,
    exit_bar: Bar,
    reason: str,
    slippage_rate: float,
) -> CompletedTrade:
    """Calculate dual PnL (Midpoint vs Net Slippage) and return a CompletedTrade."""
    exit_p = exit_bar.close
    if reason == "TARGET_PROFIT":
        exit_p = pos.target_price
    elif reason == "STOP_LOSS":
        exit_p = pos.stop_loss_price

    if pos.action == "BUY":
        pnl_mid = (exit_p - pos.entry_price) * pos.shares
        ret_mid = ((exit_p / pos.entry_price) - 1.0) * 100.0 if pos.entry_price > 0 else 0.0
        net_entry = pos.entry_price * (1.0 + slippage_rate)
        net_exit = exit_p * (1.0 - slippage_rate)
        pnl_net = (net_exit - net_entry) * pos.shares
        ret_net = ((net_exit / net_entry) - 1.0) * 100.0 if net_entry > 0 else 0.0
    else:  # SELL / SHORT
        pnl_mid = (pos.entry_price - exit_p) * pos.shares
        ret_mid = ((pos.entry_price - exit_p) / pos.entry_price) * 100.0 if pos.entry_price > 0 else 0.0
        net_entry = pos.entry_price * (1.0 - slippage_rate)
        net_exit = exit_p * (1.0 + slippage_rate)
        pnl_net = (net_entry - net_exit) * pos.shares
        ret_net = ((net_entry - net_exit) / net_entry) * 100.0 if net_entry > 0 else 0.0

    return CompletedTrade(
        ticker=pos.ticker,
        entry_time=pos.entry_time.isoformat(),
        entry_price=round(pos.entry_price, 4),
        exit_time=exit_bar.time_utc.isoformat(),
        exit_price=round(exit_p, 4),
        action=pos.action,
        shares=pos.shares,
        pnl_midpoint=round(pnl_mid, 2),
        pnl_net=round(pnl_net, 2),
        return_pct_midpoint=round(ret_mid, 2),
        return_pct_net=round(ret_net, 2),
        exit_reason=reason,
        catalyst_headline=pos.catalyst_headline,
        confidence=pos.confidence,
    )


def build_backtest_summary(
    starting_capital: float,
    equity_midpoint: float,
    equity_net: float,
    all_trades: list[CompletedTrade],
    skipped_trades: list[SkippedTrade],
    equity_curve: list[dict[str, Any]],
    weeks_breakdown: list[dict[str, Any]],
    llm_call_count: int,
) -> dict[str, Any]:
    """Calculate final returns, win rates, drawdowns, and package result dictionary."""
    total_trades = len(all_trades)
    wins = [t for t in all_trades if t.pnl_net > 0]
    losses = [t for t in all_trades if t.pnl_net < 0]
    win_rate = round((len(wins) / total_trades) * 100.0, 1) if total_trades > 0 else 0.0

    gross_profit = sum(t.pnl_net for t in wins)
    gross_loss = abs(sum(t.pnl_net for t in losses))
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)

    peak = starting_capital
    max_dd_pct = 0.0
    for pt in equity_curve:
        eq = pt["equity_net"]
        if eq > peak:
            peak = eq
        dd = ((peak - eq) / peak) * 100.0 if peak > 0 else 0.0
        if dd > max_dd_pct:
            max_dd_pct = dd

    return {
        "starting_capital": starting_capital,
        "ending_capital_midpoint": round(equity_midpoint, 2),
        "ending_capital_net": round(equity_net, 2),
        "total_return_pct_midpoint": round(((equity_midpoint / starting_capital) - 1.0) * 100.0, 2),
        "total_return_pct_net": round(((equity_net / starting_capital) - 1.0) * 100.0, 2),
        "total_trades": total_trades,
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate_pct": win_rate,
        "profit_factor": profit_factor,
        "max_drawdown_pct": round(max_dd_pct, 2),
        "llm_calls_made": llm_call_count,
        "equity_curve": equity_curve,
        "trades": [asdict(t) for t in all_trades],
        "skipped_trades": [asdict(s) for s in skipped_trades],
        "weeks_breakdown": weeks_breakdown,
    }
