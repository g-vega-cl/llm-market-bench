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

# MiniMax M3.1 emits native tool syntax (`]<]minimax[>[<tool_call>...`) and
# `think` blocks when it continues a tool conversation, and its reasoning
# tokens share the `max_completion_tokens` budget (often 10k-14k tokens).
MINIMAX_MAX_CONTEXT_CHARS = 60000
MINIMAX_INITIAL_CONTEXT_CHARS = 12000
MINIMAX_HISTORY_HEAD_CHARS = 16000
MINIMAX_HISTORY_TAIL_CHARS = 32000
MINIMAX_EXTRACTION_MAX_TOKENS = 32768
_MINIMAX_HISTORY_MARKER = "\n\n=== Tool Execution History ===\n"
_MINIMAX_EXTRACTION_SYSTEM_PROMPT = (
    "You are a financial data extraction assistant. Your sole job is to extract and structure "
    "the analysis and tool results into a valid JSON object matching the requested schema. "
    "Do NOT call tools, do NOT emit tool-call syntax, and do NOT withhold decisions awaiting tool calls."
)
_MINIMAX_TOOL_BLOCK_RE = re.compile(r"<tool_call\b.*?</tool_call\s*>", re.DOTALL | re.IGNORECASE)
_MINIMAX_INVOKE_BLOCK_RE = re.compile(r"<invoke\b.*?</invoke\s*>", re.DOTALL | re.IGNORECASE)
_MINIMAX_MARKER_RE = re.compile(r"\[<\]minimax\[>\[?|<\]minimax\[>\[?")
_MINIMAX_THINK_RE = re.compile(r"<think\b.*?(?:</think\s*>|$)", re.DOTALL | re.IGNORECASE)
_MINIMAX_TAG_RE = re.compile(r"</?(?:tool_call|invoke|ticker|content|parameter)\b[^>]*>", re.IGNORECASE)


def sanitize_minimax_content(text: str) -> str:
    """Strips MiniMax native tool/thinking syntax so only candidate JSON remains."""
    text = text or ""
    text = _MINIMAX_THINK_RE.sub("", text)
    text = _MINIMAX_TOOL_BLOCK_RE.sub("", text)
    text = _MINIMAX_INVOKE_BLOCK_RE.sub("", text)
    text = _MINIMAX_MARKER_RE.sub("\n", text)
    text = _MINIMAX_TAG_RE.sub("", text)
    return text.strip()


def _slice_head_on_newline(text: str, limit: int) -> str:
    """Truncate text to at most `limit` chars, preferring the last newline boundary."""
    if len(text) <= limit:
        return text
    nl = text.rfind("\n", 0, limit)
    return text[:nl] if nl > limit // 2 else text[:limit]


def _slice_tail_on_newline(text: str, limit: int) -> str:
    """Keep trailing `limit` chars of text, preferring the first newline boundary."""
    if len(text) <= limit:
        return text
    start = len(text) - limit
    nl = text.find("\n", start)
    return text[nl + 1 :] if nl != -1 and nl < len(text) - limit // 2 else text[start:]


def _compact_minimax_user_content(user_content: str) -> str:
    """Keep initial context, ledger/news menu source IDs, and recent tool outputs within budget."""
    if len(user_content) <= MINIMAX_MAX_CONTEXT_CHARS:
        return user_content

    if _MINIMAX_HISTORY_MARKER in user_content:
        initial_ctx, history = user_content.split(_MINIMAX_HISTORY_MARKER, 1)
        kept_initial = _slice_head_on_newline(initial_ctx, MINIMAX_INITIAL_CONTEXT_CHARS)
        if len(history) <= MINIMAX_HISTORY_HEAD_CHARS + MINIMAX_HISTORY_TAIL_CHARS:
            kept_history = history
        else:
            kept_history = (
                _slice_head_on_newline(history, MINIMAX_HISTORY_HEAD_CHARS)
                + "\n\n...[middle history omitted for extraction]...\n\n"
                + _slice_tail_on_newline(history, MINIMAX_HISTORY_TAIL_CHARS)
            )
        return f"{kept_initial}{_MINIMAX_HISTORY_MARKER}{kept_history}"

    half = MINIMAX_MAX_CONTEXT_CHARS // 2
    return (
        f"{_slice_head_on_newline(user_content, half)}"
        "\n\n...[middle content omitted for extraction]...\n\n"
        f"{_slice_tail_on_newline(user_content, half)}"
    )


async def extract_with_minimax_openai(
    *,
    messages: list,
    model_name: str,
    response_model: Any,
    schema_hint: str,
) -> Any:
    """Extracts structured decisions through MiniMax's OpenAI-compatible endpoint.

    The Anthropic-compatible endpoint returns MiniMax's native tool syntax for
    extraction prompts (`No text content in response` -> `JSON extraction
    malformed-input work limit exceeded`), so extraction runs on the documented
    OpenAI-format endpoint instead and is parsed locally with bounded retry recovery.
    """
    from core.llm.minimax import MiniMaxClient

    user_parts = []
    for msg in messages:
        if not isinstance(msg, dict) or msg.get("role") != "user":
            continue
        content = msg.get("content") or ""
        if isinstance(content, list):
            content = "".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
        text = str(content).strip()
        if text:
            user_parts.append(text)

    user_content = _compact_minimax_user_content("\n\n".join(user_parts))

    instruction = (
        "The research tool phase is complete. Extract and structure your final output "
        "(including any BUY or SELL recommendations to be sized in the next stage). "
        "Do NOT continue the tool conversation. Do NOT emit tool-call syntax. "
        "Respond with ONLY the raw JSON object matching this schema exactly:\n"
        f"{schema_hint}"
    )

    chat_messages: list[dict[str, str]] = [
        {"role": "system", "content": _MINIMAX_EXTRACTION_SYSTEM_PROMPT},
        {"role": "user", "content": f"{user_content}\n\n{instruction}"},
    ]

    client = MiniMaxClient()
    last_sanitized = ""
    last_finish_reason = None
    last_usage = None
    try:
        for attempt in range(2):
            result = await client.chat(
                messages=chat_messages,
                model=model_name,
                max_completion_tokens=MINIMAX_EXTRACTION_MAX_TOKENS,
                response_format={"type": "json_object"},
            )
            last_finish_reason = result.get("finish_reason")
            last_usage = result.get("usage")
            last_sanitized = sanitize_minimax_content(result.get("content") or "")
            parsed = try_parse_response(last_sanitized, response_model)
            if parsed is not None:
                logger.debug("[minimax/%s] OpenAI-endpoint extraction produced a valid payload", model_name)
                return [parsed]

            if attempt == 0:
                logger.warning(
                    "[minimax/%s] Extraction parse failed (attempt 1/2, finish_reason=%s, usage=%s, len=%d). Retrying...",
                    model_name,
                    last_finish_reason,
                    last_usage,
                    len(last_sanitized),
                )
                if last_sanitized:
                    chat_messages.append({"role": "assistant", "content": last_sanitized[:2000]})
                chat_messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Your previous output could not be parsed or failed schema validation. "
                            "Return ONLY a single valid, complete JSON object matching this exact schema "
                            f"(no markdown, no truncation, strings for string fields):\n{schema_hint}"
                        ),
                    }
                )
    finally:
        await client.close()

    logger.error(
        "[minimax/%s] Failed to parse extraction output after 2 attempts (finish_reason=%s, usage=%s, %d chars): %s",
        model_name,
        last_finish_reason,
        last_usage,
        len(last_sanitized),
        last_sanitized[:500],
    )
    return [create_fallback_model(response_model)]


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
    model_fields = getattr(response_model, "model_fields", None)
    if isinstance(model_fields, dict):
        if "decisions" in model_fields:
            init_args["decisions"] = []
        if "macro_events" in model_fields:
            init_args["macro_events"] = []
    else:
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
    if provider == "minimax":
        return await extract_with_minimax_openai(
            messages=messages,
            model_name=model_name,
            response_model=response_model,
            schema_hint=schema_hint,
        )

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
