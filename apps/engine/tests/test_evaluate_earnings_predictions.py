"""Hermetic unit tests for evaluate_earnings_predictions task."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from tasks.evaluate_earnings_predictions import evaluate_earnings_predictions


@pytest.fixture
def pending_predictions():
    return [
        {
            "id": "pred-1",
            "target_date": "2026-10-06",
            "ticker": "NVDA",
            "model_name": "gpt-5.6-luna",
            "predicted_direction": "UP",
            "confidence": 80.0,
            "status": "pending",
        },
        {
            "id": "pred-2",
            "target_date": "2026-10-06",
            "ticker": "NVDA",
            "model_name": "~typesafe/jev-latest",
            "predicted_direction": "DOWN",
            "confidence": 70.0,
            "status": "pending",
        },
    ]


@pytest.mark.asyncio
async def test_evaluate_earnings_predictions_up_and_down_outcomes(pending_predictions):
    """Verify evaluation of predictions against RTH Open and Close prices."""
    mock_db = MagicMock()
    mock_table = MagicMock()
    mock_db.table.return_value = mock_table
    mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = pending_predictions

    # Suppose Open = 100.0, Close = 105.0 -> Actual is UP
    mock_prices = (100.0, 106.0, 99.5, 105.0)

    with (
        patch("tasks.evaluate_earnings_predictions.get_supabase_client", return_value=mock_db),
        patch("tasks.evaluate_earnings_predictions.fetch_intraday_prices", AsyncMock(return_value=mock_prices)),
    ):
        count = await evaluate_earnings_predictions(target_date="2026-10-06", force_recalc=False)
        assert count == 2

        # Check updates called
        assert mock_table.update.call_count == 2
        calls = mock_table.update.call_args_list

        # First prediction was UP -> Actual UP -> is_correct True
        first_payload = calls[0][0][0]
        assert first_payload["actual_direction"] == "UP"
        assert first_payload["is_correct"] is True
        assert first_payload["open_price"] == 100.0
        assert first_payload["close_price"] == 105.0
        # Brier score for conf 80% (p=0.8) and hit (y=1): (0.8 - 1)^2 = 0.04
        assert pytest.approx(first_payload["brier_score"], 0.001) == 0.04

        # Second prediction was DOWN -> Actual UP -> is_correct False
        second_payload = calls[1][0][0]
        assert second_payload["actual_direction"] == "UP"
        assert second_payload["is_correct"] is False
        # Brier score for conf 70% (p=0.7) and miss (y=0): (0.7 - 0)^2 = 0.49
        assert pytest.approx(second_payload["brier_score"], 0.001) == 0.49


@pytest.mark.asyncio
async def test_evaluate_skips_active_session_before_1605(pending_predictions):
    """Verify that today's predictions are skipped prior to 16:05 ET unless force_recalc=True."""
    mock_db = MagicMock()
    mock_table = MagicMock()
    mock_db.table.return_value = mock_table
    # Target date is today
    pending_today = [dict(pending_predictions[0], target_date="2026-10-07")]
    mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = pending_today

    # Mock time as 14:30 ET (market active)
    mock_now = datetime(2026, 10, 7, 14, 30, tzinfo=ZoneInfo("America/New_York"))

    with (
        patch("tasks.evaluate_earnings_predictions.get_supabase_client", return_value=mock_db),
        patch("tasks.evaluate_earnings_predictions.get_ny_now", return_value=mock_now),
        patch("tasks.evaluate_earnings_predictions.fetch_intraday_prices", AsyncMock()) as mock_fetch,
    ):
        count = await evaluate_earnings_predictions(target_date="2026-10-07", force_recalc=False)
        assert count == 0
        mock_fetch.assert_not_called()
