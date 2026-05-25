"""Tests for post_analysis module."""

import asyncio
import os
import sys
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.config import GEMINI_MODEL

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))


@pytest.mark.asyncio
async def test_post_analysis_skips_existing_memory():
    """Verify that trades already analyzed for a given window are skipped.

    This test verifies the deduplication logic without requiring full LLM mocking.
    """
    from apps.engine.analysis.post_analysis import perform_post_analysis

    mock_sb = MagicMock()
    mock_gemini_client = MagicMock()

    trade = {
        "id": "trade-uuid-789",
        "ticker": "GOOGL",
        "quantity": 3,
        "price": 175.0,
        "signal": "BUY",
        "executed_at": (datetime.now(UTC) - timedelta(days=5)).isoformat(),
        "decisions": [
            {"reasoning": "AI momentum", "model_name": "test_model", "metadata": {"strategy_reasoning": "Theme play"}}
        ],
    }

    mock_sb.table.return_value.select.return_value.filter.return_value.filter.return_value.execute.return_value.data = [
        trade
    ]
    mock_sb.table.return_value.select.return_value.filter.return_value.execute.return_value.data = [
        {"id": "existing-memory"}
    ]

    with (
        patch("apps.engine.analysis.post_analysis.get_supabase_client", return_value=mock_sb),
        patch("apps.engine.analysis.post_analysis.get_gemini_client", return_value=mock_gemini_client),
        patch("apps.engine.analysis.post_analysis.MarketDataManager"),
        patch("apps.engine.analysis.post_analysis.add_memory") as mock_add_memory,
    ):
        await perform_post_analysis(windows=[5])

        assert mock_gemini_client.chat.completions.create.call_count == 0
        mock_add_memory.assert_not_called()

        print("\nTest Passed: Existing memory correctly skipped.")


def test_post_analysis_result_model():
    """Verify PostAnalysisResult model structure."""
    from apps.engine.analysis.post_analysis import PostAnalysisResult

    result = PostAnalysisResult(lesson="Test lesson", is_regret=False, sentiment_shift="Maintain bullish")

    assert result.lesson == "Test lesson"
    assert result.is_regret is False
    assert result.sentiment_shift == "Maintain bullish"

    print("\nTest Passed: PostAnalysisResult model validates correctly.")


def test_price_change_calculation_buy():
    """Verify price change calculation for BUY signals."""
    entry_price = 100.0
    current_price = 105.0
    price_change_pct = ((current_price - entry_price) / entry_price) * 100

    assert abs(price_change_pct - 5.0) < 0.01

    print("\nTest Passed: BUY price change calculated correctly (+5%).")


def test_price_change_calculation_sell():
    """Verify price change calculation for SELL signals (inverted)."""
    entry_price = 100.0
    current_price = 90.0
    signal = "SELL"

    price_change_pct = ((current_price - entry_price) / entry_price) * 100
    if signal.upper() == "SELL":
        price_change_pct = -price_change_pct

    assert abs(price_change_pct - 10.0) < 0.01

    print("\nTest Passed: SELL price change calculated correctly (+10% when price drops).")


def test_window_date_calculation():
    """Verify window date calculation for 5, 14, 30 days ago."""
    from datetime import timedelta

    now = datetime.now(UTC)

    for days_back in [5, 14, 30]:
        target_date = (now - timedelta(days=days_back)).date()
        start_time = datetime.combine(target_date, datetime.min.time()).isoformat()
        end_time = datetime.combine(target_date, datetime.max.time()).isoformat()

        assert f"{(now - timedelta(days=days_back)).date()}" in start_time
        assert f"{(now - timedelta(days=days_back)).date()}" in end_time

    print("\nTest Passed: Window date calculations correct.")


@pytest.mark.asyncio
async def test_post_analysis_metadata_includes_model_name():
    """Verify that model_name from decisions is included in memory metadata."""
    from apps.engine.analysis.post_analysis import perform_post_analysis

    mock_sb = MagicMock()
    mock_gemini_client = MagicMock()
    mock_mdm = MagicMock()
    mock_quote = MagicMock()
    mock_quote.price = 185.0

    # Setup: trade has decisions with model_name, no existing memory (so it proceeds)
    trade = {
        "id": "trade-uuid-001",
        "ticker": "AAPL",
        "quantity": 10,
        "price": 180.0,
        "signal": "BUY",
        "executed_at": (datetime.now(UTC) - timedelta(days=5)).isoformat(),
        "decisions": [
            {
                "reasoning": "Strong earnings momentum",
                "model_name": GEMINI_MODEL,
                "metadata": {"strategy_reasoning": "Tech sector rotation"},
            }
        ],
    }

    # Mock: return trade, no existing memory, successful LLM call
    mock_sb.table.return_value.select.return_value.filter.return_value.filter.return_value.execute.return_value.data = [
        trade
    ]
    mock_sb.table.return_value.select.return_value.filter.return_value.filter.return_value.filter.return_value.execute.return_value.data = []

    # Mock LLM response
    from apps.engine.analysis.post_analysis import PostAnalysisResult

    mock_response = PostAnalysisResult(
        lesson="Buying at resistance was premature", is_regret=True, sentiment_shift="Wait for pullback below 175"
    )
    mock_gemini_client.chat.completions.create.return_value = mock_response

    mock_mdm.get_quote = AsyncMock(return_value=mock_quote)

    with (
        patch("apps.engine.analysis.post_analysis.get_supabase_client", return_value=mock_sb),
        patch("apps.engine.analysis.post_analysis.get_gemini_client", return_value=mock_gemini_client),
        patch("apps.engine.analysis.post_analysis.MarketDataManager", return_value=mock_mdm),
        patch("apps.engine.analysis.post_analysis.add_memory") as mock_add_memory,
    ):
        mock_add_memory.return_value = True

        await perform_post_analysis(windows=[5])

        # Verify add_memory was called with model_name in metadata
        call_kwargs = mock_add_memory.call_args[1]
        assert "metadata" in call_kwargs
        assert call_kwargs["memory_type"] == "POST_MORTEM"
        assert call_kwargs["metadata"]["model_name"] == GEMINI_MODEL
        assert call_kwargs["metadata"]["trade_id"] == "trade-uuid-001"
        assert call_kwargs["metadata"]["analysis_window"] == "5"

        print("\nTest Passed: model_name and memory_type included in post-analysis memory metadata.")


if __name__ == "__main__":
    asyncio.run(test_post_analysis_skips_existing_memory())
    test_post_analysis_result_model()
    test_price_change_calculation_buy()
    test_price_change_calculation_sell()
    test_window_date_calculation()
    asyncio.run(test_post_analysis_metadata_includes_model_name())
