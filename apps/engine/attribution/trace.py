"""Execution trace attribution module.

Captures factual system-level provenance for trading decisions, recording
the batch of newsletters present in context and the sequence of tools called
by the LLM during analysis.
"""

import json
from datetime import UTC, datetime
from typing import Any, TypedDict


class ToolCallRecord(TypedDict):
    """Factual record of an individual tool execution."""

    tool: str
    args: dict[str, Any]
    ticker: str | None


class NewsletterRecord(TypedDict):
    """Metadata for an ingested newsletter chunk present in context."""

    source_id: str
    sender: str | None
    subject: str | None


class ExecutionTrace(TypedDict):
    """Complete provenance trace of the decision environment."""

    active_source_ids: list[str]
    newsletters: list[NewsletterRecord]
    tools_called: list[ToolCallRecord]
    captured_at: str


def _extract_ticker_from_args(args: dict[str, Any]) -> str | None:
    """Extract and normalize a ticker symbol if present in tool arguments."""
    ticker = args.get("ticker")
    if ticker and isinstance(ticker, str):
        cleaned = ticker.strip().upper()
        if cleaned:
            return cleaned
    return None


def extract_tool_trace_from_messages(messages: list[dict[str, Any]]) -> list[ToolCallRecord]:
    """Extract tool calls from LLM multi-turn message history.

    Supports OpenAI, Anthropic, Gemini, and DeepSeek message structures.

    Args:
        messages: List of message dictionaries from the tool loop.

    Returns:
        List of ToolCallRecord dictionaries.
    """
    records: list[ToolCallRecord] = []

    for msg in messages:
        if not isinstance(msg, dict):
            continue

        # 1. OpenAI / DeepSeek format: tool_calls on assistant message
        tool_calls = msg.get("tool_calls")
        if tool_calls and isinstance(tool_calls, list):
            for tc in tool_calls:
                func = tc.get("function") if isinstance(tc, dict) else getattr(tc, "function", None)
                if not func:
                    continue

                name = func.get("name") if isinstance(func, dict) else getattr(func, "name", None)
                raw_args = func.get("arguments") if isinstance(func, dict) else getattr(func, "arguments", {})

                if isinstance(raw_args, str):
                    try:
                        parsed_args = json.loads(raw_args)
                    except Exception:
                        parsed_args = {"raw": raw_args}
                elif isinstance(raw_args, dict):
                    parsed_args = raw_args
                else:
                    parsed_args = {}

                if name:
                    records.append(
                        {
                            "tool": str(name),
                            "args": parsed_args,
                            "ticker": _extract_ticker_from_args(parsed_args),
                        }
                    )

        # 2. Anthropic format: content is a list of blocks with type='tool_use'
        content = msg.get("content")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    name = block.get("name")
                    input_args = block.get("input")
                    parsed_args = input_args if isinstance(input_args, dict) else {}
                    if name:
                        records.append(
                            {
                                "tool": str(name),
                                "args": parsed_args,
                                "ticker": _extract_ticker_from_args(parsed_args),
                            }
                        )

    return records


def build_execution_trace(
    chunks: list[dict[str, Any]],
    messages: list[dict[str, Any]],
) -> ExecutionTrace:
    """Compile input newsletter chunks and message tool calls into an ExecutionTrace.

    Args:
        chunks: List of newsletter chunk dictionaries provided to the model.
        messages: Unflattened message history capturing all tool turns.

    Returns:
        An ExecutionTrace dictionary.
    """
    newsletters: list[NewsletterRecord] = []
    active_source_ids: list[str] = []

    for c in chunks:
        if not isinstance(c, dict):
            continue
        sid = c.get("source_id")
        if sid:
            active_source_ids.append(str(sid))
            newsletters.append(
                {
                    "source_id": str(sid),
                    "sender": c.get("sender"),
                    "subject": c.get("subject"),
                }
            )

    tools_called = extract_tool_trace_from_messages(messages)

    return {
        "active_source_ids": active_source_ids,
        "newsletters": newsletters,
        "tools_called": tools_called,
        "captured_at": datetime.now(UTC).isoformat(),
    }


def attach_trace_to_decisions(decisions: list[Any], trace: ExecutionTrace) -> None:
    """Attach the execution trace to the metadata of each decision in the batch.

    Args:
        decisions: List of DecisionObject instances.
        trace: The ExecutionTrace to attach.
    """
    for d in decisions:
        current_meta = getattr(d, "metadata", None)
        if current_meta is None or not isinstance(current_meta, dict):
            current_meta = {}
        current_meta["execution_trace"] = trace
        d.metadata = current_meta
