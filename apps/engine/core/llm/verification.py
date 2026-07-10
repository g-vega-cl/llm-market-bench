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


async def verify_trading_decision(
    decision: DecisionObject,
    portfolio_context: str,
    aggregated_context: str,
    contrarian_context: str = "",
    uncrowded_context: str = "",
    max_tool_steps: int = 5,
) -> VerificationResult:
    """Performs a skeptical second reasoning step on a proposed trade.

    Args:
        decision: The proposed decision object.
        portfolio_context: Current portfolio summary.
        aggregated_context: Historical context and lessons.
        contrarian_context: Contrarian agent insights.
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

    # Use the same provider and model as the original decision
    provider = decision.model_provider or "openai"  # Default to openai if not set
    model_name = decision.model_name or "gpt-4o"

    # --- Specialized Agent Model Mapping ---
    from core.config import ANTHROPIC_MODEL, DEEPSEEK_MODEL, GEMINI_MODEL

    AGENT_MODEL_MAPPING = {
        "contrarian_agent": GEMINI_MODEL,
        "post_mortem_agent": ANTHROPIC_MODEL,
        "deepseek_reasoner": DEEPSEEK_MODEL,
    }

    AGENT_PROVIDER_MAPPING = {
        "contrarian_agent": "gemini",
        "post_mortem_agent": "anthropic",
        "deepseek_reasoner": "deepseek",
    }

    if model_name in AGENT_MODEL_MAPPING:
        provider = AGENT_PROVIDER_MAPPING[model_name]
        model_name = AGENT_MODEL_MAPPING[model_name]

    factory = clients.CLIENT_FACTORIES.get(provider)
    if not factory:
        logger.error(f"Provider {provider} not found for verification. Falling back to openai.")
        provider = "openai"
        model_name = "gpt-4o"
        factory = clients.CLIENT_FACTORIES.get(provider)

    client = factory()

    try:
        targeted_context = retrieve_for_decision(
            ticker=decision.ticker,
            reasoning=decision.reasoning,
            model_name=decision.model_name,
        )
        full_context = aggregated_context
        if targeted_context:
            if full_context:
                full_context += "\n\n=== TARGETED TRADE MEMORY CHECK ===\n" + targeted_context
            else:
                full_context = "=== TRADE MEMORY CHECK ===\n" + targeted_context

        # 1. Prepare Prompt
        # Fetch current market price for context (not LLM-produced)
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
            contrarian_context=contrarian_context
            if contrarian_context
            else "No specific contrarian context available.",
            uncrowded_context="No specific secondary effects noted.",
        )

        # 2. Run the verifier tool loop with the unified verifier toolset.
        # Handlers translate canonical defs to provider-specific formats internally.
        verifier_tools = [
            tools.STOCK_TOOL,
            tools.PRICE_HISTORY_TOOL,
            tools.VOLATILITY_METRICS_TOOL,
            tools.SECTOR_ALTERNATIVES_TOOL,
            tools.AUDIT_FINANCIAL_VALUATION_TOOL,
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

            await run_tool_loop(client.client, model_name, messages, max_tool_steps, verifier_tools)
        elif provider == "gemini":
            from core.llm.handlers.gemini import run_tool_loop

            await run_tool_loop(client.client, model_name, messages, max_tool_steps, verifier_tools)

        # DeepSeek-specific: Prepare messages for Instructor extraction
        # DeepSeek with thinking mode may return empty content with reasoning_content.
        # We must strip reasoning_content from non-tool-call messages so Instructor
        # can process them, and detect empty content to issue a recovery prompt.
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

        # 3. Final Extraction using Instructor for structured VerificationResult
        instructor_messages = []
        for m in messages:
            if isinstance(m, dict):
                # IMPORTANT: For OpenAI/DeepSeek, we MUST preserve tool_calls and tool_call_id
                # to avoid "Invalid parameter: messages with role 'tool' must be a response to a preceeding message with 'tool_calls'"
                if "tool_calls" in m or m.get("role") == "tool":
                    instructor_messages.append(m)
                    continue

                content = m.get("content", "")
                if isinstance(content, list):
                    # Flatten Anthropic/Gemini parts
                    flat_content = ""
                    for part in content:
                        if isinstance(part, dict) and "text" in part:
                            flat_content += part["text"]
                        elif isinstance(part, dict) and "input" in part:
                            flat_content += f"\n[Tool Call: {part['name']}({part['input']})]"
                        elif isinstance(part, dict) and "content" in part and "tool_use_id" in part:
                            flat_content += f"\n[Tool Result: {part['content']}]"
                    content = flat_content
                instructor_messages.append({"role": m["role"], "content": str(content)})
            elif hasattr(m, "role"):
                # Handle Google GenAI Content objects
                content_text = ""
                for part in m.parts:
                    if getattr(part, "text", None):
                        content_text += part.text
                    elif getattr(part, "function_call", None):
                        content_text += f"\n[Tool Call: {part.function_call.name}({part.function_call.args})]"
                    elif getattr(part, "function_response", None):
                        content_text += f"\n[Tool Result: {part.function_response.response}]"

                role = "model" if m.role == "model" else "user"
                instructor_messages.append({"role": role, "content": content_text})

        response_model = list[VerificationResult] if provider == "gemini" else VerificationResult

        # Anthropic calls via instructor require max_tokens
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
        if provider == "anthropic":
            create_args["max_tokens"] = 4000

        # Retry loop for Instructor extraction — handles both validation errors
        # and empty/None responses by injecting repair prompts.
        wrapper = None
        last_error = None
        for attempt in range(3):
            try:
                resp_awaitable = client.chat.completions.create(**create_args)
                if hasattr(resp_awaitable, "__await__") or asyncio.iscoroutine(resp_awaitable):
                    wrapper = await resp_awaitable
                else:
                    wrapper = resp_awaitable

                # Check if we got a non-empty result
                if wrapper is not None:
                    wrapped_check = ensure_list(wrapper)
                    if wrapped_check:
                        break

                # Empty/None result — add repair message and retry
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
                error_str = str(e).lower()
                attempt_num = attempt + 1
                is_transient = any(
                    k in error_str
                    for k in [
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
                    ]
                )

                if (
                    "validation error" in error_str
                    or "input should be a valid" in error_str
                    or "list_type" in error_str
                ):
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
                    # Non-validation, non-transient error — log and re-raise to outer handler
                    logger.error(
                        "[%s/%s] Verification Instructor non-retryable error on attempt %d/3: %s",
                        provider,
                        model_name,
                        attempt_num,
                        str(e),
                    )
                    raise

        # After retry loop: handle case where all attempts failed
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

        # Select the last verification result if multiple were returned
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
        else:
            final_resp = resp

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
        logger.error(
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
