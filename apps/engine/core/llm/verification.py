"""Second-step trade verification logic."""

import asyncio
import json
import logging
import re
from typing import Any, List, Optional

from core.models import DecisionObject, VerificationResult
from core.llm import clients, prompts, tools
from .utils import ensure_list
from core.llm.handlers import base
from core.llm.handlers import openai, deepseek, anthropic, gemini
from core.llm.logger import log_reasoning_trace

logger = logging.getLogger("engine")

async def verify_trading_decision(
    decision: DecisionObject,
    portfolio_context: str,
    aggregated_context: str,
    contrarian_context: str = "",
    uncrowded_context: str = "",
    decision_id: str | None = None,
    max_tool_steps: int = 5
) -> tuple[VerificationResult, Optional[str]]:
    """Performs a skeptical second reasoning step on a proposed trade.

    Args:
        decision: The proposed decision object.
        portfolio_context: Current portfolio summary.
        aggregated_context: Historical context and lessons.
        contrarian_context: Contrarian agent insights.
        uncrowded_context: Isolated secondary effect / uncrowded trade notes.
        max_tool_steps: Maximum iterations for the verifier's tool loop.

    Returns:
        A tuple of (VerificationResult object, Optional log_trace_id).
    """
    if decision.signal == "HOLD":
        return VerificationResult(
            status="APPROVED",
            verification_reasoning="HOLD decisions do not require second-step verification.",
            confidence_score=100
        ), None

    # Use the same provider and model as the original decision
    provider = decision.model_provider or "openai" # Default to openai if not set
    model_name = decision.model_name or "gpt-4o"
    
    # --- Specialized Agent Model Mapping ---
    from core.config import GEMINI_MODEL, ANTHROPIC_MODEL, OPENAI_MODEL, DEEPSEEK_MODEL
    AGENT_MODEL_MAPPING = {
        "contrarian_agent": GEMINI_MODEL,
        "post_mortem_agent": ANTHROPIC_MODEL,
        "deepseek_reasoner": DEEPSEEK_MODEL,
    }
    
    if model_name in AGENT_MODEL_MAPPING:
        model_name = AGENT_MODEL_MAPPING[model_name]

    factory = clients.CLIENT_FACTORIES.get(provider)
    if not factory:
        logger.error(f"Provider {provider} not found for verification. Falling back to openai.")
        provider = "openai"
        model_name = "gpt-4o"
        factory = clients.CLIENT_FACTORIES.get(provider)

    client = factory()
    
    try:
        # 1. Prepare Prompt
        prompt = prompts.VERIFIER_USER_PROMPT_TEMPLATE.format(
            ticker=decision.ticker,
            signal=decision.signal,
            reasoning=decision.reasoning,
            strategy_reasoning=getattr(decision, "strategy_reasoning", "None"),
            advance_planning_notes=getattr(decision, "advance_planning_notes", "None"),
            quantity=getattr(decision, "quantity", 0) or 1,
            price=decision.price or "unknown",
            limit_price=getattr(decision, "limit_price", "None"),
            portfolio_context=portfolio_context,
            context=aggregated_context,
            contrarian_context=contrarian_context if contrarian_context else "No specific contrarian context available.",
            uncrowded_context=uncrowded_context if uncrowded_context else "No specific secondary effects noted."
        )

        messages = [
            {"role": "system", "content": prompts.VERIFIER_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        raw_messages = messages

        # 2. Select Verifier Tools based on Provider
        if provider == "openai":
            verifier_tools = [
                tools.STOCK_TOOL_DEFINITION_OPENAI,
                tools.PRICE_HISTORY_TOOL_DEFINITION_OPENAI,
                tools.VOLATILITY_METRICS_TOOL_DEFINITION_OPENAI,
                tools.SECTOR_ALTERNATIVES_TOOL_DEFINITION_OPENAI,
            ]
            await openai.run_tool_loop(client.client, model_name, messages, provider, max_tool_steps, verifier_tools, enable_web_search=False)
        elif provider == "deepseek":
            verifier_tools = [
                tools.STOCK_TOOL_DEFINITION_OPENAI,
                tools.PRICE_HISTORY_TOOL_DEFINITION_OPENAI,
                tools.VOLATILITY_METRICS_TOOL_DEFINITION_OPENAI,
                tools.SECTOR_ALTERNATIVES_TOOL_DEFINITION_OPENAI,
            ]
            await deepseek.run_tool_loop(client.client, model_name, messages, provider, max_tool_steps, verifier_tools, enable_web_search=False)
            
        elif provider == "anthropic":
            verifier_tools = [
                tools.STOCK_TOOL_DEFINITION_ANTHROPIC,
                tools.PRICE_HISTORY_TOOL_DEFINITION_ANTHROPIC,
                tools.VOLATILITY_METRICS_TOOL_DEFINITION_ANTHROPIC,
                tools.SECTOR_ALTERNATIVES_TOOL_DEFINITION_ANTHROPIC,
            ]
            await anthropic.run_tool_loop(client.client, model_name, messages, max_tool_steps, verifier_tools)
            
        elif provider == "gemini":
            verifier_tools = [
                tools.STOCK_TOOL_DEFINITION_GEMINI,
                tools.PRICE_HISTORY_TOOL_DEFINITION_GEMINI,
                tools.VOLATILITY_METRICS_TOOL_DEFINITION_GEMINI,
                tools.SECTOR_ALTERNATIVES_TOOL_DEFINITION_GEMINI,
            ]
            await gemini.run_tool_loop(client.client, model_name, messages, max_tool_steps, verifier_tools)

        # 3. Final Extraction using Instructor for structured VerificationResult
        instructor_messages = []
        for m in raw_messages:
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

        # Anthropic calls via instructor require max_tokens
        create_args = {
            "model": model_name,
            "response_model": List[VerificationResult], # Use List to handle Gemini multi-block tool calls
            "messages": instructor_messages,
            "max_retries": 2
        }
        if provider == "anthropic":
            create_args["max_tokens"] = 4000

        resp_awaitable = client.chat.completions.create(**create_args)
        
        if hasattr(resp_awaitable, "__await__") or asyncio.iscoroutine(resp_awaitable):
            wrapper = await resp_awaitable
        else:
            wrapper = resp_awaitable

        # Select the last verification result if multiple were returned
        wrapped_results = ensure_list(wrapper)
        final_resp = wrapped_results[-1] if wrapped_results else VerificationResult(status="REJECTED_VERIFICATION", verification_reasoning="No verification returned", confidence_score=0)
        
        # --- Tool Integrity Enforcement (Deliverable 4 Hardening) ---
        # Verifier must consume the CANONICAL transcript as the sole source of truth.
        # Normalization failure is treated as missing tools (safe-fail: reject rather than approve).
        from core.llm.normalization import normalize_transcript

        # Sterilize messages for normalization to handle multi-provider types
        def _sterilize(obj):
            if isinstance(obj, list): return [_sterilize(x) for x in obj]
            if isinstance(obj, dict): return {k: _sterilize(v) for k, v in obj.items()}
            if hasattr(obj, "model_dump"): return _sterilize(obj.model_dump())
            if hasattr(obj, "to_dict"): return _sterilize(obj.to_dict())
            return obj

        try:
            canonical = normalize_transcript(
                _sterilize(raw_messages),
                model_name=model_name,
                provider=provider
            )
            tool_calls_found = [tc.name for tc in canonical.tool_calls]
        except Exception as e:
            logger.warning(f"[{decision.ticker}] Transcript normalization failed, treating as missing tools: {e}")
            tool_calls_found = []
            canonical = None

        # Mandatory Tools Invariant
        mandatory_tools = ["get_stock_quote"]
        if decision.signal == "BUY":
            mandatory_tools.append("calculate_buy_quantity")
        elif decision.signal == "SELL":
            mandatory_tools.append("calculate_sell_quantity")

        missing_mandatory = [t for t in mandatory_tools if t not in tool_calls_found]

        # Block ANY non-rejected outcome — APPROVED and ADJUSTED_ALLOCATION both require tool evidence
        if missing_mandatory and final_resp.status != "REJECTED_VERIFICATION":
            logger.warning(f"[{decision.ticker}] Hardening Reject: Missing mandatory tools {missing_mandatory}")
            final_resp = VerificationResult(
                status="REJECTED_VERIFICATION",
                verification_reasoning=f"Verification rejected due to missing mandatory tool calls: {', '.join(missing_mandatory)}. Verifier must prove claims using tools.",
                confidence_score=0
            )

        # Log completion with decision_id anchor for precise attribution
        meta = {
            "ticker": decision.ticker,
            "signal": decision.signal,
            "source_id": decision.source_id,
            "mandatory_tools_verified": not missing_mandatory,
        }
        if decision_id:
            meta["decision_id"] = str(decision_id)

        log_id = await log_reasoning_trace(
            task_type="VERIFICATION",
            model_provider=provider,
            model_name=model_name,
            prompt=raw_messages,
            response=final_resp,
            metadata=meta,
            pre_normalized_transcript=canonical,
        )

        return final_resp, log_id

    except Exception as e:
        logger.error(f"Verification failed for {decision.ticker} ({provider}): {e}")
        return VerificationResult(
            status="REJECTED_VERIFICATION",
            verification_reasoning=f"Verification failed due to an internal error. Rejecting as a safety precaution.",
            confidence_score=0
        ), None
    finally:
        await clients.close_client(client, provider)
