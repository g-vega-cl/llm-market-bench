"""Point-in-time backtest trade settlement and incremental snapshot accounting."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from recipes.portfolio_engine import (
    DEFAULT_CONCURRENCY_CONFIG,
    DEFAULT_SLIPPAGE_BPS,
    DEFAULT_STARTING_CAPITAL,
    PortfolioState,
    apply_portfolio_step,
    compute_total_equity,
    compute_unrealized_midpoint_pnl,
)


@dataclass
class BacktestAccumulator:
    """Mutable accumulator for incremental multi-slot Long-Only backtest settlement."""

    window_dates: list[str]
    starting_capital: float = DEFAULT_STARTING_CAPITAL
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS
    concurrency_config: dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_CONCURRENCY_CONFIG))
    llm_calls_made: int = 0
    intraday_bars: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    daily_close: dict[str, dict[str, float]] = field(default_factory=dict)
    portfolio: PortfolioState = field(init=False)
    day_steps: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.portfolio = PortfolioState(
            cash=float(self.starting_capital),
            peak_equity=float(self.starting_capital),
        )

    def settle_slot(
        self,
        *,
        idx: int,
        slot_label: str,
        signals: list[dict[str, str]],
        slot_prices: dict[str, float],
        tool_calls: list[str],
        output_text: str,
        day_status: str,
        is_final_step: bool = False,
    ) -> None:
        """Apply one 3h slot turn of Long-Only BUY / EXIT signals and record step telemetry."""
        step_res = apply_portfolio_step(
            self.portfolio,
            slot_label=slot_label,
            signals=signals,
            prices=slot_prices,
            concurrency_config=self.concurrency_config,
            slippage_bps=self.slippage_bps,
            is_final_step=is_final_step,
        )
        trades_executed = step_res["trades_opened"] + step_res["trades_closed"]
        self.day_steps.append(
            {
                "day": slot_label,
                "day_index": idx,
                "status": day_status,
                "signals": list(signals),
                "tool_calls": list(tool_calls),
                "output_excerpt": output_text[:600],
                "day_pnl_net": step_res["realized_pnl_net"],
                "trades_executed": trades_executed,
                "trades_skipped": step_res["trades_skipped"],
                "open_positions_count": step_res["open_positions_count"],
                "total_equity": step_res["total_equity"],
            }
        )

    def snapshot(
        self,
        *,
        days_completed: int,
        current_day: str | None,
        latest_prices: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Return an isolated point-in-time snapshot of the running or completed backtest."""
        trades = [dict(t) for t in self.portfolio.trades]
        winning_trades = sum(1 for t in trades if t["pnl_net"] > 0)
        losing_trades = len(trades) - winning_trades
        gross_profit = sum(t["pnl_net"] for t in trades if t["pnl_net"] > 0)
        gross_loss = abs(sum(t["pnl_net"] for t in trades if t["pnl_net"] < 0))
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)
        win_rate = round((winning_trades / len(trades)) * 100.0, 1) if trades else 0.0

        current_equity = compute_total_equity(self.portfolio, latest_prices)
        total_net_pct = (
            round(((current_equity - self.starting_capital) / self.starting_capital) * 100.0, 2)
            if self.starting_capital > 0
            else 0.0
        )
        realized_mid_pnl = sum(t["pnl_midpoint"] for t in trades)
        unrealized_mid_pnl = compute_unrealized_midpoint_pnl(self.portfolio, latest_prices)
        total_mid_pnl = realized_mid_pnl + unrealized_mid_pnl
        total_mid_pct = round((total_mid_pnl / self.starting_capital) * 100.0, 2) if self.starting_capital > 0 else 0.0

        return {
            "mode": "backtest",
            "window_dates": list(self.window_dates),
            "days_completed": days_completed,
            "total_days": len(self.window_dates),
            "current_day": current_day,
            "starting_capital": self.starting_capital,
            "cash": round(self.portfolio.cash, 2),
            "total_equity": round(current_equity, 2),
            "open_positions": [dict(p) for p in self.portfolio.positions],
            "ending_capital_midpoint": round(self.starting_capital + total_mid_pnl, 2),
            "ending_capital_net": round(current_equity, 2),
            "total_return_pct_midpoint": total_mid_pct,
            "total_return_pct_net": total_net_pct,
            "win_rate_pct": win_rate,
            "profit_factor": profit_factor,
            "max_drawdown_pct": round(self.portfolio.max_drawdown_pct, 2),
            "total_trades": len(trades),
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "llm_calls_made": self.llm_calls_made,
            "trades": trades,
            "skipped_trades": [dict(s) for s in self.portfolio.skipped_trades],
            "equity_curve": [dict(pt) for pt in self.portfolio.equity_curve],
            "day_steps": [dict(step) for step in self.day_steps],
        }
