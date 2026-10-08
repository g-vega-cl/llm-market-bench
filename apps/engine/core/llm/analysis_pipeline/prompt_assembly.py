"""Prompt assembly and provider message preparation vertical slice island."""

import copy
import logging
import re
from typing import Any

from core.config import (
    AUTORESEARCH_EXPERIMENT_OWNER_IDS,
    ENABLE_ANTHROPIC_WEB_SEARCH,
    ENABLE_DEEPSEEK_WEB_SEARCH,
    ENABLE_GEMINI_WEB_SEARCH,
    ENABLE_OPENAI_WEB_SEARCH,
    MIN_TRADE_VALUE,
)
from core.llm import tools
from core.llm.prompt_factory import PromptFactory

logger = logging.getLogger("engine")

# Common words that look like tickers but aren't (for $SYMB extraction)
_TICKER_FALSE_POSITIVES_RAW = (
    "THE AND CEO CFO ETF IPO FOR ARE NEW YEAR MARKET STOCK TRADE FUND DOWN OVER "
    "FROM THAT THIS WITH WILL HAVE MORE LESS WHEN THAN ALSO INTO JUST LIKE SOME "
    "MUCH SUCH ONLY VERY MAKE HUGE BULL BEAR SELL BUY HOLD CALL PUT NOTE HERE "
    "MUST NEED WELL HIGH LOW LONG SHORT BIG SEE USE US TOP OUT END TRUMP BIDEN "
    "HARRIS USA FED FOMC CPI GDP PCE PMI VIX WACC DCF"
)
_TICKER_FALSE_POSITIVES = frozenset(_TICKER_FALSE_POSITIVES_RAW.split())

_MAJOR_INDICES = frozenset({"SPY", "QQQ", "DIA", "IWM"})
_DOLLAR_TICKER_PATTERN = re.compile(r"\$([A-Z]{1,5})\b")


def safe_deepcopy(obj: Any) -> Any:
    """Safely deepcopy an object, gracefully degrading for MagicMocks or recursion issues."""
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


def format_news_content(chunks: list[dict], summaries: dict | None = None) -> str:
    """Format news content using high-level summaries menu if available, otherwise chunk text."""
    if summaries:
        parts = []
        for chunk in chunks:
            source_id = chunk["source_id"]
            summary_text = summaries.get(source_id, "No summary available.")
            sender = chunk.get("sender", "Unknown")
            subject = chunk.get("subject", "No Subject")
            parts.append(
                f"- Source ID: {source_id}\n  Sender: {sender}\n  Subject: {subject}\n  Summary: {summary_text}"
            )
        return "\n".join(parts)

    return "".join([f"\n---\nSource ID: {chunk['source_id']}\nContent: {chunk['content']}\n---\n" for chunk in chunks])


def extract_held_tickers(portfolio_context: str) -> list[str]:
    """Extract held ticker symbols from portfolio context string."""
    held_tickers = []
    if not portfolio_context:
        return held_tickers

    pattern = r"^-\s+([A-Z]{1,5}):"
    for line in portfolio_context.split("\n"):
        match = re.match(pattern, line.strip())
        if match:
            ticker = match.group(1)
            if ticker not in ["None", "Cash", "Total", "Buying", "SMA", "Realized", "Maintenance"]:
                held_tickers.append(ticker)

    return held_tickers


def extract_tickers_from_chunks(chunks: list[dict], portfolio_tickers: list[str]) -> frozenset[str]:
    """Extract ticker candidates from newsletter chunks and portfolio for pre-fetching market data."""
    tickers: set[str] = set(t.strip().upper() for t in portfolio_tickers)
    tickers.update(_MAJOR_INDICES)

    for chunk in chunks:
        content = chunk.get("content", "")
        for match in _DOLLAR_TICKER_PATTERN.finditer(content):
            ticker = match.group(1)
            if ticker not in _TICKER_FALSE_POSITIVES:
                tickers.add(ticker)

    return frozenset(tickers)


async def resolve_experiment_tools(model_name: str, prompt_type: str) -> tuple[list | None, bool]:
    """Resolve allowed tools and web search configuration for autoresearch experiment variants."""
    if prompt_type == "macro":
        return [], False

    if model_name not in AUTORESEARCH_EXPERIMENT_OWNER_IDS:
        return None, False

    try:
        from autoresearch.prompt_store import get_active_variant

        variant = await get_active_variant()
        selected_tool_names = None
        if variant:
            research_output = variant.get("research_output")
            if isinstance(research_output, dict):
                selected_tool_names = research_output.get("selected_tools")

        if not isinstance(selected_tool_names, list):
            selected_tool_names = [
                "get_portfolio_ledger",
                "get_todays_news_menu",
                "get_ticker_news",
                "get_market_moving_news",
                "web_search",
            ]
            logger.info(
                "No selected_tools found in active variant for experiment agent %s. Defaulting to baseline tools.",
                model_name,
            )

        override_tools = []
        for name in selected_tool_names:
            t_def = tools.CANONICAL_TOOLS_REGISTRY.get(name)
            if t_def:
                override_tools.append(t_def)
            else:
                logger.warning("Active prompt variant specified invalid tool name: %s", name)

        for st in [tools.CALCULATE_BUY_QUANTITY_TOOL, tools.CALCULATE_SELL_QUANTITY_TOOL]:
            if st not in override_tools:
                override_tools.append(st)

        enable_web_search = False
        if tools.WEB_SEARCH_TOOL in override_tools:
            enable_web_search = True
            override_tools = [t for t in override_tools if t != tools.WEB_SEARCH_TOOL]

        return override_tools, enable_web_search

    except Exception as e:
        logger.warning("Failed to fetch selected tools for experiment variant: %s. Using baseline.", e)
        fallback_tools = [
            tools.CANONICAL_TOOLS_REGISTRY["get_portfolio_ledger"],
            tools.CANONICAL_TOOLS_REGISTRY["get_todays_news_menu"],
            tools.CANONICAL_TOOLS_REGISTRY["get_ticker_news"],
            tools.CANONICAL_TOOLS_REGISTRY["get_market_moving_news"],
            tools.CALCULATE_BUY_QUANTITY_TOOL,
            tools.CALCULATE_SELL_QUANTITY_TOOL,
        ]
        return fallback_tools, True


def resolve_web_search_flag(provider: str, override_tools: list | None, enable_web_search: bool) -> bool:
    """Determine native web search flag based on provider defaults if not overridden."""
    if override_tools is not None:
        return enable_web_search

    defaults = {
        "anthropic": ENABLE_ANTHROPIC_WEB_SEARCH,
        "gemini": ENABLE_GEMINI_WEB_SEARCH,
        "openai": ENABLE_OPENAI_WEB_SEARCH,
        "deepseek": ENABLE_DEEPSEEK_WEB_SEARCH,
    }
    return defaults.get(provider, False)


def flatten_messages_for_minimax(messages: list) -> list:
    """Flatten tool loop conversation history into a single user message for MiniMax-M3."""
    system_msg = None
    first_user_msg = None
    history_blocks = []

    for m in messages:
        if not isinstance(m, dict):
            continue
        role = m.get("role")
        content = m.get("content", "")

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


def flatten_messages_for_anthropic(messages: list, preserve_thinking: bool = True) -> list:
    """Flatten nested content blocks in Anthropic conversation history for Instructor compatibility."""
    flattened = []
    for m in messages:
        if not isinstance(m, dict):
            continue
        content = m.get("content", "")
        if isinstance(content, list):
            flat_content = ""
            for part in content:
                if isinstance(part, dict) and "text" in part:
                    flat_content += part["text"]
                elif isinstance(part, dict) and "thinking" in part and preserve_thinking:
                    flat_content += f"\n[Thinking: {part['thinking']}]"
                elif isinstance(part, dict) and "input" in part:
                    flat_content += f"\n[Tool Call: {part['name']}({part['input']})]"
                elif isinstance(part, dict) and "content" in part and "tool_use_id" in part:
                    flat_content += f"\n[Tool Result: {part['content']}]"
            content = flat_content.strip()
        if content:
            flattened.append({"role": m["role"], "content": str(content)})
    return flattened


def prepare_messages_for_provider(messages: list, provider: str, model_name: str) -> list:
    """Shape and normalize message history for final Instructor extraction based on provider."""
    msgs = safe_deepcopy(messages)

    if provider == "deepseek":
        from core.llm.handlers import deepseek

        msgs = deepseek.prepare_messages_for_instructor(msgs)
        if not deepseek.has_valid_content(msgs):
            logger.info("[%s/%s] DeepSeek returned empty content. Requesting JSON output.", provider, model_name)
            msgs.append(
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
        return msgs

    if provider == "minimax":
        return flatten_messages_for_minimax(msgs)

    if provider == "anthropic":
        return flatten_messages_for_anthropic(msgs, preserve_thinking=True)

    return msgs


def build_schema_hint(response_model: Any) -> str:
    """Generate dynamic JSON schema hint string for validation recovery prompts."""
    if hasattr(response_model, "decisions") and hasattr(response_model, "macro_events"):
        return '{"decisions": [{"ticker": "string", "signal": "BUY|SELL|HOLD", ...}], "macro_events": [...]}\n'
    if hasattr(response_model, "decisions"):
        return '{"decisions": [{"ticker": "string", "signal": "BUY|SELL|HOLD", ...}]}\n'
    if hasattr(response_model, "macro_events"):
        return '{"macro_events": [{"event_name": "string", "impact": "BULLISH|BEARISH|NEUTRAL", ...}]}\n'
    return "{}"


def build_provider_extraction_args(
    provider: str,
    model_name: str,
    messages: list,
    response_model: Any,
) -> dict[str, Any]:
    """Construct final extraction arguments for Instructor chat completions."""
    final_args: dict[str, Any] = {
        "model": model_name,
        "response_model": response_model if provider != "gemini" else list[response_model],
        "messages": safe_deepcopy(messages),
        "max_retries": 2,
    }

    if provider == "openai":
        final_args["reasoning_effort"] = "none"

    if provider == "gemini":
        for msg in final_args["messages"]:
            if isinstance(msg, dict) and msg.get("role") == "assistant":
                msg["role"] = "model"

    if provider in ("gemini", "anthropic") and final_args["messages"]:
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

    if provider == "deepseek" and "deepseek" in model_name.lower():
        final_args["extra_body"] = {"thinking": {"type": "enabled"}}

    if provider in ("anthropic", "minimax"):
        final_args["max_tokens"] = 32000
        if messages and messages[0]["role"] == "system":
            sys_content = messages[0]["content"]
            if provider == "anthropic":
                final_args["system"] = [{"type": "text", "text": sys_content, "cache_control": {"type": "ephemeral"}}]
            else:
                final_args["system"] = sys_content
            final_args["messages"] = messages[1:]
        if provider == "anthropic":
            final_args["cache_control"] = {"type": "ephemeral"}
            final_args["thinking"] = {"type": "enabled", "budget_tokens": 2048}

    if provider == "gemini":
        from google.genai import types

        if hasattr(types, "ThinkingConfig"):
            final_args["thinking_config"] = types.ThinkingConfig(thinking_level="high")

    return final_args


async def assemble_analysis_messages(
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
    prompt_type: str = "analysis",
    consensus_context: str = "",
    enable_web_search: bool = False,
) -> list[dict]:
    """Assemble provider-specific prompt messages for analysis or macro evaluation."""
    news_content = format_news_content(chunks, summaries)

    if prompt_type == "macro":
        return PromptFactory.build_macro_analysis_messages(
            provider=provider,
            current_day_info=current_day_info,
            news_content=news_content,
        )

    held_tickers = extract_held_tickers(portfolio_context)
    held_tickers_list = ", ".join(held_tickers) if held_tickers else "None (you have no positions)"

    return await PromptFactory.build_analysis_messages(
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
