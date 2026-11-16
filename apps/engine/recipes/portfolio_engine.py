"""Shared Long-Only persistent portfolio engine for live_turn and point-in-time backtests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

DEFAULT_STARTING_CAPITAL = 10000.0
DEFAULT_SLIPPAGE_BPS = 5.0
DEFAULT_MAX_OPEN_TRADES = 4
DEFAULT_MAX_EQUITY_PCT_PER_TRADE = 25.0
DEFAULT_CONCURRENCY_CONFIG: dict[str, Any] = {
    "max_open_trades": DEFAULT_MAX_OPEN_TRADES,
    "max_equity_pct_per_trade": DEFAULT_MAX_EQUITY_PCT_PER_TRADE,
}
_MIN_TRADE_NOTIONAL = 10.0


@dataclass
class PortfolioState:
    """Mutable persistent Long-Only portfolio state shared across live and simulated turns."""

    cash: float = DEFAULT_STARTING_CAPITAL
    positions: list[dict[str, Any]] = field(default_factory=list)
    trades: list[dict[str, Any]] = field(default_factory=list)
    skipped_trades: list[dict[str, Any]] = field(default_factory=list)
    equity_curve: list[dict[str, Any]] = field(default_factory=list)
    peak_equity: float = DEFAULT_STARTING_CAPITAL
    max_drawdown_pct: float = 0.0
    last_prices: dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_recipe_row(cls, row: dict[str, Any] | None) -> PortfolioState:
        """Hydrate live paper portfolio state from a public.strategy_recipes row."""
        data = row or {}
        cash = float(data.get("paper_cash") if data.get("paper_cash") is not None else DEFAULT_STARTING_CAPITAL)
        positions = [
            {**p, "ticker": str(p.get("ticker", "")).upper().strip()} for p in (data.get("paper_positions") or [])
        ]
        trades = list(data.get("paper_trades") or [])
        equity_curve = list(data.get("paper_equity_curve") or [])
        open_cost = sum(float(p.get("cost_basis") or 0.0) for p in positions)
        baseline_eq = max(DEFAULT_STARTING_CAPITAL, cash + open_cost)
        peak = max([baseline_eq, *(float(pt.get("equity", baseline_eq)) for pt in equity_curve)], default=baseline_eq)
        max_dd = 0.0
        running_peak = DEFAULT_STARTING_CAPITAL
        for pt in equity_curve:
            eq = float(pt.get("equity", running_peak))
            running_peak = max(running_peak, eq)
            if running_peak > 0:
                max_dd = max(max_dd, ((running_peak - eq) / running_peak) * 100.0)
        return cls(
            cash=cash,
            positions=positions,
            trades=trades,
            equity_curve=equity_curve,
            peak_equity=peak,
            max_drawdown_pct=round(max_dd, 2),
        )


def _normalize_concurrency(concurrency_config: dict[str, Any] | None) -> tuple[int, float]:
    cfg = concurrency_config or {}
    max_open = max(1, int(cfg.get("max_open_trades") or DEFAULT_MAX_OPEN_TRADES))
    pct_per_trade = float(cfg.get("max_equity_pct_per_trade") or DEFAULT_MAX_EQUITY_PCT_PER_TRADE)
    pct_per_trade = max(1.0, min(100.0, pct_per_trade))
    return max_open, pct_per_trade


def _resolve_mark_price(state: PortfolioState, pos: dict[str, Any], px_map: dict[str, float]) -> float:
    tkr = str(pos.get("ticker", "")).upper().strip()
    return float(px_map.get(tkr) or state.last_prices.get(tkr) or pos.get("entry_price") or 0.0)


def compute_total_equity(state: PortfolioState, prices: dict[str, float] | None = None) -> float:
    """Compute mark-to-market equity from cash plus open long positions."""
    px_map = {str(k).upper(): float(v) for k, v in (prices or {}).items() if v}
    holdings_value = sum(
        float(pos.get("shares") or 0.0) * _resolve_mark_price(state, pos, px_map) for pos in state.positions
    )
    return state.cash + holdings_value


def enrich_open_positions(
    state: PortfolioState,
    prices: dict[str, float] | None = None,
    *,
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
) -> list[dict[str, Any]]:
    """Attach canonical mark price, market value, and net-of-slippage unrealized P&L."""
    px_map = {str(k).upper(): float(v) for k, v in (prices or {}).items() if v}
    slip = slippage_bps / 10000.0
    enriched: list[dict[str, Any]] = []
    for raw in state.positions:
        pos = dict(raw)
        shares = float(pos.get("shares") or 0.0)
        entry_px = float(pos.get("entry_price") or 0.0)
        cost_basis = float(pos.get("cost_basis") or (shares * entry_px))
        cur_px = _resolve_mark_price(state, pos, px_map)
        market_val = shares * cur_px
        net_liquidation = market_val * (1.0 - slip)
        unr_pnl = net_liquidation - cost_basis
        unr_pct = (unr_pnl / cost_basis) * 100.0 if cost_basis > 0 else 0.0
        pos["current_price"] = round(cur_px, 4)
        pos["market_value"] = round(market_val, 2)
        pos["unrealized_pnl_net"] = round(unr_pnl, 2)
        pos["unrealized_return_pct"] = round(unr_pct, 2)
        enriched.append(pos)
    return enriched


def compute_unrealized_midpoint_pnl(state: PortfolioState, prices: dict[str, float] | None = None) -> float:
    """Compute zero-slippage unrealized P&L across open long positions."""
    px_map = {str(k).upper(): float(v) for k, v in (prices or {}).items() if v}
    total = 0.0
    for pos in state.positions:
        entry_px = float(pos.get("entry_price") or 0.0)
        cost_basis = float(pos.get("cost_basis") or 0.0)
        if entry_px <= 0 or cost_basis <= 0:
            continue
        mark_px = _resolve_mark_price(state, pos, px_map)
        total += (cost_basis / entry_px) * (mark_px - entry_px)
    return total


def _close_position(
    state: PortfolioState,
    pos: dict[str, Any],
    *,
    exit_px: float,
    exit_time: str,
    exit_reason: str,
    slip: float,
) -> float:
    shares = float(pos["shares"])
    entry_px = float(pos["entry_price"])
    cost_basis = float(pos["cost_basis"])
    proceeds_net = shares * exit_px * (1.0 - slip)
    pnl_net = proceeds_net - cost_basis
    shares_mid = (cost_basis / entry_px) if entry_px > 0 else shares
    pnl_mid = shares_mid * (exit_px - entry_px)
    ret_net = (pnl_net / cost_basis) * 100.0 if cost_basis > 0 else 0.0
    ret_mid = ((exit_px - entry_px) / entry_px) * 100.0 if entry_px > 0 else 0.0

    state.cash += proceeds_net
    state.trades.append(
        {
            "ticker": pos["ticker"],
            "action": "BUY",
            "entry_time": pos["entry_time"],
            "entry_price": round(entry_px, 2),
            "exit_time": exit_time,
            "exit_price": round(exit_px, 2),
            "shares": round(shares, 4),
            "pnl_midpoint": round(pnl_mid, 2),
            "pnl_net": round(pnl_net, 2),
            "return_pct_midpoint": round(ret_mid, 2),
            "return_pct_net": round(ret_net, 2),
            "exit_reason": exit_reason,
            "confidence": 100,
        }
    )
    return pnl_net


def _record_skip(state: PortfolioState, slot_label: str, skip_type: str, reason: str) -> None:
    """Append a structured skipped-signal trace entry to PortfolioState."""
    state.skipped_trades.append({"time": slot_label, "skip_type": skip_type, "reason": reason})


def _partition_signals(
    state: PortfolioState,
    slot_label: str,
    signals: list[dict[str, str]],
) -> tuple[list[str], list[str], int]:
    """Split raw signals into exit tickers and buy tickers under Long-Only rules."""
    held = {str(p["ticker"]).upper() for p in state.positions}
    exits: list[str] = []
    buys: list[str] = []
    skipped = 0
    for sig in signals:
        action = str(sig.get("action", "")).upper().strip()
        ticker = str(sig.get("ticker", "")).upper().strip()
        if not ticker:
            continue
        if action == "EXIT" or (action == "SELL" and ticker in held):
            exits.append(ticker)
        elif action == "SELL":
            skipped += 1
            _record_skip(
                state,
                slot_label,
                "SHORT_NOT_ALLOWED",
                f"SELL {ticker} skipped (Long-Only portfolio has no open {ticker} position)",
            )
        elif action == "BUY":
            buys.append(ticker)
    return exits, buys, skipped


def _process_exits(
    state: PortfolioState,
    slot_label: str,
    exit_tickers: list[str],
    prices: dict[str, float],
    slip: float,
) -> tuple[float, int, int, list[dict[str, Any]]]:
    """Execute explicit EXIT / SELL-long closures and return (realized_pnl, closed, skipped, filled)."""
    realized = 0.0
    closed = 0
    skipped = 0
    filled: list[dict[str, Any]] = []
    for tkr in exit_tickers:
        pos_idx = next((i for i, p in enumerate(state.positions) if str(p.get("ticker", "")).upper() == tkr), None)
        if pos_idx is None:
            skipped += 1
            _record_skip(state, slot_label, "NO_OPEN_POSITION", f"EXIT {tkr} skipped (no open {tkr} position)")
            continue
        exit_px = float(prices.get(tkr) or 0.0)
        if exit_px <= 0:
            skipped += 1
            _record_skip(state, slot_label, "NO_PRICE_DATA", f"Missing bar price to exit {tkr} at {slot_label}")
            continue
        pos = state.positions.pop(pos_idx)
        realized += _close_position(
            state,
            pos,
            exit_px=exit_px,
            exit_time=slot_label,
            exit_reason="SIGNAL_EXIT",
            slip=slip,
        )
        filled.append({"action": "EXIT", "ticker": tkr, "price": round(exit_px, 4)})
        closed += 1
    return realized, closed, skipped, filled


def _process_entries(
    state: PortfolioState,
    slot_label: str,
    buy_tickers: list[str],
    prices: dict[str, float],
    *,
    pre_step_equity: float,
    max_open: int,
    pct_per_trade: float,
    slip: float,
) -> tuple[int, int, list[dict[str, Any]]]:
    """Open new Long positions honoring max_open_trades and allocation caps."""
    opened = 0
    skipped = 0
    filled: list[dict[str, Any]] = []
    for tkr in buy_tickers:
        if any(str(p.get("ticker", "")).upper() == tkr for p in state.positions):
            skipped += 1
            _record_skip(state, slot_label, "ALREADY_HOLDING", f"BUY {tkr} skipped (already holding {tkr})")
            continue
        if len(state.positions) >= max_open:
            skipped += 1
            _record_skip(
                state,
                slot_label,
                "MAX_OPEN_TRADES",
                f"BUY {tkr} skipped (open slots full: {len(state.positions)}/{max_open})",
            )
            continue
        entry_px = float(prices.get(tkr) or 0.0)
        if entry_px <= 0:
            skipped += 1
            _record_skip(state, slot_label, "NO_PRICE_DATA", f"Missing bar price to buy {tkr} at {slot_label}")
            continue
        alloc = round(min(state.cash, pre_step_equity * (pct_per_trade / 100.0)), 4)
        if alloc < _MIN_TRADE_NOTIONAL:
            skipped += 1
            _record_skip(
                state,
                slot_label,
                "INSUFFICIENT_CASH",
                f"BUY {tkr} skipped (available cash ${state.cash:.2f} < ${_MIN_TRADE_NOTIONAL:.0f})",
            )
            continue
        shares = alloc / (entry_px * (1.0 + slip))
        state.cash -= alloc
        state.positions.append(
            {
                "ticker": tkr,
                "side": "LONG",
                "shares": round(shares, 6),
                "entry_price": round(entry_px, 4),
                "entry_time": slot_label,
                "cost_basis": alloc,
            }
        )
        filled.append({"action": "BUY", "ticker": tkr, "price": round(entry_px, 4)})
        opened += 1
    return opened, skipped, filled


def _close_remaining_positions(
    state: PortfolioState,
    slot_label: str,
    prices: dict[str, float],
    slip: float,
) -> tuple[float, int]:
    """Close all lingering open positions at END_OF_WINDOW on the final backtest slot."""
    if not state.positions:
        return 0.0, 0
    realized = 0.0
    closed = 0
    remaining = list(state.positions)
    state.positions.clear()
    for pos in remaining:
        exit_px = _resolve_mark_price(state, pos, prices)
        realized += _close_position(
            state,
            pos,
            exit_px=exit_px,
            exit_time=slot_label,
            exit_reason="END_OF_WINDOW",
            slip=slip,
        )
        closed += 1
    return realized, closed


def apply_portfolio_step(
    state: PortfolioState,
    *,
    slot_label: str,
    signals: list[dict[str, str]],
    prices: dict[str, float],
    concurrency_config: dict[str, Any] | None = None,
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
    is_final_step: bool = False,
) -> dict[str, Any]:
    """Apply one turn of Long-Only BUY / EXIT signals to PortfolioState.

    Exits execute before entries so freed cash and position slots can be reused in the
    same turn. Remaining positions are marked to market on every turn and closed with
    exit_reason='END_OF_WINDOW' when is_final_step=True.
    """
    norm_prices = {str(k).upper(): float(v) for k, v in prices.items() if v and float(v) > 0}
    state.last_prices.update(norm_prices)
    max_open, pct_per_trade = _normalize_concurrency(concurrency_config)
    slip = slippage_bps / 10000.0
    pre_step_equity = compute_total_equity(state, norm_prices)

    exit_tickers, buy_tickers, part_skips = _partition_signals(state, slot_label, signals)
    exit_pnl, exits_closed, exit_skips, filled_exits = _process_exits(
        state, slot_label, exit_tickers, norm_prices, slip
    )
    trades_opened, entry_skips, filled_buys = _process_entries(
        state,
        slot_label,
        buy_tickers,
        norm_prices,
        pre_step_equity=pre_step_equity,
        max_open=max_open,
        pct_per_trade=pct_per_trade,
        slip=slip,
    )
    eow_pnl, eow_closed = (
        _close_remaining_positions(state, slot_label, norm_prices, slip) if is_final_step else (0.0, 0)
    )
    step_realized_pnl_net = exit_pnl + eow_pnl
    trades_closed = exits_closed + eow_closed
    trades_skipped = part_skips + exit_skips + entry_skips

    post_equity = compute_total_equity(state, norm_prices)
    state.peak_equity = max(state.peak_equity, post_equity)
    dd = ((state.peak_equity - post_equity) / state.peak_equity) * 100.0 if state.peak_equity > 0 else 0.0
    state.max_drawdown_pct = max(state.max_drawdown_pct, dd)
    state.equity_curve.append({"time": slot_label, "equity": round(post_equity, 2)})

    return {
        "slot_label": slot_label,
        "total_equity": round(post_equity, 2),
        "cash": round(state.cash, 4),
        "open_positions_count": len(state.positions),
        "trades_opened": trades_opened,
        "trades_closed": trades_closed,
        "trades_skipped": trades_skipped,
        "executed_signals": [*filled_exits, *filled_buys],
        "realized_pnl_net": round(step_realized_pnl_net, 2),
    }


def format_portfolio_prompt_block(
    state: PortfolioState,
    *,
    current_prices: dict[str, float] | None = None,
    concurrency_config: dict[str, Any] | None = None,
) -> str:
    """Format current portfolio cash, open positions, and unrealized P&L for LLM prompts."""
    max_open, pct_per_trade = _normalize_concurrency(concurrency_config)
    px_map = current_prices or {}
    total_equity = compute_total_equity(state, px_map)
    header = (
        "[Current Portfolio State (Long-Only)]:\n"
        f"- Cash Available: ${state.cash:,.2f} | Total Equity: ${total_equity:,.2f} "
        f"| Open Slots: {len(state.positions)} / {max_open} ({pct_per_trade:.1f}% max/trade)"
    )
    if not state.positions:
        return f"{header}\n- Open Positions: None (100% cash)"

    lines = [header, "- Open Positions:"]
    for pos in state.positions:
        tkr = str(pos["ticker"]).upper()
        shares = float(pos["shares"])
        entry_px = float(pos["entry_price"])
        cur_px = float(px_map.get(tkr) or entry_px)
        unr_pct = ((cur_px - entry_px) / entry_px) * 100.0 if entry_px > 0 else 0.0
        lines.append(
            f"  * {tkr}: {shares:.4f} shares | Entry ${entry_px:.2f} @ {pos['entry_time']} "
            f"| Current ${cur_px:.2f} ({unr_pct:+.2f}%)"
        )
    return "\n".join(lines)
