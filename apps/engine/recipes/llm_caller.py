"""LLM endpoint routing and tool-loop execution for Recipe Studio runners."""

from __future__ import annotations

import inspect
import json
import os
from collections.abc import Awaitable, Callable
from typing import Any

from openai import AsyncOpenAI

from core.config import logger
from core.llm.handlers.base import execute_tool
from core.llm.tools import CANONICAL_TOOLS_REGISTRY

LLMCaller = Callable[[str, list[str], str | None], Awaitable[dict[str, Any]]]


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


async def run_tool_loop(
    client: AsyncOpenAI,
    model_id: str,
    prompt: str,
    tool_schemas: list[dict[str, Any]],
    cutoff_date: str | None,
    as_of_utc: str | None = None,
) -> dict[str, Any]:
    """Run up to 4 OpenAI-compatible tool-calling iterations and return final text + trace."""
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
    for _ in range(4):
        kwargs: dict[str, Any] = {"model": model_id, "messages": messages, "temperature": 0.1}
        if tool_schemas:
            kwargs["tools"] = tool_schemas
        resp = await client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message
        tool_calls = getattr(msg, "tool_calls", None) or []
        if not tool_calls:
            return {"output": msg.content or "", "tool_calls": tool_traces}

        messages.append(
            {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in tool_calls
                ],
            }
        )
        for tc in tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            tool_traces.append(f"{tc.function.name}({json.dumps(args)})")
            tool_result = await execute_tool(
                tc.function.name,
                args,
                model_name=model_id,
                cutoff_date=cutoff_date,
                as_of_utc=as_of_utc,
                pit_mode=bool(cutoff_date or as_of_utc),
            )
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": str(tool_result)[:4000]})

    return {"output": "Max tool iterations reached without final answer.", "tool_calls": tool_traces}


async def default_llm_caller(
    prompt: str,
    selected_tools: list[str],
    cutoff_date: str | None = None,
    openrouter_key: str | None = None,
    model: str = "auto-strata",
    as_of_utc: str | None = None,
) -> dict[str, Any]:
    """Execute a single Stage with OpenAI-compatible tool calling and Strata->Proxy failover."""
    tool_schemas = [CANONICAL_TOOLS_REGISTRY[t] for t in selected_tools if t in CANONICAL_TOOLS_REGISTRY]
    endpoints = llm_endpoints(openrouter_key, model)
    last_exc: Exception | None = None
    for idx, (base_url, api_key, model_id) in enumerate(endpoints):
        client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=90)
        try:
            return await run_tool_loop(client, model_id, prompt, tool_schemas, cutoff_date, as_of_utc=as_of_utc)
        except Exception as exc:
            last_exc = exc
            if idx + 1 < len(endpoints):
                logger.warning("Recipe LLM endpoint %s failed (%s); failing over to next endpoint", base_url, exc)
                continue
            raise
    if last_exc:
        raise last_exc
    return {"output": "", "tool_calls": []}


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
