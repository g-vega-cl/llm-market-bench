"""Hermetic tests for technical indicators and condition evaluation."""

from datetime import UTC, datetime, timedelta

from recipes.indicators import (
    Bar,
    compute_bar_indicators,
    evaluate_condition,
    evaluate_technical_gate,
)
from recipes.schema import ConditionRule


def _make_sample_bars(n: int = 60, base_price: float = 100.0) -> list[Bar]:
    base_time = datetime(2026, 3, 2, 9, 30, tzinfo=UTC)
    bars = []
    for i in range(n):
        t = base_time + timedelta(minutes=5 * i)
        # Gentle sine/linear price variation
        p = base_price + (i * 0.2) + ((i % 5) * 0.1)
        bars.append(
            Bar(
                time_utc=t,
                open=p - 0.05,
                high=p + 0.15,
                low=p - 0.10,
                close=p,
                volume=1000 + (i * 10),
            )
        )
    return bars


def test_empty_bars():
    assert compute_bar_indicators([]) == []


def test_compute_bar_indicators_sma_and_rsi():
    bars = _make_sample_bars(60)
    computed = compute_bar_indicators(bars)

    # First 19 bars should have no sma_20
    assert computed[0].sma_20 is None
    assert computed[18].sma_20 is None
    # 20th bar (index 19) should have sma_20
    assert computed[19].sma_20 is not None
    assert computed[19].sma_20 > 0

    # 50th bar (index 49) should have sma_50
    assert computed[48].sma_50 is None
    assert computed[49].sma_50 is not None

    # RSI should be computed from index 14
    assert computed[13].rsi_14 is None
    assert computed[14].rsi_14 is not None
    assert 0.0 <= computed[14].rsi_14 <= 100.0
    assert 0.0 <= computed[59].rsi_14 <= 100.0

    # VWAP should be computed on every bar
    assert computed[0].vwap is not None
    assert computed[59].vwap is not None

    # RVOL should be 1.0 initially, then computed
    assert computed[0].rvol == 1.0
    assert computed[30].rvol is not None


def test_evaluate_condition_numeric():
    bar = Bar(
        time_utc=datetime(2026, 3, 2, 10, 0, tzinfo=UTC),
        open=100.0,
        high=105.0,
        low=99.0,
        close=103.5,
        volume=5000,
        rsi_14=28.5,
        vwap=102.0,
    )

    # RSI < 30 (Oversold condition)
    cond1 = ConditionRule(metric="rsi_14", operator="<", target=30.0)
    passed1, expl1 = evaluate_condition(cond1, bar)
    assert passed1 is True
    assert "PASS" in expl1

    # RSI > 50 (Should fail)
    cond2 = ConditionRule(metric="rsi_14", operator=">", target=50.0)
    passed2, expl2 = evaluate_condition(cond2, bar)
    assert passed2 is False
    assert "FAIL" in expl2

    # Price > vwap (Dynamic comparison)
    cond3 = ConditionRule(metric="price", operator=">", target="vwap")
    passed3, expl3 = evaluate_condition(cond3, bar)
    assert passed3 is True
    assert "PASS" in expl3


def test_evaluate_technical_gate_and_logic():
    bar = Bar(
        time_utc=datetime(2026, 3, 2, 10, 0, tzinfo=UTC),
        open=100.0,
        high=105.0,
        low=99.0,
        close=103.5,
        volume=5000,
        rsi_14=25.0,
        vwap=102.0,
    )

    conditions = [
        ConditionRule(metric="rsi_14", operator="<", target=30.0),
        ConditionRule(metric="price", operator=">", target="vwap"),
    ]
    passed, reasons = evaluate_technical_gate(conditions, bar)
    assert passed is True
    assert len(reasons) == 2

    # If one condition fails
    failing_conditions = [
        ConditionRule(metric="rsi_14", operator="<", target=20.0),  # 25 < 20 is False
        ConditionRule(metric="price", operator=">", target="vwap"),
    ]
    passed_fail, reasons_fail = evaluate_technical_gate(failing_conditions, bar)
    assert passed_fail is False
    assert any("FAIL" in r for r in reasons_fail)
