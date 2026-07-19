from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tasks.evaluate_predictions import run_evaluation


@pytest.mark.asyncio
async def test_run_evaluation_runner():
    """Test that run_evaluation finds pending ripe predictions, calculates scores, and updates status using mocked DB."""
    today = datetime.now(UTC).date()
    target_date = today - timedelta(days=1)
    prediction_date = target_date - timedelta(days=7)

    test_model = "test-evaluator-temp-model"
    prompt_tag = "test-eval-tag"

    # 1. Mock prediction row
    mock_prediction = {
        "id": "mock-uuid-123456",
        "prediction_date": prediction_date.isoformat(),
        "target_date": target_date.isoformat(),
        "timeframe": "7d",
        "model_name": test_model,
        "prompt_tag": prompt_tag,
        "predicted_sector": "XLK",
        "predicted_pair": ["XLK", "XLU"],
        "reasoning": "Test reasoning.",
        "status": "pending",
    }

    # 2. Mock Supabase Client Chain
    mock_client = MagicMock()
    mock_chain = MagicMock()

    # Mocking chain: select("*").eq("status", "pending").lte("target_date", today.isoformat()).execute()
    mock_select_execute = MagicMock()
    mock_select_execute.data = [mock_prediction]

    # Mocking chain for update: update(...).eq("id", ...).execute()
    mock_update_execute = MagicMock()
    mock_update_execute.data = [{"id": "mock-uuid-123456"}]

    # Define a helper to handle the chain calls dynamically
    mock_chain.select.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain
    mock_chain.or_.return_value = mock_chain
    mock_chain.lte.return_value = mock_chain
    mock_chain.update.return_value = mock_chain

    # Control what execute() returns depending on what was last called
    def mock_execute_side_effect():
        if mock_chain.update.called:
            return mock_update_execute
        return mock_select_execute

    mock_chain.execute = mock_execute_side_effect
    mock_client.table.return_value = mock_chain

    # 3. Mock financial provider get_history
    # We want XLK to be 1st (+10%), XLU to be 2nd (+5%), all others to be 0% return.
    mock_history = {}
    sectors = ["XLK", "SMH", "XLE", "XLF", "XLV", "XLY", "XLI", "XLB", "XLU", "XLRE", "XLC", "XOP", "XME", "XBI"]
    for s in sectors:
        if s == "XLK":
            mock_history[s] = [
                {"price": 110.0, "fetched_at": target_date.isoformat()},
                {"price": 100.0, "fetched_at": prediction_date.isoformat()},
            ]
        elif s == "XLU":
            mock_history[s] = [
                {"price": 105.0, "fetched_at": target_date.isoformat()},
                {"price": 100.0, "fetched_at": prediction_date.isoformat()},
            ]
        else:
            mock_history[s] = [
                {"price": 100.0, "fetched_at": target_date.isoformat()},
                {"price": 100.0, "fetched_at": prediction_date.isoformat()},
            ]

    async def mock_get_history(ticker, days=14):
        return mock_history.get(ticker, [])

    mock_provider = AsyncMock()
    mock_provider.get_history = mock_get_history

    # 4. Run the evaluation
    with (
        patch("tasks.evaluate_predictions.get_supabase_client", return_value=mock_client),
        patch("tasks.evaluate_predictions.get_financial_provider", return_value=mock_provider),
    ):
        await run_evaluation()

    # 5. Verify the update assertions
    mock_chain.update.assert_called_once()
    update_args = mock_chain.update.call_args[0][0]

    # Status should be set to evaluated
    assert update_args["status"] == "evaluated"

    # XLK had return of +10%, other sectors 0%. Percentile should be 100.0
    assert update_args["sector_percentile_score"] == 100.0

    # XLK + XLU had average return of 7.5%, others 0%. Percentile should be 100.0
    assert update_args["pair_percentile_score"] == 100.0

    # Check that it updated the correct ID
    mock_chain.eq.assert_any_call("id", "mock-uuid-123456")
