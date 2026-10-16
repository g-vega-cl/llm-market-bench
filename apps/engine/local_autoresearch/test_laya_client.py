"""Hermetic unit tests for local_autoresearch.laya_client."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from local_autoresearch.laya_client import (
    evaluate_with_laya,
    format_laya_payload,
    is_laya_available,
)
from local_autoresearch.manifest import JevCriteriaConfig


@pytest.fixture
def sample_criteria() -> JevCriteriaConfig:
    return JevCriteriaConfig(
        criteria_up="Treasury yields declining and positive gap.",
        criteria_down="Yields surging and gap rejection.",
        min_confidence=58.0,
    )


def test_format_laya_payload(sample_criteria: JevCriteriaConfig):
    context = "=== POINT-IN-TIME MARKET CONTEXT: SPY ==="
    payload = format_laya_payload(context, sample_criteria, ticker="SPY")

    assert payload["model"] == "laya"
    assert payload["state"]["ticker"] == "SPY"
    assert payload["state"]["market_context"] == context
    assert "direction" in payload["questions"]
    q = payload["questions"]["direction"]
    assert q["type"] == "choice"
    assert "UP" in q["criteria"]
    assert "DOWN" in q["criteria"]
    assert q["criteria"]["UP"] == sample_criteria.criteria_up


@pytest.mark.asyncio
async def test_is_laya_available_true():
    mock_resp = AsyncMock()
    mock_resp.status_code = 200

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        assert await is_laya_available("http://127.0.0.1:8081/health") is True


@pytest.mark.asyncio
async def test_is_laya_available_false():
    with patch("httpx.AsyncClient.get", side_effect=Exception("Connection refused")):
        assert await is_laya_available("http://127.0.0.1:8081/health") is False


@pytest.mark.asyncio
async def test_evaluate_with_laya_success(sample_criteria: JevCriteriaConfig):
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "answers": {
            "direction": {
                "type": "choice",
                "choice": "UP",
                "confidence": 0.72,
                "probabilities": {"UP": 0.72, "DOWN": 0.28},
            }
        },
        "routing": {"model": "laya"},
    }

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        res = await evaluate_with_laya(
            context="Test context",
            criteria=sample_criteria,
            ticker="SPY",
            actual_direction="UP",
        )

    assert res["predicted_direction"] == "UP"
    assert res["confidence"] == 72.0
    assert res["is_correct"] is True
    assert res["is_traded"] is True  # 72.0 >= 58.0 min_confidence
    assert res["gated_action"] == "UP"
    assert res["brier_score"] == pytest.approx((1.0 - 0.72) ** 2, abs=1e-4)


@pytest.mark.asyncio
async def test_evaluate_with_laya_gated_out(sample_criteria: JevCriteriaConfig):
    sample_criteria.min_confidence = 75.0
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "answers": {
            "direction": {
                "type": "choice",
                "choice": "UP",
                "confidence": 0.60,
                "probabilities": {"UP": 0.60, "DOWN": 0.40},
            }
        }
    }

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        res = await evaluate_with_laya(
            context="Test context",
            criteria=sample_criteria,
            ticker="SPY",
            actual_direction="UP",
        )

    assert res["predicted_direction"] == "UP"
    assert res["confidence"] == 60.0
    assert res["is_traded"] is False  # 60.0 < 75.0 min_confidence
    assert res["gated_action"] == "NO_TRADE"


@pytest.mark.asyncio
async def test_evaluate_with_laya_fallback_to_jev(sample_criteria: JevCriteriaConfig):
    # Laya fails with connection error, but Jev succeeds on fallback
    laya_fail = Exception("Laya offline")

    jev_mock_resp = AsyncMock()
    jev_mock_resp.status_code = 200
    jev_mock_resp.json.return_value = {
        "answers": {
            "direction": {
                "type": "choice",
                "choice": "DOWN",
                "confidence": 0.65,
                "probabilities": {"UP": 0.35, "DOWN": 0.65},
            }
        }
    }

    async def mock_post(url, *args, **kwargs):
        if "8081" in str(url):
            raise laya_fail
        return jev_mock_resp

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        res = await evaluate_with_laya(
            context="Test context",
            criteria=sample_criteria,
            ticker="SPY",
            actual_direction="DOWN",
            api_key="test-openrouter-key",
            fallback_to_jev=True,
        )

    assert res["predicted_direction"] == "DOWN"
    assert res["confidence"] == 65.0
    assert res["is_correct"] is True
    assert res["model_backend"] == "openrouter-jev-fallback"


@pytest.mark.asyncio
async def test_evaluate_with_laya_default_disables_fallback(sample_criteria: JevCriteriaConfig):
    # Laya fails with connection error, default fallback_to_jev=False raises without calling OpenRouter
    with (
        patch("httpx.AsyncClient.post", side_effect=Exception("Laya offline")),
        pytest.raises(Exception, match="Laya offline"),
    ):
        await evaluate_with_laya(
            context="Test context",
            criteria=sample_criteria,
            ticker="SPY",
            actual_direction="DOWN",
        )
