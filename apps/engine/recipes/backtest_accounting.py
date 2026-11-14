"""Point-in-time backtest trade settlement and incremental snapshot accounting."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BacktestAccumulator:
    """Mutable accumulator for incremental day-by-day backtest settlement."""

    window_dates: list[str]
    starting_capital: float = 10000.0
    slippage_bps: float = 5.0
    equity: float = 10000.0
    peak: float = 10000.0
    max_dd: float = 0.0
    llm_calls_made: int = 0
    daily_close: dict[str, dict[str, float]] = field(default_factory=dict)
    trades: list[dict[str, Any]] = field(default_factory=list)
    skipped_trades: list[dict[str, Any]] = field(default_factory=list)
    equity_curve: list[dict[str, Any]] = field(default_factory=list)
    day_steps: list[dict[str, Any]] = field(default_factory=list)

    def settle_day(
        self,
        *,
        idx: int,
        day_str: str,
        signals: list[dict[str, str]],
        tool_calls: list[str],
        output_text: str,
        day_status: str,
    ) -> None:
        """Settle signals emitted on simulated day ``idx`` against next-day close."""
        total_days = len(self.window_dates)
        next_day = self.window_dates[idx + 1] if idx + 1 < total_days else None
        slip = self.slippage_bps / 10000.0
        day_pnl_net = 0.0
        trades_executed = 0
        trades_skipped = 0

        for sig in signals:
            tkr = sig["ticker"]
            prices = self.daily_close.get(tkr, {})
            entry_px = prices.get(day_str)
            exit_px = prices.get(next_day) if next_day else None
            if entry_px and exit_px and entry_px > 0:
                raw_ret = (exit_px - entry_px) / entry_px
                if sig["action"] == "SELL":
                    raw_ret = -raw_ret
                net_ret = raw_ret - (2 * slip)
                pnl_mid = 1000.0 * raw_ret
                pnl_net = 1000.0 * net_ret
                self.equity += pnl_net
                day_pnl_net += pnl_net
                trades_executed += 1
                self.peak = max(self.peak, self.equity)
                dd = ((self.peak - self.equity) / self.peak) * 100.0 if self.peak > 0 else 0.0
                self.max_dd = max(self.max_dd, dd)
                self.trades.append(
                    {
                        "ticker": tkr,
                        "action": sig["action"],
                        "entry_time": day_str,
                        "entry_price": round(entry_px, 2),
                        "exit_time": next_day,
                        "exit_price": round(exit_px, 2),
                        "shares": round(1000.0 / entry_px, 4),
                        "pnl_midpoint": round(pnl_mid, 2),
                        "pnl_net": round(pnl_net, 2),
                        "return_pct_midpoint": round(raw_ret * 100.0, 2),
                        "return_pct_net": round(net_ret * 100.0, 2),
                        "exit_reason": "NEXT_DAY_CLOSE",
                        "confidence": 100,
                    }
                )
            else:
                trades_skipped += 1
                self.skipped_trades.append(
                    {
                        "time": day_str,
                        "skip_type": "NO_PRICE_DATA",
                        "reason": f"Missing daily bar for {tkr} on {day_str} -> {next_day or 'EOF'}",
                    }
                )

        self.equity_curve.append({"time": day_str, "equity": round(self.equity, 2)})
        self.day_steps.append(
            {
                "day": day_str,
                "day_index": idx,
                "status": day_status,
                "signals": signals,
                "tool_calls": tool_calls,
                "output_excerpt": output_text[:600],
                "day_pnl_net": round(day_pnl_net, 2),
                "trades_executed": trades_executed,
                "trades_skipped": trades_skipped,
            }
        )

    def snapshot(self, *, days_completed: int, current_day: str | None) -> dict[str, Any]:
        """Return an immutable point-in-time snapshot of the running or completed backtest."""
        winning_trades = sum(1 for t in self.trades if t["pnl_net"] > 0)
        losing_trades = len(self.trades) - winning_trades
        gross_profit = sum(t["pnl_net"] for t in self.trades if t["pnl_net"] > 0)
        gross_loss = abs(sum(t["pnl_net"] for t in self.trades if t["pnl_net"] < 0))
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)
        win_rate = round((winning_trades / len(self.trades)) * 100.0, 1) if self.trades else 0.0
        total_net_pct = round(((self.equity - self.starting_capital) / self.starting_capital) * 100.0, 2)
        total_mid_pnl = sum(t["pnl_midpoint"] for t in self.trades)
        total_mid_pct = round((total_mid_pnl / self.starting_capital) * 100.0, 2)

        return {
            "mode": "backtest",
            "window_dates": list(self.window_dates),
            "days_completed": days_completed,
            "total_days": len(self.window_dates),
            "current_day": current_day,
            "starting_capital": self.starting_capital,
            "ending_capital_midpoint": round(self.starting_capital + total_mid_pnl, 2),
            "ending_capital_net": round(self.equity, 2),
            "total_return_pct_midpoint": total_mid_pct,
            "total_return_pct_net": total_net_pct,
            "win_rate_pct": win_rate,
            "profit_factor": profit_factor,
            "max_drawdown_pct": round(self.max_dd, 2),
            "total_trades": len(self.trades),
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "llm_calls_made": self.llm_calls_made,
            "trades": list(self.trades),
            "skipped_trades": list(self.skipped_trades),
            "equity_curve": list(self.equity_curve),
            "day_steps": list(self.day_steps),
        }
