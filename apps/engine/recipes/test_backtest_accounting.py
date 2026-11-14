"""Unit tests for BacktestAccumulator incremental settlement and snapshots."""

from __future__ import annotations

from recipes.backtest_accounting import BacktestAccumulator


def test_accumulator_settles_buy_and_sell_and_emits_isolated_snapshots():
    acc = BacktestAccumulator(window_dates=["2026-02-02", "2026-02-03", "2026-02-04"], slippage_bps=5.0)
    acc.daily_close["NVDA"] = {"2026-02-02": 100.0, "2026-02-03": 110.0, "2026-02-04": 105.0}

    snap0 = acc.snapshot(days_completed=0, current_day="2026-02-02")
    assert snap0["days_completed"] == 0
    assert snap0["trades"] == []

    acc.llm_calls_made += 1
    acc.settle_day(
        idx=0,
        day_str="2026-02-02",
        signals=[{"action": "BUY", "ticker": "NVDA"}],
        tool_calls=["get_stock_quote(NVDA)"],
        output_text='[{"action": "BUY", "ticker": "NVDA"}]',
        day_status="completed",
    )
    snap1 = acc.snapshot(days_completed=1, current_day="2026-02-03")
    assert len(snap1["trades"]) == 1
    assert snap1["trades"][0]["pnl_midpoint"] == 100.0
    assert snap1["trades"][0]["pnl_net"] == 99.0
    assert snap1["win_rate_pct"] == 100.0
    assert snap0["trades"] == []  # Earlier snapshot remains untouched

    acc.llm_calls_made += 1
    acc.settle_day(
        idx=1,
        day_str="2026-02-03",
        signals=[{"action": "BUY", "ticker": "MISSING"}],
        tool_calls=[],
        output_text="BUY MISSING",
        day_status="completed",
    )
    snap2 = acc.snapshot(days_completed=2, current_day="2026-02-04")
    assert len(snap2["skipped_trades"]) == 1
    assert snap2["day_steps"][1]["trades_skipped"] == 1
