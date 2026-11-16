"""Hermetic TDD tests for Recipe Studio LLM caller, tool filtering, and full trace capture."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_completion(
    *,
    content: str = "",
    reasoning_content: str | None = None,
    tool_calls: list[tuple[str, str, str]] | None = None,
) -> SimpleNamespace:
    tcs = [
        SimpleNamespace(
            id=tc_id,
            function=SimpleNamespace(name=name, arguments=args_json),
        )
        for tc_id, name, args_json in (tool_calls or [])
    ]
    msg = SimpleNamespace(content=content, reasoning_content=reasoning_content, tool_calls=tcs)
    return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


@pytest.mark.asyncio
async def test_default_llm_caller_strips_web_search_always_and_non_pit_tools_in_backtest():
    from recipes.llm_caller import default_llm_caller

    captured_tools: list[list[str]] = []

    async def fake_run_tool_loop(
        client, model_id, prompt, tool_schemas, cutoff_date, as_of_utc=None, allowed_tools=None
    ):
        captured_tools.append([t["function"]["name"] for t in tool_schemas])
        assert allowed_tools == {t["function"]["name"] for t in tool_schemas}
        return {"output": "[]", "tool_calls": [], "trace": {"rounds": [], "forced_final_synthesis": False}}

    selected = ["web_search", "run_stock_screener", "get_stock_quote"]
    with patch("recipes.llm_caller.run_tool_loop", side_effect=fake_run_tool_loop):
        await default_llm_caller("Prompt", selected, cutoff_date=None)
        await default_llm_caller("Prompt", selected, cutoff_date="2026-06-05", as_of_utc="2026-06-05T13:30:00+00:00")

    # Live mode: web_search removed, run_stock_screener + get_stock_quote retained
    assert captured_tools[0] == ["run_stock_screener", "get_stock_quote"]
    # Backtest PIT mode: both web_search and non-PIT run_stock_screener filtered out
    assert captured_tools[1] == ["get_stock_quote"]


@pytest.mark.asyncio
async def test_run_tool_loop_forces_final_synthesis_after_5_tool_rounds_and_captures_trace():
    from recipes.llm_caller import run_tool_loop

    responses = [
        _make_completion(
            content="",
            reasoning_content=f"Round {i} thinking",
            tool_calls=[(f"tc-{i}", "get_stock_quote", '{"ticker": "NVDA"}')],
        )
        for i in range(1, 6)
    ]
    # 6th call (tools omitted) returns final trading decision with <think> block
    responses.append(
        _make_completion(
            content='<think>Synthesizing all 5 rounds.</think>\n[{"action": "BUY", "ticker": "NVDA"}]',
            reasoning_content="Final synthesis reasoning",
            tool_calls=[],
        )
    )

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=responses)

    with patch("recipes.llm_caller.execute_tool", new=AsyncMock(return_value="Ticker: NVDA\nPrice: $210.00")):
        res = await run_tool_loop(
            mock_client,
            "auto-strata",
            "Analyze NVDA",
            [{"type": "function", "function": {"name": "get_stock_quote"}}],
            cutoff_date="2026-06-05",
            as_of_utc="2026-06-05T13:30:00+00:00",
        )

    assert mock_client.chat.completions.create.await_count == 6
    final_call_kwargs = mock_client.chat.completions.create.await_args_list[-1].kwargs
    assert "tools" not in final_call_kwargs
    assert "Max tool iterations reached" not in res["output"]
    assert '"BUY"' in res["output"]
    assert res["trace"]["forced_final_synthesis"] is True
    assert len(res["trace"]["rounds"]) == 6
    assert res["trace"]["rounds"][0]["reasoning"] == "Round 1 thinking"
    assert res["trace"]["rounds"][0]["tool_calls"][0]["result"] == "Ticker: NVDA\nPrice: $210.00"
    assert "Synthesizing all 5 rounds." in res["trace"]["rounds"][5]["reasoning"]


def test_pit_safe_tool_names_matches_pit_dispatch_keys():
    from datetime import UTC, datetime

    from recipes.pit_tools import PIT_SAFE_TOOL_NAMES, _build_pit_dispatch

    dispatch = _build_pit_dispatch("NVDA", {}, "2026-06-05", "2026-06-05T13:30:00+00:00", datetime.now(UTC))
    assert set(dispatch.keys()) == set(PIT_SAFE_TOOL_NAMES)


@pytest.mark.asyncio
async def test_run_tool_loop_does_not_leak_think_block_into_output_when_visible_text_empty():
    from recipes.llm_caller import run_tool_loop

    responses = [
        _make_completion(
            content="<think>Considering BUY NVDA, wait no—insufficient data.</think>",
            reasoning_content=None,
            tool_calls=[],
        ),
        _make_completion(
            content="<think>Still thinking about BUY NVDA.</think>",
            reasoning_content=None,
            tool_calls=[],
        ),
    ]
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=responses)

    res = await run_tool_loop(mock_client, "auto-strata", "Analyze NVDA", [], cutoff_date=None)

    assert "BUY NVDA" not in res["output"]
    assert "<think>" not in res["output"]
    assert "Considering BUY NVDA" in res["trace"]["rounds"][0]["reasoning"]


@pytest.mark.asyncio
async def test_run_tool_loop_blocks_disallowed_tools_and_non_dict_json_args_at_dispatch():
    from recipes.llm_caller import run_tool_loop

    responses = [
        _make_completion(
            content="",
            tool_calls=[
                ("tc-bad-tool", "web_search", '{"query": "NVDA"}'),
                ("tc-bad-args", "get_stock_quote", "null"),
            ],
        ),
        _make_completion(content="[]", tool_calls=[]),
    ]
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=responses)
    mock_execute = AsyncMock(return_value="Ticker: SPY\nPrice: $500.00")

    with patch("recipes.llm_caller.execute_tool", new=mock_execute):
        res = await run_tool_loop(
            mock_client,
            "auto-strata",
            "Analyze NVDA",
            [{"type": "function", "function": {"name": "get_stock_quote"}}],
            cutoff_date=None,
        )

    assert mock_execute.await_count == 1
    assert mock_execute.await_args_list[0].args[0] == "get_stock_quote"
    assert mock_execute.await_args_list[0].args[1] == {}
    round1_calls = res["trace"]["rounds"][0]["tool_calls"]
    assert "not allowed" in round1_calls[0]["result"].lower()
    assert round1_calls[1]["args"] == {}


@pytest.mark.asyncio
async def test_default_llm_caller_closes_openai_client():
    from recipes.llm_caller import default_llm_caller

    fake_client = MagicMock()
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("recipes.llm_caller.AsyncOpenAI", return_value=fake_client),
        patch(
            "recipes.llm_caller.run_tool_loop",
            new=AsyncMock(return_value={"output": "[]", "tool_calls": [], "trace": {"rounds": []}}),
        ),
    ):
        await default_llm_caller("Prompt", ["get_stock_quote"], cutoff_date=None)

    fake_client.__aenter__.assert_awaited_once()
    fake_client.__aexit__.assert_awaited_once()
