from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tasks.evaluate_predictions import run_evaluation
from tasks.predictor_autoresearch import MetaPromptResponse, run_predictor_autoresearch


@pytest.mark.asyncio
async def test_case_insensitivity():
    """Test that lowercase tickers are correctly uppercase-coerced and evaluated rather than skipped."""
    today = datetime.now(UTC).date()
    target_date = today - timedelta(days=1)
    prediction_date = target_date - timedelta(days=7)

    # Prediction with lowercase predicted_sector and pair
    mock_prediction = {
        "id": "mock-casing-123",
        "prediction_date": prediction_date.isoformat(),
        "target_date": target_date.isoformat(),
        "timeframe": "7d",
        "model_name": "deepseek-v4-flash",
        "prompt_tag": "test-casing-tag",
        "predicted_sector": "xlk",  # lowercase
        "predicted_pair": ["xlk", "xlv"],  # lowercase
        "reasoning": "Test reasoning.",
        "status": "pending",
    }

    mock_client = MagicMock()
    mock_chain = MagicMock()
    mock_select_execute = MagicMock()
    mock_select_execute.data = [mock_prediction]

    mock_update_execute = MagicMock()
    mock_update_execute.data = [{"id": "mock-casing-123"}]

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

    # Mock correlation_runs lookup to return standard tickers in uppercase
    mock_run_execute = MagicMock()
    mock_run_execute.data = [{"tickers": ["XLK", "XLV", "XLF"]}]

    # We will use this mock for correlation runs table lookup
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

    # Mock prices for uppercase tickers
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

    # The update method should be called since the prediction should NOT be skipped
    mock_chain.update.assert_called_once()
    update_args = mock_chain.update.call_args[0][0]
    assert update_args["status"] == "evaluated"
    assert update_args["sector_percentile_score"] == 100.0  # XLK (+10%) > XLV (+5%) > XLF (0%)


@pytest.mark.asyncio
async def test_dynamic_reference_universe_isolation():
    """Test that predictions on different weeks are evaluated against their respective week's correlation run tickers and do not pollute each other's percentile calculation."""
    today = datetime.now(UTC).date()
    target_date = today - timedelta(days=1)

    # Prediction A: made 7 days ago
    pred_date_a = target_date - timedelta(days=7)
    # Prediction B: made 14 days ago
    pred_date_b = target_date - timedelta(days=14)

    mock_predictions = [
        {
            "id": "pred-a",
            "prediction_date": pred_date_a.isoformat(),
            "target_date": target_date.isoformat(),
            "timeframe": "7d",
            "model_name": "deepseek-v4-flash",
            "prompt_tag": "tag-a",
            "predicted_sector": "XLK",
            "predicted_pair": ["XLK", "XLV"],
            "status": "pending",
        },
        {
            "id": "pred-b",
            "prediction_date": pred_date_b.isoformat(),
            "target_date": target_date.isoformat(),
            "timeframe": "14d",
            "model_name": "deepseek-v4-flash",
            "prompt_tag": "tag-b",
            "predicted_sector": "XLF",
            "predicted_pair": ["XLF", "KRE"],  # KRE is non-standard, predicted only in week B
            "status": "pending",
        },
    ]

    mock_client = MagicMock()
    mock_chain = MagicMock()
    mock_select_execute = MagicMock()
    mock_select_execute.data = mock_predictions

    mock_update_execute = MagicMock()
    mock_update_execute.data = [{"id": "pred-a"}, {"id": "pred-b"}]

    mock_chain.select.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain
    mock_chain.lte.return_value = mock_chain
    mock_chain.update.return_value = mock_chain

    # We want to record the actual updates sent to the database
    db_updates = {}

    def mock_update_routing(data):
        # Capture the data being updated
        nonlocal db_updates
        # This will be called before eq("id", UUID).execute()
        # We need to capture the current data and return the chain
        mock_eq_chain = MagicMock()
        mock_eq_chain.eq = lambda field, val: mock_execute_chain(val, data)
        return mock_eq_chain

    def mock_execute_chain(item_id, data):
        exec_mock = MagicMock()

        def execute_side():
            db_updates[item_id] = data
            return mock_update_execute

        exec_mock.execute = execute_side
        return exec_mock

    mock_chain.update.side_effect = mock_update_routing
    mock_client.table.return_value = mock_chain

    # Mock correlation runs:
    # Run for pred_date_a has ONLY XLK and XLV
    # Run for pred_date_b has XLK, XLV, XLF, and KRE
    mock_runs = {
        pred_date_a.isoformat(): {"tickers": ["XLK", "XLV"]},
        pred_date_b.isoformat(): {"tickers": ["XLK", "XLV", "XLF", "KRE"]},
    }

    # Standard chain for sector_predictions table
    mock_sec_pred_chain = MagicMock()
    mock_sec_pred_chain.select.return_value = mock_sec_pred_chain
    mock_sec_pred_chain.eq.return_value = mock_sec_pred_chain
    mock_sec_pred_chain.or_.return_value = mock_sec_pred_chain
    mock_sec_pred_chain.lte.return_value = mock_sec_pred_chain
    mock_sec_pred_chain.update.side_effect = mock_update_routing
    mock_sec_pred_chain.execute.return_value = mock_select_execute

    def mock_table_routing(table_name):
        if table_name == "correlation_runs":
            mock_run_chain = MagicMock()
            mock_run_chain.select.return_value = mock_run_chain
            mock_run_chain.order.return_value = mock_run_chain
            mock_run_chain.limit.return_value = mock_run_chain

            # Match by the date query parameter lte("run_date", date)
            def mock_lte(field, val):
                mock_run_chain.last_val = val
                return mock_run_chain

            mock_run_chain.lte.side_effect = mock_lte

            def mock_execute():
                val = getattr(mock_run_chain, "last_val", None)
                if val:
                    matching_date = max([d for d in mock_runs if d <= val])
                    return MagicMock(data=[mock_runs[matching_date]])
                return MagicMock(data=[])

            mock_run_chain.execute.side_effect = mock_execute
            return mock_run_chain

        if table_name == "sector_predictions":
            return mock_sec_pred_chain

        return mock_chain

    mock_client.table.side_effect = mock_table_routing

    # Returns:
    # XLK = +10%
    # XLV = +5%
    # XLF = +2%
    # KRE = -5%
    mock_history = {
        "XLK": [
            {"price": 110.0, "fetched_at": target_date.isoformat()},
            {"price": 100.0, "fetched_at": pred_date_a.isoformat()},
            {"price": 100.0, "fetched_at": pred_date_b.isoformat()},
        ],
        "XLV": [
            {"price": 105.0, "fetched_at": target_date.isoformat()},
            {"price": 100.0, "fetched_at": pred_date_a.isoformat()},
            {"price": 100.0, "fetched_at": pred_date_b.isoformat()},
        ],
        "XLF": [
            {"price": 102.0, "fetched_at": target_date.isoformat()},
            {"price": 100.0, "fetched_at": pred_date_b.isoformat()},
        ],
        "KRE": [
            {"price": 95.0, "fetched_at": target_date.isoformat()},
            {"price": 100.0, "fetched_at": pred_date_b.isoformat()},
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

    print("\nDB UPDATES RECORDED:")
    for pid, data in db_updates.items():
        print(f"ID: {pid}, Data: {data}")

    # Verify predictions were updated
    assert "pred-a" in db_updates
    assert "pred-b" in db_updates

    # Pred A: universe is ['XLK', 'XLV'] (size 2).
    # Returns: XLK = +10% (rank 1), XLV = +5% (rank 0).
    # Percentile score for XLK: (1 / 1) * 100 = 100.0.
    # If the universe leaked XLF and KRE, it would have size 4, and XLK percentile would be different or polluted.
    assert db_updates["pred-a"]["sector_percentile_score"] == 100.0

    # Pred B: universe is ['XLK', 'XLV', 'XLF', 'KRE'] (size 4).
    # Returns: XLK (+10%), XLV (+5%), XLF (+2%), KRE (-5%).
    # Percentile score for XLF: rank is 1 (only KRE is lower). (1 / 3) * 100 = 33.33333333333333.
    assert abs(db_updates["pred-b"]["sector_percentile_score"] - 33.33) < 0.1


@pytest.mark.asyncio
@patch("tasks.predictor_autoresearch.get_gemini_client")
async def test_predictor_autoresearch_ratchet_success(mock_get_gemini):
    """Test that if the weekly score beats the baseline, the active prompt is marked kept, and its variant tag is used as parent_tag for the next mutation."""
    mock_client = MagicMock()
    mock_chain = MagicMock()
    mock_client.table.return_value = mock_chain

    # Mock evaluated predictions: avg score = 85.0
    mock_predictions = [
        {"sector_percentile_score": 90.0, "pair_percentile_score": 80.0},
        {"sector_percentile_score": 85.0, "pair_percentile_score": 85.0},
    ]
    mock_pred_execute = MagicMock(data=mock_predictions)

    # Mock active prompt: tag='active-tag', content='ACTIVE_PROMPT_CONTENT'
    mock_active_prompt = [
        {
            "variant_tag": "active-tag",
            "prompt_name": "SECTOR_PREDICTOR_PROMPT",
            "prompt_content": "ACTIVE_PROMPT_CONTENT",
            "status": "active",
            "metrics": {},
        }
    ]
    mock_active_execute = MagicMock(data=mock_active_prompt)

    # Mock all variants for baseline query: baseline-tag has score 80.0
    mock_all_variants = [
        {
            "variant_tag": "baseline-tag",
            "prompt_name": "SECTOR_PREDICTOR_PROMPT",
            "prompt_content": "BASELINE_PROMPT_CONTENT",
            "status": "baseline",
            "metrics": {"score": 80.0},
        },
        mock_active_prompt[0],
    ]
    mock_all_execute = MagicMock(data=mock_all_variants)

    # DB call routing
    def mock_table_routing(table_name):
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.order.return_value = chain
        chain.limit.return_value = chain
        chain.gte.return_value = chain
        chain.lte.return_value = chain
        chain.update.return_value = chain
        chain.insert.return_value = chain

        def mock_execute():
            # If we queried predictions table
            if table_name == "sector_predictions":
                return mock_pred_execute
            # If we queried prompt_experiments table
            if table_name == "prompt_experiments":
                # Check if it was filtered by status = 'active'
                calls = chain.eq.call_args_list
                is_active_query = any(c[0] == ("status", "active") for c in calls)
                if is_active_query:
                    return mock_active_execute
                return mock_all_execute
            return MagicMock(data=[])

        chain.execute.side_effect = mock_execute
        return chain

    mock_client.table.side_effect = mock_table_routing

    # Mock Gemini researcher
    gemini_client = MagicMock()
    gemini_client.chat.completions.create = AsyncMock(
        return_value=MetaPromptResponse(new_prompt="MUTATED_PROMPT_CONTENT")
    )
    mock_get_gemini.return_value = gemini_client

    db_updates = []
    db_inserts = []

    # Capture updates/inserts
    def intercept_db(table_name):
        chain = mock_table_routing(table_name)

        def mock_update(data):
            db_updates.append((table_name, data))
            return chain

        def mock_insert(data):
            db_inserts.append((table_name, data))
            return chain

        chain.update.side_effect = mock_update
        chain.insert.side_effect = mock_insert
        return chain

    mock_client.table.side_effect = intercept_db

    with patch("tasks.predictor_autoresearch.get_supabase_client", return_value=mock_client):
        await run_predictor_autoresearch()

    # Assert metrics update on active-tag
    assert any(up[0] == "prompt_experiments" and up[1].get("metrics") == {"score": 85.0} for up in db_updates)
    # Assert active-tag status updated to baseline (beats baseline 80)
    assert any(up[0] == "prompt_experiments" and up[1].get("status") == "baseline" for up in db_updates)
    # Assert other variants demoted to saved
    assert any(up[0] == "prompt_experiments" and up[1].get("status") == "saved" for up in db_updates)
    # Assert insert contains parent_tag = 'active-tag' and mutated content wrapped in sandwich
    assert len(db_inserts) == 1
    assert db_inserts[0][0] == "prompt_experiments"
    assert db_inserts[0][1]["parent_tag"] == "active-tag"
    assert "MUTATED_PROMPT_CONTENT" in db_inserts[0][1]["prompt_content"]
    assert db_inserts[0][1]["prompt_content"].startswith("You are a highly sophisticated macro-quantitative AI")


@pytest.mark.asyncio
@patch("tasks.predictor_autoresearch.get_gemini_client")
async def test_predictor_autoresearch_ratchet_revert(mock_get_gemini):
    """Test that if the weekly score underperforms the baseline, the active prompt is marked discarded, and the baseline variant is used as parent_tag and reverted to for mutating the next prompt."""
    mock_client = MagicMock()
    mock_chain = MagicMock()
    mock_client.table.return_value = mock_chain

    # Mock evaluated predictions: avg score = 70.0
    mock_predictions = [
        {"sector_percentile_score": 75.0, "pair_percentile_score": 65.0},
        {"sector_percentile_score": 70.0, "pair_percentile_score": 70.0},
    ]
    mock_pred_execute = MagicMock(data=mock_predictions)

    # Mock active prompt: tag='active-tag', content='ACTIVE_PROMPT_CONTENT'
    mock_active_prompt = [
        {
            "variant_tag": "active-tag",
            "prompt_name": "SECTOR_PREDICTOR_PROMPT",
            "prompt_content": "ACTIVE_PROMPT_CONTENT",
            "status": "active",
            "metrics": {},
        }
    ]
    mock_active_execute = MagicMock(data=mock_active_prompt)

    # Mock all variants for baseline query: baseline-tag has score 80.0
    mock_all_variants = [
        {
            "variant_tag": "baseline-tag",
            "prompt_name": "SECTOR_PREDICTOR_PROMPT",
            "prompt_content": "BASELINE_PROMPT_CONTENT",
            "status": "baseline",
            "metrics": {"score": 80.0},
        },
        mock_active_prompt[0],
    ]
    mock_all_execute = MagicMock(data=mock_all_variants)

    # DB call routing
    def mock_table_routing(table_name):
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.order.return_value = chain
        chain.limit.return_value = chain
        chain.gte.return_value = chain
        chain.lte.return_value = chain
        chain.update.return_value = chain
        chain.insert.return_value = chain

        def mock_execute():
            if table_name == "sector_predictions":
                return mock_pred_execute
            if table_name == "prompt_experiments":
                calls = chain.eq.call_args_list
                is_active_query = any(c[0] == ("status", "active") for c in calls)
                if is_active_query:
                    return mock_active_execute
                return mock_all_execute
            return MagicMock(data=[])

        chain.execute.side_effect = mock_execute
        return chain

    gemini_client = MagicMock()
    gemini_client.chat.completions.create = AsyncMock(
        return_value=MetaPromptResponse(new_prompt="MUTATED_PROMPT_CONTENT")
    )
    mock_get_gemini.return_value = gemini_client

    db_updates = []
    db_inserts = []

    def intercept_db(table_name):
        chain = mock_table_routing(table_name)

        def mock_update(data):
            db_updates.append((table_name, data))
            return chain

        def mock_insert(data):
            db_inserts.append((table_name, data))
            return chain

        chain.update.side_effect = mock_update
        chain.insert.side_effect = mock_insert
        return chain

    mock_client.table.side_effect = intercept_db

    with patch("tasks.predictor_autoresearch.get_supabase_client", return_value=mock_client):
        await run_predictor_autoresearch()

    # Assert metrics update on active-tag
    assert any(up[0] == "prompt_experiments" and up[1].get("metrics") == {"score": 70.0} for up in db_updates)
    # Assert active-tag status updated to discarded (underperformed baseline 80)
    assert any(up[0] == "prompt_experiments" and up[1].get("status") == "discarded" for up in db_updates)
    # Assert insert contains parent_tag = 'baseline-tag' (reverted) and mutated content wrapped in sandwich
    assert len(db_inserts) == 1
    assert db_inserts[0][0] == "prompt_experiments"
    assert db_inserts[0][1]["parent_tag"] == "baseline-tag"
    assert "MUTATED_PROMPT_CONTENT" in db_inserts[0][1]["prompt_content"]
    assert db_inserts[0][1]["prompt_content"].startswith("You are a highly sophisticated macro-quantitative AI")


@pytest.mark.asyncio
@patch("tasks.predictor_autoresearch.get_gemini_client")
async def test_predictor_autoresearch_always_inserts_active(mock_get_gemini):
    """Test that even if the new prompt is identical to the current prompt, we still insert a new active variant to prevent timeline gaps."""
    mock_client = MagicMock()
    mock_chain = MagicMock()
    mock_client.table.return_value = mock_chain

    # Mock predictions: avg score = 85.0
    mock_predictions = [
        {"sector_percentile_score": 85.0, "pair_percentile_score": 85.0},
    ]
    mock_pred_execute = MagicMock(data=mock_predictions)

    # Mock active prompt: tag='active-tag', content='IDENTICAL_CONTENT'
    mock_active_prompt = [
        {
            "variant_tag": "active-tag",
            "prompt_name": "SECTOR_PREDICTOR_PROMPT",
            "prompt_content": "IDENTICAL_CONTENT",
            "status": "active",
            "metrics": {},
        }
    ]
    mock_active_execute = MagicMock(data=mock_active_prompt)

    # Mock all variants for baseline query
    mock_all_variants = [
        {
            "variant_tag": "baseline-tag",
            "prompt_name": "SECTOR_PREDICTOR_PROMPT",
            "prompt_content": "IDENTICAL_CONTENT",
            "status": "baseline",
            "metrics": {"score": 80.0},
        },
        mock_active_prompt[0],
    ]
    mock_all_execute = MagicMock(data=mock_all_variants)

    # DB call routing
    def mock_table_routing(table_name):
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.order.return_value = chain
        chain.limit.return_value = chain
        chain.gte.return_value = chain
        chain.lte.return_value = chain
        chain.update.return_value = chain
        chain.insert.return_value = chain

        def mock_execute():
            if table_name == "sector_predictions":
                return mock_pred_execute
            if table_name == "prompt_experiments":
                calls = chain.eq.call_args_list
                is_active_query = any(c[0] == ("status", "active") for c in calls)
                if is_active_query:
                    return mock_active_execute
                return mock_all_execute
            return MagicMock(data=[])

        chain.execute.side_effect = mock_execute
        return chain

    mock_client.table.side_effect = mock_table_routing

    # Mock Gemini researcher returning IDENTICAL content
    gemini_client = MagicMock()
    gemini_client.chat.completions.create = AsyncMock(return_value=MetaPromptResponse(new_prompt="IDENTICAL_CONTENT"))
    mock_get_gemini.return_value = gemini_client

    db_updates = []
    db_inserts = []

    def intercept_db(table_name):
        chain = mock_table_routing(table_name)

        def mock_update(data):
            db_updates.append((table_name, data))
            return chain

        def mock_insert(data):
            db_inserts.append((table_name, data))
            return chain

        chain.update.side_effect = mock_update
        chain.insert.side_effect = mock_insert
        return chain

    mock_client.table.side_effect = intercept_db

    with patch("tasks.predictor_autoresearch.get_supabase_client", return_value=mock_client):
        await run_predictor_autoresearch()

    # Assert that even though the content is identical, the new active variant is still inserted
    assert len(db_inserts) == 1
    assert db_inserts[0][0] == "prompt_experiments"
    assert "IDENTICAL_CONTENT" in db_inserts[0][1]["prompt_content"]
    assert db_inserts[0][1]["status"] == "active"
