"""Core LLM analysis logic for trading decisions."""

import asyncio
import copy
import json
import logging
import re

from core.config import MIN_TRADE_VALUE
from core.llm import clients
from core.llm.logger import log_reasoning_trace
from core.llm.prompt_factory import PromptFactory
from core.models import DecisionsResponse

from .utils import ensure_list

logger = logging.getLogger("engine")

# Common words that look like tickers but aren't (for $SYMB extraction)
_TICKER_FALSE_POSITIVES = frozenset(
    {
        "THE",
        "AND",
        "CEO",
        "CFO",
        "ETF",
        "IPO",
        "FOR",
        "ARE",
        "NEW",
        "YEAR",
        "MARKET",
        "STOCK",
        "TRADE",
        "FUND",
        "DOWN",
        "OVER",
        "FROM",
        "THAT",
        "THIS",
        "WITH",
        "WILL",
        "HAVE",
        "MORE",
        "LESS",
        "WHEN",
        "THAN",
        "ALSO",
        "INTO",
        "JUST",
        "LIKE",
        "SOME",
        "MUCH",
        "SUCH",
        "ONLY",
        "VERY",
        "MAKE",
        "HUGE",
        "BULL",
        "BEAR",
        "SELL",
        "BUY",
        "HOLD",
        "CALL",
        "PUT",
        "NOTE",
        "HERE",
        "MUST",
        "NEED",
        "WELL",
        "HIGH",
        "LOW",
        "LONG",
        "SHORT",
        "BIG",
        "SEE",
        "USE",
        "US",
        "TOP",
        "OUT",
        "END",
    }
)

_MAJOR_INDICES = frozenset({"SPY", "QQQ", "DIA", "IWM"})


def _repair_json_string(json_str: str) -> str:
    """Attempt to repair a malformed JSON string by extracting valid JSON.

    This handles cases where the LLM returns a JSON string inside another JSON,
    or returns the JSON with extra text/quotes around it.

    Args:
        json_str: The potentially malformed JSON string.

    Returns:
        A cleaned JSON string that can be parsed.
    """
    if isinstance(json_str, str):
        json_str = json_str.strip()

        if json_str.startswith('"') and json_str.endswith('"'):
            json_str = json_str[1:-1]
            json_str = json_str.replace('\\"', '"').replace("\\n", "\n").replace("\\r", "\r")

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
                # Now trim trailing
                if json_str.startswith("{"):
                    end_idx = json_str.rfind("}")
                    if end_idx != -1:
                        json_str = json_str[: end_idx + 1]
                elif json_str.startswith("["):
                    end_idx = json_str.rfind("]")
                    if end_idx != -1:
                        json_str = json_str[: end_idx + 1]

    return json_str


def _try_parse_decisions_response(data, max_retries: int = 2) -> DecisionsResponse | None:
    """Attempt to parse data into a DecisionsResponse, trying various repair strategies.

    Args:
        data: Raw data from Instructor.
        max_retries: Number of repair strategies to try.

    Returns:
        DecisionsResponse if parsing succeeds, None otherwise.
    """
    strategies = []

    if isinstance(data, dict):
        strategies.append(lambda d: DecisionsResponse(**d))

        if "decisions" in data and isinstance(data["decisions"], str):
            repaired = _repair_json_string(data["decisions"])
            try:
                data_copy = dict(data)
                data_copy["decisions"] = json.loads(repaired)
                strategies.append(lambda d, dc=data_copy: DecisionsResponse(**dc))
            except Exception:
                pass

        if "macro_events" in data and isinstance(data["macro_events"], str):
            repaired = _repair_json_string(data["macro_events"])
            try:
                data_copy = dict(data)
                data_copy["macro_events"] = json.loads(repaired)
                strategies.append(lambda d, dc=data_copy: DecisionsResponse(**dc))
            except Exception:
                pass

    elif isinstance(data, str):
        strategies.append(lambda d: DecisionsResponse.model_validate_json(d))

        repaired = _repair_json_string(data)
        strategies.append(lambda d, r=repaired: DecisionsResponse.model_validate_json(r))

        try:
            parsed = json.loads(repaired)
            strategies.append(
                lambda d, p=parsed: (
                    DecisionsResponse.model_validate_json(p) if isinstance(p, str) else DecisionsResponse(**p)
                )
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
        logger.warning(
            "All %d DecisionsResponse parse strategies failed. Errors: %s",
            len(strategies),
            "; ".join(f"Strategy {i}: {type(e).__name__}: {e}" for i, e in errors),
        )

    return None


async def _analyze_with_minimax(
    model_name: str,
    chunks: list[dict],
    context: str = "",
    portfolio_context: str = "",
    current_day_info: str = "No date context available.",
    calendar_knowledge: str = "",
    macro_context: str = "",
) -> DecisionsResponse:
    """Analysis pipeline for MiniMax M2.7.

    MiniMax does not support the OpenAI function-calling / Instructor flow.
    Instead we:
      1. Build a flat JSON-in-text prompt using the existing prompt templates.
      2. Call MiniMaxClient.chat() directly (raw HTTP).
      3. Parse the text response into a DecisionsResponse using the existing
         repair helpers — no Instructor, no tool loop.

    Args:
        model_name: MiniMax model identifier (e.g. ``MiniMax-M2.7``).
        chunks: Newsletter chunks to analyse.
        context: Aggregated historical context.
        portfolio_context: Current portfolio summary text.
        current_day_info: Today's date/calendar context string.
        calendar_knowledge: Calendar strategy knowledge.
        macro_context: Current macro-economic indicator summary.

    Returns:
        DecisionsResponse — empty on parse failure (never raises).
    """
    import json as _json

    from core.llm.minimax import MiniMaxClient
    from core.llm.prompt_factory import PromptFactory

    news_content = "".join(
        [f"\n---\nSource ID: {chunk['source_id']}\nContent: {chunk['content']}\n---\n" for chunk in chunks]
    )

    held_tickers = _extract_held_tickers(portfolio_context)
    held_tickers_list = ", ".join(held_tickers) if held_tickers else "None (you have no positions)"

    # Build the standard analysis messages (no web search for MiniMax).
    # PromptFactory returns [{"role": "system", ...}, {"role": "user", ...}]
    messages = await PromptFactory.build_analysis_messages(
        provider="minimax",
        owner_id=model_name,
        portfolio_context=portfolio_context if portfolio_context else "No portfolio data available.",
        context=context if context else "No relevant historical context found.",
        news_content=news_content,
        min_trade_value=1000,
        current_day_info=current_day_info,
        calendar_knowledge=calendar_knowledge,
        macro_context=macro_context if macro_context else "No macro data available.",
        held_tickers_list=held_tickers_list,
        enable_web_search=False,
    )

    # Append an explicit JSON output instruction so MiniMax knows the expected format.
    messages.append(
        {
            "role": "user",
            "content": (
                "Output your response ONLY as a valid JSON object with no additional text, "
                "no markdown, and no code fences. The JSON must match this schema exactly:\n"
                "{\n"
                '  "decisions": [\n'
                "    {\n"
                '      "signal": "BUY" | "SELL" | "HOLD",\n'
                '      "confidence": 0-100,\n'
                '      "reasoning": "string",\n'
                '      "ticker": "string",\n'
                '      "catalyst_type": "MACRO" | "EARNINGS" | "M_A" | "PRODUCT" | "REGULATORY" | "EVENT" | "INNOVATION" | "TECHNICAL" | "UNCROWDED_TRADE" | "OTHER",\n'
                '      "catalyst_duration": "INTRADAY" | "SHORT_TERM" | "MEDIUM_TERM" | "LONG_TERM",\n'
                '      "source_id": "string",\n'
                '      "allocation_percentage": 0-100,\n'
                '      "is_priced_in": boolean,\n'
                '      "is_priced_in_reasoning": "string",\n'
                '      "profit_potential_reasoning": "string",\n'
                '      "strategy_reasoning": "string",\n'
                '      "advance_planning_notes": "string",\n'
                '      "buy_tool_called": boolean,\n'
                '      "sell_tool_called": boolean,\n'
                '      "quantity": integer\n'
                "    }\n"
                "  ],\n"
                '  "macro_events": [\n'
                "    {\n"
                '      "event_name": "string",\n'
                '      "impact": "BULLISH" | "BEARISH" | "NEUTRAL",\n'
                '      "catalyst_type": "MACRO" | "EARNINGS" | "M_A" | "PRODUCT" | "REGULATORY" | "EVENT" | "INNOVATION" | "TECHNICAL" | "UNCROWDED_TRADE" | "OTHER",\n'
                '      "is_ongoing": boolean,\n'
                '      "is_future_catalyst": boolean,\n'
                '      "historical_parallel": "string",\n'
                '      "expiry_date": "string",\n'
                '      "importance_score": 1-10,\n'
                '      "confidence": 0-100,\n'
                '      "reasoning": "string",\n'
                '      "scenario_analysis": "string",\n'
                '      "source_id": "string"\n'
                "    }\n"
                "  ]\n"
                "}"
            ),
        }
    )

    client = MiniMaxClient()
    try:
        resp = await client.chat(
            messages=messages,
            model=model_name,
            temperature=0.3,
            max_completion_tokens=4096,
        )
    except Exception:
        logger.exception("[minimax/%s] API call failed — returning empty response.", model_name)
        return DecisionsResponse(decisions=[], macro_events=[])
    finally:
        await client.close()

    content = resp.get("content", "").strip()

    # Strip markdown code fences if present
    if content.startswith("```"):
        lines = content.split("\n")
        # Remove first line (```json or ```) and last line (```)
        content = "\n".join(lines[1:-1]) if len(lines) > 2 else ""

    # Attempt to extract JSON substring if there is surrounding text
    content = _repair_json_string(content)

    if not content:
        logger.warning("[minimax/%s] Empty content after extraction — returning empty response.", model_name)
        return DecisionsResponse(decisions=[], macro_events=[])

    # Parse the content
    try:
        raw = _json.loads(content)
    except _json.JSONDecodeError:
        logger.warning(
            "[minimax/%s] JSON decode failed — returning empty response. Content snippet: %.200s",
            model_name,
            content,
        )
        return DecisionsResponse(decisions=[], macro_events=[])

    result = _try_parse_decisions_response(raw)
    if result is None:
        logger.warning("[minimax/%s] DecisionsResponse parse failed — returning empty response.", model_name)
        return DecisionsResponse(decisions=[], macro_events=[])

    # Pre-analysis ownership validation: convert phantom SELL → HOLD
    validated = []
    for decision in result.decisions:
        if decision.signal == "SELL" and decision.ticker.upper() not in [t.upper() for t in held_tickers]:
            logger.warning(
                "[minimax/%s] PRE-ANALYSIS VALIDATION: SELL for %s rejected — ticker not held. Held: %s",
                model_name,
                decision.ticker,
                held_tickers,
            )
            decision.signal = "HOLD"
            decision.reasoning = (
                f"REJECTED_OWNERSHIP: Attempted to sell {decision.ticker} but ticker is not held. "
                f"Original reasoning: {decision.reasoning[:200]}"
            )
        validated.append(decision)
    result.decisions = validated

    await log_reasoning_trace(
        task_type="INGESTION",
        model_provider="minimax",
        model_name=model_name,
        prompt=messages,
        response=result,
        metadata={
            "chunk_ids": [c.get("source_id") for c in chunks],
            "portfolio_status": "injected" if portfolio_context else "none",
        },
    )

    logger.info(
        "[minimax/%s] Analysis complete: %d decisions, %d macro_events.",
        model_name,
        len(result.decisions),
        len(result.macro_events),
    )
    return result


async def analyze_with_provider(
    provider: str,
    model_name: str,
    chunks: list[dict],
    context: str = "",
    portfolio_context: str = "",
    current_day_info: str = "No date context available.",
    calendar_knowledge: str = "",
    macro_context: str = "",
) -> DecisionsResponse:
    """Analyzes a batch of newsletter chunks using the specified provider.

    Args:
        provider: The LLM provider name (openai, anthropic, gemini, deepseek, minimax).
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
    # MiniMax uses its own raw HTTP client (not Instructor) and has no tool loop.
    # Route it through a dedicated code path before the Instructor factory lookup.
    if provider == "minimax":
        return await _analyze_with_minimax(
            model_name=model_name,
            chunks=chunks,
            context=context,
            portfolio_context=portfolio_context,
            current_day_info=current_day_info,
            calendar_knowledge=calendar_knowledge,
            macro_context=macro_context,
        )

    factory = clients.CLIENT_FACTORIES.get(provider)
    if factory is None:
        raise ValueError(f"Unknown provider: {provider}")

    client = factory()

    try:
        # Construct batch prompt
        news_content = "".join(
            [f"\n---\nSource ID: {chunk['source_id']}\nContent: {chunk['content']}\n---\n" for chunk in chunks]
        )

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

        messages = await PromptFactory.build_analysis_messages(
            provider=provider,
            owner_id=model_name,
            portfolio_context=portfolio_context if portfolio_context else "No portfolio data available.",
            context=context if context else "No relevant historical context found.",
            news_content=news_content,
            min_trade_value=MIN_TRADE_VALUE,
            current_day_info=current_day_info,
            calendar_knowledge=calendar_knowledge,
            macro_context=macro_context if macro_context else "No macro data available.",
            held_tickers_list=held_tickers_list,
            enable_web_search=enable_web_search,
        )

        # Tool execution loop (delegated to provider-specific handlers)
        raw_client = client.client
        if provider == "openai":
            from .handlers import openai

            await openai.run_tool_loop(raw_client, model_name, messages, provider, enable_web_search=enable_web_search)
        elif provider == "deepseek":
            from .handlers import deepseek

            await deepseek.run_tool_loop(
                raw_client, model_name, messages, provider, enable_web_search=enable_web_search
            )
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
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Your previous output was empty or only contains reasoning. "
                            "To complete this task, you MUST now output ONLY a valid JSON object following the schema. "
                            "No more reasoning, no explanations. Just the raw JSON object. "
                            'Example: {"decisions": [], "macro_events": []}'
                        ),
                    }
                )

        # Keep an unflattened copy of the message history for tool call verification
        unflattened_messages = copy.deepcopy(messages)

        # Anthropic-specific: flatten nested content blocks for Instructor compatibility
        if provider == "anthropic":
            flattened = []
            for m in messages:
                if isinstance(m, dict):
                    content = m.get("content", "")
                    if isinstance(content, list):
                        flat_content = ""
                        for part in content:
                            if isinstance(part, dict) and "text" in part:
                                flat_content += part["text"]
                            elif isinstance(part, dict) and "input" in part:
                                flat_content += f"\n[Tool Call: {part['name']}({part['input']})]"
                            elif isinstance(part, dict) and "content" in part and "tool_use_id" in part:
                                flat_content += f"\n[Tool Result: {part['content']}]"
                        content = flat_content
                    flattened.append({"role": m["role"], "content": str(content)})
            messages = flattened

        final_args = {
            "model": model_name,
            "response_model": DecisionsResponse
            if provider != "gemini"
            else list[DecisionsResponse],  # Use List to handle Gemini multi-block tool calls
            "messages": copy.deepcopy(messages),
            "max_retries": 2,
        }

        if provider == "anthropic":
            final_args["max_tokens"] = 32000  # Increased from 8000 to handle long outputs
            if messages[0]["role"] == "system":
                final_args["system"] = messages[0]["content"]
                final_args["messages"] = messages[1:]

        # Instructor extraction with retry and JSON repair for validation errors
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

                # Check if it's a validation error that might be fixed with JSON repair
                if (
                    "validation error" in error_str
                    or "input should be a valid" in error_str
                    or "list_type" in error_str
                ):
                    logger.warning(
                        "[%s/%s] Instructor validation error (attempt %d/3): %s. Attempting JSON repair...",
                        provider,
                        model_name,
                        attempt + 1,
                        str(e)[:200],
                    )

                    # Add a user message requesting clean JSON output
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                "Your last response failed schema validation. Error details:\n"
                                f"{str(e)[:500]}\n\n"
                                "Your response must be a valid JSON object matching this schema exactly:\n"
                                '{"decisions": [{"ticker": "string", "signal": "BUY|SELL|HOLD", ...}], "macro_events": [...]}\n'
                                "Do NOT return JSON as a string. Do NOT use quotes around the JSON object. "
                                "Return the raw JSON object directly with no additional text."
                            ),
                        }
                    )
                    final_args["messages"] = copy.deepcopy(messages)
                else:
                    # Non-validation error, re-raise
                    raise

        if wrapper is None:
            logger.error(
                "[%s/%s] All Instructor extraction attempts failed. Last error: %s", provider, model_name, last_error
            )
            wrapper = [DecisionsResponse(decisions=[], macro_events=[])]

        # Aggregate all results from the list of response blocks
        final_resp = DecisionsResponse(decisions=[], macro_events=[])
        if wrapper:
            for r in ensure_list(wrapper):
                # Try to parse each response with JSON repair if needed
                parsed_r = _try_parse_decisions_response(r)
                if parsed_r is not None:
                    final_resp.decisions.extend(parsed_r.decisions)
                    final_resp.macro_events.extend(parsed_r.macro_events)
                else:
                    # Fallback: try the original extension method
                    final_resp.decisions.extend(r.decisions)
                    final_resp.macro_events.extend(r.macro_events)

        # Diagnostic logging for raw Instructor responses
        logger.debug(
            "[%s/%s] Instructor extraction complete: %d decisions, %d macro_events",
            provider,
            model_name,
            len(final_resp.decisions),
            len(final_resp.macro_events),
        )

        # HARD TOOL ENFORCEMENT: Verify that tools were ACTUALLY called in the history
        for decision in final_resp.decisions:
            if decision.signal in ["BUY", "SELL"]:
                results = _scan_history_for_tools(unflattened_messages, decision.ticker)
                calls_found = _get_history_tool_calls_diagnostic(unflattened_messages)

                # Update buy_tool_called/sell_tool_called based on ACTUAL history
                if decision.signal == "BUY":
                    was_self_reported = decision.buy_tool_called
                    decision.buy_tool_called = results["buy_tool_found"]

                    if was_self_reported and not results["buy_tool_found"]:
                        logger.warning(
                            "[%s/%s] HARD ENFORCEMENT: Agent claimed buy tool was called for %s but it was NOT found in history. "
                            "Total messages in history: %d. Tools called: %s. Rejecting trade.",
                            provider,
                            model_name,
                            decision.ticker,
                            len(unflattened_messages),
                            calls_found,
                        )
                    elif not results["buy_tool_found"]:
                        logger.warning(
                            "[%s/%s] HARD ENFORCEMENT: Agent recommended BUY for %s without executing 'calculate_buy_quantity' tool. "
                            "Total messages in history: %d. Tools called: %s. Rejecting trade.",
                            provider,
                            model_name,
                            decision.ticker,
                            len(unflattened_messages),
                            calls_found,
                        )

                elif decision.signal == "SELL":
                    was_self_reported = decision.sell_tool_called
                    decision.sell_tool_called = results["sell_tool_found"]

                    if was_self_reported and not results["sell_tool_found"]:
                        logger.warning(
                            "[%s/%s] HARD ENFORCEMENT: Agent claimed sell tool was called for %s but it was NOT found in history. "
                            "Total messages in history: %d. Tools called: %s. Rejecting trade.",
                            provider,
                            model_name,
                            decision.ticker,
                            len(unflattened_messages),
                            calls_found,
                        )
                    elif not results["sell_tool_found"]:
                        logger.warning(
                            "[%s/%s] HARD ENFORCEMENT: Agent recommended SELL for %s without executing 'calculate_sell_quantity' tool. "
                            "Total messages in history: %d. Tools called: %s. Rejecting trade.",
                            provider,
                            model_name,
                            decision.ticker,
                            len(unflattened_messages),
                            calls_found,
                        )

        # PRE-ANALYSIS PORTFOLIO VALIDATION: Filter out SELL decisions for tickers not held
        # This catches hallucinations before they reach the verification layer
        held_tickers = _extract_held_tickers(portfolio_context)
        validated_decisions = []
        for decision in final_resp.decisions:
            if decision.signal == "SELL" and decision.ticker.upper() not in [t.upper() for t in held_tickers]:
                logger.warning(
                    "[%s/%s] PRE-ANALYSIS VALIDATION: SELL signal for %s rejected - ticker not in portfolio. Held: %s",
                    provider,
                    model_name,
                    decision.ticker,
                    held_tickers,
                )
                # Mark as rejected but keep for audit trail
                decision.signal = "HOLD"  # Convert to HOLD to preserve audit trail
                decision.reasoning = f"REJECTED_OWNERSHIP: Attempted to sell {decision.ticker} but ticker is not held. Original reasoning: {decision.reasoning[:200]}"
            validated_decisions.append(decision)
        final_resp.decisions = validated_decisions

        # Log completion
        await log_reasoning_trace(
            task_type="INGESTION",
            model_provider=provider,
            model_name=model_name,
            prompt=messages,
            response=final_resp,
            metadata={
                "chunk_ids": [c.get("source_id") for c in chunks],
                "portfolio_status": "injected" if portfolio_context else "none",
            },
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
            "buy_tool_found": bool,
            "sell_tool_found": bool
        }
    """
    ticker = ticker.strip().upper()
    buy_tool_found = False
    sell_tool_found = False

    def _record_call(name, args):
        nonlocal buy_tool_found, sell_tool_found

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

        if name == "calculate_buy_quantity":
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
                    calls.append(
                        (getattr(f_call, "name", None), getattr(f_call, "args", getattr(f_call, "arguments", {})))
                    )
                tool_call = getattr(part, "tool_call", None)
                if tool_call is not None:
                    calls.append(
                        (
                            getattr(tool_call, "name", None),
                            getattr(tool_call, "args", getattr(tool_call, "arguments", {})),
                        )
                    )

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

    return {"buy_tool_found": buy_tool_found, "sell_tool_found": sell_tool_found}


def _get_history_tool_calls_diagnostic(messages: list) -> list[str]:
    """Extracts a diagnostic summary list of all tool calls made in the message history.

    This provides visibility in log streams when tool enforcement fails.
    """
    tool_calls = []

    def _extract(value):
        calls = []
        if value is None:
            return calls

        if isinstance(value, dict):
            t_calls = value.get("tool_calls")
            if t_calls:
                for tc in t_calls:
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
                    calls.extend(_extract(part))

            parts = value.get("parts")
            if isinstance(parts, list):
                for part in parts:
                    calls.extend(_extract(part))

            if value.get("type") in {"tool_use", "function_call", "functionCall"}:
                if "name" in value:
                    calls.append((value.get("name"), value.get("input", value.get("arguments", {}))))
                elif "function" in value:
                    func = value.get("function", {})
                    if isinstance(func, dict):
                        calls.append((func.get("name"), func.get("arguments", "{}")))

            return calls

        t_calls = getattr(value, "tool_calls", None)
        if t_calls:
            for tc in t_calls:
                func = getattr(tc, "function", None)
                if func is not None:
                    calls.append((getattr(func, "name", None), getattr(func, "arguments", "{}")))

        parts = getattr(value, "parts", None)
        if parts:
            for part in parts:
                f_call = getattr(part, "function_call", None)
                if f_call is not None:
                    calls.append(
                        (getattr(f_call, "name", None), getattr(f_call, "args", getattr(f_call, "arguments", {})))
                    )
                tool_call = getattr(part, "tool_call", None)
                if tool_call is not None:
                    calls.append(
                        (
                            getattr(tool_call, "name", None),
                            getattr(tool_call, "args", getattr(tool_call, "arguments", {})),
                        )
                    )

        content = getattr(value, "content", None)
        if isinstance(content, list):
            for part in content:
                calls.extend(_extract(part))

        if getattr(value, "type", None) in {"tool_use", "function_call", "functionCall"}:
            name = getattr(value, "name", None)
            args = getattr(value, "input", getattr(value, "arguments", {}))
            if name is not None:
                calls.append((name, args))

        return calls

    for message in messages:
        for name, args in _extract(message):
            if name:
                args_str = str(args).strip().replace("\n", " ")
                tool_calls.append(f"{name}({args_str})")

    return tool_calls


def _extract_held_tickers(portfolio_context: str) -> list[str]:
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
    pattern = r"^-\s+([A-Z]{1,5}):"
    for line in portfolio_context.split("\n"):
        match = re.match(pattern, line.strip())
        if match:
            ticker = match.group(1)
            # Skip common non-ticker matches
            if ticker not in ["None", "Cash", "Total", "Buying", "SMA", "Realized", "Maintenance"]:
                held_tickers.append(ticker)

    return held_tickers


_DOLLAR_TICKER_PATTERN = re.compile(r"\$([A-Z]{1,5})\b")


def _extract_tickers_from_chunks(chunks: list[dict], portfolio_tickers: list[str]) -> frozenset[str]:
    """Extract ticker candidates from newsletter chunks for pre-fetching market data.

    Scans chunks for $SYMB patterns (reliable in financial text) and unions with
    portfolio tickers plus major market indices.

    Args:
        chunks: List of dicts with 'content' keys containing newsletter text.
        portfolio_tickers: List of tickers currently held in portfolio.

    Returns:
        Frozen set of uppercase ticker symbols.
    """
    tickers: set[str] = set(t.strip().upper() for t in portfolio_tickers)
    tickers.update(_MAJOR_INDICES)

    for chunk in chunks:
        content = chunk.get("content", "")
        for match in _DOLLAR_TICKER_PATTERN.finditer(content):
            ticker = match.group(1)
            if ticker not in _TICKER_FALSE_POSITIVES:
                tickers.add(ticker)

    return frozenset(tickers)
