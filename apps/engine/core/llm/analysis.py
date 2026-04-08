"""Core LLM analysis logic for trading decisions."""

import asyncio
import copy
import json
import logging
from typing import List

from core.models import DecisionsResponse, MacroEvent
from core.llm import clients
from core.llm.prompt_factory import PromptFactory
from core.llm import tools
from .utils import ensure_list
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
    calendar_knowledge: str = "",
    macro_context: str = ""
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
        macro_context: Recent macro-economic indicators and anomalies.

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

        # Extract held tickers from portfolio context for quick reference
        held_tickers = _extract_held_tickers(portfolio_context)
        held_tickers_list = ", ".join(held_tickers) if held_tickers else "None (you have no positions)"

        # Determine if web search should be enabled for this provider
        enable_web_search = False
        if provider == "anthropic":
            from core.config import ENABLE_ANTHROPIC_WEB_SEARCH
            enable_web_search = ENABLE_ANTHROPIC_WEB_SEARCH
        elif provider == "gemini":
            from core.config import ENABLE_GEMINI_WEB_SEARCH
            enable_web_search = ENABLE_GEMINI_WEB_SEARCH
        elif provider == "openai":
            from core.config import ENABLE_OPENAI_WEB_SEARCH
            enable_web_search = ENABLE_OPENAI_WEB_SEARCH

        messages = PromptFactory.build_analysis_messages(
            provider=provider,
            portfolio_context=portfolio_context if portfolio_context else "No portfolio data available.",
            context=context if context else "No relevant historical context found.",
            news_content=news_content,
            min_trade_value=MIN_TRADE_VALUE,
            current_day_info=current_day_info,
            calendar_knowledge=calendar_knowledge,
            macro_context=macro_context if macro_context else "No macro data available.",
            held_tickers_list=held_tickers_list,
            enable_web_search=enable_web_search
        )

        # Tool execution loop (delegated to provider-specific handlers)
        raw_client = client.client
        if provider == "openai":
            from .handlers import openai
            await openai.run_tool_loop(raw_client, model_name, messages, provider, enable_web_search=enable_web_search)
        elif provider == "deepseek":
            from .handlers import deepseek
            await deepseek.run_tool_loop(raw_client, model_name, messages, provider, enable_web_search=enable_web_search)
        elif provider == "anthropic":
            from .handlers import anthropic
            await anthropic.run_tool_loop(raw_client, model_name, messages, enable_web_search=enable_web_search)
        elif provider == "gemini":
            from .handlers import gemini
            await gemini.run_tool_loop(raw_client, model_name, messages, enable_google_search=enable_web_search)

        # Final structured extraction using Instructor
        logger.debug("Executing final extraction for %s/%s", provider, model_name)

        # DeepSeek-specific: Prepare messages for Instructor extraction
        # DeepSeek with thinking mode may return empty content with reasoning_content
        if provider == "deepseek":
            from .handlers import deepseek
            messages = deepseek.prepare_messages_for_instructor(messages)

            # If content is empty/whitespace, add a user prompt requesting JSON output
            if not deepseek.has_valid_content(messages):
                logger.info("[%s/%s] DeepSeek returned empty content. Requesting JSON output.", provider, model_name)
                messages.append({
                    "role": "user",
                    "content": (
                        "Your previous output was empty or only contains reasoning. "
                        "To complete this task, you MUST now output ONLY a valid JSON object following the schema. "
                        "No more reasoning, no explanations. Just the raw JSON object. "
                        "Example: {\"decisions\": [], \"macro_events\": []}"
                    )
                })

        final_args = {
            "model": model_name,
            "response_model": DecisionsResponse if provider != "gemini" else List[DecisionsResponse], # Use List to handle Gemini multi-block tool calls
            "messages": copy.deepcopy(messages),
            "max_retries": 2,
        }

        if provider == "anthropic":
            final_args["max_tokens"] = 32000  # Increased from 8000 to handle long outputs
            if messages[0]["role"] == "system":
                final_args["system"] = messages[0]["content"]
                final_args["messages"] = messages[1:]
        resp_awaitable = client.chat.completions.create(**final_args)
        if hasattr(resp_awaitable, "__await__") or asyncio.iscoroutine(resp_awaitable):
            wrapper = await resp_awaitable
        else:
            wrapper = resp_awaitable

        # Aggregate all results from the list of response blocks
        final_resp = DecisionsResponse(decisions=[], macro_events=[])
        if wrapper:
            for r in ensure_list(wrapper):
                final_resp.decisions.extend(r.decisions)
                final_resp.macro_events.extend(r.macro_events)

        # HARD TOOL ENFORCEMENT: Verify that tools were ACTUALLY called in the history
        for decision in final_resp.decisions:
            if decision.signal in ["BUY", "SELL"]:
                results = _scan_history_for_tools(messages, decision.ticker)

                # Update buy_tool_called/sell_tool_called based on ACTUAL history
                if decision.signal == "BUY":
                    was_self_reported = decision.buy_tool_called
                    decision.buy_tool_called = results["buy_tool_found"]

                    if was_self_reported and not results["buy_tool_found"]:
                        logger.warning(
                            "[%s/%s] HARD ENFORCEMENT: Agent claimed buy tool was called for %s but it was NOT found in history. Rejecting trade.",
                            provider, model_name, decision.ticker
                        )
                    elif not results["buy_tool_found"]:
                        logger.warning(
                            "[%s/%s] HARD ENFORCEMENT: Agent recommended BUY for %s without executing 'calculate_buy_quantity' tool. Rejecting trade.",
                            provider, model_name, decision.ticker
                        )

                elif decision.signal == "SELL":
                    was_self_reported = decision.sell_tool_called
                    decision.sell_tool_called = results["sell_tool_found"]

                    if was_self_reported and not results["sell_tool_found"]:
                        logger.warning(
                            "[%s/%s] HARD ENFORCEMENT: Agent claimed sell tool was called for %s but it was NOT found in history. Rejecting trade.",
                            provider, model_name, decision.ticker
                        )
                    elif not results["sell_tool_found"]:
                        logger.warning(
                            "[%s/%s] HARD ENFORCEMENT: Agent recommended SELL for %s without executing 'calculate_sell_quantity' tool. Rejecting trade.",
                            provider, model_name, decision.ticker
                        )

                # Check get_stock_quote enforcement with confidence scoring
                if not results["quote_found"]:
                     logger.warning(
                        "[%s/%s] HARD ENFORCEMENT: Agent recommended trade for %s without 'get_stock_quote' verification. Decision may be invalid.",
                        provider, model_name, decision.ticker
                    )
                     # Add confidence penalty - flag as low confidence
                     decision.confidence = int(getattr(decision, 'confidence', 50) * 0.5)  # Reduce by 50%
                     logger.info(
                        "[%s/%s] CONFIDENCE PENALTY: Reduced confidence score for %s due to missing tool call.",
                        provider, model_name, decision.ticker
                    )

        # PRE-ANALYSIS PORTFOLIO VALIDATION: Filter out SELL decisions for tickers not held
        # This catches hallucinations before they reach the verification layer
        held_tickers = _extract_held_tickers(portfolio_context)
        validated_decisions = []
        for decision in final_resp.decisions:
            if decision.signal == "SELL" and decision.ticker.upper() not in [t.upper() for t in held_tickers]:
                logger.warning(
                    "[%s/%s] PRE-ANALYSIS VALIDATION: SELL signal for %s rejected - ticker not in portfolio. Held: %s",
                    provider, model_name, decision.ticker, held_tickers
                )
                # Mark as rejected but keep for audit trail
                decision.signal = "HOLD"  # Convert to HOLD to preserve audit trail
                decision.reasoning = f"REJECTED_OWNERSHIP: Attempted to sell {decision.ticker} but ticker is not held. Original reasoning: {decision.reasoning[:200]}"
            validated_decisions.append(decision)
        final_resp.decisions = validated_decisions

        # GOVERNMENT INCENTIVE ENFORCEMENT: Promote or synthesize government policy events
        # so obvious policy/news signals are not dropped if the model misses the flag.
        _ensure_government_incentive_events(final_resp, chunks, provider, model_name)

        # GOVERNMENT INCENTIVE ENFORCEMENT: Check if news contains government policy content
        # but no macro_events were generated
        gov_keywords = [
            "bill", "act", "congress", "parliament", "legislation", "subsidy", "grant",
            "incentive", "budget", "funding", "appropriation", "tax credit", "policy",
            "regulation", "directive", "executive order", "defense production act",
            "government program", "federal", "treasury", "usda", "dod", "doe", "sec"
        ]
        
        for chunk in chunks:
            content_lower = chunk.get("content", "").lower()
            has_gov_content = any(kw in content_lower for kw in gov_keywords)
            
            if has_gov_content and not final_resp.macro_events:
                logger.warning(
                    "[%s/%s] GOVERNMENT INCENTIVE ENFORCEMENT: News chunk '%s' contains "
                    "government policy content but NO macro_events were generated. "
                    "This may indicate a prompt compliance issue.",
                    provider, model_name, chunk.get("source_id", "unknown")
                )
            elif has_gov_content:
                # Check if any macro_event has is_government_incentive=true
                has_gov_incentive_event = any(
                    getattr(event, "is_government_incentive", False)
                    for event in final_resp.macro_events
                )
                if not has_gov_incentive_event:
                    logger.warning(
                        "[%s/%s] GOVERNMENT INCENTIVE ENFORCEMENT: News chunk '%s' contains "
                        "government policy content but no macro_event marked with "
                        "is_government_incentive=true.",
                        provider, model_name, chunk.get("source_id", "unknown")
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


def _ensure_government_incentive_events(
    response: DecisionsResponse,
    chunks: list[dict],
    provider: str,
    model_name: str,
) -> None:
    """Ensures policy-heavy snippets are represented by at least one flagged macro event."""
    gov_keywords = [
        "bill", "act", "congress", "parliament", "legislation", "subsidy", "grant",
        "incentive", "budget", "funding", "appropriation", "tax credit", "policy",
        "regulation", "directive", "executive order", "defense production act",
        "government program", "federal", "treasury", "usda", "dod", "doe", "sec",
        "appropriations", "tariff", "deregulation"
    ]

    def chunk_has_gov_content(content: str) -> bool:
        content_lower = content.lower()
        return any(kw in content_lower for kw in gov_keywords)

    def event_looks_like_gov_policy(event: MacroEvent) -> bool:
        event_text = " ".join(
            str(part or "")
            for part in (
                event.event_name,
                event.reasoning,
                event.scenario_analysis,
                event.expiry_date,
            )
        ).lower()
        return any(kw in event_text for kw in gov_keywords) or "government" in event_text or "policy" in event_text

    def mark_event(event: MacroEvent) -> None:
        if not event.is_government_incentive:
            event.is_government_incentive = True
            logger.info(
                "[%s/%s] GOVERNMENT INCENTIVE ENFORCEMENT: Auto-marked macro event '%s' as government incentive.",
                provider, model_name, event.event_name
            )

    fallback_scenarios = (
        "Scenario A: Policy advances or expands -> Trading Plan: Favor direct beneficiaries, "
        "sector ETFs, and suppliers tied to the incentive.\n"
        "Scenario B: Policy stalls, dilutes, or faces legal delay -> Trading Plan: Trim exposure "
        "to direct beneficiaries and shift to defensive hedges or broader indices."
    )

    gov_chunks = [chunk for chunk in chunks if chunk_has_gov_content(chunk.get("content", ""))]
    if not gov_chunks:
        return

    if not response.macro_events:
        for chunk in gov_chunks:
            response.macro_events.append(
                MacroEvent(
                    event_name="Government Policy Update",
                    impact="NEUTRAL",
                    catalyst_type="REGULATORY",
                    is_ongoing=False,
                    is_future_catalyst=False,
                    historical_parallel=None,
                    is_government_incentive=True,
                    expiry_date=None,
                    importance_score=6,
                    confidence=55,
                    reasoning=(
                        "Fallback macro event synthesized because the source chunk contains "
                        "government policy content but the model returned no macro event."
                    ),
                    scenario_analysis=fallback_scenarios,
                    source_id=chunk.get("source_id", "unknown"),
                    model_provider=provider,
                    model_name=model_name,
                )
            )
        return

    for chunk in gov_chunks:
        source_id = str(chunk.get("source_id", "unknown")).strip().lower()
        related_events = [
            event for event in response.macro_events
            if str(getattr(event, "source_id", "unknown")).strip().lower() == source_id
        ]

        flagged_events = [event for event in related_events if getattr(event, "is_government_incentive", False)]
        if flagged_events:
            continue

        gov_related_events = [event for event in related_events if event_looks_like_gov_policy(event)]
        target_event = gov_related_events[0] if gov_related_events else (related_events[0] if related_events else None)

        if target_event is not None:
            mark_event(target_event)
        else:
            response.macro_events.append(
                MacroEvent(
                    event_name="Government Policy Update",
                    impact="NEUTRAL",
                    catalyst_type="REGULATORY",
                    is_ongoing=False,
                    is_future_catalyst=False,
                    historical_parallel=None,
                    is_government_incentive=True,
                    expiry_date=None,
                    importance_score=6,
                    confidence=55,
                    reasoning=(
                        "Fallback macro event synthesized because the source chunk contains "
                        "government policy content but no matching macro event was returned."
                    ),
                    scenario_analysis=fallback_scenarios,
                    source_id=chunk.get("source_id", "unknown"),
                    model_provider=provider,
                    model_name=model_name,
                )
            )


def _scan_history_for_tools(messages: list, ticker: str) -> dict:
    """Scans message history for tool calls related to a specific ticker.

    This provides a 'hard' check against self-reported tool usage by LLMs.

    Returns:
        dict: {
            "quote_found": bool,
            "buy_tool_found": bool,
            "sell_tool_found": bool
        }
    """
    ticker = ticker.strip().upper()
    quote_found = False
    buy_tool_found = False
    sell_tool_found = False

    def _record_call(name, args):
        nonlocal quote_found, buy_tool_found, sell_tool_found

        if not name:
            return

        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                return

        if not isinstance(args, dict):
            return

        call_ticker = str(args.get("ticker", "")).strip().upper()
        if call_ticker != ticker:
            return

        if name == "get_stock_quote":
            quote_found = True
            logger.debug("Confirmed 'get_stock_quote' call for %s in history.", ticker)
        elif name == "calculate_buy_quantity":
            buy_tool_found = True
            logger.debug("Confirmed 'calculate_buy_quantity' call for %s in history.", ticker)
        elif name == "calculate_sell_quantity":
            sell_tool_found = True
            logger.debug("Confirmed 'calculate_sell_quantity' call for %s in history.", ticker)

    def _extract_calls(value):
        calls = []

        if value is None:
            return calls

        if isinstance(value, dict):
            tool_calls = value.get("tool_calls")
            if tool_calls:
                for tc in tool_calls:
                    if isinstance(tc, dict):
                        func = tc.get("function", {})
                        if isinstance(func, dict):
                            calls.append((func.get("name"), func.get("arguments", "{}")))
                        else:
                            calls.append((getattr(func, "name", None), getattr(func, "arguments", "{}")))
                    else:
                        func = getattr(tc, "function", None)
                        if func is not None:
                            calls.append((getattr(func, "name", None), getattr(func, "arguments", "{}")))

            content = value.get("content")
            if isinstance(content, list):
                for part in content:
                    calls.extend(_extract_calls(part))

            parts = value.get("parts")
            if isinstance(parts, list):
                for part in parts:
                    calls.extend(_extract_calls(part))

            if value.get("type") in {"tool_use", "function_call", "functionCall"}:
                if "name" in value:
                    calls.append((value.get("name"), value.get("input", value.get("arguments", {}))))
                elif "function" in value:
                    func = value.get("function", {})
                    if isinstance(func, dict):
                        calls.append((func.get("name"), func.get("arguments", "{}")))

            return calls

        tool_calls = getattr(value, "tool_calls", None)
        if tool_calls:
            for tc in tool_calls:
                func = getattr(tc, "function", None)
                if func is not None:
                    calls.append((getattr(func, "name", None), getattr(func, "arguments", "{}")))

        parts = getattr(value, "parts", None)
        if parts:
            for part in parts:
                f_call = getattr(part, "function_call", None)
                if f_call is not None:
                    calls.append((getattr(f_call, "name", None), getattr(f_call, "args", getattr(f_call, "arguments", {}))))
                tool_call = getattr(part, "tool_call", None)
                if tool_call is not None:
                    calls.append((getattr(tool_call, "name", None), getattr(tool_call, "args", getattr(tool_call, "arguments", {}))))

        content = getattr(value, "content", None)
        if isinstance(content, list):
            for part in content:
                calls.extend(_extract_calls(part))

        if getattr(value, "type", None) in {"tool_use", "function_call", "functionCall"}:
            name = getattr(value, "name", None)
            args = getattr(value, "input", getattr(value, "arguments", {}))
            if name is not None:
                calls.append((name, args))

        return calls

    for message in messages:
        for name, args in _extract_calls(message):
            _record_call(name, args)

    return {
        "quote_found": quote_found, 
        "buy_tool_found": buy_tool_found,
        "sell_tool_found": sell_tool_found
    }


def _extract_held_tickers(portfolio_context: str) -> List[str]:
    """Extracts held ticker symbols from portfolio context string.
    
    Parses the portfolio context to find all tickers the agent currently owns.
    
    Args:
        portfolio_context: The portfolio summary text.
        
    Returns:
        List of ticker symbols held in the portfolio.
    """
    held_tickers = []
    if not portfolio_context:
        return held_tickers
    
    # Look for pattern like "- NVDA: 100 shares" or "- {TICKER}:"
    import re
    # Match lines like "- NVDA: 100 shares @ $500.00"
    pattern = r'^-\s+([A-Z]{1,5}):'
    for line in portfolio_context.split('\n'):
        match = re.match(pattern, line.strip())
        if match:
            ticker = match.group(1)
            # Skip common non-ticker matches
            if ticker not in ['None', 'Cash', 'Total', 'Buying', 'SMA', 'Realized', 'Maintenance']:
                held_tickers.append(ticker)
    
    return held_tickers
