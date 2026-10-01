"""Response parsing, JSON repair, and Instructor extraction vertical slice island."""

import asyncio
import json
import logging
import re
from typing import Any

from core.llm.analysis_pipeline.prompt_assembly import safe_deepcopy
from core.llm.utils import ensure_list
from core.models import DecisionsResponse

logger = logging.getLogger("engine")


def repair_json_string(json_str: str) -> str:
    """Attempt to repair a malformed JSON string by extracting and unescaping valid JSON."""
    if not isinstance(json_str, str):
        return json_str

    json_str = json_str.strip()

    # Repair unescaped single backslashes that escape delimiter double-quotes
    pattern = r'(?<!\\)\\"(?=\s*(?:\}\s*\]?|\}\s*\}|\]\s*\}|\]\s*\]|\}\s*,|\]\s*,|,\s*"\w+"\s*:|,\s*\}|,\s*\]|\s*$))'
    json_str = re.sub(pattern, r'\\\\"', json_str)

    if json_str.startswith('"') and json_str.endswith('"'):
        json_str = json_str[1:-1]
        json_str = json_str.replace('\\"', '"').replace("\\\\n", "\\n").replace("\\\\r", "\\r")

    # Always trim trailing text after JSON object/array
    if json_str.startswith("{"):
        end_idx = json_str.rfind("}")
        if end_idx != -1:
            json_str = json_str[: end_idx + 1]
    elif json_str.startswith("["):
        end_idx = json_str.rfind("]")
        if end_idx != -1:
            json_str = json_str[: end_idx + 1]
    else:
        # JSON doesn't start at beginning, find and extract it
        start_idx = json_str.find("{")
        if start_idx == -1:
            start_idx = json_str.find("[")
        if start_idx != -1:
            json_str = json_str[start_idx:]
            if json_str.startswith("{"):
                end_idx = json_str.rfind("}")
                if end_idx != -1:
                    json_str = json_str[: end_idx + 1]
            elif json_str.startswith("["):
                end_idx = json_str.rfind("]")
                if end_idx != -1:
                    json_str = json_str[: end_idx + 1]

    return json_str


def try_parse_response(data: Any, response_model: Any, max_retries: int = 2) -> Any:
    """Attempt to parse data into the specified response_model using multi-level repair strategies."""
    strategies = []

    if isinstance(data, dict):
        strategies.append(lambda d: response_model(**d))

        if "decisions" in data and isinstance(data["decisions"], str):
            repaired = repair_json_string(data["decisions"])
            try:
                data_copy = dict(data)
                data_copy["decisions"] = json.loads(repaired, strict=False)
                strategies.append(lambda d, dc=data_copy: response_model(**dc))
            except Exception:
                pass

        if "macro_events" in data and isinstance(data["macro_events"], str):
            repaired = repair_json_string(data["macro_events"])
            try:
                data_copy = dict(data)
                data_copy["macro_events"] = json.loads(repaired, strict=False)
                strategies.append(lambda d, dc=data_copy: response_model(**dc))
            except Exception:
                pass

    elif isinstance(data, str):
        strategies.append(lambda d: response_model.model_validate_json(d))

        repaired = repair_json_string(data)
        strategies.append(lambda d, r=repaired: response_model.model_validate_json(r))

        try:
            parsed = json.loads(repaired, strict=False)
            strategies.append(
                lambda d, p=parsed: response_model.model_validate_json(p) if isinstance(p, str) else response_model(**p)
            )
        except Exception:
            pass

    errors = []
    for i, strategy in enumerate(strategies):
        try:
            return strategy(data)
        except Exception as e:
            errors.append((i, e))
            continue

    if errors:
        model_name = getattr(response_model, "__name__", str(response_model))
        logger.warning(
            "All %d %s parse strategies failed. Errors: %s",
            len(strategies),
            model_name,
            "; ".join(f"Strategy {i}: {type(e).__name__}: {e}" for i, e in errors),
        )

    return None


def try_parse_decisions_response(data: Any, max_retries: int = 2) -> DecisionsResponse | None:
    """Legacy backward-compatible wrapper parsing specifically into DecisionsResponse."""
    return try_parse_response(data, DecisionsResponse, max_retries)


def create_fallback_model(response_model: Any) -> Any:
    """Create an empty instance of the response model with empty arrays for decisions/macro_events."""
    init_args = {}
    if hasattr(response_model, "decisions"):
        init_args["decisions"] = []
    if hasattr(response_model, "macro_events"):
        init_args["macro_events"] = []
    return response_model(**init_args)


async def extract_structured_response(
    client: Any,
    final_args: dict[str, Any],
    provider: str,
    model_name: str,
    response_model: Any,
    schema_hint: str,
    messages: list,
    is_retryable_error: Any = None,
) -> Any:
    """Execute Instructor structured extraction with retry and JSON repair for validation errors."""
    wrapper = None
    last_error = None

    for attempt in range(3):
        try:
            resp_awaitable = client.chat.completions.create(**final_args)
            if hasattr(resp_awaitable, "__await__") or asyncio.iscoroutine(resp_awaitable):
                wrapper = await resp_awaitable
            else:
                wrapper = resp_awaitable
            break
        except Exception as e:
            last_error = e
            error_str = str(e).lower()

            retryable = (
                is_retryable_error(error_str)
                if is_retryable_error is not None
                else (
                    "validation error" in error_str
                    or "input should be a valid" in error_str
                    or "list_type" in error_str
                    or "no tool calls" in error_str
                    or "function call found" in error_str
                )
            )

            if retryable:
                logger.warning(
                    "[%s/%s] Instructor validation error (attempt %d/3): %s. Attempting JSON repair...",
                    provider,
                    model_name,
                    attempt + 1,
                    str(e)[:200],
                )

                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Your last response failed schema validation. Error details:\n"
                            f"{str(e)[:500]}\n\n"
                            f"Your response must be a valid JSON object matching this schema exactly:\n"
                            f"{schema_hint}"
                            "Do NOT return JSON as a string. Do NOT use quotes around the JSON object. "
                            "Return the raw JSON object directly with no additional text."
                        ),
                    }
                )
                final_args["messages"] = safe_deepcopy(messages)
            else:
                raise

    if wrapper is None:
        logger.error(
            "[%s/%s] All Instructor extraction attempts failed. Last error: %s", provider, model_name, last_error
        )
        wrapper = [create_fallback_model(response_model)]

    return wrapper


def aggregate_response_blocks(wrapper: Any, response_model: Any) -> Any:
    """Aggregate all results from single or multi-block Instructor response wrappers."""
    final_resp = create_fallback_model(response_model)

    if not wrapper:
        return final_resp

    for r in ensure_list(wrapper):
        parsed_r = try_parse_response(r, response_model)
        if parsed_r is not None:
            if hasattr(final_resp, "decisions") and hasattr(parsed_r, "decisions"):
                final_resp.decisions.extend(parsed_r.decisions)
            if hasattr(final_resp, "macro_events") and hasattr(parsed_r, "macro_events"):
                final_resp.macro_events.extend(parsed_r.macro_events)
        else:
            if hasattr(final_resp, "decisions") and hasattr(r, "decisions"):
                final_resp.decisions.extend(r.decisions)
            if hasattr(final_resp, "macro_events") and hasattr(r, "macro_events"):
                final_resp.macro_events.extend(r.macro_events)

    return final_resp
