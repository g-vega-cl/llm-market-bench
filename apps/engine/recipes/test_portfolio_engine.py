"""Hermetic tests for shared Long-Only persistent portfolio engine."""

from __future__ import annotations

import pytest

from recipes.portfolio_engine import (  # noqa: F401 - tested below
    DEFAULT_CONCURRENCY_CONFIG,
    PortfolioState,
    apply_portfolio_step,
    format_portfolio_prompt_block,
)


def test_long_only_multi_day_hold_exit_and_cash_conservation():
    state = PortfolioState(cash=10000.0)
    cfg = {"max_open_trades": 4, "max_equity_pct_per_trade": 25.0}

    # Turn 1: BUY NVDA at $100 -> 25% of $10,000 = $2,500 deployed (+5bps slip)
    res1 = apply_portfolio_step(
        state,
        slot_label="2026-04-06 09:30 ET",
        signals=[{"action": "BUY", "ticker": "NVDA"}],
        prices={"NVDA": 100.0},
        concurrency_config=cfg,
        slippage_bps=5.0,
    )
    assert res1["trades_opened"] == 1
    assert res1["trades_closed"] == 0
    assert len(state.positions) == 1
    # Whole shares only: 24 shares at $100 + 5bps slip = $2,401.20 spent, not the full $2,500 alloc
    assert state.positions[0]["shares"] == 24
    assert state.cash == pytest.approx(7598.8)
    assert len(state.trades) == 0  # Not closed next bar! Held across turns!

    # Turn 2: HOLD (no signals) at $110 -> equity marks up cleanly, still open
    apply_portfolio_step(
        state,
        slot_label="2026-04-06 12:30 ET",
        signals=[],
        prices={"NVDA": 110.0},
        concurrency_config=cfg,
        slippage_bps=5.0,
    )
    assert len(state.positions) == 1
    assert state.equity_curve[-1]["equity"] > 10200.0

    # Turn 3: EXIT NVDA at $110 -> realizes ~+10% minus 10bps round-trip slippage
    res3 = apply_portfolio_step(
        state,
        slot_label="2026-04-07 09:30 ET",
        signals=[{"action": "EXIT", "ticker": "NVDA"}],
        prices={"NVDA": 110.0},
        concurrency_config=cfg,
        slippage_bps=5.0,
    )
    assert res3["trades_closed"] == 1
    assert len(state.positions) == 0
    assert len(state.trades) == 1
    trade = state.trades[0]
    assert trade["ticker"] == "NVDA"
    assert trade["action"] == "BUY"
    assert trade["entry_time"] == "2026-04-06 09:30 ET"
    assert trade["exit_time"] == "2026-04-07 09:30 ET"
    assert trade["exit_reason"] == "SIGNAL_EXIT"
    assert trade["shares"] == 24
    assert trade["pnl_net"] == pytest.approx(24 * 110.0 * (1 - 0.0005) - 2401.2, abs=0.01)
    # Cash conservation: starting 10000 + realized net P&L == ending cash
    assert round(10000.0 + trade["pnl_net"], 2) == round(state.cash, 2)


def test_long_only_rejects_flat_short_and_enforces_max_4_open_trades():
    state = PortfolioState(cash=10000.0)
    cfg = {"max_open_trades": 4, "max_equity_pct_per_trade": 25.0}

    apply_portfolio_step(
        state,
        slot_label="2026-04-06 09:30 ET",
        signals=[
            {"action": "SELL", "ticker": "TSLA"},  # flat short -> rejected!
            {"action": "BUY", "ticker": "NVDA"},
            {"action": "BUY", "ticker": "AMZN"},
            {"action": "BUY", "ticker": "MSFT"},
            {"action": "BUY", "ticker": "AAPL"},
            {"action": "BUY", "ticker": "META"},  # 5th long -> rejected by max_open_trades=4!
        ],
        prices={"TSLA": 200.0, "NVDA": 100.0, "AMZN": 200.0, "MSFT": 400.0, "AAPL": 200.0, "META": 500.0},
        concurrency_config=cfg,
    )

    assert [p["ticker"] for p in state.positions] == ["NVDA", "AMZN", "MSFT", "AAPL"]
    skip_types = [s["skip_type"] for s in state.skipped_trades]
    assert "SHORT_NOT_ALLOWED" in skip_types
    assert "MAX_OPEN_TRADES" in skip_types


def test_sell_on_held_long_closes_position_and_final_step_closes_end_of_window():
    state = PortfolioState(cash=10000.0)
    cfg = DEFAULT_CONCURRENCY_CONFIG

    apply_portfolio_step(
        state,
        slot_label="2026-04-06 09:30 ET",
        signals=[{"action": "BUY", "ticker": "NVDA"}, {"action": "BUY", "ticker": "AMZN"}],
        prices={"NVDA": 100.0, "AMZN": 200.0},
        concurrency_config=cfg,
    )
    # SELL on held NVDA acts as exit; AMZN remains open until final step END_OF_WINDOW
    apply_portfolio_step(
        state,
        slot_label="2026-04-06 15:30 ET",
        signals=[{"action": "SELL", "ticker": "NVDA"}],
        prices={"NVDA": 105.0, "AMZN": 210.0},
        concurrency_config=cfg,
        is_final_step=True,
    )
    assert len(state.positions) == 0
    assert len(state.trades) == 2
    by_tkr = {t["ticker"]: t for t in state.trades}
    assert by_tkr["NVDA"]["exit_reason"] == "SIGNAL_EXIT"
    assert by_tkr["AMZN"]["exit_reason"] == "END_OF_WINDOW"


def test_format_portfolio_prompt_block_renders_holdings_and_unrealized_pct():
    state = PortfolioState(
        cash=7500.0,
        positions=[
            {
                "ticker": "NVDA",
                "side": "LONG",
                "shares": 25.0,
                "entry_price": 100.0,
                "entry_time": "2026-04-06 09:30 ET",
                "cost_basis": 2500.0,
            }
        ],
    )
    text = format_portfolio_prompt_block(
        state, current_prices={"NVDA": 110.0}, concurrency_config=DEFAULT_CONCURRENCY_CONFIG
    )
    assert "Cash Available: $7,500.00" in text
    assert "Open Slots: 1 / 4" in text
    assert "NVDA: 25 shares | Entry $100.00 @ 2026-04-06 09:30 ET | Current $110.00 (+10.00%)" in text


def test_prompt_block_keeps_legacy_fractional_rows_readable():
    state = PortfolioState(
        cash=7500.0,
        positions=[
            {
                "ticker": "DIS",
                "side": "LONG",
                "shares": 20.474849,
                "entry_price": 122.04,
                "entry_time": "2026-11-19 09:30 ET",
                "cost_basis": 2500.0,
            }
        ],
    )
    text = format_portfolio_prompt_block(state, current_prices={"DIS": 122.04})
    assert "DIS: 20.4748 shares | Entry $122.04" in text


def test_entries_size_to_whole_shares_and_charge_actual_spend():
    state = PortfolioState(cash=10000.0)
    res = apply_portfolio_step(
        state,
        slot_label="2026-11-19 09:30 ET",
        signals=[{"action": "BUY", "ticker": "DIS"}],
        prices={"DIS": 122.04},
        concurrency_config={"max_open_trades": 4, "max_equity_pct_per_trade": 25.0},
        slippage_bps=5.0,
    )
    assert res["trades_opened"] == 1
    pos = state.positions[0]
    assert pos["shares"] == 20
    assert isinstance(pos["shares"], int)
    expected_spend = round(20 * 122.04 * 1.0005, 4)
    assert pos["cost_basis"] == pytest.approx(expected_spend, abs=1e-6)
    # Cash must equal exactly what was spent: no silent leak from the $2,500 notional cap
    assert state.cash == pytest.approx(10000.0 - expected_spend, abs=1e-6)


def test_alloc_below_one_share_is_skipped_not_rounded_up():
    state = PortfolioState(cash=10000.0)
    res = apply_portfolio_step(
        state,
        slot_label="2026-11-19 09:30 ET",
        signals=[{"action": "BUY", "ticker": "BRKA"}],
        prices={"BRKA": 700000.0},
        concurrency_config={"max_open_trades": 4, "max_equity_pct_per_trade": 25.0},
        slippage_bps=5.0,
    )
    assert res["trades_opened"] == 0
    assert state.positions == []
    assert state.cash == 10000.0
    assert "ALLOCATION_BELOW_ONE_SHARE" in [s["skip_type"] for s in state.skipped_trades]


def test_lowercase_held_ticker_exits_and_computes_clean_pnl_midpoint():
    from recipes.portfolio_engine import PortfolioState, apply_portfolio_step

    state = PortfolioState.from_recipe_row(
        {
            "paper_cash": 7500.0,
            "paper_positions": [
                {
                    "ticker": "nvda",
                    "shares": 24.975,
                    "entry_price": 100.0,
                    "entry_time": "2026-04-06 09:30 ET",
                    "cost_basis": 2500.0,
                }
            ],
            "paper_trades": [],
            "paper_equity_curve": [],
        },
    )
    assert [p["ticker"] for p in state.positions] == ["NVDA"]

    res = apply_portfolio_step(
        state,
        signals=[{"action": "EXIT", "ticker": "NVDA"}],
        prices={"NVDA": 110.0},
        slot_label="2026-04-06 12:30 ET",
        slippage_bps=10.0,
    )
    assert len(state.positions) == 0
    assert res["trades_closed"] == 1
    assert len(res["executed_signals"]) == 1
    trade = state.trades[-1]
    assert trade["pnl_midpoint"] == 250.0  # (2500 / 100.0) * (110.0 - 100.0), zero entry slippage leak
