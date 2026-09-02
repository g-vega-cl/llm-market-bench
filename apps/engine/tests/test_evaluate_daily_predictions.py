from unittest.mock import MagicMock, patch

import pytest

from tasks.evaluate_daily_predictions import (
    calculate_brier_score,
    compute_intraday_hit_metrics,
    evaluate_daily_predictions,
)


def test_calculate_brier_score():
    # Correct UP prediction with 80% confidence
    score_correct = calculate_brier_score(predicted_direction="UP", confidence=80.0, actual_direction="UP")
    # (0.80 - 1.0)^2 = 0.04
    assert pytest.approx(score_correct, 0.001) == 0.04

    # Incorrect UP prediction with 80% confidence
    score_incorrect = calculate_brier_score(predicted_direction="UP", confidence=80.0, actual_direction="DOWN")
    # (0.80 - 0.0)^2 = 0.64
    assert pytest.approx(score_incorrect, 0.001) == 0.64


def test_compute_intraday_hit_metrics():
    # Scenario: Predicted UP +0.35%, Open $500, High $502 (+0.40%), Low $498, Close $499 (-0.20%)
    # Intraday hit target hit should be True (+0.40% >= +0.35%)
    hit, dir_hit = compute_intraday_hit_metrics(
        predicted_direction="UP",
        expected_return_pct=0.35,
        open_price=500.0,
        high_price=502.0,
        low_price=498.0,
    )
    assert hit is True
    assert dir_hit is True

    # Scenario: Predicted DOWN -0.30%, Open $500, High $501, Low $499 (-0.20%), Close $500.50
    # Intraday target not hit (-0.20% is not <= -0.30%), but direction hit is True ($499 < $500)
    hit_down, dir_hit_down = compute_intraday_hit_metrics(
        predicted_direction="DOWN",
        expected_return_pct=-0.30,
        open_price=500.0,
        high_price=501.0,
        low_price=499.0,
    )
    assert hit_down is False
    assert dir_hit_down is True


@pytest.mark.asyncio
async def test_evaluate_daily_predictions_success():
    mock_supabase = MagicMock()

    # Pending predictions data
    pending_data = [
        {
            "id": "pred-uuid-1",
            "target_date": "2026-08-03",
            "ticker": "SPY",
            "predicted_direction": "UP",
            "confidence": 75.0,
            "expected_return_pct": 0.35,
            "status": "pending",
        }
    ]

    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = pending_data

    with (
        patch("tasks.evaluate_daily_predictions.get_supabase_client", return_value=mock_supabase),
        patch("tasks.evaluate_daily_predictions.fetch_intraday_prices", return_value=(450.0, 452.0, 448.0, 455.0)),
    ):
        evaluated_count = await evaluate_daily_predictions()
        assert evaluated_count == 1
        mock_supabase.table.return_value.update.assert_called()


@pytest.mark.asyncio
async def test_fetch_intraday_prices_forces_refresh_when_missing_from_cache():
    """Test that fetch_intraday_prices forces a provider refresh when target date is missing from cached history."""
    from unittest.mock import AsyncMock

    from tasks.evaluate_daily_predictions import fetch_intraday_prices

    cached_history = [{"price": 765.0, "open": 764.0, "high": 766.0, "low": 763.0, "fetched_at": "2026-08-26"}]
    fresh_history = [
        {"price": 771.10, "open": 768.50, "high": 772.36, "low": 767.16, "fetched_at": "2026-08-27"},
        {"price": 765.0, "open": 764.0, "high": 766.0, "low": 763.0, "fetched_at": "2026-08-26"},
    ]

    mock_mdm = MagicMock()
    mock_mdm.get_history = AsyncMock(side_effect=[cached_history, fresh_history])

    with patch("execution.market_data.MarketDataManager", return_value=mock_mdm):
        open_p, high_p, low_p, close_p = await fetch_intraday_prices("SPY", "2026-08-27")

        assert open_p == 768.50
        assert high_p == 772.36
        assert low_p == 767.16
        assert close_p == 771.10
        assert mock_mdm.get_history.call_count == 2
        mock_mdm.get_history.assert_called_with("SPY", days=10, force_refresh=True)


@pytest.mark.asyncio
async def test_fetch_intraday_open_close_missing_date():
    from unittest.mock import AsyncMock

    from tasks.evaluate_daily_predictions import fetch_intraday_open_close

    mock_history = [{"price": 105.0, "fetched_at": "2026-08-04T00:00:00Z"}]
    mock_mdm = MagicMock()
    mock_mdm.get_history = AsyncMock(return_value=mock_history)

    with patch("execution.market_data.MarketDataManager", return_value=mock_mdm):
        open_p, close_p = await fetch_intraday_open_close("SPY", "2026-08-05")
        assert open_p is None
        assert close_p is None


@pytest.mark.asyncio
async def test_fetch_intraday_prices_uses_ohlc():
    """Regression test: get_history() must propagate OHLC fields so that
    fetch_intraday_prices() returns correct Open/High/Low values.

    Previously, MarketDataManager.get_history() stripped OHLC from HistoryData,
    causing all four values to collapse to the single close price — making
    intraday_hit always False when the target was non-zero.
    """
    from unittest.mock import AsyncMock

    from tasks.evaluate_daily_predictions import fetch_intraday_prices

    # Simulate get_history() returning full OHLC (the fixed behaviour)
    mock_history = [
        {
            "price": 773.26,
            "open": 771.02,
            "high": 773.915,
            "low": 769.61,
            "fetched_at": "2026-08-07",
        }
    ]
    mock_mdm = MagicMock()
    mock_mdm.get_history = AsyncMock(return_value=mock_history)

    with patch("execution.market_data.MarketDataManager", return_value=mock_mdm):
        open_p, high_p, low_p, close_p = await fetch_intraday_prices("SPY", "2026-08-07")

    assert open_p == pytest.approx(771.02)
    assert high_p == pytest.approx(773.915)
    assert low_p == pytest.approx(769.61)
    assert close_p == pytest.approx(773.26)

    # Verify the intraday hit that was previously wrong
    hit, dir_hit = compute_intraday_hit_metrics(
        predicted_direction="UP",
        expected_return_pct=0.25,
        open_price=open_p,
        high_price=high_p,
        low_price=low_p,
    )
    assert hit is True, "SPY hit +0.375% intraday vs +0.25% target — should be True"
    assert dir_hit is True


@pytest.mark.asyncio
async def test_fetch_regular_trading_hours_ohlc_filters_pre_and_post_market():
    """Test that fetch_regular_trading_hours_ohlc strictly includes 09:30 - 16:00 ET bars
    and discards pre-market (08:30) and post-market (17:00) price spikes.
    """
    from unittest.mock import AsyncMock

    from tasks.evaluate_daily_predictions import fetch_regular_trading_hours_ohlc

    mock_bars = [
        # Pre-market spike at 08:30 (should be discarded)
        {"date": "2026-09-01 08:30:00", "open": 750.0, "high": 755.0, "low": 745.0, "close": 752.0},
        # Regular trading hours bars
        {"date": "2026-09-01 09:30:00", "open": 762.04, "high": 764.0, "low": 761.17, "close": 763.76},
        {"date": "2026-09-01 11:30:00", "open": 763.59, "high": 764.67, "low": 762.29, "close": 762.55},
        {"date": "2026-09-01 14:30:00", "open": 761.20, "high": 761.57, "low": 759.50, "close": 761.39},
        {"date": "2026-09-01 15:30:00", "open": 761.37, "high": 761.54, "low": 760.61, "close": 761.48},
        # Post-market spike at 17:00 (should be discarded)
        {"date": "2026-09-01 17:00:00", "open": 770.0, "high": 780.0, "low": 740.0, "close": 775.0},
    ]

    mock_provider = MagicMock()
    mock_provider.get_hourly_history = AsyncMock(return_value=mock_bars)

    mock_mdm = MagicMock()
    mock_mdm.provider = mock_provider

    with patch("execution.market_data.MarketDataManager", return_value=mock_mdm):
        open_p, high_p, low_p, close_p = await fetch_regular_trading_hours_ohlc("SPY", "2026-09-01")

    assert open_p == pytest.approx(762.04)  # 09:30 bar open, not 08:30 pre-market
    assert high_p == pytest.approx(764.67)  # RTH max, not 17:00 post-market 780.0
    assert low_p == pytest.approx(759.50)  # RTH min from 14:30 bar, not 08:30 pre-market 745.0
    assert close_p == pytest.approx(761.48)  # 15:30 bar close, not 17:00 post-market


@pytest.mark.asyncio
async def test_evaluate_daily_predictions_with_target_date_and_force():
    """Test evaluate_daily_predictions targeting a specific date and forcing recalculation."""
    mock_supabase = MagicMock()

    evaluated_data = [
        {
            "id": "pred-uuid-2",
            "target_date": "2026-09-01",
            "ticker": "SPY",
            "predicted_direction": "DOWN",
            "confidence": 60.0,
            "expected_return_pct": -0.30,
            "status": "evaluated",
        }
    ]

    mock_query = MagicMock()
    mock_query.eq.return_value = mock_query
    mock_query.execute.return_value.data = evaluated_data
    mock_supabase.table.return_value.select.return_value = mock_query

    with (
        patch("tasks.evaluate_daily_predictions.get_supabase_client", return_value=mock_supabase),
        patch(
            "tasks.evaluate_daily_predictions.fetch_intraday_prices",
            return_value=(762.01, 764.67, 759.48, 761.78),
        ),
    ):
        evaluated_count = await evaluate_daily_predictions(target_date="2026-09-01", force_recalc=True)
        assert evaluated_count == 1
        mock_supabase.table.return_value.update.assert_called()
