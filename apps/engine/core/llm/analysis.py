"""Core LLM analysis logic for trading decisions."""

import asyncio
import json
import logging

from core.models import DecisionsResponse
from core.llm import clients
from core.llm import prompts
from core.llm import tools
from core.llm.logger import log_reasoning_trace
from core.config import MIN_TRADE_VALUE

logger = logging.getLogger("engine")


async def analyze_with_provider(
    provider: str,
    model_name: str,
    chunks: list[dict],
    context: str = "",
    portfolio_context: str = "",
    current_day_info: str = "No date context available.",
    calendar_knowledge: str = ""
) -> DecisionsResponse:
    """Analyzes a batch of newsletter chunks using the specified provider.

    Args:
        provider: The LLM provider name (openai, anthropic, gemini, deepseek).
        model_name: The specific model identifier for the provider.
        chunks: List of dictionaries containing 'source_id' and 'content'.
        context: Aggregated historical context.
        portfolio_context: Current portfolio status context.
        current_day_info: Current date and week context.
        calendar_knowledge: Knowledge of calendar strategies.

    Returns:
        A DecisionsResponse instance containing trading signals and macro events.

    Raises:
        ValueError: If the provider is not recognized.
        Exception: If the LLM API call fails after retries.
    """
    factory = clients.CLIENT_FACTORIES.get(provider)
    if factory is None:
        raise ValueError(f"Unknown provider: {provider}")

    client = factory()

    try:
        # Construct batch prompt
        news_content = "".join([
            f"\n---\nSource ID: {chunk['source_id']}\nContent: {chunk['content']}\n---\n"
            for chunk in chunks
        ])

        prompt = prompts.ANALYSIS_USER_PROMPT_TEMPLATE.format(
            portfolio_context=portfolio_context if portfolio_context else "No portfolio data available.",
            context=context if context else "No relevant historical context found.",
            news_content=news_content,
            min_trade_value=MIN_TRADE_VALUE,
            current_day_info=current_day_info,
            calendar_knowledge=calendar_knowledge
        )


        messages = [
            {"role": "system", "content": prompts.ANALYSIS_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        # Tool execution loop (delegated to provider-specific handlers)
        raw_client = client.client
        if provider in ["openai", "deepseek"]:
            from core.llm.handlers import openai
            await openai.run_tool_loop(raw_client, model_name, messages, provider)
        elif provider == "anthropic":
            from core.llm.handlers import anthropic
            await anthropic.run_tool_loop(raw_client, model_name, messages)
        elif provider == "gemini":
            from core.llm.handlers import gemini
            await gemini.run_tool_loop(raw_client, model_name, messages)

        # Final structured extraction using Instructor
        logger.debug("Executing final extraction for %s/%s", provider, model_name)

        final_args = {
            "model": model_name,
            "response_model": DecisionsResponse,
            "messages": messages,
            "max_retries": 2,
        }

        if provider == "anthropic":
            final_args["max_tokens"] = 8000
            if messages[0]["role"] == "system":
                final_args["system"] = messages[0]["content"]
                final_args["messages"] = messages[1:]

        resp_awaitable = client.chat.completions.create(**final_args)
        if hasattr(resp_awaitable, "__await__") or asyncio.iscoroutine(resp_awaitable):
            final_resp = await resp_awaitable
        else:
            final_resp = resp_awaitable

        # HARD TOOL ENFORCEMENT: Verify that tools were ACTUALLY called in the history
        for decision in final_resp.decisions:
            if decision.signal in ["BUY", "SELL"]:
                results = _scan_history_for_tools(messages, decision.ticker)
                
                # Update sell_tool_called based on ACTUAL history
                if decision.signal == "SELL":
                    was_self_reported = decision.sell_tool_called
                    decision.sell_tool_called = results["sell_tool_found"]
                    
                    if was_self_reported and not results["sell_tool_found"]:
                        logger.warning(
                            "[%s/%s] HARD ENFORCEMENT: Agent claimed sell tool was called for %s but it was NOT found in history. Rejecting trade.",
                            provider, model_name, decision.ticker
                        )
                
                # Check get_stock_quote enforcement
                if not results["quote_found"]:
                     logger.warning(
                        "[%s/%s] HARD ENFORCEMENT: Agent recommended trade for %s without 'get_stock_quote' verification. Decison may be invalid.",
                        provider, model_name, decision.ticker
                    )

        # Log completion
        await log_reasoning_trace(
            task_type="INGESTION",
            model_provider=provider,
            model_name=model_name,
            prompt=messages,
            response=final_resp,
            metadata={
                "chunk_ids": [c.get("source_id") for c in chunks],
                "portfolio_status": "injected" if portfolio_context else "none"
            }
        )

        return final_resp

    except Exception as e:
        logger.error("Error analyzing batch with %s/%s: %s", provider, model_name, e)
        raise
    finally:
        await clients.close_client(client, provider)


def _scan_history_for_tools(messages: list, ticker: str) -> dict:
    """Scans message history for tool calls related to a specific ticker.
    
    This provides a 'hard' check against self-reported tool usage by LLMs.
    
    Returns:
        dict: {
            "quote_found": bool,
            "sell_tool_found": bool
        }
    """
    ticker = ticker.upper()
    quote_found = False
    sell_tool_found = False
    
    for m in messages:
        calls = []
        # 1. Handle dictionaries (OpenAI, Anthropic, Instructor-formatted)
        if isinstance(m, dict):
            # OpenAI style tool calls
            if m.get("tool_calls"):
                for tc in m["tool_calls"]:
                    calls.append((tc["function"]["name"], tc["function"].get("arguments", "{}")))
            # Anthropic style tool calls (content list)
            elif isinstance(m.get("content"), list):
                for part in m["content"]:
                    if isinstance(part, dict) and part.get("type") == "tool_use":
                        calls.append((part["name"], part.get("input", {})))
        # 2. Handle native Google types (Gemini)
        elif hasattr(m, "parts"):
            for part in m.parts:
                if hasattr(part, "function_call") and part.function_call:
                    calls.append((part.function_call.name, part.function_call.args))
                    
        for name, args in calls:
            # args can be a string (JSON) or a dictionary
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except:
                    continue
            
            call_ticker = str(args.get("ticker", "")).upper()
            if call_ticker == ticker:
                if name == "get_stock_quote":
                    quote_found = True
                elif name.startswith("sell_") and name.endswith("_percent"):
                    sell_tool_found = True
                    
    return {"quote_found": quote_found, "sell_tool_found": sell_tool_found}
