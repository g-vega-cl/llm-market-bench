"""LLM endpoint routing, PIT tool filtering, and full-trace tool-loop execution."""

from __future__ import annotations

import inspect
import json
import os
import re
from collections.abc import Awaitable, Callable
from typing import Any

from openai import AsyncOpenAI

from core.config import logger
from core.llm.handlers.base import execute_tool
from core.llm.tools import CANONICAL_TOOLS_REGISTRY
from recipes.pit_tools import PIT_SAFE_TOOL_NAMES

LLMCaller = Callable[[str, list[str], str | None], Awaitable[dict[str, Any]]]

RECIPE_DISABLED_TOOLS: frozenset[str] = frozenset({"web_search"})
MAX_TOOL_ROUNDS = 5
_TOOL_RESULT_TRACE_LIMIT = 4000
_THINK_BLOCK_RE = re.compile(r"<think>([\s\S]*?)</think>", re.IGNORECASE)


def filter_recipe_tool_names(selected_tools: list[str], *, pit_mode: bool) -> list[str]:
    """Filter Recipe Studio tools: never allow web_search, and restrict backtests to PIT-safe tools."""
    allowed: list[str] = []
    for name in selected_tools:
        if name in RECIPE_DISABLED_TOOLS or name not in CANONICAL_TOOLS_REGISTRY:
            continue
        if pit_mode and name not in PIT_SAFE_TOOL_NAMES:
            continue
        if name not in allowed:
            allowed.append(name)
    return allowed


def _extract_reasoning_and_text(msg: Any) -> tuple[str, str]:
    """Separate reasoning_content / <think> blocks from visible assistant output."""
    raw_content = str(getattr(msg, "content", None) or "")
    think_chunks = [chunk.strip() for chunk in _THINK_BLOCK_RE.findall(raw_content) if chunk.strip()]
    visible_text = _THINK_BLOCK_RE.sub("", raw_content).strip()

    explicit_reasoning = getattr(msg, "reasoning_content", None) or getattr(msg, "reasoning", None) or ""
    reasoning_parts = [str(explicit_reasoning).strip(), *think_chunks]
    reasoning = "\n\n".join(part for part in reasoning_parts if part)
    return reasoning, visible_text


def _build_assistant_history_entry(msg: Any, tool_calls: list[Any]) -> dict[str, Any]:
    """Build OpenAI-compatible assistant message preserving reasoning_content when present."""
    entry: dict[str, Any] = {
        "role": "assistant",
        "content": getattr(msg, "content", None) or "",
        "tool_calls": [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in tool_calls
        ],
    }
    raw_reasoning = getattr(msg, "reasoning_content", None)
    if raw_reasoning:
        entry["reasoning_content"] = raw_reasoning
    return entry


def llm_endpoints(openrouter_key: str | None, model: str) -> list[tuple[str, str, str]]:
    """Resolve prioritized (base_url, api_key, model_id) endpoints with Strata->Proxy failover."""
    if openrouter_key:
        model_id = "deepseek/deepseek-chat" if model == "auto-strata" else model
        return [("https://openrouter.ai/api/v1", openrouter_key, model_id)]
    proxy_key = os.getenv("FREE_PROXY_MASTER_KEY") or os.getenv("STRATA_API_KEY", "local")
    strata_url = os.getenv("STRATA_BASE_URL", "").strip()
    proxy_url = os.getenv("FREE_LLM_PROXY_URL", "https://llm.clvg.uk/v1").strip()
    endpoints: list[tuple[str, str, str]] = []
    if strata_url:
        endpoints.append((strata_url, proxy_key, model))
    if proxy_url and proxy_url != strata_url:
        endpoints.append((proxy_url, proxy_key, model))
    return endpoints or [("https://llm.clvg.uk/v1", proxy_key, model)]


async def _execute_round_tools(
    tool_calls: list[Any],
    *,
    allowed_tools: set[str],
    model_id: str,
    cutoff_date: str | None,
    as_of_utc: str | None,
    messages: list[dict[str, Any]],
    tool_traces: list[str],
) -> list[dict[str, Any]]:
    """Run all permitted tool calls in one assistant turn and record structured + string traces."""
    round_calls: list[dict[str, Any]] = []
    for tc in tool_calls:
        try:
            parsed = json.loads(tc.function.arguments or "{}")
        except json.JSONDecodeError:
            parsed = {}
        args: dict[str, Any] = parsed if isinstance(parsed, dict) else {}
        fn_name = str(getattr(tc.function, "name", "") or "")
        tool_traces.append(f"{fn_name}({json.dumps(args)})")

        if fn_name in RECIPE_DISABLED_TOOLS or (allowed_tools and fn_name not in allowed_tools):
            clipped = f"Error: Tool '{fn_name}' is not allowed in this Recipe Studio run."
        else:
            tool_result = await execute_tool(
                fn_name,
                args,
                model_name=model_id,
                cutoff_date=cutoff_date,
                as_of_utc=as_of_utc,
                pit_mode=bool(cutoff_date or as_of_utc),
            )
            clipped = str(tool_result)[:_TOOL_RESULT_TRACE_LIMIT]

        messages.append({"role": "tool", "tool_call_id": tc.id, "content": clipped})
        round_calls.append({"name": fn_name, "args": args, "result": clipped})
    return round_calls


async def _run_final_synthesis(
    client: AsyncOpenAI,
    model_id: str,
    messages: list[dict[str, Any]],
    rounds: list[dict[str, Any]],
) -> str:
    """Force one tool-free synthesis turn if the model exhausted MAX_TOOL_ROUNDS."""
    synthesis_messages = [
        *messages,
        {
            "role": "user",
            "content": (
                "Tool budget reached. Using only the data already retrieved above, provide your final "
                "BUY/EXIT JSON array (or [] to HOLD) immediately with no further tool calls."
            ),
        },
    ]
    resp = await client.chat.completions.create(model=model_id, messages=synthesis_messages, temperature=0.1)
    msg = resp.choices[0].message
    reasoning, visible_text = _extract_reasoning_and_text(msg)
    final_text = visible_text
    rounds.append(
        {
            "round": len(rounds) + 1,
            "reasoning": reasoning,
            "assistant_text": final_text,
            "tool_calls": [],
        }
    )
    return final_text


async def run_tool_loop(
    client: AsyncOpenAI,
    model_id: str,
    prompt: str,
    tool_schemas: list[dict[str, Any]],
    cutoff_date: str | None,
    as_of_utc: str | None = None,
    allowed_tools: set[str] | None = None,
) -> dict[str, Any]:
    """Run up to MAX_TOOL_ROUNDS tool iterations (+ forced synthesis) and return output + full trace."""
    permitted = (
        set(allowed_tools)
        if allowed_tools is not None
        else {t["function"]["name"] for t in tool_schemas if t.get("function", {}).get("name")}
    ) - set(RECIPE_DISABLED_TOOLS)
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "You are a quantitative Long-Only trading strategy agent. Use the provided tools when helpful "
                "and finish with clear BUY/EXIT ticker decisions (or HOLD / []) as JSON or concise text."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    tool_traces: list[str] = []
    rounds: list[dict[str, Any]] = []
    for round_idx in range(1, MAX_TOOL_ROUNDS + 1):
        kwargs: dict[str, Any] = {"model": model_id, "messages": messages, "temperature": 0.1}
        if tool_schemas:
            kwargs["tools"] = tool_schemas
        resp = await client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message
        reasoning, visible_text = _extract_reasoning_and_text(msg)
        tool_calls = getattr(msg, "tool_calls", None) or []

        if not tool_calls:
            final_text = visible_text
            rounds.append(
                {
                    "round": round_idx,
                    "reasoning": reasoning,
                    "assistant_text": final_text,
                    "tool_calls": [],
                }
            )
            return {
                "output": final_text,
                "tool_calls": tool_traces,
                "trace": {"rounds": rounds, "forced_final_synthesis": False},
            }

        messages.append(_build_assistant_history_entry(msg, tool_calls))
        round_calls = await _execute_round_tools(
            tool_calls,
            allowed_tools=permitted,
            model_id=model_id,
            cutoff_date=cutoff_date,
            as_of_utc=as_of_utc,
            messages=messages,
            tool_traces=tool_traces,
        )
        rounds.append(
            {
                "round": round_idx,
                "reasoning": reasoning,
                "assistant_text": visible_text,
                "tool_calls": round_calls,
            }
        )

    final_text = await _run_final_synthesis(client, model_id, messages, rounds)
    return {
        "output": final_text,
        "tool_calls": tool_traces,
        "trace": {"rounds": rounds, "forced_final_synthesis": True},
    }


async def default_llm_caller(
    prompt: str,
    selected_tools: list[str],
    cutoff_date: str | None = None,
    openrouter_key: str | None = None,
    model: str = "auto-strata",
    as_of_utc: str | None = None,
) -> dict[str, Any]:
    """Execute a single Stage with OpenAI-compatible tool calling and Strata->Proxy failover."""
    pit_mode = bool(cutoff_date or as_of_utc)
    allowed_names = filter_recipe_tool_names(selected_tools, pit_mode=pit_mode)
    tool_schemas = [CANONICAL_TOOLS_REGISTRY[t] for t in allowed_names]
    endpoints = llm_endpoints(openrouter_key, model)
    last_exc: Exception | None = None
    for idx, (base_url, api_key, model_id) in enumerate(endpoints):
        try:
            async with AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=90) as client:
                return await run_tool_loop(
                    client,
                    model_id,
                    prompt,
                    tool_schemas,
                    cutoff_date,
                    as_of_utc=as_of_utc,
                    allowed_tools=set(allowed_names),
                )
        except Exception as exc:
            last_exc = exc
            if idx + 1 < len(endpoints):
                logger.warning("Recipe LLM endpoint %s failed (%s); failing over to next endpoint", base_url, exc)
                continue
            raise
    if last_exc:
        raise last_exc
    return {"output": "", "tool_calls": [], "trace": {"rounds": [], "forced_final_synthesis": False}}


async def invoke_llm(
    caller: LLMCaller,
    prompt: str,
    selected_tools: list[str],
    cutoff_date: str | None,
    as_of_utc: str | None = None,
) -> dict[str, Any]:
    """Call LLMCaller while passing as_of_utc only if supported by the callable."""
    params = inspect.signature(caller).parameters
    if "as_of_utc" in params:
        return await caller(prompt, selected_tools, cutoff_date, as_of_utc=as_of_utc)  # type: ignore[call-arg]
    return await caller(prompt, selected_tools, cutoff_date)
