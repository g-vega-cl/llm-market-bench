"""Laya.cpp Native Decision Client with TypeSafe Jev Wire Protocol and Cloud Fallback."""

from __future__ import annotations

import os
import sys
from typing import Any

import httpx

# Ensure apps/engine root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import JEV_MODEL, OPENROUTER_API_KEY, logger
from local_autoresearch.manifest import JevCriteriaConfig

DEFAULT_LAYA_URL = os.getenv("LAYA_SERVER_URL", "http://127.0.0.1:8081/v1/systemone")
DEFAULT_LAYA_HEALTH_URL = os.getenv("LAYA_HEALTH_URL", "http://127.0.0.1:8081/health")
OPENROUTER_DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"


def format_laya_payload(
    context: str,
    criteria: JevCriteriaConfig,
    ticker: str = "SPY",
    model_name: str = "laya",
) -> dict[str, Any]:
    """Format request payload matching the TypeSafe Jev / Laya wire protocol."""
    return {
        "model": model_name,
        "state": {
            "ticker": ticker.upper(),
            "market_context": context,
        },
        "questions": {
            "direction": {
                "type": "choice",
                "instructions": (
                    f"Predict whether {ticker} will close HIGHER (UP) or LOWER (DOWN) "
                    "at 4:00 PM ET compared to the 9:30 AM ET Open price."
                ),
                "criteria": {
                    "UP": criteria.criteria_up.strip(),
                    "DOWN": criteria.criteria_down.strip(),
                },
            }
        },
    }


async def is_laya_available(health_url: str = DEFAULT_LAYA_HEALTH_URL) -> bool:
    """Check if the local Laya inference server is responding."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(health_url)
            return resp.status_code == 200
    except Exception:
        return False


async def evaluate_with_laya(
    context: str,
    criteria: JevCriteriaConfig,
    ticker: str = "SPY",
    actual_direction: str | None = None,
    base_url: str = DEFAULT_LAYA_URL,
    client: httpx.AsyncClient | None = None,
    api_key: str | None = None,
    fallback_to_jev: bool = False,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    """Execute intraday decision prediction using local Laya server with optional Jev fallback."""
    payload = format_laya_payload(context, criteria, ticker=ticker, model_name="laya")
    headers = {"Content-Type": "application/json"}

    should_close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=timeout_seconds)
        should_close_client = True

    model_backend = "laya-local"
    data: dict[str, Any] | None = None

    try:
        try:
            resp = await client.post(base_url, headers=headers, json=payload)
            if resp.status_code == 200:
                raw_json = resp.json()
                data = await raw_json if hasattr(raw_json, "__await__") else raw_json
            else:
                raise RuntimeError(f"Laya server returned HTTP {resp.status_code}: {resp.text}")
        except Exception as laya_err:
            if not fallback_to_jev:
                raise laya_err

            # Attempt cloud fallback to OpenRouter Jev
            logger.warning(f"Laya server unreachable at {base_url} ({laya_err}). Attempting Jev fallback...")
            key = api_key or OPENROUTER_API_KEY
            if not key:
                raise RuntimeError(
                    f"Laya failed ({laya_err}) and OPENROUTER_API_KEY is not set for fallback."
                ) from laya_err

            payload["model"] = JEV_MODEL
            jev_headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            }
            jev_resp = await client.post(OPENROUTER_DECISIONS_URL, headers=jev_headers, json=payload)
            if jev_resp.status_code != 200:
                raise RuntimeError(
                    f"Fallback OpenRouter Jev API error {jev_resp.status_code}: {jev_resp.text}"
                ) from laya_err
            raw_json = jev_resp.json()
            data = await raw_json if hasattr(raw_json, "__await__") else raw_json
            model_backend = "openrouter-jev-fallback"
    finally:
        if should_close_client:
            await client.aclose()

    if data is None:
        raise RuntimeError("No response data received from Laya or Jev fallback.")

    answers = data.get("answers", {})
    dir_ans = answers.get("direction", {})
    choice = str(dir_ans.get("choice", "UP")).upper()
    probabilities = dir_ans.get("probabilities", {})
    prob = float(probabilities.get(choice, dir_ans.get("confidence", 0.5)))
    confidence = round(prob * 100.0, 1) if prob <= 1.0 else round(prob, 1)

    # Confidence gating
    is_gated_out = confidence < criteria.min_confidence
    gated_action = "NO_TRADE" if is_gated_out else choice

    actual_dir = str(actual_direction).upper() if actual_direction else None
    is_correct = (choice == actual_dir) if actual_dir else None

    brier_score = None
    if actual_dir:
        prob_actual = float(probabilities.get(actual_dir, 1.0 - prob if is_correct else prob))
        brier_score = round(float((1.0 - prob_actual) ** 2), 4)

    return {
        "predicted_direction": choice,
        "gated_action": gated_action,
        "actual_direction": actual_dir,
        "confidence": confidence,
        "probabilities": probabilities,
        "is_correct": is_correct,
        "is_traded": not is_gated_out,
        "brier_score": brier_score,
        "model_backend": model_backend,
    }
