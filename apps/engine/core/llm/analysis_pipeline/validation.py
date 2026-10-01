"""Tool enforcement, history scanning, portfolio ownership validation, and attribution tracing vertical slice island."""

import json
import logging
from typing import Any

from core.llm.analysis_pipeline.prompt_assembly import extract_held_tickers

logger = logging.getLogger("engine")


def scan_history_for_tools(messages: list, ticker: str) -> dict[str, bool]:
    """Scan message history for quantity calculation tool calls related to a specific ticker.

    Supports OpenAI tool_calls, Anthropic content blocks, and Gemini function calls.
    """
    ticker = ticker.strip().upper()
    buy_tool_found = False
    sell_tool_found = False

    def _record_call(name: Any, args: Any) -> None:
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

    def _extract_calls(value: Any) -> list[tuple[Any, Any]]:
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


def get_history_tool_calls_diagnostic(messages: list) -> list[str]:
    """Extract a diagnostic summary list of all tool calls made in the message history."""
    tool_calls = []

    def _extract(value: Any) -> list[tuple[Any, Any]]:
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


def detect_missing_tool_decisions(final_resp: Any, unflattened_messages: list) -> list:
    """Identify BUY or SELL decisions that are missing required quantity calculation tool calls."""
    if not hasattr(final_resp, "decisions"):
        return []

    missing = []
    for d in final_resp.decisions:
        if d.signal in ["BUY", "SELL"]:
            results = scan_history_for_tools(unflattened_messages, d.ticker)
            if (d.signal == "BUY" and not results["buy_tool_found"]) or (
                d.signal == "SELL" and not results["sell_tool_found"]
            ):
                missing.append(d)

    return missing


def build_tool_correction_message(missing_decisions: list) -> dict[str, str]:
    """Build user correction message prompting the agent to execute missing mandatory tool calls."""
    correction_lines = []
    for d in missing_decisions:
        tool_name = "calculate_buy_quantity" if d.signal == "BUY" else "calculate_sell_quantity"
        correction_lines.append(
            f"- You recommended {d.signal} {d.ticker} but did NOT call `{tool_name}`. "
            f"You MUST call `{tool_name}(ticker='{d.ticker}', percentage=...)` NOW before providing your final response. "
            f"Your trade will be REJECTED if this tool call is missing."
        )

    return {
        "role": "user",
        "content": (
            "CORRECTION REQUIRED: The following trades are missing mandatory tool calls:\n"
            + "\n".join(correction_lines)
            + "\nPlease execute the required tool calls NOW, then re-output your complete decisions JSON."
        ),
    }


def enforce_tool_call_history(
    final_resp: Any,
    unflattened_messages: list,
    provider: str,
    model_name: str,
) -> None:
    """Audit decisions against actual message history and override self-reported tool calls."""
    if not hasattr(final_resp, "decisions"):
        return

    for decision in final_resp.decisions:
        if decision.signal in ["BUY", "SELL"]:
            results = scan_history_for_tools(unflattened_messages, decision.ticker)
            calls_found = get_history_tool_calls_diagnostic(unflattened_messages)

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


def validate_portfolio_holdings(
    final_resp: Any,
    portfolio_context: str,
    provider: str,
    model_name: str,
) -> None:
    """Pre-analysis portfolio validation: convert SELL signals for non-held tickers to HOLD."""
    if not hasattr(final_resp, "decisions"):
        return

    held_tickers = extract_held_tickers(portfolio_context)
    held_tickers_upper = [t.upper() for t in held_tickers]
    validated_decisions = []

    for decision in final_resp.decisions:
        if decision.signal == "SELL" and decision.ticker.upper() not in held_tickers_upper:
            logger.warning(
                "[%s/%s] PRE-ANALYSIS VALIDATION: SELL signal for %s rejected - ticker not in portfolio. Held: %s",
                provider,
                model_name,
                decision.ticker,
                held_tickers,
            )
            decision.signal = "HOLD"
            decision.reasoning = (
                f"REJECTED_OWNERSHIP: Attempted to sell {decision.ticker} but ticker is not held. "
                f"Original reasoning: {decision.reasoning[:200]}"
            )
        validated_decisions.append(decision)

    final_resp.decisions = validated_decisions


def attach_attribution_trace(final_resp: Any, chunks: list[dict], unflattened_messages: list) -> None:
    """Attach execution trace to decisions for factual attribution logging."""
    if hasattr(final_resp, "decisions") and final_resp.decisions:
        from attribution.trace import attach_trace_to_decisions, build_execution_trace

        trace = build_execution_trace(chunks, unflattened_messages)
        attach_trace_to_decisions(final_resp.decisions, trace)
