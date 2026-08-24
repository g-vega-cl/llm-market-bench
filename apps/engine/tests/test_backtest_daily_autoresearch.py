import sqlite3
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import tasks.backtest_daily_autoresearch as backtest_module
from tasks.backtest_daily_autoresearch import (
    evaluate_simulated_daily_prediction,
    init_backtest_daily_db,
    reset_backtest_daily_db,
    run_backtest_daily_autoresearch,
    run_simulated_daily_prediction,
)


@pytest.fixture(autouse=True)
def isolate_test_db(tmp_path, monkeypatch):
    test_db_file = str(tmp_path / "backtest_test.db")
    monkeypatch.setattr(backtest_module, "DB_PATH", test_db_file)
    init_backtest_daily_db()
    yield test_db_file


def test_init_and_reset_backtest_daily_db():
    """Verify SQLite database initialization and reset for daily predictor backtests."""
    init_backtest_daily_db()

    conn = sqlite3.connect(backtest_module.DB_PATH)
    cursor = conn.cursor()

    # Verify tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='daily_predictions'")
    assert cursor.fetchone() is not None

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='prompt_experiments'")
    assert cursor.fetchone() is not None

    conn.close()

    reset_backtest_daily_db()

    conn = sqlite3.connect(backtest_module.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM daily_predictions")
    assert cursor.fetchone()[0] == 0
    conn.close()


@pytest.mark.asyncio
async def test_run_simulated_daily_prediction():
    """Verify running a simulated daily prediction writes a pending prediction to SQLite."""
    init_backtest_daily_db()
    reset_backtest_daily_db()

    t_sim = datetime(2026, 4, 27, 9, 0, 0, tzinfo=UTC)

    mock_resp = MagicMock()
    mock_resp.predicted_direction = "UP"
    mock_resp.confidence = 75.0
    mock_resp.expected_return_pct = 0.8
    mock_resp.rationale = "Strong morning momentum."
    mock_resp.catalysts = ["Tech earnings beat"]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)

    with patch("tasks.backtest_daily_autoresearch.get_deepseek_client", return_value=mock_client):
        with patch("tasks.backtest_daily_autoresearch.close_client", new_callable=AsyncMock):
            pred = await run_simulated_daily_prediction(
                t_sim=t_sim,
                active_prompt="Predict UP or DOWN.",
                prompt_tag="test-tag-123",
                model_name="deepseek-v4-flash",
                ticker="SPY",
            )

    assert pred is not None
    assert pred["predicted_direction"] == "UP"
    assert pred["confidence"] == 75.0
    assert pred["model_name"] == "deepseek-v4-flash"

    # Verify saved in SQLite DB
    conn = sqlite3.connect(backtest_module.DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM daily_predictions WHERE target_date = ?", ("2026-04-27",))
    row = cursor.fetchone()
    assert row is not None
    assert row["predicted_direction"] == "UP"
    assert row["status"] == "pending"
    conn.close()


@pytest.mark.asyncio
async def test_evaluate_simulated_daily_prediction():
    """Verify evaluating daily prediction updates open, close, is_correct, and brier score."""
    init_backtest_daily_db()
    reset_backtest_daily_db()

    t_sim = datetime(2026, 4, 27, 17, 15, 0, tzinfo=UTC)

    conn = sqlite3.connect(backtest_module.DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO daily_predictions (
            id, prediction_date, target_date, ticker, model_name, prompt_variant_tag,
            predicted_direction, confidence, expected_return_pct, rationale, status, created_at
        ) VALUES (
            'pred-1', '2026-04-27', '2026-04-27', 'SPY', 'deepseek-v4-flash', 'test-tag-123',
            'UP', 80.0, 0.5, 'Test reasoning', 'pending', datetime('now')
        )
        """
    )
    conn.commit()
    conn.close()

    eval_result = await evaluate_simulated_daily_prediction(
        t_sim=t_sim,
        target_date="2026-04-27",
        open_price=500.0,
        close_price=505.0,
    )

    assert eval_result is not None
    assert eval_result["is_correct"] is True
    assert eval_result["actual_direction"] == "UP"
    assert eval_result["brier_score"] == pytest.approx((0.8 - 1.0) ** 2)

    # Check updated SQLite row
    conn = sqlite3.connect(backtest_module.DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT status, is_correct FROM daily_predictions WHERE id = 'pred-1'")
    row = cursor.fetchone()
    assert row["status"] == "evaluated"
    assert row["is_correct"] == 1
    conn.close()


@pytest.mark.asyncio
async def test_run_backtest_daily_autoresearch_1_week():
    """Verify running a 1-week backtest dry-run executes daily predictions and autoresearch prompt mutation."""
    mock_pred_resp = MagicMock()
    mock_pred_resp.predicted_direction = "UP"
    mock_pred_resp.confidence = 70.0
    mock_pred_resp.expected_return_pct = 0.5
    mock_pred_resp.rationale = "Bullish momentum"
    mock_pred_resp.catalysts = ["Macro stability"]

    mock_meta_resp = MagicMock()
    mock_meta_resp.new_prompt = "Focus on macro trend and VIX index level."

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=[mock_pred_resp] * 5 + [mock_meta_resp])

    with patch("tasks.backtest_daily_autoresearch.get_deepseek_client", return_value=mock_client):
        with patch("tasks.backtest_daily_autoresearch.close_client", new_callable=AsyncMock):
            with patch(
                "tasks.backtest_daily_autoresearch.fetch_historical_spy_prices",
                return_value=(500.0, 503.0),
            ):
                summary = await run_backtest_daily_autoresearch(start_date_str="2026-04-27", weeks=1)

    assert summary["weeks_completed"] == 1
    assert summary["predictions_evaluated"] == 5
    assert summary["final_ratchet_score"] is not None

    # Check SQLite for saved backtest prompt experiment
    conn = sqlite3.connect(backtest_module.DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM prompt_experiments WHERE prompt_name = 'DAILY_PREDICTOR_PROMPT'")
    rows = cursor.fetchall()
    assert len(rows) >= 1
    conn.close()
