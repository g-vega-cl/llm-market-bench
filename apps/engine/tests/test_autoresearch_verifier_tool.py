"""Unit tests for the track_claude verifier inspection tool and autoresearcher tool loop."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autoresearch import researcher
from core.llm import prompts, tools
from core.llm.handlers import base


@pytest.mark.asyncio
async def test_inspect_verifier_rules_tool_track_isolation():
    """Verify tool strictly rejects execution for non-Claude tracks."""
    # track_default should be rejected
    res_default = await tools.execute_inspect_verifier_rules_tool(track_id="track_default")
    assert (
        "strictly scoped to 'track_claude'" in res_default.lower()
        or "only available for track_claude" in res_default.lower()
    )
    assert prompts.VERIFIER_SYSTEM_PROMPT not in res_default

    # track_openai should also be rejected
    res_openai = await tools.execute_inspect_verifier_rules_tool(track_id="track_openai")
    assert "track_claude" in res_openai.lower()
    assert prompts.VERIFIER_SYSTEM_PROMPT not in res_openai


@pytest.mark.asyncio
async def test_inspect_verifier_rules_tool_claude_track_payload():
    """Verify tool returns verbatim verifier SOP, rejected decisions, and strategic nudge."""
    mock_sb = MagicMock()
    mock_res = MagicMock()
    mock_res.data = [
        {
            "id": "dec-1",
            "ticker": "NVDA",
            "signal": "BUY",
            "status": "REJECTED_VERIFICATION",
            "reasoning": "Strong hyperscaler demand and datacenter growth momentum.",
            "model_name": "claude-haiku-4-5",
            "metadata": {"reason": "DCF intrinsic valuation indicates 25% downside; trailing multiple is stretched."},
            "created_at": "2026-09-01T10:00:00Z",
        },
        {
            "id": "dec-2",
            "ticker": "TSLA",
            "signal": "BUY",
            "status": "REJECTED_VERIFICATION",
            "reasoning": "Breakout above 50-day moving average on robotaxi sentiment.",
            "model_name": "deepseek-v4-flash",
            "metadata": {"reason": "Stock moved >6% in last 24h; priced in per SOP check 1."},
            "created_at": "2026-09-02T11:00:00Z",
        },
    ]

    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.in_.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.execute = AsyncMock(return_value=mock_res)
    mock_sb.table.return_value = chain

    with patch("core.llm.tools.get_async_supabase_client", return_value=mock_sb):
        output = await tools.execute_inspect_verifier_rules_tool(track_id="track_claude", limit=5)

    # 1. Contains verbatim verifier SOP
    assert prompts.VERIFIER_SYSTEM_PROMPT in output
    assert "Is this priced in?" in output
    assert "Intrinsic Valuation & Multiple Audit" in output

    # 2. Contains rejected trades details
    assert "NVDA" in output
    assert "TSLA" in output
    assert "claude-haiku-4-5" in output
    assert "DCF intrinsic valuation indicates 25% downside" in output
    assert "Stock moved >6% in last 24h" in output

    # 3. Contains strategic nudge for autoresearcher
    assert "STRATEGIC NUDGE" in output or "nudge" in output.lower()
    assert "track_claude" in output


@pytest.mark.asyncio
async def test_inspect_verifier_rules_tool_claude_track_zero_rejections():
    """Verify tool returns SOP and fallback notice when no rejections exist."""
    mock_sb = MagicMock()
    mock_res = MagicMock()
    mock_res.data = []

    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.in_.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.execute = AsyncMock(return_value=mock_res)
    mock_sb.table.return_value = chain

    with patch("core.llm.tools.get_async_supabase_client", return_value=mock_sb):
        output = await tools.execute_inspect_verifier_rules_tool(track_id="track_claude", limit=5)

    # Contains SOP and nudge even with zero rejections
    assert prompts.VERIFIER_SYSTEM_PROMPT in output
    assert "No recent verifier rejections recorded" in output
    assert "track_claude" in output


@pytest.mark.asyncio
async def test_base_execute_tool_dispatches_inspect_verifier_rules():
    """Verify handler base.execute_tool properly dispatches inspect_verifier_rules_and_rejections."""
    with patch("core.llm.tools.execute_inspect_verifier_rules_tool", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = "Mocked Verifier Tool Output"
        res = await base.execute_tool(
            "inspect_verifier_rules_and_rejections",
            {"limit": 3, "ticker": "MSFT"},
            model_name="deepseek-v4-flash",
            track_id="track_claude",
        )
        assert res == "Mocked Verifier Tool Output"
        mock_exec.assert_called_once_with(limit=3, ticker="MSFT", track_id="track_claude")


@pytest.mark.asyncio
async def test_autoresearcher_tool_loop_for_track_claude():
    """Verify researcher.run_research executes run_tool_loop with inspect_verifier_rules only for track_claude."""
    mock_client = MagicMock()
    mock_raw_client = MagicMock()
    mock_client.client = mock_raw_client

    mock_result = researcher.PromptResearchResult(
        new_prompt_text="New Prompt",
        selected_tools=["get_stock_quote"],
        selected_prompt_blocks=[],
        change_description="Test change",
        experiment_type="incremental",
        research_reasoning="Reasoning",
        confidence=90,
    )
    mock_client.chat.completions.create = AsyncMock(return_value=mock_result)

    with (
        patch("autoresearch.researcher._get_client_and_provider_for_model", return_value=(mock_client, "deepseek")),
        patch("autoresearch.tools.query_trade_postmortems", new_callable=AsyncMock, return_value=""),
        patch("core.llm.handlers.deepseek.run_tool_loop", new_callable=AsyncMock) as mock_deepseek_tool_loop,
    ):
        # 1. Run on track_claude -> tool loop should be called with inspect_verifier_rules_and_rejections tool
        await researcher.run_research(report="Report", track_id="track_claude")
        assert mock_deepseek_tool_loop.call_count == 1
        call_kwargs = mock_deepseek_tool_loop.call_args.kwargs
        override_tools = call_kwargs.get("override_tools") or []
        tool_names = [t.get("function", {}).get("name") for t in override_tools]
        assert "inspect_verifier_rules_and_rejections" in tool_names

        # 2. Run on track_default -> verifier tool should NOT be passed
        mock_deepseek_tool_loop.reset_mock()
        await researcher.run_research(report="Report", track_id="track_default")
        if mock_deepseek_tool_loop.call_count > 0:
            call_kwargs = mock_deepseek_tool_loop.call_args.kwargs
            override_tools = call_kwargs.get("override_tools") or []
            tool_names = [t.get("function", {}).get("name") for t in override_tools]
            assert "inspect_verifier_rules_and_rejections" not in tool_names
