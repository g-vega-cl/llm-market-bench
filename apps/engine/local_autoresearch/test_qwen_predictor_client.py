"""Hermetic unit tests for local_autoresearch.qwen_predictor_client."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from local_autoresearch.manifest import JevCriteriaConfig
from local_autoresearch.qwen_predictor_client import (
    evaluate_with_qwen_predictor,
    extract_predictor_decision,
)


@pytest.fixture
def default_criteria() -> JevCriteriaConfig:
    return JevCriteriaConfig(
        criteria_up="Overnight tape shows SPY gap >= +0.15% with QQQ confirmation and yields falling.",
        criteria_down="Overnight tape shows gap rejection or tech weakness with rising yields.",
        min_confidence=56.0,
    )


def test_predictor_prompt_has_no_hardcoded_tie_break(default_criteria: JevCriteriaConfig):
    """Tie-breaking is a trading heuristic; the baseline must not seed a momentum bias."""
    from local_autoresearch.qwen_predictor_client import (
        DEFAULT_QWEN_PREDICTOR_PROMPT,
        format_predictor_system_prompt,
    )

    full = format_predictor_system_prompt(default_criteria)
    assert "break ties" not in DEFAULT_QWEN_PREDICTOR_PROMPT.lower()
    assert "dominant momentum" not in full
    # Structural contract stays: binary output, no abstention
    assert "NO abstaining" in full


def test_format_predictor_prompt_zero_abstention_no_conviction_guidance(default_criteria: JevCriteriaConfig):
    """Predictor prompt must enforce zero abstention and contain no conviction guidance or min_confidence."""
    from local_autoresearch.qwen_predictor_client import format_predictor_system_prompt

    full = format_predictor_system_prompt(default_criteria)
    assert "Conviction Guidance" not in full
    assert "min_confidence" not in full.lower()


def test_extract_predictor_decision_clean_json(default_criteria: JevCriteriaConfig):
    raw_response = """
    <think>
    Treasury yields are falling and tech breadth confirms the gap up.
    </think>
    {
      "direction": "UP",
      "confidence": 68.5,
      "probabilities": {"UP": 0.685, "DOWN": 0.315},
      "rationale": "Strong gap up confirmed by falling 10Y yields and positive QQQ breadth."
    }
    """
    res = extract_predictor_decision(
        raw_text=raw_response,
        criteria=default_criteria,
        actual_direction="UP",
    )

    assert res["predicted_direction"] == "UP"
    assert res["gated_action"] == "UP"
    assert res["confidence"] == 68.5
    assert res["is_correct"] is True
    assert res["is_traded"] is True
    assert res["probabilities"]["UP"] == 0.685
    # Brier score: (1.0 - 0.685)^2 = 0.0992
    assert res["brier_score"] == pytest.approx(0.0992, abs=0.001)
    assert "falling 10Y yields" in res["rationale"]


def test_extract_predictor_decision_binary_commitment(default_criteria: JevCriteriaConfig):
    raw_response = """
    ```json
    {
      "direction": "DOWN",
      "confidence": 53.0,
      "probabilities": {"UP": 0.47, "DOWN": 0.53},
      "rationale": "Slight weakness in yields."
    }
    ```
    """
    # Even at 53.0% confidence, there is NO abstention: model trades DOWN
    res = extract_predictor_decision(
        raw_text=raw_response,
        criteria=default_criteria,
        actual_direction="DOWN",
    )

    assert res["predicted_direction"] == "DOWN"
    assert res["gated_action"] == "DOWN"
    assert res["confidence"] == 53.0
    assert res["is_traded"] is True
    assert res["is_correct"] is True


def test_extract_predictor_decision_legacy_no_trade_fallback(default_criteria: JevCriteriaConfig):
    raw_response = """
    {
      "direction": "NO_TRADE",
      "confidence": 50.0,
      "probabilities": {"UP": 0.50, "DOWN": 0.50},
      "rationale": "Conflicting signals between yields and tech breadth."
    }
    """
    # Zero abstention rule: legacy NO_TRADE or balanced tie breaks to binary choice (UP/DOWN)
    res = extract_predictor_decision(
        raw_text=raw_response,
        criteria=default_criteria,
        actual_direction="UP",
    )

    assert res["predicted_direction"] in ("UP", "DOWN")
    assert res["gated_action"] in ("UP", "DOWN")
    assert res["is_traded"] is True
    assert res["is_correct"] == (res["predicted_direction"] == "UP")


def test_extract_predictor_decision_malformed_fallback(default_criteria: JevCriteriaConfig):
    raw_response = """
    I predict the direction is DOWN with high confidence of 62.0% because yields are spiking.
    """
    res = extract_predictor_decision(
        raw_text=raw_response,
        criteria=default_criteria,
        actual_direction="DOWN",
    )

    assert res["predicted_direction"] == "DOWN"
    assert res["gated_action"] == "DOWN"
    assert res["confidence"] == 62.0
    assert res["is_traded"] is True
    assert res["is_correct"] is True


@pytest.mark.asyncio
async def test_evaluate_with_qwen_predictor(default_criteria: JevCriteriaConfig):
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": (
                        "<think>Evaluating brief...</think>\n"
                        "{\n"
                        '  "direction": "DOWN",\n'
                        '  "confidence": 64.0,\n'
                        '  "probabilities": {"UP": 0.36, "DOWN": 0.64},\n'
                        '  "rationale": "Yield spike and tech breadth divergence."\n'
                        "}"
                    )
                }
            }
        ]
    }

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        res = await evaluate_with_qwen_predictor(
            briefing="## Daily Briefing\nYields rose 5 bps...",
            criteria=default_criteria,
            ticker="SPY",
            actual_direction="DOWN",
            strata_url="http://localhost:8080/v1",
        )

        assert res["predicted_direction"] == "DOWN"
        assert res["gated_action"] == "DOWN"
        assert res["confidence"] == 64.0
        assert res["is_correct"] is True
        assert res["is_traded"] is True
        assert res["model_backend"] == "qwen-predictor-local"


@pytest.mark.asyncio
async def test_evaluate_with_qwen_predictor_with_memories(default_criteria: JevCriteriaConfig):
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"direction": "UP", "confidence": 62.0, "rationale": "Memories support continuation"}'
                }
            }
        ]
    }

    memories = [
        {"memory_type": "LESSON_LEARNED", "content": "Never fade unconfirmed trend days"},
        {"memory_type": "POST_MORTEM", "content": "10Y yield spike caused tech roll-over"},
    ]

    with patch("httpx.AsyncClient.post", return_value=mock_resp) as mock_post:
        res = await evaluate_with_qwen_predictor(
            briefing="## Daily Briefing...",
            criteria=default_criteria,
            ticker="SPY",
            actual_direction="UP",
            memories=memories,
            strata_url="http://localhost:8080/v1",
        )

        assert res["predicted_direction"] == "UP"
        mock_post.assert_called_once()
        sent_payload = mock_post.call_args.kwargs["json"]
        user_msg = sent_payload["messages"][1]["content"]
        assert "POINT-IN-TIME HISTORICAL MEMORIES" in user_msg
        assert "Never fade unconfirmed trend days" in user_msg
