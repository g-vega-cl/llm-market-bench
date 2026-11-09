"""Unit tests for Contrarian Options Sentiment Fader strategy.

Hermetic tests with zero external network calls.
"""

from execution.sentiment_fader import (
    DEFAULT_EUPHORIA_THRESHOLD_PC,
    DEFAULT_FADER_MAX_HOLDING_DAYS,
    DEFAULT_FADER_SLIPPAGE_BPS,
    DEFAULT_FADER_STOP_LOSS_PCT,
    DEFAULT_PANIC_THRESHOLD_PC,
    SYS_SENTIMENT_FADER_OWNER_ID,
    compute_sentiment_fader_rebalance_orders,
    evaluate_sentiment_holding_exit,
    evaluate_sentiment_signal,
)


def test_sys_sentiment_fader_constants():
    """Verify owner ID and default quantitative thresholds."""
    assert SYS_SENTIMENT_FADER_OWNER_ID == "sys-sentiment-fader"
    assert DEFAULT_PANIC_THRESHOLD_PC == 1.30
    assert DEFAULT_EUPHORIA_THRESHOLD_PC == 0.60
    assert DEFAULT_FADER_STOP_LOSS_PCT == 1.5
    assert DEFAULT_FADER_MAX_HOLDING_DAYS == 3
    assert DEFAULT_FADER_SLIPPAGE_BPS == 1.0


def test_evaluate_sentiment_signal_extreme_panic():
    """Verify BUY signal when Put/Call volume ratio exceeds panic threshold (>= 1.30)."""
    metrics = {
        "ticker": "SPY",
        "pv_ratio": 1.45,
        "poi_ratio": 1.10,
        "call_volume": 100000,
        "put_volume": 145000,
    }
    action, reason = evaluate_sentiment_signal(metrics)
    assert action == "BUY"
    assert "Extreme put panic exhaustion" in reason
    assert "1.45" in reason


def test_evaluate_sentiment_signal_extreme_euphoria():
    """Verify SELL signal when Put/Call volume ratio drops to extreme greed (<= 0.60)."""
    metrics = {
        "ticker": "QQQ",
        "pv_ratio": 0.48,
        "poi_ratio": 0.75,
        "call_volume": 200000,
        "put_volume": 96000,
    }
    action, reason = evaluate_sentiment_signal(metrics)
    assert action == "SELL"
    assert "Extreme call complacency / euphoria" in reason
    assert "0.48" in reason


def test_evaluate_sentiment_signal_neutral_hold():
    """Verify HOLD signal when Put/Call volume ratio is within normal bounds."""
    metrics = {
        "ticker": "SPY",
        "pv_ratio": 0.95,
        "poi_ratio": 1.05,
        "call_volume": 100000,
        "put_volume": 95000,
    }
    action, reason = evaluate_sentiment_signal(metrics)
    assert action == "HOLD"
    assert "Neutral sentiment" in reason


def test_evaluate_sentiment_signal_missing_data():
    """Verify graceful handling when metrics are empty or invalid."""
    action, reason = evaluate_sentiment_signal({})
    assert action == "HOLD"
    assert "Data insufficient" in reason


def test_evaluate_holding_exit_stop_loss():
    """Verify position is liquidated when price drops > 1.5% below entry price."""
    holding_info = {
        "ticker": "SPY",
        "entry_price": 550.0,
        "shares": 10,
    }
    # 1.5% drop from 550 is 541.75
    should_exit, reason = evaluate_sentiment_holding_exit(
        holding_info=holding_info,
        current_price=540.0,
        days_held=1,
    )
    assert should_exit is True
    assert "Adverse stop loss triggered" in reason


def test_evaluate_holding_exit_max_days():
    """Verify position is liquidated after maximum 3-day holding horizon."""
    holding_info = {
        "ticker": "QQQ",
        "entry_price": 480.0,
        "shares": 10,
    }
    should_exit, reason = evaluate_sentiment_holding_exit(
        holding_info=holding_info,
        current_price=485.0,
        days_held=3,
    )
    assert should_exit is True
    assert "Max holding horizon reached" in reason
    assert "3 days" in reason


def test_evaluate_holding_exit_euphoria_take_profit():
    """Verify position is liquidated when options sentiment flips to extreme call complacency."""
    holding_info = {
        "ticker": "SPY",
        "entry_price": 550.0,
        "shares": 10,
    }
    current_sentiment = {
        "ticker": "SPY",
        "pv_ratio": 0.52,
    }
    should_exit, reason = evaluate_sentiment_holding_exit(
        holding_info=holding_info,
        current_price=555.0,
        current_sentiment=current_sentiment,
        days_held=1,
    )
    assert should_exit is True
    assert "Extreme call euphoria detected" in reason


def test_evaluate_holding_exit_retain():
    """Verify holding is kept when price is within risk bounds, days < 3, and sentiment neutral."""
    holding_info = {
        "ticker": "SPY",
        "entry_price": 550.0,
        "shares": 10,
    }
    current_sentiment = {
        "ticker": "SPY",
        "pv_ratio": 1.10,
    }
    should_exit, reason = evaluate_sentiment_holding_exit(
        holding_info=holding_info,
        current_price=552.0,
        current_sentiment=current_sentiment,
        days_held=1,
    )
    assert should_exit is False
    assert "Holding criteria healthy" in reason


def test_compute_rebalance_orders_full_lifecycle():
    """Verify sales processing, freed cash calculation, and equal candidate deployment."""
    current_holdings = [
        {
            "ticker": "SPY",
            "shares": 10,
            "cost_basis": 500.0,
            "current_price": 500.0,
        },
        {
            "ticker": "QQQ",
            "shares": 10,
            "cost_basis": 400.0,
            "current_price": 390.0,  # Stop loss triggered
        },
    ]
    holding_evaluations = {
        "SPY": {"should_exit": False, "reason": "Holding criteria healthy"},
        "QQQ": {"should_exit": True, "reason": "Adverse stop loss triggered"},
    }
    qualified_candidates = [
        {
            "ticker": "IWM",
            "price": 200.0,
            "pv_ratio": 1.55,
        }
    ]
    # Slippage 1 bps = 0.0001
    # QQQ sale: 10 * 390 * (1 - 0.0001) = 3899.61 freed
    # Available cash = 1100.39 -> Total = 5000.00
    orders = compute_sentiment_fader_rebalance_orders(
        current_holdings=current_holdings,
        holding_evaluations=holding_evaluations,
        qualified_candidates=qualified_candidates,
        available_cash=1100.39,
        max_holdings=2,
        slippage_bps=1.0,
    )

    assert len(orders["sales"]) == 1
    assert orders["sales"][0]["ticker"] == "QQQ"
    assert orders["sales"][0]["shares"] == 10
    assert abs(orders["sales"][0]["proceeds"] - 3899.61) < 0.1

    assert len(orders["retained"]) == 1
    assert orders["retained"][0]["ticker"] == "SPY"

    assert len(orders["buys"]) == 1
    assert orders["buys"][0]["ticker"] == "IWM"
    # Buy price: 200 * 1.0001 = 200.02
    # Shares: 5000 // 200.02 = 24 shares
    assert orders["buys"][0]["shares"] == 24
    assert orders["buys"][0]["execution_price"] == 200.02
    assert orders["buys"][0]["total_cost"] == round(24 * 200.02, 2)
