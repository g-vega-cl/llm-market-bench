"""Spec-driven Hypothesis property-based tests for portfolio accounting, Reg T, and zero lookahead."""

from copy import deepcopy

from hypothesis import example, given, settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule

from core.config import MIN_TRADE_VALUE
from execution.reg_t_validation import calculate_reg_t_metrics, validate_trade_compliance
from recipes.backtest_accounting import BacktestAccumulator
from recipes.portfolio_engine import (
    PortfolioState,
    apply_portfolio_step,
    compute_total_equity,
)

TICKERS = ("AAPL", "MSFT", "NVDA", "SPY", "TLT")

price_map_st = st.dictionaries(
    keys=st.sampled_from(TICKERS),
    values=st.floats(min_value=5.0, max_value=1500.0, allow_nan=False, allow_infinity=False),
    min_size=1,
    max_size=5,
)

signal_st = st.fixed_dictionaries(
    {
        "action": st.sampled_from(["BUY", "EXIT", "SELL"]),
        "ticker": st.sampled_from(TICKERS),
    }
)


@settings(max_examples=80, deadline=100)
@example(
    starting_capital=16152.0,
    steps=[
        ({"AAPL": 5.0}, []),
        ({"AAPL": 5.0, "NVDA": 5.625}, [{"action": "BUY", "ticker": "NVDA"}]),
        ({"AAPL": 5.0, "MSFT": 5.0, "NVDA": 5.0}, []),
    ],
    max_open=1,
    pct_per_trade=7.0,
    slippage_bps=0.0,
)
@given(
    starting_capital=st.floats(min_value=1000.0, max_value=100_000.0, allow_nan=False, allow_infinity=False),
    steps=st.lists(st.tuples(price_map_st, st.lists(signal_st, max_size=5)), min_size=1, max_size=10),
    max_open=st.integers(min_value=1, max_value=5),
    pct_per_trade=st.floats(min_value=5.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    slippage_bps=st.floats(min_value=0.0, max_value=50.0, allow_nan=False, allow_infinity=False),
)
def test_portfolio_conservation_and_long_only_invariants(
    starting_capital, steps, max_open, pct_per_trade, slippage_bps
):
    """Portfolio steps must conserve cash + net realized PnL, stay long-only, and liquidate on final step."""
    state = PortfolioState(cash=starting_capital, peak_equity=starting_capital)
    cfg = {"max_open_trades": max_open, "max_equity_pct_per_trade": pct_per_trade}

    for idx, (prices, signals) in enumerate(steps):
        is_last = idx == len(steps) - 1
        apply_portfolio_step(
            state,
            slot_label=f"2026-11-{idx + 1:02d}T10:00",
            signals=signals,
            prices=prices,
            concurrency_config=cfg,
            slippage_bps=slippage_bps,
            is_final_step=is_last,
        )
        assert state.cash >= -1e-4, f"Cash went negative: {state.cash}"
        assert len(state.positions) <= max_open
        seen_tickers: set[str] = set()
        for pos in state.positions:
            assert pos["side"] == "LONG"
            assert isinstance(pos["shares"], int) and pos["shares"] >= 1
            assert pos["ticker"] not in seen_tickers, "Duplicate open lot for same ticker"
            seen_tickers.add(pos["ticker"])

    assert state.positions == [], "Final step must liquidate all open positions"
    realized_pnl_net = sum(float(t["pnl_net"]) for t in state.trades)
    assert abs(state.cash - (starting_capital + realized_pnl_net)) <= (len(state.trades) * 0.01 + 1e-3)


@settings(max_examples=80, deadline=100)
@given(
    cash_balance=st.floats(min_value=-5000.0, max_value=250_000.0, allow_nan=False, allow_infinity=False),
    qty=st.integers(min_value=0, max_value=500),
    cost_basis=st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
    mkt_price=st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
    trade_cost=st.floats(min_value=0.01, max_value=300_000.0, allow_nan=False, allow_infinity=False),
    signal=st.sampled_from(["BUY", "SELL"]),
    is_sell_tool_used=st.booleans(),
)
def test_reg_t_cash_only_buying_power_and_floor_invariants(
    cash_balance, qty, cost_basis, mkt_price, trade_cost, signal, is_sell_tool_used
):
    """Reg T must clamp buying_power at max(0, cash), bound max_affordable_shares, and enforce BUY/SELL floors."""
    positions = {"SPY": {"quantity": qty, "average_cost_basis": cost_basis}} if qty > 0 else {}
    metrics = calculate_reg_t_metrics(cash_balance, positions, {"SPY": mkt_price})

    assert metrics.buying_power == max(0.0, cash_balance)
    assert abs(metrics.total_equity - (cash_balance + qty * mkt_price)) < 1e-5

    verdict = validate_trade_compliance(
        portfolio_metrics=metrics,
        estimated_trade_cost=trade_cost,
        ticker="AAPL",
        price=mkt_price,
        signal=signal,
        is_sell_tool_used=is_sell_tool_used,
    )
    if signal == "BUY":
        dynamic_floor = max(MIN_TRADE_VALUE, 0.10 * metrics.total_equity)
        if trade_cost > metrics.buying_power:
            assert not verdict.passed
            assert verdict.max_affordable_shares * mkt_price <= metrics.buying_power + 1e-6
        elif trade_cost < dynamic_floor:
            assert not verdict.passed
        else:
            assert verdict.passed
    else:
        if not is_sell_tool_used and trade_cost < MIN_TRADE_VALUE:
            assert not verdict.passed
        else:
            assert verdict.passed


@settings(max_examples=50, deadline=100)
@given(
    steps=st.lists(
        st.tuples(
            st.dictionaries(st.sampled_from(TICKERS), st.floats(min_value=10.0, max_value=500.0), min_size=5),
            st.lists(signal_st, max_size=4),
        ),
        min_size=2,
        max_size=8,
    ),
    cutoff=st.integers(min_value=1, max_value=7),
)
def test_zero_lookahead_future_slots_never_alter_historical_prefix(steps, cutoff):
    """Appending or mutating future slots after cutoff k must never alter portfolio state at step k."""
    k = min(cutoff, len(steps) - 1)
    dates_full = [f"2026-11-{i + 1:02d}" for i in range(len(steps))]
    dates_trunc = dates_full[:k]

    acc_full = BacktestAccumulator(window_dates=dates_full, starting_capital=10_000.0)
    acc_trunc = BacktestAccumulator(window_dates=dates_trunc, starting_capital=10_000.0)

    for idx in range(k):
        prices, signals = steps[idx]
        for acc in (acc_full, acc_trunc):
            acc.settle_slot(
                idx=idx,
                slot_label=dates_full[idx],
                signals=deepcopy(signals),
                slot_prices=dict(prices),
                tool_calls=[],
                output_text="ok",
                day_status="ok",
                is_final_step=False,
            )

    snap_before_future = acc_trunc.snapshot(
        days_completed=k, current_day=dates_full[k - 1], latest_prices=steps[k - 1][0]
    )

    for idx in range(k, len(steps)):
        prices, signals = steps[idx]
        acc_full.settle_slot(
            idx=idx,
            slot_label=dates_full[idx],
            signals=deepcopy(signals),
            slot_prices={tkr: px * 3.0 for tkr, px in prices.items()},
            tool_calls=["future_tool"],
            output_text="future",
            day_status="ok",
            is_final_step=(idx == len(steps) - 1),
        )

    assert acc_full.day_steps[:k] == snap_before_future["day_steps"]


class PortfolioEngineStateMachine(RuleBasedStateMachine):
    """Stateful Hypothesis machine testing arbitrary interleavings, DB row rehydration, and window closure."""

    def __init__(self):
        super().__init__()
        self.acc = BacktestAccumulator(window_dates=["2026-11-01", "2026-11-02"], starting_capital=10_000.0)
        self.step_idx = 0
        self.latest_prices = {t: 100.0 for t in TICKERS}

    @rule(prices=price_map_st, signals=st.lists(signal_st, max_size=4), close_window=st.booleans())
    def execute_slot(self, prices, signals, close_window):
        self.latest_prices.update(prices)
        self.acc.settle_slot(
            idx=self.step_idx,
            slot_label=f"slot-{self.step_idx}",
            signals=signals,
            slot_prices=dict(self.latest_prices),
            tool_calls=[],
            output_text="step",
            day_status="ok",
            is_final_step=close_window,
        )
        if close_window:
            assert self.acc.portfolio.positions == []
        self.step_idx += 1

    @invariant()
    def accounting_and_rehydration_invariants_hold(self):
        snap = self.acc.snapshot(
            days_completed=self.step_idx,
            current_day=f"slot-{self.step_idx}",
            latest_prices=self.latest_prices,
        )
        assert snap["cash"] >= 0.0
        assert 0.0 <= snap["max_drawdown_pct"] <= 100.0
        expected_eq = compute_total_equity(self.acc.portfolio, self.latest_prices)
        assert abs(snap["total_equity"] - round(expected_eq, 2)) <= 0.02

        # Live paper-trading DB row round-trip hydration must preserve exact mark-to-market equity
        rehydrated = PortfolioState.from_recipe_row(
            {
                "paper_cash": self.acc.portfolio.cash,
                "paper_positions": deepcopy(self.acc.portfolio.positions),
                "paper_trades": deepcopy(self.acc.portfolio.trades),
                "paper_equity_curve": deepcopy(self.acc.portfolio.equity_curve),
            }
        )
        assert abs(compute_total_equity(rehydrated, self.latest_prices) - expected_eq) <= 1e-6


TestPortfolioStateMachine = PortfolioEngineStateMachine.TestCase
TestPortfolioStateMachine.settings = settings(max_examples=40, stateful_step_count=12, deadline=100)
