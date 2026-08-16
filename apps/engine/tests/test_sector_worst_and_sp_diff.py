import pytest

from tasks.evaluate_predictions import (
    calculate_worst_sector_percentile_score,
)
from tasks.predictor_autoresearch import calculate_baseline_score
from tasks.sector_predictor import SectorPredictionResponse


def test_calculate_worst_sector_percentile_score_perfect_bottom():
    """When the predicted worst sector has the lowest return, it gets 100% score."""
    sector_returns = {
        "XLK": 10.0,
        "XLV": 5.0,
        "XLF": 0.0,
        "XLE": -5.0,
    }
    # XLE has the lowest return (-5.0). All 3 other sectors performed better.
    score = calculate_worst_sector_percentile_score("XLE", sector_returns)
    assert score == 100.0


def test_calculate_worst_sector_percentile_score_worst_call():
    """When the predicted worst sector was actually the top performer, it gets 0% score."""
    sector_returns = {
        "XLK": 10.0,
        "XLV": 5.0,
        "XLF": 0.0,
        "XLE": -5.0,
    }
    # XLK had the highest return (+10.0). 0 other sectors performed better.
    score = calculate_worst_sector_percentile_score("XLK", sector_returns)
    assert score == 0.0


def test_calculate_worst_sector_percentile_score_middle():
    """When the predicted worst sector is in the middle, score is proportional."""
    sector_returns = {
        "XLK": 10.0,
        "XLV": 5.0,
        "XLF": 0.0,
        "XLE": -5.0,
    }
    # XLF (0.0): XLK (10.0) and XLV (5.0) performed better -> rank = 2 / 3 -> 66.666...%
    score = calculate_worst_sector_percentile_score("XLF", sector_returns)
    assert score == pytest.approx(66.6666, rel=1e-3)


def test_calculate_worst_sector_percentile_score_missing_ticker():
    """Missing ticker returns 0.0."""
    sector_returns = {"XLK": 10.0, "XLV": 5.0}
    score = calculate_worst_sector_percentile_score("NONEXISTENT", sector_returns)
    assert score == 0.0


def test_calculate_worst_sector_percentile_score_single_ticker():
    """Single ticker in returns returns 100.0."""
    sector_returns = {"XLK": 10.0}
    score = calculate_worst_sector_percentile_score("XLK", sector_returns)
    assert score == 100.0


def test_sector_prediction_response_with_worst_sector():
    """SectorPredictionResponse accepts and parses predicted_worst_sector."""
    payload = {
        "predicted_sector": "XLK",
        "predicted_worst_sector": "XLE",
        "predicted_pair": ["XLK", "XLU"],
        "confidence": 85.0,
        "reasoning": "Tech momentum vs energy headwinds.",
    }
    resp = SectorPredictionResponse(**payload)
    assert resp.predicted_sector == "XLK"
    assert resp.predicted_worst_sector == "XLE"
    assert resp.predicted_pair == ["XLK", "XLU"]
    assert resp.confidence == 85.0


def test_calculate_baseline_score_with_worst_sector_and_sp_alpha_bonus():
    """Baseline score integrates best sector, worst sector, pair score, SPY alpha bonus, and Brier penalty."""
    predictions = [
        {
            "sector_percentile_score": 80.0,
            "worst_sector_percentile_score": 90.0,
            "pair_percentile_score": 70.0,
            "predicted_sector_return": 6.0,
            "benchmark_spy_return": 2.0,  # Alpha = +4.0%
            "brier_score": 0.04,
        },
        {
            "sector_percentile_score": 60.0,
            "worst_sector_percentile_score": 80.0,
            "pair_percentile_score": 70.0,
            "predicted_sector_return": 1.0,
            "benchmark_spy_return": 3.0,  # Negative alpha (-2.0%) -> 0 bonus
            "brier_score": 0.04,
        },
    ]
    # Prediction 1: Base = (80 + 90 + 70) / 3 = 80.0, Alpha Bonus = +4.0 -> Total = 84.0
    # Prediction 2: Base = (60 + 80 + 70) / 3 = 70.0, Alpha Bonus = 0.0 -> Total = 70.0
    # Avg Score = (84.0 + 70.0) / 2 = 77.0
    # Mean Brier = 0.04 -> penalty = 0.04 * 50 = 2.0
    # Final Ratchet Score = 77.0 - 2.0 = 75.0
    score = calculate_baseline_score(predictions)
    assert score == pytest.approx(75.0)


@pytest.mark.asyncio
async def test_run_evaluation_with_worst_sector_and_sp_diff():
    """Verify run_evaluation correctly evaluates worst sector, calculates S&P diff, and saves audit data."""
    from datetime import UTC, datetime, timedelta
    from unittest.mock import AsyncMock, MagicMock, patch

    from tasks.evaluate_predictions import run_evaluation

    today = datetime.now(UTC).date()
    target_date = today - timedelta(days=1)
    prediction_date = target_date - timedelta(days=7)

    mock_prediction = {
        "id": "pred-worst-test-1",
        "prediction_date": prediction_date.isoformat(),
        "target_date": target_date.isoformat(),
        "timeframe": "7d",
        "model_name": "deepseek-v4-flash",
        "prompt_tag": "test-tag",
        "predicted_sector": "XLK",
        "predicted_worst_sector": "XLE",
        "predicted_pair": ["XLK", "XLV"],
        "confidence": 80.0,
        "reasoning": "Tech vs Energy.",
        "status": "pending",
    }

    mock_client = MagicMock()
    mock_chain = MagicMock()
    mock_select_execute = MagicMock()
    mock_select_execute.data = [mock_prediction]

    mock_update_execute = MagicMock()
    mock_update_execute.data = [{"id": "pred-worst-test-1"}]

    mock_chain.select.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain
    mock_chain.or_.return_value = mock_chain
    mock_chain.lte.return_value = mock_chain
    mock_chain.update.return_value = mock_chain

    def mock_execute_side_effect():
        if mock_chain.update.called:
            return mock_update_execute
        return mock_select_execute

    mock_chain.execute = mock_execute_side_effect
    mock_client.table.return_value = mock_chain

    mock_run_execute = MagicMock()
    mock_run_execute.data = [{"tickers": ["XLK", "XLV", "XLF", "XLE"]}]

    def mock_table_routing(table_name):
        if table_name == "correlation_runs":
            mock_run_chain = MagicMock()
            mock_run_chain.select.return_value = mock_run_chain
            mock_run_chain.lte.return_value = mock_run_chain
            mock_run_chain.order.return_value = mock_run_chain
            mock_run_chain.limit.return_value = mock_run_chain
            mock_run_chain.execute.return_value = mock_run_execute
            return mock_run_chain
        return mock_chain

    mock_client.table.side_effect = mock_table_routing

    # XLK: +10% (100 -> 110)
    # XLV: +5%  (100 -> 105)
    # XLF: 0%   (100 -> 100)
    # XLE: -10% (100 -> 90)
    # SPY: +2%  (100 -> 102)
    mock_history = {
        "XLK": [
            {"price": 110.0, "fetched_at": target_date.isoformat()},
            {"price": 100.0, "fetched_at": prediction_date.isoformat()},
        ],
        "XLV": [
            {"price": 105.0, "fetched_at": target_date.isoformat()},
            {"price": 100.0, "fetched_at": prediction_date.isoformat()},
        ],
        "XLF": [
            {"price": 100.0, "fetched_at": target_date.isoformat()},
            {"price": 100.0, "fetched_at": prediction_date.isoformat()},
        ],
        "XLE": [
            {"price": 90.0, "fetched_at": target_date.isoformat()},
            {"price": 100.0, "fetched_at": prediction_date.isoformat()},
        ],
        "SPY": [
            {"price": 102.0, "fetched_at": target_date.isoformat()},
            {"price": 100.0, "fetched_at": prediction_date.isoformat()},
        ],
    }

    async def mock_get_history(ticker, days=14):
        return mock_history.get(ticker.upper(), [])

    mock_provider = AsyncMock()
    mock_provider.get_history = mock_get_history

    with (
        patch("tasks.evaluate_predictions.get_supabase_client", return_value=mock_client),
        patch("tasks.evaluate_predictions.get_financial_provider", return_value=mock_provider),
    ):
        await run_evaluation()

    mock_chain.update.assert_called_once()
    update_args = mock_chain.update.call_args[0][0]
    assert update_args["status"] == "evaluated"
    assert update_args["sector_percentile_score"] == 100.0  # Top sector
    assert update_args["worst_sector_percentile_score"] == 100.0  # Lowest return (XLE -10%)
    assert update_args["predicted_sector_return"] == pytest.approx(10.0)
    assert update_args["predicted_worst_sector_return"] == pytest.approx(-10.0)
    assert update_args["benchmark_spy_return"] == pytest.approx(2.0)
    assert update_args["sector_sp_diff"] == pytest.approx(8.0)  # +10% - +2% = +8%
    assert update_args["evaluation_audit_data"]["worst_sector"]["ticker"] == "XLE"
