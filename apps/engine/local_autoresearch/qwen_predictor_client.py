"""Qwen 32B Native Predictive Decision Client for Strata Pass 2.

Evaluates dense daily catalyst briefings synthesized in Pass 1 and executes
pure quantitative directional arbitration using native chain-of-thought (<think>)
with unconstrained reasoning budget (STRATA_REASONING_BUDGET_TOKENS = -1).
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import re
import sys
from typing import Any

import httpx

# Ensure apps/engine root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import logger
from local_autoresearch.manifest import JevCriteriaConfig

DEFAULT_STRATA_URL = os.getenv("STRATA_SERVER_URL", "http://127.0.0.1:8080/v1")
DEFAULT_STRATA_MODEL = os.getenv("STRATA_MODEL_NAME", "Qwen/Qwen2.5-32B-Instruct")

DEFAULT_QWEN_PREDICTOR_PROMPT = (
    "You are an expert quantitative directional trading arbiter for the S&P 500 (SPY).\n"
    "Your objective is to evaluate a dense point-in-time morning catalyst briefing and predict whether SPY will close HIGHER (UP) or LOWER (DOWN) at 4:00 PM ET compared to the 9:30 AM ET Open price.\n"
    "There is NO abstaining. You MUST choose either UP or DOWN based on which side holds stronger quantitative evidence and conviction.\n"
    "Analyze conflicting forces: gap size vs Treasury yields, tech breadth confirmation (QQQ), 5-day momentum exhaustion, and options positioning."
)


def format_predictor_system_prompt(criteria: JevCriteriaConfig) -> str:
    """Format System Prompt for Pass 2 Qwen Predictor combining arbiter instructions with criteria."""
    return (
        f"{DEFAULT_QWEN_PREDICTOR_PROMPT}\n\n"
        "DECISION CRITERIA:\n"
        f"- UP Conditions: {criteria.criteria_up.strip()}\n"
        f"- DOWN Conditions: {criteria.criteria_down.strip()}\n\n"
        "INSTRUCTIONS:\n"
        "1. Carefully reason through conflicting signals using step-by-step deduction.\n"
        "2. You MUST commit to either UP or DOWN. There is NO abstention.\n"
        "3. Output MUST end with a valid JSON object strictly matching this schema:\n"
        "{\n"
        '  "direction": "UP" | "DOWN",\n'
        '  "confidence": 65.0,\n'
        '  "probabilities": {"UP": 0.65, "DOWN": 0.35},\n'
        '  "rationale": "<1-2 sentence concise summary of the thesis>"\n'
        "}"
    )


def extract_predictor_decision(
    raw_text: str,
    criteria: JevCriteriaConfig,
    actual_direction: str | None = None,
) -> dict[str, Any]:
    """Extract structured decision from Qwen's completion text, handling <think> tags, markdown, or fallback."""
    # Strip <think>...</think> if present in the text
    clean_text = re.sub(r"<think>[\s\S]*?</think>", "", raw_text).strip()
    if not clean_text:
        clean_text = raw_text

    data: dict[str, Any] | None = None

    # 1. Search for fenced JSON ```json ... ```
    json_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", clean_text)
    if json_match:
        with contextlib.suppress(Exception):
            data = json.loads(json_match.group(1))

    # 2. Search for outermost raw JSON { ... }
    if not data:
        bracket_match = re.search(r"(\{[\s\S]*\})", clean_text)
        if bracket_match:
            with contextlib.suppress(Exception):
                data = json.loads(bracket_match.group(1))

    direction = "UP"
    confidence = 50.0
    probabilities: dict[str, float] = {"UP": 0.50, "DOWN": 0.50}
    rationale = "Decided via Qwen Pass 2 arbitration."

    if data and isinstance(data, dict):
        raw_dir = str(data.get("direction", "")).strip().upper()
        if raw_dir in ("UP", "DOWN"):
            direction = raw_dir

        raw_conf = data.get("confidence")
        if raw_conf is not None:
            try:
                c_val = float(raw_conf)
                confidence = round(c_val * 100.0, 1) if c_val <= 1.0 else round(c_val, 1)
            except (ValueError, TypeError):
                confidence = 50.0

        raw_probs = data.get("probabilities")
        if isinstance(raw_probs, dict):
            p_up = float(raw_probs.get("UP", 0.5))
            p_down = float(raw_probs.get("DOWN", 0.5))
            probabilities = {"UP": round(p_up, 4), "DOWN": round(p_down, 4)}
            if raw_dir not in ("UP", "DOWN"):
                direction = "UP" if p_up >= p_down else "DOWN"
        else:
            p_primary = confidence / 100.0
            if direction == "UP":
                probabilities = {"UP": round(p_primary, 4), "DOWN": round(1.0 - p_primary, 4)}
            else:
                probabilities = {"UP": round(1.0 - p_primary, 4), "DOWN": round(p_primary, 4)}

        rationale = str(data.get("rationale", "")).strip() or rationale
    else:
        # Fallback regex extraction: look for explicit UP or DOWN
        dir_match = re.search(r'"direction"\s*:\s*"(UP|DOWN)"', clean_text, re.IGNORECASE)
        if not dir_match:
            dir_match = re.search(r"\b(UP|DOWN)\b", clean_text)
        if dir_match:
            direction = dir_match.group(1).upper()

        conf_match = re.search(
            r'(?:"confidence"|confidence)\s*(?:[:=]|of|\bis\b)?\s*([0-9.]+)', clean_text, re.IGNORECASE
        )
        if conf_match:
            try:
                c_val = float(conf_match.group(1))
                confidence = round(c_val * 100.0, 1) if c_val <= 1.0 else round(c_val, 1)
            except ValueError:
                confidence = 50.0

        p_primary = confidence / 100.0
        if direction == "UP":
            probabilities = {"UP": round(p_primary, 4), "DOWN": round(1.0 - p_primary, 4)}
        else:
            probabilities = {"UP": round(1.0 - p_primary, 4), "DOWN": round(p_primary, 4)}

    # Force pure binary decision: UP or DOWN (Zero abstention)
    if direction not in ("UP", "DOWN"):
        direction = "UP" if probabilities["UP"] >= probabilities["DOWN"] else "DOWN"

    gated_action = direction
    actual_dir = str(actual_direction).upper() if actual_direction else None
    is_correct = (direction == actual_dir) if actual_dir else False

    brier_score = None
    if actual_dir:
        prob_actual = float(probabilities.get(actual_dir, 0.5))
        brier_score = round(float((1.0 - prob_actual) ** 2), 4)

    return {
        "predicted_direction": direction,
        "gated_action": gated_action,
        "actual_direction": actual_dir,
        "confidence": confidence,
        "probabilities": probabilities,
        "is_correct": is_correct,
        "is_traded": True,
        "brier_score": brier_score,
        "rationale": rationale,
        "model_backend": "qwen-predictor-local",
    }


async def evaluate_with_qwen_predictor(
    briefing: str,
    criteria: JevCriteriaConfig,
    ticker: str = "SPY",
    actual_direction: str | None = None,
    memories: list[dict[str, Any]] | None = None,
    strata_url: str = DEFAULT_STRATA_URL,
    client: httpx.AsyncClient | None = None,
    timeout_seconds: float = 60.0,
    max_retries: int = 3,
    retry_delay_seconds: float = 3.0,
) -> dict[str, Any]:
    """Execute Pass 2 Predictive Decision Arbitration using local Qwen via Strata (:8080).

    Uses unconstrained reasoning budget (STRATA_REASONING_BUDGET_TOKENS = -1) to enable
    deep analytical evaluation of the catalyst briefing alongside point-in-time memories.
    """
    system_prompt = format_predictor_system_prompt(criteria)

    memories_section = ""
    if memories:
        mem_lines = ["\n=== POINT-IN-TIME HISTORICAL MEMORIES & LESSONS ==="]
        for m in memories:
            m_type = m.get("memory_type", "LESSON")
            m_content = m.get("content", "").strip()
            mem_lines.append(f"[{m_type}] {m_content}")
        memories_section = "\n".join(mem_lines) + "\n"

    user_prompt = (
        f"Target Asset: {ticker.upper()}\n\n"
        f"=== MORNING CATALYST BRIEFING ===\n{briefing}\n"
        f"{memories_section}\n"
        "Evaluate the briefing and historical lessons against your decision criteria and output your directional prediction as JSON."
    )

    reasoning_budget = int(os.getenv("STRATA_REASONING_BUDGET_TOKENS", "-1"))
    max_tokens = int(os.getenv("STRATA_PREDICTOR_MAX_TOKENS", "1536"))
    payload = {
        "model": DEFAULT_STRATA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "reasoning_budget_tokens": reasoning_budget,
        "max_tokens": max_tokens,
    }

    headers = {"Content-Type": "application/json"}
    should_close = False
    if client is None:
        client = httpx.AsyncClient(timeout=timeout_seconds)
        should_close = True

    try:
        url = f"{strata_url.rstrip('/')}/chat/completions"
        last_err: Exception | None = None

        for attempt in range(1, max_retries + 1):
            try:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code != 200:
                    raise RuntimeError(f"Strata Predictor returned HTTP {resp.status_code}: {resp.text}")

                raw_json = resp.json()
                data = await raw_json if hasattr(raw_json, "__await__") else raw_json
                msg = data.get("choices", [{}])[0].get("message", {})
                content = msg.get("content") or msg.get("reasoning_content") or ""
                if not content.strip():
                    raise RuntimeError("Strata Predictor returned empty completion content")

                return extract_predictor_decision(
                    raw_text=content,
                    criteria=criteria,
                    actual_direction=actual_direction,
                )
            except Exception as err:
                last_err = err
                if attempt < max_retries:
                    wait_time = retry_delay_seconds * attempt
                    logger.warning(
                        f"Strata Predictor request failed ({err}). Retrying locally {attempt}/{max_retries} in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Strata Predictor failed after {max_retries} attempts: {err}")

        # Fallback to neutral NO_TRADE if all local retries fail
        logger.warning(f"Strata Predictor failed all retries ({last_err}); falling back to NO_TRADE")
        return {
            "predicted_direction": "NO_TRADE",
            "gated_action": "NO_TRADE",
            "actual_direction": actual_direction.upper() if actual_direction else None,
            "confidence": 50.0,
            "probabilities": {"UP": 0.50, "DOWN": 0.50},
            "is_correct": False,
            "is_traded": False,
            "brier_score": 0.25 if actual_direction else None,
            "rationale": f"Predictor error fallback: {last_err}",
            "model_backend": "qwen-predictor-local-fallback",
        }
    finally:
        if should_close:
            await client.aclose()
