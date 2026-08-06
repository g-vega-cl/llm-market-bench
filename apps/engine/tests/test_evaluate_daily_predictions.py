from unittest.mock import MagicMock, patch

import pytest

from tasks.evaluate_daily_predictions import (
    calculate_brier_score,
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
            "status": "pending",
        }
    ]

    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = pending_data

    with (
        patch("tasks.evaluate_daily_predictions.get_supabase_client", return_value=mock_supabase),
        patch("tasks.evaluate_daily_predictions.fetch_intraday_open_close", return_value=(450.0, 455.0)),
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
