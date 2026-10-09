"""Reproduction and regression tests for Claude Haiku 5.5 migration.

Verifies:
1. Adaptive thinking and output_config effort parameter for Haiku 5.5 in Anthropic handler.
2. Preservation of empty / signature-only thinking blocks across multi-turn tool loops.
3. Adaptive thinking configuration in prompt assembly extraction args and verification.
4. Auto-research continuity: claude-haiku-5-5 resolves to track_claude and inherits active prompt variants.
5. Models configuration contract: claude-haiku-5-5 is configured as ANTHROPIC_MODEL,
   included in track_claude, and enabled for skeptical verification.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.llm.handlers.anthropic import get_anthropic_thinking_kwargs, run_tool_loop


def test_get_anthropic_thinking_kwargs_for_haiku_55():
    """Verify get_anthropic_thinking_kwargs configures adaptive thinking and effort for Haiku 5.5."""
    kwargs = get_anthropic_thinking_kwargs("claude-haiku-5-5", budget_tokens=2048, effort="medium")
    assert kwargs.get("thinking") == {"type": "adaptive", "display": "summarized"}
    assert kwargs.get("output_config") == {"effort": "medium"}

    # Legacy Claude Haiku 4.5 / Sonnet uses enabled with budget_tokens
    legacy_kwargs = get_anthropic_thinking_kwargs("claude-haiku-4-5", budget_tokens=2048)
    assert legacy_kwargs.get("thinking") == {"type": "enabled", "budget_tokens": 2048}
    assert "output_config" not in legacy_kwargs


@pytest.mark.asyncio
async def test_run_tool_loop_adaptive_thinking_for_haiku_55():
    """Verify run_tool_loop sends adaptive thinking and output_config for claude-haiku-5-5."""
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(type="text", text="Analysis complete.")]
    mock_resp.usage = None
    mock_client.messages.create = AsyncMock(return_value=mock_resp)

    messages = [{"role": "user", "content": "Analyze ticker AAPL."}]
    await run_tool_loop(
        raw_client=mock_client,
        model_name="claude-haiku-5-5",
        messages=messages,
        max_tool_steps=1,
    )

    assert mock_client.messages.create.call_count == 1
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs.get("model") == "claude-haiku-5-5"
    assert call_kwargs.get("thinking") == {"type": "adaptive", "display": "summarized"}
    assert call_kwargs.get("output_config") == {"effort": "medium"}


@pytest.mark.asyncio
async def test_run_tool_loop_preserves_empty_thinking_blocks():
    """Verify run_tool_loop preserves thinking blocks even when thinking text is empty (signature only)."""
    mock_client = MagicMock()
    # Simulate Haiku 5.5 returning a thinking block with empty string and signature, plus a tool call
    mock_thinking = MagicMock(type="thinking", thinking="", signature="sig_haiku_55_abc")
    mock_tool = MagicMock(
        type="tool_use",
        id="tool_1",
        name="get_market_health_barometer",
        input={},
    )
    mock_resp_1 = MagicMock(content=[mock_thinking, mock_tool], usage=None)

    mock_resp_2 = MagicMock(content=[MagicMock(type="text", text="Decision final.")], usage=None)
    mock_client.messages.create = AsyncMock(side_effect=[mock_resp_1, mock_resp_2])

    messages = [{"role": "user", "content": "Evaluate portfolio risk."}]

    with patch("core.llm.handlers.base.execute_tool", new=AsyncMock(return_value="Healthy")):
        await run_tool_loop(
            raw_client=mock_client,
            model_name="claude-haiku-5-5",
            messages=messages,
            max_tool_steps=2,
        )

    # First assistant message in messages history must preserve the thinking block
    assistant_msgs = [m for m in messages if isinstance(m, dict) and m.get("role") == "assistant"]
    assert len(assistant_msgs) >= 1
    content_blocks = assistant_msgs[0]["content"]
    thinking_blocks = [b for b in content_blocks if isinstance(b, dict) and b.get("type") == "thinking"]

    assert len(thinking_blocks) == 1
    assert thinking_blocks[0]["thinking"] == ""
    assert thinking_blocks[0]["signature"] == "sig_haiku_55_abc"


def test_build_provider_extraction_args_adaptive_thinking():
    """Verify build_provider_extraction_args configures adaptive thinking for Haiku 5.5."""
    from pydantic import BaseModel

    from core.llm.analysis_pipeline.prompt_assembly import build_provider_extraction_args

    class DummyResponse(BaseModel):
        summary: str

    messages = [
        {"role": "system", "content": "You are a hedge fund analyst."},
        {"role": "user", "content": "Analyze market."},
        {"role": "assistant", "content": "Preliminary notes."},
    ]

    args = build_provider_extraction_args(
        provider="anthropic",
        model_name="claude-haiku-5-5",
        messages=messages,
        response_model=DummyResponse,
    )

    assert args.get("thinking") == {"type": "adaptive", "display": "summarized"}
    assert args.get("output_config") == {"effort": "medium"}


@pytest.mark.asyncio
async def test_verify_trading_decision_adaptive_thinking():
    """Verify verify_trading_decision passes adaptive thinking for claude-haiku-5-5."""
    from core.llm.verification import verify_trading_decision
    from core.models import DecisionObject, VerificationResult

    decision = DecisionObject(
        signal="BUY",
        confidence=80,
        reasoning="Strong earnings momentum",
        ticker="AAPL",
        source_id="src_1",
        price=150.0,
        model_provider="anthropic",
        model_name="claude-haiku-5-5",
    )

    mock_result = VerificationResult(
        status="APPROVED",
        verification_reasoning="Sound fundamentals.",
        confidence_score=85,
    )

    with patch("core.llm.clients.CLIENT_FACTORIES") as mock_factories:
        mock_factory = MagicMock()
        mock_client = MagicMock()
        mock_instructor_client = MagicMock()
        mock_completions = MagicMock()
        mock_completions.create = AsyncMock(return_value=mock_result)
        mock_instructor_client.completions = mock_completions
        mock_client.chat = mock_instructor_client
        mock_client.client = MagicMock()
        mock_factory.return_value = mock_client
        mock_factories.get.return_value = mock_factory

        with (
            patch("core.llm.handlers.anthropic.run_tool_loop", new_callable=AsyncMock),
            patch("core.llm.clients.close_client", new_callable=AsyncMock),
        ):
            res = await verify_trading_decision(
                decision=decision,
                portfolio_context="Cash: $10,000",
                aggregated_context="Market context",
            )
            assert res.status == "APPROVED"

            assert mock_completions.create.call_count == 1
            call_kwargs = mock_completions.create.call_args.kwargs
            assert call_kwargs.get("model") == "claude-haiku-5-5"
            assert call_kwargs.get("thinking") == {"type": "adaptive", "display": "summarized"}
            assert call_kwargs.get("output_config") == {"effort": "medium"}


@pytest.mark.asyncio
async def test_haiku_55_resolves_to_track_claude_and_inherits_prompt():
    """Verify PromptFactory associates claude-haiku-5-5 with track_claude and inherits active prompt."""
    from core.llm.prompt_factory import PromptFactory

    with (
        patch("core.config.AUTORESEARCH_TRACKS", {"track_claude": ["claude-haiku-5-5", "deepseek-v4-flash"]}),
        patch("autoresearch.prompt_store.get_active_prompt", new_callable=AsyncMock) as mock_get_prompt,
        patch("autoresearch.prompt_store.get_active_variant", new_callable=AsyncMock) as mock_get_variant,
    ):
        mock_get_prompt.return_value = "=== CONSTRAINTS ===\nStrategy: Evolved Claude Alpha\n=== FOOTER ==="
        mock_get_variant.return_value = {"research_output": {"selected_prompt_blocks": []}}

        messages = await PromptFactory.build_analysis_messages(
            provider="anthropic",
            enable_web_search=False,
            owner_id="claude-haiku-5-5",
            market_data_block="",
            current_day_info="Friday, Oct 9",
            news_content="Breaking news content",
            portfolio_context="No positions",
        )

        mock_get_prompt.assert_called_once_with(track_id="track_claude")
        assert len(messages) >= 1
        assert "Evolved Claude Alpha" in messages[0]["content"]
