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
    """Verify evaluating daily prediction updates open, close, is_correct, and brier score with inferred high/low."""
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
    cursor.execute(
        "SELECT status, is_correct, actual_open_price, actual_close_price, actual_high_price, actual_low_price "
        "FROM daily_predictions WHERE id = 'pred-1'"
    )
    row = cursor.fetchone()
    assert row["status"] == "evaluated"
    assert row["is_correct"] == 1
    assert row["actual_open_price"] == 500.0
    assert row["actual_close_price"] == 505.0
    assert row["actual_high_price"] == 505.0
    assert row["actual_low_price"] == 500.0
    conn.close()


@pytest.mark.asyncio
async def test_evaluate_simulated_daily_prediction_with_explicit_high_low():
    """Verify evaluating daily prediction with explicit high and low prices."""
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
            'pred-2', '2026-04-27', '2026-04-27', 'SPY', 'deepseek-v4-flash', 'test-tag-123',
            'DOWN', 70.0, -0.4, 'Test reasoning', 'pending', datetime('now')
        )
        """
    )
    conn.commit()
    conn.close()

    eval_result = await evaluate_simulated_daily_prediction(
        t_sim=t_sim,
        target_date="2026-04-27",
        open_price=500.0,
        high_price=502.0,
        low_price=495.0,
        close_price=496.0,
    )

    assert eval_result is not None
    assert eval_result["is_correct"] is True
    assert eval_result["actual_direction"] == "DOWN"
    assert eval_result["intraday_hit"] is True

    conn = sqlite3.connect(backtest_module.DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT actual_high_price, actual_low_price, intraday_hit FROM daily_predictions WHERE id = 'pred-2'"
    )
    row = cursor.fetchone()
    assert row["actual_high_price"] == 502.0
    assert row["actual_low_price"] == 495.0
    assert row["intraday_hit"] == 1
    conn.close()


@pytest.mark.asyncio
async def test_fetch_historical_spy_prices_market_data_and_fallback():
    """Verify fetch_historical_spy_prices uses MarketDataManager when available, and falls back gracefully."""
    mock_mdm = MagicMock()
    mock_mdm.get_history = AsyncMock(
        return_value=[
            {"fetched_at": "2026-04-27T16:00:00Z", "open": 500.0, "high": 508.0, "low": 498.0, "price": 506.0}
        ]
    )

    with patch("execution.market_data.MarketDataManager", return_value=mock_mdm):
        open_p, high_p, low_p, close_p = await backtest_module.fetch_historical_spy_prices("2026-04-27")
        assert open_p == 500.0
        assert high_p == 508.0
        assert low_p == 498.0
        assert close_p == 506.0

    # Test fallback path when MarketDataManager raises
    with patch("execution.market_data.MarketDataManager", side_effect=RuntimeError("MDM down")):
        open_p, high_p, low_p, close_p = await backtest_module.fetch_historical_spy_prices("2026-04-27")
        assert open_p == 500.0
        assert high_p >= open_p
        assert low_p <= open_p


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
