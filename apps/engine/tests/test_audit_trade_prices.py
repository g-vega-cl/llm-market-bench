"""Hermetic tests for the recurring trade-price audit."""

from scripts.audit_trade_prices import OUT_OF_RANGE_PCT, audit_trades, classify_trade


def _trade(**overrides):
    trade = {
        "id": "t-1",
        "ticker": "ANT",
        "executed_at": "2026-11-19T14:30:00+00:00",
        "price": 100.0,
        "audit_flag": None,
    }
    trade.update(overrides)
    return trade


def _bar(**overrides):
    bar = {"low": 90.0, "high": 110.0, "close": 100.0, "fetched_at": "2026-11-19T14:30:00Z"}
    bar.update(overrides)
    return bar


def test_in_range_fill_is_clean():
    assert classify_trade(_trade(price=105.0), _bar()) is None


def test_intentional_slippage_inside_buffer_is_clean():
    # 0.4% above the high is within the model slippage + rounding buffer.
    assert classify_trade(_trade(price=110.4), _bar()) is None


def test_materially_out_of_range_fill_is_flagged():
    flag = classify_trade(_trade(price=83.04), _bar(low=92.72, high=115.10, close=100.0))

    assert flag == "PRICE_OUTSIDE_DAY_RANGE"


def test_non_trading_day_without_bar_is_flagged():
    assert classify_trade(_trade(executed_at="2026-11-26T14:30:00+00:00"), None) == "NON_TRADING_DAY"
    assert classify_trade(_trade(executed_at="2026-11-22T14:30:00+00:00"), None) == "NON_TRADING_DAY"


def test_trading_day_without_bar_is_informational_only():
    assert classify_trade(_trade(), None) == "NO_BAR"


def test_existing_annotation_is_not_reported_as_new():
    trade = _trade(price=83.04, audit_flag="PRICE_OUTSIDE_DAY_RANGE")

    assert classify_trade(trade, _bar(low=92.72, high=115.10, close=100.0)) is None


def test_after_hours_fill_matches_the_et_session_not_utc_date():
    trade = _trade(executed_at="2026-11-21T02:36:12+00:00", price=125.47)
    bars = {("ANT", "2026-11-20"): _bar(low=124.5, high=143.73, close=125.53)}

    report = audit_trades([trade], bars)

    assert report.counts["clean"] == 1
    assert report.new_violations == []


def test_threshold_is_the_documented_slippage_buffer():
    assert OUT_OF_RANGE_PCT == 0.6


def test_audit_trades_summarizes_new_violations_only():
    trades = [
        _trade(id="bad-price", price=83.04),
        _trade(id="holiday", executed_at="2026-11-26T14:30:00+00:00"),
        _trade(id="no-bar", executed_at="2026-11-18T14:30:00+00:00"),
        _trade(id="already-flagged", price=83.04, audit_flag="PRICE_OUTSIDE_DAY_RANGE"),
        _trade(id="clean", price=105.0),
    ]
    bars = {("ANT", "2026-11-19"): _bar(low=92.72, high=115.10, close=100.0)}

    report = audit_trades(trades, bars)

    assert [v.trade_id for v in report.new_violations] == ["bad-price", "holiday"]
    assert report.counts == {
        "audited": 5,
        "clean": 1,
        "no_bar": 1,
        "already_annotated": 1,
        "new_violations": 2,
    }
