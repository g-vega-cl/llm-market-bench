"""Pure request normalization, metadata extraction, and model resolution helpers."""

from __future__ import annotations

from typing import Any

from fastapi import Request

from apps.free_llm_proxy import config
from apps.free_llm_proxy.circuit_breaker import _DETERMINISTIC_4XX
from apps.free_llm_proxy.discovery import is_allowed_model
from apps.free_llm_proxy.router import Router

THINKING_KEYS = ("reasoning_effort", "reasoning", "reasoning_budget_tokens")


def failure_priority(status_code: int) -> int:
    """Orders failure statuses so downstream 404/504 never masks 429/5xx."""
    if status_code == 429:
        return 4
    if status_code in _DETERMINISTIC_4XX:
        return 3
    if status_code >= 500:
        return 2
    return 1


def resolve_candidate_model(
    router: Router,
    p_id: str,
    p_cfg: dict[str, Any],
    requested_model: str,
    available_models: list[str],
    *,
    is_paid: bool,
) -> tuple[str | None, str | None, dict[str, Any] | None]:
    """Resolves target model or returns ``(None, skip_reason, error_body)``."""
    allowed_patterns = p_cfg.get("allowed_model_patterns")
    dynamic_fallback = p_cfg.get("dynamic_fallback_model")
    if is_paid and not available_models:
        return (
            None,
            f"{p_id} (catalog unavailable; paid dispatch refused)",
            {
                "error": {
                    "message": f"{p_id} catalog discovery failed; refusing paid dispatch",
                    "type": "provider_unavailable",
                }
            },
        )
    if allowed_patterns is not None and not dynamic_fallback and not available_models:
        return (
            None,
            f"{p_id} (catalog unavailable; free-only dispatch refused)",
            {
                "error": {
                    "message": (
                        f"{p_id} catalog discovery failed; refusing ungrounded dispatch"
                    ),
                    "type": "provider_unavailable",
                }
            },
        )

    target_model = router.resolve_model_for_provider(
        p_id, requested_model, available_models
    )
    if allowed_patterns is not None and not is_allowed_model(
        target_model, allowed_patterns
    ):
        if dynamic_fallback and is_allowed_model(dynamic_fallback, allowed_patterns):
            return dynamic_fallback, None, None
        return (
            None,
            f"{p_id} (no allowed free model resolved)",
            {
                "error": {
                    "message": f"{p_id} resolved no allowed free model",
                    "type": "provider_unavailable",
                }
            },
        )
    return target_model, None, None


def _effort_from_reasoning_budget(budget: float) -> str:
    """Maps a Strata-style token budget onto an OpenAI effort band."""
    for threshold, level in config.REASONING_BUDGET_BANDS:
        if budget > threshold:
            return level
    return "low"


def apply_thinking_params(
    payload: dict[str, Any], p_cfg: dict[str, Any], model: str
) -> None:
    """Forwards thinking controls only to providers that declare support for them.

    Every thinking key is stripped first: a gateway that 400s on unknown fields
    otherwise converts a caller's effort request into a 60s provider cooldown
    (circuit_breaker: deterministic 4xx). Declared params are then re-added, with
    the OpenAI `reasoning_effort` spelling normalized to OpenRouter's object form.
    """
    requested_effort = payload.get("reasoning_effort")
    requested_reasoning = payload.get("reasoning")
    budget = payload.get("reasoning_budget_tokens")
    for key in THINKING_KEYS:
        payload.pop(key, None)

    effort = (
        requested_effort.strip().lower() if isinstance(requested_effort, str) else ""
    )
    if not effort and isinstance(budget, (int, float)) and not isinstance(budget, bool):
        effort = _effort_from_reasoning_budget(budget)
    if (
        not effort
        and config.AUTO_GO_DEFAULT_REASONING_EFFORT
        and model.lower().endswith("-go")
    ):
        effort = config.AUTO_GO_DEFAULT_REASONING_EFFORT

    declared = set(p_cfg.get("thinking_params") or [])
    if (
        "reasoning" in declared
        and isinstance(requested_reasoning, dict)
        and requested_reasoning
    ):
        payload["reasoning"] = dict(requested_reasoning)
    if "reasoning_effort" in declared and effort:
        payload["reasoning_effort"] = effort
    elif "reasoning" in declared and effort:
        reasoning = dict(payload.get("reasoning") or {})
        reasoning.setdefault("effort", effort)
        payload["reasoning"] = reasoning


def apply_output_ceiling(payload: dict[str, Any], p_cfg: dict[str, Any]) -> None:
    """Clamps both output-token spellings to the provider's declared ceiling.

    Reasoning tokens are billed inside this budget, so the ceiling is the real
    thinking cap. A provider's own limit wins; undeclared providers fall back to
    CLOUD_MAX_OUTPUT_TOKENS. The clamp only ever lowers a caller's request.
    """
    ceiling = p_cfg.get("max_output_tokens")
    if not isinstance(ceiling, int) or isinstance(ceiling, bool) or ceiling <= 0:
        ceiling = config.CLOUD_MAX_OUTPUT_TOKENS
    for key in ("max_tokens", "max_completion_tokens"):
        value = payload.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and value > ceiling:
            payload[key] = ceiling


def is_explicit_paid_request(model: str, provider_id: str) -> bool:
    """True when the caller deliberately targeted the paid provider."""
    requested = model.strip().lower()
    return requested == provider_id or requested.startswith(f"{provider_id}/")


def extract_prompt_preview(messages: list[Any], max_length: int = 60) -> str | None:
    """Extract a concise text snippet (up to max_length chars) of caller intent/why."""
    if not messages:
        return None
    user_msgs = [m for m in messages if getattr(m, "role", "") == "user"]
    target = user_msgs[-1] if user_msgs else messages[-1]
    content = getattr(target, "content", None)
    if isinstance(content, str):
        text = " ".join(content.split()).strip()
    elif isinstance(content, list):
        parts = [
            part.get("text", "")
            for part in content
            if isinstance(part, dict)
            and part.get("type") == "text"
            and part.get("text")
        ]
        text = " ".join(" ".join(parts).split()).strip()
    else:
        return None
    if not text:
        return None
    return text[:max_length] + ("..." if len(text) > max_length else "")


def extract_client_info(request: Request | None) -> tuple[str, str]:
    """Extracts client IP and User-Agent from Request."""
    if not request:
        return ("unknown", "unknown")
    client_ip = (
        request.headers.get("cf-connecting-ip")
        or request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )
    user_agent = request.headers.get("user-agent", "unknown")
    return (client_ip, user_agent)


def extract_purpose(request: Request) -> str | None:
    """Extracts caller intent header when supplied."""
    return (
        request.headers.get("x-purpose")
        or request.headers.get("x-client-id")
        or request.headers.get("x-caller-reason")
        or None
    )


def normalize_non_streaming_choices(body: Any) -> None:
    """Ensure every choice message carries a string content field."""
    if isinstance(body, dict):
        for choice in body.get("choices", []):
            msg = choice.get("message", {})
            if "content" not in msg or msg["content"] is None:
                msg["content"] = ""
