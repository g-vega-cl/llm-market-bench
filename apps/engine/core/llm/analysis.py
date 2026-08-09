"""Core LLM analysis logic for trading decisions."""

import asyncio
import copy
import json
import logging
import re
from typing import Any

from core.config import MIN_TRADE_VALUE
from core.llm import clients
from core.llm.logger import log_reasoning_trace
from core.llm.prompt_factory import PromptFactory
from core.models import DecisionsResponse

from .utils import ensure_list


def safe_deepcopy(obj):
    if "Mock" in type(obj).__name__:
        return str(obj)
    try:
        return copy.deepcopy(obj)
    except RecursionError:
        if isinstance(obj, list):
            return [safe_deepcopy(x) for x in obj]
        if isinstance(obj, dict):
            return {k: safe_deepcopy(v) for k, v in obj.items()}
        return str(obj)


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
        "TRUMP",
        "BIDEN",
        "HARRIS",
        "USA",
        "FED",
        "FOMC",
        "CPI",
        "GDP",
        "PCE",
        "PMI",
        "VIX",
        "WACC",
        "DCF",
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

        # Repair unescaped single backslashes that escape delimiter double-quotes
        pattern = (
            r'(?<!\\)\\"(?=\s*(?:\}\s*\]?|\}\s*\}|\]\s*\}|\]\s*\]|\}\s*,|\]\s*,|,\s*"\w+"\s*:|,\s*\}|,\s*\]|\s*$))'
        )
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


def _flatten_messages_for_minimax(messages: list) -> list:
    """Flatten tool loop conversation history into a single user message for MiniMax-M3.

    This prevents MiniMax-M3 from imitating or repeating previous assistant messages
    or tool calls from the multi-turn history.
    """
    system_msg = None
    first_user_msg = None
    history_blocks = []

    for m in messages:
        if not isinstance(m, dict):
            continue
        role = m.get("role")
        content = m.get("content", "")

        # If content is a list of blocks, flatten it to natural language
        if isinstance(content, list):
            flat_content = ""
            for part in content:
                if isinstance(part, dict) and "text" in part:
                    flat_content += part["text"]
                elif isinstance(part, dict) and "input" in part:
                    flat_content += f"\n(Executed tool {part['name']} with arguments: {part['input']})"
                elif isinstance(part, dict) and "content" in part and "tool_use_id" in part:
                    flat_content += f"\n(Tool returned result: {part['content']})"
            content = flat_content

        if role == "system":
            system_msg = {"role": "system", "content": str(content)}
        elif role == "user" and first_user_msg is None:
            first_user_msg = {"role": "user", "content": str(content)}
        else:
            # Collect intermediate assistant thoughts and tool results
            prefix = "Assistant" if role == "assistant" else "User"
            history_blocks.append(f"\n[{prefix}]: {str(content)}")

    combined_content = first_user_msg["content"] if first_user_msg else ""
    if history_blocks:
        combined_content += "\n\n=== Tool Execution History ===\n" + "\n".join(history_blocks)

    new_messages = []
    if system_msg:
        new_messages.append(system_msg)
    new_messages.append({"role": "user", "content": combined_content})
    return new_messages


def _try_parse_response(data, response_model, max_retries: int = 2):
    """Attempt to parse data into the specified response_model, trying various repair strategies.

    Args:
        data: Raw data from Instructor.
        response_model: The Pydantic model to parse into.
        max_retries: Number of repair strategies to try.

    Returns:
        The response_model instance if parsing succeeds, None otherwise.
    """
    strategies = []

    if isinstance(data, dict):
        strategies.append(lambda d: response_model(**d))

        if "decisions" in data and isinstance(data["decisions"], str):
            repaired = _repair_json_string(data["decisions"])
            try:
                data_copy = dict(data)
                data_copy["decisions"] = json.loads(repaired, strict=False)
                strategies.append(lambda d, dc=data_copy: response_model(**dc))
            except Exception:
                pass

        if "macro_events" in data and isinstance(data["macro_events"], str):
            repaired = _repair_json_string(data["macro_events"])
            try:
                data_copy = dict(data)
                data_copy["macro_events"] = json.loads(repaired, strict=False)
                strategies.append(lambda d, dc=data_copy: response_model(**dc))
            except Exception:
                pass

    elif isinstance(data, str):
        strategies.append(lambda d: response_model.model_validate_json(d))

        repaired = _repair_json_string(data)
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
        logger.warning(
            "All %d %s parse strategies failed. Errors: %s",
            len(strategies),
            response_model.__name__,
            "; ".join(f"Strategy {i}: {type(e).__name__}: {e}" for i, e in errors),
        )

    return None


def _try_parse_decisions_response(data, max_retries: int = 2) -> DecisionsResponse | None:
    """Legacy wrapper for backward compatibility."""
    return _try_parse_response(data, DecisionsResponse, max_retries)


async def analyze_with_provider(
    provider: str,
    model_name: str,
    chunks: list[dict],
    context: str = "",
    portfolio_context: str = "",
    current_day_info: str = "No date context available.",
    calendar_knowledge: str = "",
    macro_context: str = "",
    summaries: dict | None = None,
    market_data_block: str = "",
    response_model: Any = None,
    prompt_type: str = "analysis",
    consensus_context: str = "",
) -> Any:
    """Analyzes a batch of newsletter chunks using the specified provider."""
    if response_model is None:
        from core.models import DecisionsResponse

        response_model = DecisionsResponse

    factory = clients.CLIENT_FACTORIES.get(provider)
    if factory is None:
        raise ValueError(f"Unknown provider: {provider}")

    client = factory()

    from core.config import AUTORESEARCH_EXPERIMENT_OWNER_IDS
    from core.llm import tools

    # Set active newsletter chunks and summaries context for pull tools
    token_summaries = tools.active_news_summaries.set(summaries)
    token_chunks = tools.active_news_chunks.set(chunks)

    try:
        # Determine allowed tools for experiment variant
        override_tools = None
        enable_web_search = False
        if prompt_type == "macro":
            override_tools = []
        elif model_name in AUTORESEARCH_EXPERIMENT_OWNER_IDS:
            try:
                from autoresearch.prompt_store import get_active_variant

                variant = await get_active_variant()
                selected_tool_names = None
                if variant:
                    research_output = variant.get("research_output")
                    if isinstance(research_output, dict):
                        selected_tool_names = research_output.get("selected_tools")

                # If no tools are specified in the active variant, default to the baseline pull tools
                if not isinstance(selected_tool_names, list):
                    selected_tool_names = ["get_portfolio_ledger", "get_todays_news_menu", "web_search"]
                    logger.info(
                        f"No selected_tools found in active variant for experiment agent {model_name}. "
                        f"Defaulting to baseline pull tools: {selected_tool_names}"
                    )

                override_tools = []
                for name in selected_tool_names:
                    t_def = tools.CANONICAL_TOOLS_REGISTRY.get(name)
                    if t_def:
                        override_tools.append(t_def)
                    else:
                        logger.warning(f"Active prompt variant specified invalid tool name: {name}")

                # Force-inject calculate_buy_quantity and calculate_sell_quantity for safety
                safety_tools = [tools.CALCULATE_BUY_QUANTITY_TOOL, tools.CALCULATE_SELL_QUANTITY_TOOL]
                for st in safety_tools:
                    if st not in override_tools:
                        override_tools.append(st)

                # Intercept web_search tool to configure native web search flag
                if tools.WEB_SEARCH_TOOL in override_tools:
                    enable_web_search = True
                    override_tools = [t for t in override_tools if t != tools.WEB_SEARCH_TOOL]
            except Exception as e:
                logger.warning(
                    f"Failed to fetch selected tools for experiment variant: {e}. Defaulting to baseline pull tools."
                )
                override_tools = [
                    tools.CANONICAL_TOOLS_REGISTRY["get_portfolio_ledger"],
                    tools.CANONICAL_TOOLS_REGISTRY["get_todays_news_menu"],
                    tools.CALCULATE_BUY_QUANTITY_TOOL,
                    tools.CALCULATE_SELL_QUANTITY_TOOL,
                ]
                enable_web_search = True

        # Construct batch prompt (menu summaries if available, fallback to full text)
        if summaries:
            news_content_parts = []
            for chunk in chunks:
                source_id = chunk["source_id"]
                summary_text = summaries.get(source_id, "No summary available.")
                sender = chunk.get("sender", "Unknown")
                subject = chunk.get("subject", "No Subject")
                news_content_parts.append(
                    f"- Source ID: {source_id}\n  Sender: {sender}\n  Subject: {subject}\n  Summary: {summary_text}"
                )
            news_content = "\n".join(news_content_parts)
        else:
            news_content = "".join(
                [f"\n---\nSource ID: {chunk['source_id']}\nContent: {chunk['content']}\n---\n" for chunk in chunks]
            )

        # Extract held tickers from portfolio context for quick reference
        held_tickers = _extract_held_tickers(portfolio_context)
        held_tickers_list = ", ".join(held_tickers) if held_tickers else "None (you have no positions)"

        # Determine if web search should be enabled for this provider (if not overridden by experiment variant)
        if override_tools is None:
            if provider == "anthropic":
                from core.config import ENABLE_ANTHROPIC_WEB_SEARCH

                enable_web_search = ENABLE_ANTHROPIC_WEB_SEARCH
            elif provider == "gemini":
                from core.config import ENABLE_GEMINI_WEB_SEARCH

                enable_web_search = ENABLE_GEMINI_WEB_SEARCH
            elif provider == "openai":
                from core.config import ENABLE_OPENAI_WEB_SEARCH

                enable_web_search = ENABLE_OPENAI_WEB_SEARCH

        if prompt_type == "macro":
            messages = PromptFactory.build_macro_analysis_messages(
                provider=provider,
                current_day_info=current_day_info,
                news_content=news_content,
            )
        else:
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
                market_data_block=market_data_block,
                consensus_context=consensus_context,
            )

        # Tool execution loop (delegated to provider-specific handlers)
        raw_client = client.client
        if provider == "openai":
            from .handlers import openai

            await openai.run_tool_loop(
                raw_client,
                model_name,
                messages,
                provider,
                override_tools=override_tools,
                enable_web_search=enable_web_search,
            )
        elif provider == "deepseek":
            from .handlers import deepseek

            await deepseek.run_tool_loop(
                raw_client,
                model_name,
                messages,
                provider,
                override_tools=override_tools,
                enable_web_search=enable_web_search,
            )
        elif provider == "anthropic":
            from .handlers import anthropic

            await anthropic.run_tool_loop(
                raw_client,
                model_name,
                messages,
                override_tools=override_tools,
                enable_web_search=enable_web_search,
            )
        elif provider == "gemini":
            from .handlers import gemini

            await gemini.run_tool_loop(
                raw_client,
                model_name,
                messages,
                override_tools=override_tools,
                enable_google_search=enable_web_search,
            )
        elif provider == "minimax":
            from .handlers import anthropic

            # MiniMax-M3 supports the Anthropic API format; reusing the anthropic
            # tool-loop handler gives us native tool_use blocks and proper thinking
            # control. Web search is disabled because M3 has no native server-side
            # web_search tool via this endpoint.
            await anthropic.run_tool_loop(
                raw_client,
                model_name,
                messages,
                override_tools=override_tools,
                enable_web_search=False,
            )

        # Keep an unflattened copy of the message history for tool call verification
        # right after the tool loops run and BEFORE any flattening or preparation mutations.
        unflattened_messages = safe_deepcopy(messages)

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

        # Anthropic-specific: flatten nested content blocks for Instructor compatibility
        if provider == "minimax":
            messages = _flatten_messages_for_minimax(messages)
        elif provider == "anthropic":
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

        # Build schema hint dynamically
        schema_hint = "{}"
        if hasattr(response_model, "decisions") and hasattr(response_model, "macro_events"):
            schema_hint = (
                '{"decisions": [{"ticker": "string", "signal": "BUY|SELL|HOLD", ...}], "macro_events": [...]}\n'
            )
        elif hasattr(response_model, "decisions"):
            schema_hint = '{"decisions": [{"ticker": "string", "signal": "BUY|SELL|HOLD", ...}]}\n'
        elif hasattr(response_model, "macro_events"):
            schema_hint = '{"macro_events": [{"event_name": "string", "impact": "BULLISH|BEARISH|NEUTRAL", ...}]}\n'

        final_args = {
            "model": model_name,
            "response_model": response_model
            if provider != "gemini"
            else list[response_model],  # Use List to handle Gemini multi-block tool calls
            "messages": safe_deepcopy(messages),
            "max_retries": 2,
        }

        if provider == "gemini":
            for msg in final_args["messages"]:
                if isinstance(msg, dict) and msg.get("role") == "assistant":
                    msg["role"] = "model"
            if final_args["messages"]:
                last_msg = final_args["messages"][-1]
                last_role = last_msg.get("role") if isinstance(last_msg, dict) else getattr(last_msg, "role", None)
                if last_role in ("model", "assistant"):
                    final_args["messages"].append(
                        {
                            "role": "user",
                            "content": (
                                "Based on the preceding evaluation, extract and structure the final trade decisions "
                                "matching the schema exactly."
                            ),
                        }
                    )

        # DeepSeek specific: Enable thinking mode during final extraction so the model uses its
        # full reasoning capacity to formulate the final trade decisions.
        if provider == "deepseek" and "deepseek" in model_name.lower():
            final_args["extra_body"] = {"thinking": {"type": "enabled"}}

        if provider in ("anthropic", "minimax"):
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
                    or "no tool calls" in error_str
                    or "function call found" in error_str
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
                                f"Your response must be a valid JSON object matching this schema exactly:\n"
                                f"{schema_hint}"
                                "Do NOT return JSON as a string. Do NOT use quotes around the JSON object. "
                                "Return the raw JSON object directly with no additional text."
                            ),
                        }
                    )
                    final_args["messages"] = safe_deepcopy(messages)
                else:
                    # Non-validation error, re-raise
                    raise

        def create_fallback_model():
            init_args = {}
            if hasattr(response_model, "decisions"):
                init_args["decisions"] = []
            if hasattr(response_model, "macro_events"):
                init_args["macro_events"] = []
            return response_model(**init_args)

        if wrapper is None:
            logger.error(
                "[%s/%s] All Instructor extraction attempts failed. Last error: %s", provider, model_name, last_error
            )
            wrapper = [create_fallback_model()]

        # Aggregate all results from the list of response blocks
        final_resp = create_fallback_model()
        if wrapper:
            for r in ensure_list(wrapper):
                # Try to parse each response with JSON repair if needed
                parsed_r = _try_parse_response(r, response_model)
                if parsed_r is not None:
                    if hasattr(final_resp, "decisions") and hasattr(parsed_r, "decisions"):
                        final_resp.decisions.extend(parsed_r.decisions)
                    if hasattr(final_resp, "macro_events") and hasattr(parsed_r, "macro_events"):
                        final_resp.macro_events.extend(parsed_r.macro_events)
                else:
                    # Fallback: try the original extension method
                    if hasattr(final_resp, "decisions") and hasattr(r, "decisions"):
                        final_resp.decisions.extend(r.decisions)
                    if hasattr(final_resp, "macro_events") and hasattr(r, "macro_events"):
                        final_resp.macro_events.extend(r.macro_events)

        # Diagnostic logging for raw Instructor responses
        logger.debug(
            "[%s/%s] Instructor extraction complete: %d decisions, %d macro_events",
            provider,
            model_name,
            len(getattr(final_resp, "decisions", [])),
            len(getattr(final_resp, "macro_events", [])),
        )

        # RETRY and tool enforcement (only for models returning decisions)
        if hasattr(final_resp, "decisions"):
            # RETRY: If any BUY/SELL decision is missing its mandatory tool call, retry the tool loop once
            missing_tool_decisions = []
            for d in final_resp.decisions:
                if d.signal in ["BUY", "SELL"]:
                    results = _scan_history_for_tools(unflattened_messages, d.ticker)
                    if (d.signal == "BUY" and not results["buy_tool_found"]) or (
                        d.signal == "SELL" and not results["sell_tool_found"]
                    ):
                        missing_tool_decisions.append(d)

            if missing_tool_decisions:
                # Append the assistant's previous decisions response so it has context for correction
                try:
                    serialized_resp = final_resp.model_dump_json(indent=2)
                except Exception:
                    serialized_resp = str(final_resp)
                unflattened_messages.append({"role": "assistant", "content": serialized_resp})

                correction_lines = []
                for d in missing_tool_decisions:
                    tool_name = "calculate_buy_quantity" if d.signal == "BUY" else "calculate_sell_quantity"
                    correction_lines.append(
                        f"- You recommended {d.signal} {d.ticker} but did NOT call `{tool_name}`. "
                        f"You MUST call `{tool_name}(ticker='{d.ticker}', percentage=...)` NOW before providing your final response. "
                        f"Your trade will be REJECTED if this tool call is missing."
                    )
                correction_msg = {
                    "role": "user",
                    "content": (
                        "CORRECTION REQUIRED: The following trades are missing mandatory tool calls:\n"
                        + "\n".join(correction_lines)
                        + "\nPlease execute the required tool calls NOW, then re-output your complete decisions JSON."
                    ),
                }
                unflattened_messages.append(correction_msg)

                logger.warning(
                    "[%s/%s] Missing tool calls detected for decisions: %s. Retrying tool loop once...",
                    provider,
                    model_name,
                    [f"{d.signal} {d.ticker}" for d in missing_tool_decisions],
                )

                # Re-run the provider-specific tool loop
                if provider == "openai":
                    from .handlers import openai

                    await openai.run_tool_loop(
                        raw_client,
                        model_name,
                        unflattened_messages,
                        provider,
                        override_tools=override_tools,
                        enable_web_search=enable_web_search,
                    )
                elif provider == "deepseek":
                    from .handlers import deepseek

                    await deepseek.run_tool_loop(
                        raw_client,
                        model_name,
                        unflattened_messages,
                        provider,
                        override_tools=override_tools,
                        enable_web_search=enable_web_search,
                    )
                elif provider == "anthropic":
                    from .handlers import anthropic

                    await anthropic.run_tool_loop(
                        raw_client,
                        model_name,
                        unflattened_messages,
                        override_tools=override_tools,
                        enable_web_search=enable_web_search,
                    )
                elif provider == "gemini":
                    from .handlers import gemini

                    await gemini.run_tool_loop(
                        raw_client,
                        model_name,
                        unflattened_messages,
                        override_tools=override_tools,
                        enable_google_search=enable_web_search,
                    )
                elif provider == "minimax":
                    from .handlers import anthropic

                    await anthropic.run_tool_loop(
                        raw_client,
                        model_name,
                        unflattened_messages,
                        override_tools=override_tools,
                        enable_web_search=False,
                    )

                # Re-prepare messages for Instructor extraction from the updated unflattened history
                messages_retry = safe_deepcopy(unflattened_messages)
                if provider == "deepseek":
                    from .handlers import deepseek

                    messages_retry = deepseek.prepare_messages_for_instructor(messages_retry)
                    if not deepseek.has_valid_content(messages_retry):
                        messages_retry.append(
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

                if provider == "minimax":
                    messages_retry = _flatten_messages_for_minimax(messages_retry)
                elif provider == "anthropic":
                    flattened = []
                    for m in messages_retry:
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
                    messages_retry = flattened

                final_args_retry = {
                    "model": model_name,
                    "response_model": response_model if provider != "gemini" else list[response_model],
                    "messages": safe_deepcopy(messages_retry),
                    "max_retries": 2,
                }

                if provider == "gemini":
                    for msg in final_args_retry["messages"]:
                        if isinstance(msg, dict) and msg.get("role") == "assistant":
                            msg["role"] = "model"
                    if final_args_retry["messages"]:
                        last_msg = final_args_retry["messages"][-1]
                        last_role = (
                            last_msg.get("role") if isinstance(last_msg, dict) else getattr(last_msg, "role", None)
                        )
                        if last_role in ("model", "assistant"):
                            final_args_retry["messages"].append(
                                {
                                    "role": "user",
                                    "content": (
                                        "Based on the preceding evaluation, extract and structure the final trade decisions "
                                        "matching the schema exactly."
                                    ),
                                }
                            )

                if provider == "deepseek" and "deepseek" in model_name.lower():
                    final_args_retry["extra_body"] = {"thinking": {"type": "enabled"}}

                if provider in ("anthropic", "minimax"):
                    final_args_retry["max_tokens"] = 32000
                    if messages_retry[0]["role"] == "system":
                        final_args_retry["system"] = messages_retry[0]["content"]
                        final_args_retry["messages"] = messages_retry[1:]

                # Re-run Instructor extraction
                wrapper_retry = None
                last_error_retry = None
                for attempt in range(3):
                    try:
                        resp_awaitable = client.chat.completions.create(**final_args_retry)
                        if hasattr(resp_awaitable, "__await__") or asyncio.iscoroutine(resp_awaitable):
                            wrapper_retry = await resp_awaitable
                        else:
                            wrapper_retry = resp_awaitable
                        break
                    except Exception as e:
                        last_error_retry = e
                        error_str = str(e).lower()
                        if (
                            "validation error" in error_str
                            or "input should be a valid" in error_str
                            or "list_type" in error_str
                        ):
                            logger.warning(
                                "[%s/%s] Instructor validation error in retry (attempt %d/3): %s. Attempting JSON repair...",
                                provider,
                                model_name,
                                attempt + 1,
                                str(e)[:200],
                            )
                            messages_retry.append(
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
                            final_args_retry["messages"] = safe_deepcopy(messages_retry)
                        else:
                            raise

                if wrapper_retry is None:
                    logger.error(
                        "[%s/%s] All Instructor extraction attempts in retry failed. Last error: %s",
                        provider,
                        model_name,
                        last_error_retry,
                    )
                    wrapper_retry = [create_fallback_model()]

                # Aggregate all results from the retry
                final_resp = create_fallback_model()
                if wrapper_retry:
                    for r in ensure_list(wrapper_retry):
                        parsed_r = _try_parse_response(r, response_model)
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

                logger.info(
                    "[%s/%s] Retry extraction complete: %d decisions, %d macro_events",
                    provider,
                    model_name,
                    len(getattr(final_resp, "decisions", [])),
                    len(getattr(final_resp, "macro_events", [])),
                )

                # Update messages so the logged prompt reflects the retry history
                messages = unflattened_messages

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
            task_type="MACRO_EXTRACTION" if prompt_type == "macro" else "INGESTION",
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
        tools.active_news_summaries.reset(token_summaries)
        tools.active_news_chunks.reset(token_chunks)
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
