"""Second-step trade verification logic."""

import asyncio
import copy
import logging
from asyncio import sleep as asyncio_sleep

from core.llm import clients, tools
from core.llm.logger import log_reasoning_trace
from core.llm.prompt_factory import PromptFactory
from core.models import DecisionObject, VerificationResult
from memory.store import retrieve_for_decision

from .utils import ensure_list

logger = logging.getLogger("engine")


def _resolve_verifier_model_and_client(decision: DecisionObject) -> tuple[str, str, object]:
    """Resolves the provider, model_name, and initialized client for verification."""
    from core.config import ANTHROPIC_MODEL, DEEPSEEK_FLASH_MODEL

    provider = decision.model_provider or "openai"
    model_name = decision.model_name or "gpt-4o"

    agent_model_mapping = {
        "post_mortem_agent": ANTHROPIC_MODEL,
        "deepseek_reasoner": DEEPSEEK_FLASH_MODEL,
    }
    agent_provider_mapping = {
        "post_mortem_agent": "anthropic",
        "deepseek_reasoner": "deepseek",
    }

    if model_name in agent_model_mapping:
        provider = agent_provider_mapping[model_name]
        model_name = agent_model_mapping[model_name]
    elif provider == "deepseek" or "deepseek" in model_name.lower():
        provider = "deepseek"
        model_name = DEEPSEEK_FLASH_MODEL

    factory = clients.CLIENT_FACTORIES.get(provider)
    if not factory:
        logger.error(f"Provider {provider} not found for verification. Falling back to openai.")
        provider = "openai"
        model_name = "gpt-4o"
        factory = clients.CLIENT_FACTORIES.get(provider)

    return provider, model_name, factory()


def _build_full_verification_context(decision: DecisionObject, aggregated_context: str) -> str:
    """Combines aggregated context with targeted decision memory."""
    targeted_context = retrieve_for_decision(
        ticker=decision.ticker,
        reasoning=decision.reasoning,
        model_name=decision.model_name,
    )
    if not targeted_context:
        return aggregated_context
    if aggregated_context:
        return aggregated_context + "\n\n=== TARGETED TRADE MEMORY CHECK ===\n" + targeted_context
    return "=== TRADE MEMORY CHECK ===\n" + targeted_context


async def _run_verifier_tool_loop(
    client: object,
    provider: str,
    model_name: str,
    messages: list,
    max_tool_steps: int,
) -> list:
    """Executes the provider-specific tool loop and prepares DeepSeek messages if needed."""
    verifier_tools = [
        tools.STOCK_TOOL,
        tools.PRICE_HISTORY_TOOL,
        tools.VOLATILITY_METRICS_TOOL,
        tools.SECTOR_ALTERNATIVES_TOOL,
        tools.AUDIT_FINANCIAL_VALUATION_TOOL,
        tools.GET_OPTIONS_SENTIMENT_TOOL,
        tools.GET_TICKER_NEWS_TOOL,
    ]

    if provider == "openai":
        from .handlers.openai import run_tool_loop

        await run_tool_loop(
            client.client,
            model_name,
            messages,
            provider,
            max_tool_steps,
            verifier_tools,
            enable_web_search=False,
        )
    elif provider == "deepseek":
        from .handlers.deepseek import run_tool_loop

        await run_tool_loop(
            client.client,
            model_name,
            messages,
            provider,
            max_tool_steps,
            verifier_tools,
            enable_web_search=False,
        )
    elif provider == "anthropic":
        from core.llm.handlers.anthropic import run_tool_loop

        await run_tool_loop(
            client.client,
            model_name,
            messages,
            max_tool_steps,
            verifier_tools,
            thinking_budget=1024,
        )
    elif provider == "gemini":
        from core.llm.handlers.gemini import run_tool_loop

        await run_tool_loop(
            client.client,
            model_name,
            messages,
            max_tool_steps,
            verifier_tools,
            thinking_level="low",
        )

    if provider == "deepseek":
        from .handlers import deepseek as deepseek_handler

        messages = deepseek_handler.prepare_messages_for_instructor(messages)
        if not deepseek_handler.has_valid_content(messages):
            logger.info(
                "[%s/%s] DeepSeek returned empty verification content. Requesting JSON output.",
                provider,
                model_name,
            )
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Your previous output was empty or only contains reasoning. "
                        "To complete this task, you MUST now output ONLY a valid JSON object matching the schema. "
                        "No more reasoning, no explanations. Just the raw JSON object."
                    ),
                }
            )
    return messages


def _flatten_content_parts(content: list) -> str:
    """Flattens Anthropic/Gemini dict content parts into a string."""
    flat_content = ""
    for part in content:
        if not isinstance(part, dict):
            continue
        if "text" in part:
            flat_content += part["text"]
        elif "thinking" in part:
            flat_content += f"\n[Thinking: {part['thinking']}]"
        elif "input" in part:
            flat_content += f"\n[Tool Call: {part['name']}({part['input']})]"
        elif "content" in part and "tool_use_id" in part:
            flat_content += f"\n[Tool Result: {part['content']}]"
    return flat_content.strip()


def _flatten_genai_content(m: object) -> dict | None:
    """Flattens Google GenAI Content object into an Instructor message dict."""
    content_text = ""
    for part in m.parts:
        if getattr(part, "text", None):
            content_text += part.text
        elif getattr(part, "function_call", None):
            content_text += f"\n[Tool Call: {part.function_call.name}({part.function_call.args})]"
        elif getattr(part, "function_response", None):
            content_text += f"\n[Tool Result: {part.function_response.response}]"

    role = "model" if m.role == "model" else "user"
    if content_text.strip():
        return {"role": role, "content": content_text.strip()}
    return None


def _build_instructor_messages(messages: list) -> list[dict]:
    """Converts message history into flattened messages suitable for Instructor."""
    instructor_messages = []
    for m in messages:
        if isinstance(m, dict):
            if "tool_calls" in m or m.get("role") == "tool":
                instructor_messages.append(m)
                continue
            content = m.get("content", "")
            if isinstance(content, list):
                content = _flatten_content_parts(content)
            if content:
                instructor_messages.append({"role": m["role"], "content": str(content)})
        elif hasattr(m, "role"):
            flattened = _flatten_genai_content(m)
            if flattened:
                instructor_messages.append(flattened)
    return instructor_messages


def _build_instructor_create_args(
    provider: str,
    model_name: str,
    instructor_messages: list[dict],
) -> dict:
    """Builds provider-specific kwargs for client.chat.completions.create."""
    response_model = list[VerificationResult] if provider == "gemini" else VerificationResult
    create_args = {
        "model": model_name,
        "response_model": response_model,
        "messages": copy.deepcopy(instructor_messages),
        "max_retries": 2,
    }
    if provider == "gemini":
        for msg in create_args["messages"]:
            if isinstance(msg, dict) and msg.get("role") == "assistant":
                msg["role"] = "model"

    if provider in ("gemini", "anthropic") and create_args["messages"]:
        last_msg = create_args["messages"][-1]
        last_role = last_msg.get("role") if isinstance(last_msg, dict) else getattr(last_msg, "role", None)
        if last_role in ("model", "assistant"):
            create_args["messages"].append(
                {
                    "role": "user",
                    "content": (
                        "Based on the preceding evaluation, extract and structure the final verification result "
                        "matching the schema exactly."
                    ),
                }
            )

    if provider == "anthropic":
        from core.llm.handlers.anthropic import get_anthropic_thinking_kwargs

        create_args["max_tokens"] = 4000
        create_args["cache_control"] = {"type": "ephemeral"}
        create_args.update(get_anthropic_thinking_kwargs(model_name, budget_tokens=1024, effort="medium"))
        if create_args["messages"] and create_args["messages"][0].get("role") == "system":
            create_args["system"] = [
                {
                    "type": "text",
                    "text": create_args["messages"][0]["content"],
                    "cache_control": {"type": "ephemeral"},
                }
            ]
            create_args["messages"] = create_args["messages"][1:]
    if provider == "gemini":
        from google.genai import types

        if hasattr(types, "ThinkingConfig"):
            create_args["thinking_config"] = types.ThinkingConfig(thinking_level="low")
    if provider == "openai":
        create_args["reasoning_effort"] = "none"
    if provider == "deepseek" and "deepseek" in model_name.lower():
        create_args["extra_body"] = {"thinking": {"type": "enabled"}}

    return create_args


_TRANSIENT_KEYWORDS = (
    "rate limit",
    "429",
    "timeout",
    "502",
    "503",
    "504",
    "bad gateway",
    "service unavailable",
    "connection",
    "temporary",
    "try again",
)


async def _handle_extraction_exception(
    e: Exception,
    attempt: int,
    provider: str,
    model_name: str,
    instructor_messages: list[dict],
    create_args: dict,
) -> None:
    """Handles retryable validation or transient errors during Instructor extraction."""
    error_str = str(e).lower()
    attempt_num = attempt + 1
    is_transient = any(k in error_str for k in _TRANSIENT_KEYWORDS)
    is_validation = (
        "validation error" in error_str or "input should be a valid" in error_str or "list_type" in error_str
    )

    if is_validation:
        logger.warning(
            "[%s/%s] Verification Instructor validation error (attempt %d/3): %s. Attempting JSON repair...",
            provider,
            model_name,
            attempt_num,
            str(e)[:200],
        )
        instructor_messages.append(
            {
                "role": "user",
                "content": (
                    "Your response must be a valid JSON array matching the schema exactly. "
                    "Return raw JSON with no additional text."
                ),
            }
        )
        create_args["messages"] = copy.deepcopy(instructor_messages)
    elif is_transient:
        logger.warning(
            "[%s/%s] Verification Instructor transient error (attempt %d/3): %s. Retrying after delay...",
            provider,
            model_name,
            attempt_num,
            str(e)[:200],
        )
        await asyncio_sleep(2**attempt)
    else:
        logger.error(
            "[%s/%s] Verification Instructor non-retryable error on attempt %d/3: %s",
            provider,
            model_name,
            attempt_num,
            str(e),
        )
        raise


async def _extract_verification_with_retries(
    client: object,
    provider: str,
    model_name: str,
    instructor_messages: list[dict],
    create_args: dict,
) -> VerificationResult:
    """Runs the Instructor extraction loop with repair prompts and returns the final VerificationResult."""
    wrapper = None
    last_error = None
    for attempt in range(3):
        try:
            resp_awaitable = client.chat.completions.create(**create_args)
            if hasattr(resp_awaitable, "__await__") or asyncio.iscoroutine(resp_awaitable):
                wrapper = await resp_awaitable
            else:
                wrapper = resp_awaitable

            if wrapper is not None and ensure_list(wrapper):
                break

            attempt_num = attempt + 1
            logger.warning(
                "[%s/%s] Verification Instructor empty response (attempt %d/3). Requesting structured output.",
                provider,
                model_name,
                attempt_num,
            )
            instructor_messages.append(
                {
                    "role": "user",
                    "content": (
                        "Your response was empty or incomplete. You MUST output a valid JSON array of verification results. "
                        'Example: [{"status": "REJECTED_VERIFICATION", "verification_reasoning": "Reason", "confidence_score": 0}]'
                    ),
                }
            )
            create_args["messages"] = copy.deepcopy(instructor_messages)
        except Exception as e:
            last_error = e
            await _handle_extraction_exception(e, attempt, provider, model_name, instructor_messages, create_args)

    if wrapper is None:
        logger.error(
            "[%s/%s] All %d verification extraction attempts failed. Last: %s",
            provider,
            model_name,
            3,
            last_error or "empty response after retries",
        )
    elif not ensure_list(wrapper):
        logger.error(
            "[%s/%s] Verification extraction returned empty list after %d attempts.",
            provider,
            model_name,
            3,
        )

    wrapped_results = ensure_list(wrapper)
    resp = wrapped_results[-1] if wrapped_results else None

    if resp is None:
        reasoning = "No verification returned"
        if last_error:
            reasoning = f"Verification failed due to error: {last_error}. Defaulting to rejection."
        final_resp = VerificationResult(
            status="REJECTED_VERIFICATION",
            verification_reasoning=reasoning,
            confidence_score=0,
        )
        logger.info(
            "[%s/%s] Verification defaulted to REJECTED (no valid result after retries).",
            provider,
            model_name,
        )
        return final_resp

    return resp


async def verify_trading_decision(
    decision: DecisionObject,
    portfolio_context: str,
    aggregated_context: str,
    uncrowded_context: str = "",
    max_tool_steps: int = 5,
) -> VerificationResult:
    """Performs a skeptical second reasoning step on a proposed trade.

    Args:
        decision: The proposed decision object.
        portfolio_context: Current portfolio summary.
        aggregated_context: Historical context and lessons.
        uncrowded_context: Isolated secondary effect / uncrowded trade notes.
        max_tool_steps: Maximum iterations for the verifier's tool loop.

    Returns:
        A VerificationResult object.
    """
    if decision.signal.upper() == "HOLD":
        return VerificationResult(
            status="APPROVED",
            verification_reasoning="HOLD decisions do not require second-step verification.",
            confidence_score=100,
        )

    provider, model_name, client = _resolve_verifier_model_and_client(decision)

    try:
        full_context = _build_full_verification_context(decision, aggregated_context)

        # 1. Prepare Prompt
        from execution.market_data import MarketDataManager

        mdm = MarketDataManager()
        quote = await mdm.get_quote(decision.ticker)
        market_price = f"${quote.price:.2f}" if quote and quote.exists else "unknown"

        messages = PromptFactory.build_verifier_messages(
            provider=provider,
            ticker=decision.ticker,
            signal=decision.signal,
            reasoning=decision.reasoning,
            strategy_reasoning=getattr(decision, "strategy_reasoning", "None"),
            advance_planning_notes=getattr(decision, "advance_planning_notes", "None"),
            quantity=getattr(decision, "quantity", 0) or 1,
            market_price=market_price,
            portfolio_context=portfolio_context,
            context=full_context,
            uncrowded_context="No specific secondary effects noted.",
        )

        # 2. Run the verifier tool loop
        messages = await _run_verifier_tool_loop(client, provider, model_name, messages, max_tool_steps)

        # 3. Final Extraction using Instructor for structured VerificationResult
        instructor_messages = _build_instructor_messages(messages)
        create_args = _build_instructor_create_args(provider, model_name, instructor_messages)
        final_resp = await _extract_verification_with_retries(
            client, provider, model_name, instructor_messages, create_args
        )

        # Log completion
        await log_reasoning_trace(
            task_type="VERIFICATION",
            model_provider=provider,
            model_name=model_name,
            prompt=instructor_messages,
            response=final_resp,
            metadata={
                "ticker": decision.ticker,
                "signal": decision.signal,
                "source_id": decision.source_id,
            },
        )

        return final_resp

    except Exception as e:
        logger.exception(
            f"Verification failed for {decision.ticker} ({provider}): {e}",
            extra={
                "ticker": decision.ticker,
                "signal": decision.signal,
                "model_name": model_name,
                "provider": provider,
                "error_type": type(e).__name__,
                "source_id": getattr(decision, "source_id", None),
            },
        )
        return VerificationResult(
            status="REJECTED_VERIFICATION",
            verification_reasoning=f"Verification failed due to error: {e}. Defaulting to rejection.",
            confidence_score=0,
        )
    finally:
        await clients.close_client(client, provider)
