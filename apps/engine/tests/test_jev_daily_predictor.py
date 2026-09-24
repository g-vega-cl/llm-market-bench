from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.config import JEV_MODEL
from core.llm.daily_predictor_prompts import (
    JEV_DEFAULT_CRITERIA,
    format_jev_prompt_content,
    parse_jev_prompt_content,
)


def test_jev_criteria_format_and_parse():
    """Verify serialization and deserialization of Jev criteria for prompt_experiments."""
    formatted = format_jev_prompt_content(JEV_DEFAULT_CRITERIA)
    assert '"UP":' in formatted
    assert '"DOWN":' in formatted

    parsed = parse_jev_prompt_content(formatted)
    assert parsed["UP"] == JEV_DEFAULT_CRITERIA["UP"]
    assert parsed["DOWN"] == JEV_DEFAULT_CRITERIA["DOWN"]

    # Test fallback on invalid JSON
    fallback = parse_jev_prompt_content("invalid json content")
    assert fallback["UP"] == JEV_DEFAULT_CRITERIA["UP"]
    assert fallback["DOWN"] == JEV_DEFAULT_CRITERIA["DOWN"]


@pytest.mark.asyncio
async def test_predict_daily_with_jev_success():
    """Verify predict_daily_with_jev posts to OpenRouter Decisions API and parses typed decision."""
    from tasks.daily_predictor import predict_daily_with_jev

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "id": "gen-dec-12345",
        "model": "typesafe/jev-1.13-20260917",
        "provider": "TypeSafe",
        "answers": {
            "direction": {
                "type": "choice",
                "choice": "UP",
                "confidence": 0.74,
                "probabilities": {"UP": 0.74, "DOWN": 0.26},
            }
        },
        "usage": {"input_tokens": 450, "output_tokens": 0, "cost": 0.00002},
    }

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("tasks.daily_predictor.httpx.AsyncClient", return_value=mock_client),
        patch("tasks.daily_predictor.OPENROUTER_API_KEY", "test-or-key"),
    ):
        pred = await predict_daily_with_jev(
            context="S&P 500 pre-market context: futures up 0.4%, tech leading.",
            criteria=JEV_DEFAULT_CRITERIA,
            ticker="SPY",
            model_name=JEV_MODEL,
        )

        assert pred["predicted_direction"] == "UP"
        assert pred["confidence"] == 74.0
        assert pred["expected_return_pct"] == 0.0
        assert "Jev System One decision: UP" in pred["rationale"]
        assert pred["catalysts"] == []

        # Verify exact request parameters sent to OpenRouter Decisions API
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "https://openrouter.ai/api/alpha/decisions"
        headers = call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer test-or-key"
        payload = call_args[1]["json"]
        assert payload["model"] == JEV_MODEL
        assert payload["state"]["ticker"] == "SPY"
        assert "futures up 0.4%" in payload["state"]["market_context"]
        assert payload["questions"]["direction"]["type"] == "choice"
        assert payload["questions"]["direction"]["criteria"]["UP"] == JEV_DEFAULT_CRITERIA["UP"]


@pytest.mark.asyncio
async def test_predict_daily_with_jev_missing_api_key():
    """Verify predict_daily_with_jev raises ValueError if OPENROUTER_API_KEY is unset."""
    from tasks.daily_predictor import predict_daily_with_jev

    with patch("tasks.daily_predictor.OPENROUTER_API_KEY", None):
        with pytest.raises(ValueError, match="OPENROUTER_API_KEY is not set"):
            await predict_daily_with_jev(
                context="Context",
                criteria=JEV_DEFAULT_CRITERIA,
                ticker="SPY",
            )


@pytest.mark.asyncio
async def test_predict_daily_with_jev_api_error():
    """Verify predict_daily_with_jev raises RuntimeError on API failure."""
    from tasks.daily_predictor import predict_daily_with_jev

    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = "Bad Request: Invalid model"

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("tasks.daily_predictor.httpx.AsyncClient", return_value=mock_client),
        patch("tasks.daily_predictor.OPENROUTER_API_KEY", "test-or-key"),
    ):
        with pytest.raises(RuntimeError, match="OpenRouter Decisions API error 400"):
            await predict_daily_with_jev(
                context="Context",
                criteria=JEV_DEFAULT_CRITERIA,
                ticker="SPY",
            )


@pytest.mark.asyncio
async def test_run_daily_prediction_includes_jev_track():
    """Verify run_daily_prediction includes Jev model in the arena and logs prediction."""
    from tasks.daily_predictor import run_daily_prediction

    mock_supabase = MagicMock()
    # Mock active prompt response for models
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
        {"variant_tag": "daily-pred-tag", "prompt_content": "active content"}
    ]
    upserted_rows = []

    def mock_upsert(row, on_conflict=None):
        upserted_rows.append(row)
        return MagicMock(execute=MagicMock(return_value=MagicMock(data=[{"id": "test-uuid"}])))

    mock_supabase.table.return_value.upsert.side_effect = mock_upsert

    mock_deepseek = MagicMock()
    mock_deepseek_pred = MagicMock(
        predicted_direction="UP",
        confidence=70.0,
        expected_return_pct=0.35,
        rationale="DeepSeek rationale",
        catalysts=["Catalyst 1"],
    )
    mock_deepseek.chat.completions.create = AsyncMock(return_value=mock_deepseek_pred)

    mock_minimax = MagicMock()
    mock_minimax.chat_with_json_response = AsyncMock(
        return_value={
            "predicted_direction": "DOWN",
            "confidence": 65.0,
            "expected_return_pct": -0.25,
            "rationale": "MiniMax rationale",
            "catalysts": ["Catalyst 2"],
        }
    )
    mock_minimax.close = AsyncMock()

    mock_jev_pred = {
        "predicted_direction": "UP",
        "confidence": 78.0,
        "expected_return_pct": 0.0,
        "rationale": "Jev System One decision: UP (P=0.78)",
        "catalysts": [],
    }

    mock_mdm = MagicMock()
    mock_mdm.is_trading_day = AsyncMock(return_value=True)

    with (
        patch("tasks.daily_predictor.get_supabase_client", return_value=mock_supabase),
        patch("tasks.daily_predictor.get_deepseek_client", return_value=mock_deepseek),
        patch("tasks.daily_predictor.MiniMaxClient", return_value=mock_minimax),
        patch("tasks.daily_predictor.predict_daily_with_jev", new_callable=AsyncMock, return_value=mock_jev_pred),
        patch("tasks.daily_predictor.get_daily_market_context", new_callable=AsyncMock, return_value="Context"),
        patch("execution.market_data.MarketDataManager", return_value=mock_mdm),
    ):
        results = await run_daily_prediction(ticker="SPY", force=True)

        # 3 models in the arena: DeepSeek, MiniMax, Jev
        model_names = [r["model_name"] for r in results]
        assert JEV_MODEL in model_names
        assert len(results) == 3

        jev_row = next(r for r in results if r["model_name"] == JEV_MODEL)
        assert jev_row["predicted_direction"] == "UP"
        assert jev_row["confidence"] == 78.0
        assert jev_row["expected_return_pct"] == 0.0
