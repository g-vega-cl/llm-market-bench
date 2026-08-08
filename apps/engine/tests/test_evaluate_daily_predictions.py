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

