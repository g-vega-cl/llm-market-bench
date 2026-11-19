"""Unit tests for BacktestAccumulator incremental multi-slot Long-Only settlement and snapshots."""

from __future__ import annotations

import pytest

from recipes.backtest_accounting import BacktestAccumulator


def test_accumulator_tracks_multi_slot_long_only_positions_and_snapshots():
    acc = BacktestAccumulator(
        window_dates=["2026-04-06 09:30 ET", "2026-04-06 12:30 ET", "2026-04-07 09:30 ET"],
        starting_capital=10000.0,
        slippage_bps=5.0,
        concurrency_config={"max_open_trades": 4, "max_equity_pct_per_trade": 25.0},
    )

    snap0 = acc.snapshot(days_completed=0, current_day="2026-04-06 09:30 ET")
    assert snap0["days_completed"] == 0
    assert snap0["total_days"] == 3
    assert snap0["trades"] == []
    assert snap0["open_positions"] == []

    # Slot 0: BUY NVDA @ 100.00 -> stays open across turns!
    acc.llm_calls_made += 1
    acc.settle_slot(
        idx=0,
        slot_label="2026-04-06 09:30 ET",
        signals=[{"action": "BUY", "ticker": "NVDA"}],
        slot_prices={"NVDA": 100.0},
        tool_calls=["get_stock_quote(NVDA)"],
        output_text='[{"action": "BUY", "ticker": "NVDA"}]',
        day_status="completed",
    )
    snap1 = acc.snapshot(days_completed=1, current_day="2026-04-06 12:30 ET", latest_prices={"NVDA": 105.0})
    assert len(snap1["trades"]) == 0  # Held open, NOT prematurely closed!
    assert len(snap1["open_positions"]) == 1
    assert snap1["day_steps"][0]["trades_executed"] == 1
    assert snap1["total_equity"] > 10100.0
    assert snap0["open_positions"] == []  # Earlier snapshot isolated

    # Slot 1: HOLD + BUY MISSING -> MISSING skipped cleanly while NVDA stays open
    acc.llm_calls_made += 1
    acc.settle_slot(
        idx=1,
        slot_label="2026-04-06 12:30 ET",
        signals=[{"action": "BUY", "ticker": "MISSING"}],
        slot_prices={"NVDA": 105.0},
        tool_calls=[],
        output_text='[{"action": "BUY", "ticker": "MISSING"}]',
        day_status="completed",
    )
    snap2 = acc.snapshot(days_completed=2, current_day="2026-04-07 09:30 ET", latest_prices={"NVDA": 105.0})
    assert len(snap2["skipped_trades"]) == 1
    assert snap2["day_steps"][1]["trades_skipped"] == 1
    assert len(snap2["open_positions"]) == 1

    # Slot 2 (final): EXIT NVDA @ 110.00
    acc.llm_calls_made += 1
    acc.settle_slot(
        idx=2,
        slot_label="2026-04-07 09:30 ET",
        signals=[{"action": "EXIT", "ticker": "NVDA"}],
        slot_prices={"NVDA": 110.0},
        tool_calls=["get_stock_quote(NVDA)"],
        output_text='[{"action": "EXIT", "ticker": "NVDA"}]',
        day_status="completed",
        is_final_step=True,
    )
    snap3 = acc.snapshot(days_completed=3, current_day="2026-04-07 09:30 ET")
    assert len(snap3["open_positions"]) == 0
    assert len(snap3["trades"]) == 1
    assert snap3["trades"][0]["exit_reason"] == "SIGNAL_EXIT"
    # 24 whole shares @ $100 spent $2,401.20; exit at $110 nets $2,638.68
    assert snap3["trades"][0]["shares"] == 24
    assert snap3["trades"][0]["pnl_net"] == pytest.approx(237.48, abs=0.01)
    assert snap3["win_rate_pct"] == 100.0


def test_snapshot_ending_capital_midpoint_includes_open_position_mtm():
    acc = BacktestAccumulator(
        window_dates=["2026-04-06 09:30 ET", "2026-04-06 12:30 ET"],
        starting_capital=10000.0,
        slippage_bps=0.0,
        concurrency_config={"max_open_trades": 4, "max_equity_pct_per_trade": 25.0},
    )
    acc.settle_slot(
        idx=0,
        slot_label="2026-04-06 09:30 ET",
        signals=[{"action": "BUY", "ticker": "NVDA"}],
        slot_prices={"NVDA": 100.0},
        tool_calls=[],
        output_text='[{"action": "BUY", "ticker": "NVDA"}]',
        day_status="completed",
    )
    snap = acc.snapshot(days_completed=1, current_day="2026-04-06 12:30 ET", latest_prices={"NVDA": 120.0})
    assert snap["ending_capital_midpoint"] == 10500.0
    assert snap["total_return_pct_midpoint"] == 5.0


def test_snapshot_enriches_open_positions_with_mtm_and_stores_full_trace():
    acc = BacktestAccumulator(
        window_dates=["2026-04-06 09:30 ET"],
        starting_capital=10000.0,
        slippage_bps=5.0,
        concurrency_config={"max_open_trades": 4, "max_equity_pct_per_trade": 25.0},
    )
    long_output = "X" * 800 + '\n[{"action": "BUY", "ticker": "NVDA"}]'
    trace = {
        "rounds": [{"round": 1, "reasoning": "Strong momentum", "tool_calls": []}],
        "forced_final_synthesis": False,
    }
    acc.settle_slot(
        idx=0,
        slot_label="2026-04-06 09:30 ET",
        signals=[{"action": "BUY", "ticker": "NVDA"}],
        slot_prices={"NVDA": 100.0},
        tool_calls=['get_stock_quote({"ticker": "NVDA"})'],
        output_text=long_output,
        day_status="completed",
        prompt="Hydrated slot prompt",
        trace=trace,
    )
    snap = acc.snapshot(days_completed=1, current_day="2026-04-06 09:30 ET", latest_prices={"NVDA": 110.0})
    pos = snap["open_positions"][0]
    assert pos["ticker"] == "NVDA"
    assert pos["current_price"] == 110.0
    # 24 whole shares: $2,640 mark, net of the 5bps exit slip $2,639.68 vs $2,401.20 cost
    assert pos["shares"] == 24
    assert pos["market_value"] == 2640.0
    assert pos["unrealized_pnl_net"] == pytest.approx(237.48, abs=0.01)
    assert pos["unrealized_return_pct"] > 9.0

    step = snap["day_steps"][0]
    assert step["prompt"] == "Hydrated slot prompt"
    assert step["full_output"] == long_output
    assert step["trace"] == trace
