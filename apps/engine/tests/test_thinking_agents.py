"""Tests verifying that agents operate as thinking agents across pipelines without interfering with tool calling."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from autoresearch.researcher import PromptResearchResult
from core.llm.daily_predictor_prompts import DailyPredictionOutput
from core.models import VerificationResult


class DummyPredictionResponse(BaseModel):
    predicted_sector: str = "XLK"
    predicted_worst_sector: str = "XLE"
    predicted_pair: str = "XLK/XLE"
    confidence: float = 75.0
    reasoning: str = "Tech momentum vs energy weakness"


@pytest.mark.asyncio
async def test_daily_predictor_enables_thinking_for_deepseek():
    """Verify that daily_predictor passes extra_body with thinking enabled for DeepSeek."""
    from tasks.daily_predictor import run_daily_prediction

    mock_deepseek_client = MagicMock()
    captured_kwargs = []

    async def mock_create(**kwargs):
        captured_kwargs.append(kwargs)
        return DailyPredictionOutput(
            predicted_direction="UP",
            confidence=70.0,
            expected_return_pct=0.35,
            rationale="Dovish CPI and falling yields",
            catalysts=["CPI"],
        )

    mock_deepseek_client.chat.completions.create = mock_create

    with (
        patch("tasks.daily_predictor.get_deepseek_client", return_value=mock_deepseek_client),
        patch("tasks.daily_predictor.get_daily_market_context", new_callable=AsyncMock, return_value="Market Context"),
        patch(
            "tasks.daily_predictor.fetch_active_daily_prompt", new_callable=AsyncMock, return_value=("tag-1", "Prompt")
        ),
        patch("tasks.daily_predictor.get_supabase_client") as mock_sb,
        patch("tasks.daily_predictor.MiniMaxClient") as mock_minimax_cls,
    ):
        mock_minimax = MagicMock()
        mock_minimax.chat_with_json_response = AsyncMock(
            return_value={
                "predicted_direction": "UP",
                "confidence": 65.0,
                "expected_return_pct": 0.2,
                "rationale": "r",
                "catalysts": [],
            }
        )
        mock_minimax.close = AsyncMock()
        mock_minimax_cls.return_value = mock_minimax

        mock_table = MagicMock()
        mock_sb.return_value.table.return_value = mock_table
        mock_table.insert.return_value.execute = MagicMock()

        await run_daily_prediction(ticker="SPY", force=True)

    assert len(captured_kwargs) > 0, "Expected DeepSeek client to be called in daily predictor"
    ds_call = captured_kwargs[0]
    assert "extra_body" in ds_call, "DeepSeek daily prediction must include extra_body"
    assert ds_call["extra_body"].get("thinking", {}).get("type") == "enabled", (
        f"DeepSeek daily prediction must enable thinking mode, got {ds_call.get('extra_body')}"
    )


@pytest.mark.asyncio
async def test_verification_enables_thinking_for_deepseek():
    """Verify that verify_trading_decision enables thinking mode for DeepSeek extraction."""
    from core.llm.verification import verify_trading_decision
    from core.models import DecisionObject

    mock_client = MagicMock()
    captured_kwargs = []

    async def mock_create(**kwargs):
        captured_kwargs.append(kwargs)
        return VerificationResult(
            status="APPROVED",
            verification_reasoning="Sound DCF valuation",
            confidence_score=90,
        )

    mock_client.chat.completions.create = mock_create

    decision = DecisionObject(
        ticker="NVDA",
        signal="BUY",
        model_provider="deepseek",
        model_name="deepseek-v4-flash",
        quantity=10,
        confidence=85,
        reasoning="Strong demand",
        source_id="src-1",
    )

    with (
        patch.dict("core.llm.clients.CLIENT_FACTORIES", {"deepseek": lambda: mock_client}),
        patch("core.llm.handlers.deepseek.run_tool_loop", new_callable=AsyncMock),
        patch("core.llm.verification.log_reasoning_trace", new_callable=AsyncMock),
        patch(
            "execution.market_data.MarketDataManager.get_quote",
            new_callable=AsyncMock,
            return_value=MagicMock(price=120.0, exists=True),
        ),
        patch("core.llm.verification.retrieve_for_decision", return_value=""),
    ):
        await verify_trading_decision(decision, portfolio_context="", aggregated_context="")

    assert len(captured_kwargs) > 0, "Expected DeepSeek client create call during verification"
    ds_call = captured_kwargs[0]
    assert "extra_body" in ds_call, "DeepSeek verification must include extra_body"
    assert ds_call["extra_body"].get("thinking", {}).get("type") == "enabled", (
        f"DeepSeek verification must enable thinking mode, got {ds_call.get('extra_body')}"
    )


@pytest.mark.asyncio
async def test_sector_predictor_enables_thinking_for_deepseek():
    """Verify that sector_predictor passes extra_body with thinking enabled for DeepSeek."""
    from tasks.sector_predictor import run_sector_predictions

    mock_ds_client = MagicMock()
    captured_ds_kwargs = []

    async def mock_ds_create(**kwargs):
        captured_ds_kwargs.append(kwargs)
        return DummyPredictionResponse()

    mock_ds_client.chat.completions.create = mock_ds_create

    mock_gemini_client = MagicMock()
    captured_gemini_kwargs = []

    async def mock_gemini_create(**kwargs):
        captured_gemini_kwargs.append(kwargs)
        return DummyPredictionResponse()

    mock_gemini_client.chat.completions.create = mock_gemini_create

    mock_minimax = MagicMock()
    mock_minimax.chat_with_json_response = AsyncMock(
        return_value={
            "predicted_sector": "XLK",
            "predicted_worst_sector": "XLE",
            "predicted_pair": "XLK/XLE",
            "confidence": 70,
            "reasoning": "r",
        }
    )
    mock_minimax.close = AsyncMock()

    with (
        patch("tasks.sector_predictor.get_deepseek_client", return_value=mock_ds_client),
        patch("tasks.sector_predictor.get_openai_client", return_value=MagicMock()),
        patch("tasks.sector_predictor.get_gemini_client", return_value=mock_gemini_client),
        patch("tasks.sector_predictor.MiniMaxClient", return_value=mock_minimax),
        patch("tasks.sector_predictor.get_supabase_client") as mock_sb,
        patch("tasks.sector_predictor.fetch_active_prompt", new_callable=AsyncMock, return_value=("tag", "prompt")),
        patch("tasks.sector_predictor.get_predictor_data", new_callable=AsyncMock, return_value="Data block"),
        patch("core.llm.tools.execute_get_calendar_scenario_analysis_tool", new_callable=AsyncMock, return_value="Cal"),
    ):
        mock_table = MagicMock()
        mock_sb.return_value.table.return_value = mock_table
        mock_table.insert.return_value.execute = MagicMock()

        await run_sector_predictions()

    assert len(captured_ds_kwargs) > 0, "Expected DeepSeek create calls in sector predictor"
    ds_call = captured_ds_kwargs[0]
    assert "extra_body" in ds_call, "DeepSeek sector prediction must include extra_body"
    assert ds_call["extra_body"].get("thinking", {}).get("type") == "enabled"

    assert len(captured_gemini_kwargs) > 0, "Expected Gemini create calls in sector predictor"
    gemini_call = captured_gemini_kwargs[0]
    assert gemini_call.get("thinking_config") is not None
    assert gemini_call["thinking_config"].thinking_budget == 2048


@pytest.mark.asyncio
async def test_autoresearcher_enables_thinking_for_deepseek():
    """Verify that researcher.run_research passes extra_body with thinking enabled for DeepSeek."""
    from autoresearch import researcher

    mock_client = MagicMock()
    captured_kwargs = []

    async def mock_create(**kwargs):
        captured_kwargs.append(kwargs)
        return PromptResearchResult(
            rationale_for_change="Deep quantitative reasoning on regime change",
            new_prompt_text="New optimized prompt",
            tags=["regime", "discipline"],
        )

    mock_client.chat.completions.create = mock_create

    with (
        patch("autoresearch.researcher.get_deepseek_client", return_value=mock_client),
        patch("core.llm.handlers.deepseek.run_tool_loop", new_callable=AsyncMock),
        patch("autoresearch.prompt_store.get_active_prompt", new_callable=AsyncMock, return_value="Baseline prompt"),
        patch("core.time_utils.get_current_day_info", return_value="Monday"),
        patch("autoresearch.prompt_blocks.render_prompt_blocks", return_value=""),
        patch("autoresearch.tools.query_trade_postmortems", new_callable=AsyncMock, return_value="Postmortems"),
        patch("autoresearch.tools.query_past_newsletters", new_callable=AsyncMock, return_value="Newsletters"),
        patch("autoresearch.tools.search_wiki_concepts", new_callable=AsyncMock, return_value="Wiki concepts"),
        patch("autoresearch.tools.query_verifier_audit_context", new_callable=AsyncMock, return_value="Verifier rules"),
    ):
        await researcher.run_research(
            report="Performance Report",
            track_id="track_default",
            model_name="deepseek-v4-flash",
        )

    assert len(captured_kwargs) > 0, "Expected chat.completions.create in autoresearch"
    call = captured_kwargs[0]
    assert "extra_body" in call, "DeepSeek autoresearch must include extra_body"
    assert call["extra_body"].get("thinking", {}).get("type") == "enabled"


@pytest.mark.asyncio
async def test_tool_loop_suppresses_thinking_to_prevent_narration():
    """Verify that the tool loop suppresses thinking mode so models do not hallucinate tool calls."""
    from core.llm.handlers import deepseek, openai

    # 1. DeepSeek tool loop check
    mock_ds_raw = MagicMock()
    mock_ds_msg = MagicMock(content="Done", tool_calls=None)
    mock_ds_raw.chat.completions.create = AsyncMock(return_value=MagicMock(choices=[MagicMock(message=mock_ds_msg)]))

    messages = [{"role": "user", "content": "Fetch stock quote"}]
    await deepseek.run_tool_loop(
        raw_client=mock_ds_raw,
        model_name="deepseek-v4-flash",
        messages=messages,
        max_tool_steps=1,
    )
    ds_args = mock_ds_raw.chat.completions.create.call_args[1]
    assert "extra_body" not in ds_args or "thinking" not in ds_args.get("extra_body", {}), (
        "DeepSeek tool loop must NOT pass thinking mode to prevent tool narration hallucination"
    )

    # 2. OpenAI tool loop check
    mock_oa_raw = MagicMock()
    mock_oa_msg = MagicMock(tool_calls=None)
    mock_oa_msg.model_dump.return_value = {"role": "assistant", "content": "Done"}
    mock_oa_raw.chat.completions.create = AsyncMock(return_value=MagicMock(choices=[MagicMock(message=mock_oa_msg)]))

    oa_messages = [{"role": "user", "content": "Fetch stock quote"}]
    await openai.run_tool_loop(
        raw_client=mock_oa_raw,
        model_name="gpt-5.6-luna",
        messages=oa_messages,
        max_tool_steps=1,
    )
    oa_args = mock_oa_raw.chat.completions.create.call_args[1]
    assert oa_args.get("reasoning_effort") == "none", (
        "OpenAI tool loop must pass reasoning_effort='none' to avoid API gateway tool schema errors"
    )


@pytest.mark.asyncio
async def test_anthropic_tool_loop_enables_thinking_and_preserves_thinking_blocks():
    """Verify Anthropic tool loop enables thinking and preserves thinking blocks in history."""
    from core.llm.handlers import anthropic

    # Turn 1 response: thinking block + tool_use block
    mock_thinking = MagicMock(type="thinking", thinking="Evaluating ticker fundamentals...", signature="sig_test_123")
    mock_tool_use = MagicMock(type="tool_use", id="call_1", name="get_stock_quote", input={"ticker": "AAPL"})
    resp_turn_1 = MagicMock(content=[mock_thinking, mock_tool_use])

    # Turn 2 response: final text block
    mock_text = MagicMock(type="text", text="Analysis complete.")
    resp_turn_2 = MagicMock(content=[mock_text])

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=[resp_turn_1, resp_turn_2])

    messages = [{"role": "user", "content": "Analyze AAPL"}]

    with patch("core.llm.handlers.base.execute_tool", AsyncMock(return_value='{"price": 150.0}')):
        await anthropic.run_tool_loop(
            raw_client=mock_client,
            model_name="claude-haiku-4-5",
            messages=messages,
            max_tool_steps=2,
        )

    assert mock_client.messages.create.call_count == 2
    # Check that thinking config was passed to messages.create
    first_call_kwargs = mock_client.messages.create.call_args_list[0].kwargs
    assert first_call_kwargs.get("thinking") == {"type": "enabled", "budget_tokens": 2048}

    # Verify that assistant message in history contains the preserved thinking block
    assistant_msg = next(m for m in messages if m["role"] == "assistant")
    thinking_blocks = [b for b in assistant_msg["content"] if b.get("type") == "thinking"]
    assert len(thinking_blocks) == 1, "Thinking block must be preserved in assistant message history"
    assert thinking_blocks[0]["thinking"] == "Evaluating ticker fundamentals..."
    assert thinking_blocks[0]["signature"] == "sig_test_123"


@pytest.mark.asyncio
async def test_gemini_tool_loop_enables_thinking_config():
    """Verify Gemini tool loop configures thinking_budget in GenerateContentConfig."""
    from google.genai import types

    from core.llm.handlers import gemini

    mock_candidate = MagicMock()
    mock_candidate.content = MagicMock(parts=[MagicMock(function_call=None)])
    resp = MagicMock(candidates=[mock_candidate])

    raw_client = MagicMock()
    raw_client.aio.models.generate_content = AsyncMock(return_value=resp)

    messages = [{"role": "user", "content": "Analyze NVDA"}]

    await gemini.run_tool_loop(
        raw_client=raw_client,
        model_name="gemini-3.5-flash-lite",
        messages=messages,
        max_tool_steps=1,
    )

    assert raw_client.aio.models.generate_content.called
    config_arg = raw_client.aio.models.generate_content.call_args.kwargs["config"]
    assert isinstance(config_arg, types.GenerateContentConfig)
    assert config_arg.thinking_config is not None
    assert config_arg.thinking_config.thinking_budget == 2048


def test_anthropic_client_uses_anthropic_json_mode():
    """Verify Anthropic client factory uses JSON mode so thinking mode works without tool_choice conflict."""
    import instructor

    from core.llm.clients import get_anthropic_client

    client = get_anthropic_client(api_key="test-anthropic-key")
    assert client.mode in (instructor.Mode.ANTHROPIC_JSON, instructor.Mode.JSON)


@pytest.mark.asyncio
async def test_verification_enables_thinking_for_anthropic_and_gemini():
    """Verify that verification sets thinking parameters for Anthropic and Gemini."""
    from core.llm.verification import verify_trading_decision
    from core.models import DecisionObject

    # 1. Anthropic test
    mock_anthropic = MagicMock()
    captured_anthropic = []

    async def anthropic_create(**kwargs):
        captured_anthropic.append(kwargs)
        return VerificationResult(status="APPROVED", verification_reasoning="Sound", confidence_score=85)

    mock_anthropic.chat.completions.create = anthropic_create

    decision = DecisionObject(
        ticker="AAPL",
        signal="BUY",
        model_provider="anthropic",
        model_name="claude-haiku-4-5",
        quantity=10,
        confidence=85,
        reasoning="Strong",
        source_id="src-1",
    )

    with (
        patch.dict("core.llm.clients.CLIENT_FACTORIES", {"anthropic": lambda: mock_anthropic}),
        patch("core.llm.handlers.anthropic.run_tool_loop", new_callable=AsyncMock),
        patch("core.llm.verification.log_reasoning_trace", new_callable=AsyncMock),
        patch(
            "execution.market_data.MarketDataManager.get_quote",
            new_callable=AsyncMock,
            return_value=MagicMock(price=150.0, exists=True),
        ),
        patch("core.llm.verification.retrieve_for_decision", return_value=""),
    ):
        await verify_trading_decision(decision, portfolio_context="", aggregated_context="")

    assert len(captured_anthropic) > 0
    assert captured_anthropic[0].get("thinking") == {"type": "enabled", "budget_tokens": 1024}

    # 2. Gemini test
    mock_gemini = MagicMock()
    captured_gemini = []

    async def gemini_create(**kwargs):
        captured_gemini.append(kwargs)
        return [VerificationResult(status="APPROVED", verification_reasoning="Sound", confidence_score=85)]

    mock_gemini.chat.completions.create = gemini_create

    decision_gemini = DecisionObject(
        ticker="AAPL",
        signal="BUY",
        model_provider="gemini",
        model_name="gemini-3.5-flash-lite",
        quantity=10,
        confidence=85,
        reasoning="Strong",
        source_id="src-2",
    )

    with (
        patch.dict("core.llm.clients.CLIENT_FACTORIES", {"gemini": lambda: mock_gemini}),
        patch("core.llm.handlers.gemini.run_tool_loop", new_callable=AsyncMock),
        patch("core.llm.verification.log_reasoning_trace", new_callable=AsyncMock),
        patch(
            "execution.market_data.MarketDataManager.get_quote",
            new_callable=AsyncMock,
            return_value=MagicMock(price=150.0, exists=True),
        ),
        patch("core.llm.verification.retrieve_for_decision", return_value=""),
    ):
        await verify_trading_decision(decision_gemini, portfolio_context="", aggregated_context="")

    assert len(captured_gemini) > 0
    assert captured_gemini[0].get("thinking_config") is not None
    assert captured_gemini[0]["thinking_config"].thinking_budget == 1024


@pytest.mark.asyncio
async def test_autoresearcher_enables_thinking_for_anthropic_and_gemini():
    """Verify that autoresearch passes thinking arguments for Anthropic and Gemini."""
    from autoresearch import researcher

    mock_client = MagicMock()
    captured = []

    async def mock_create(**kwargs):
        captured.append(kwargs)
        return PromptResearchResult(
            new_prompt_text="New prompt",
            selected_tools=["get_stock_quote"],
            change_description="Sharpen risk gate",
            experiment_type="incremental",
            research_reasoning="Detailed quantitative reasoning",
            confidence=85.0,
        )

    mock_client.chat.completions.create = mock_create

    with (
        patch("autoresearch.prompt_store.get_active_prompt", new_callable=AsyncMock, return_value="Baseline prompt"),
        patch("core.time_utils.get_current_day_info", return_value="Monday"),
        patch("autoresearch.prompt_blocks.render_prompt_blocks", return_value=""),
        patch("autoresearch.tools.query_trade_postmortems", new_callable=AsyncMock, return_value=""),
        patch("autoresearch.tools.query_past_newsletters", new_callable=AsyncMock, return_value=""),
        patch("autoresearch.tools.search_wiki_concepts", new_callable=AsyncMock, return_value=""),
        patch("autoresearch.tools.query_verifier_audit_context", new_callable=AsyncMock, return_value=""),
        patch("core.llm.handlers.anthropic.run_tool_loop", new_callable=AsyncMock),
        patch("core.llm.handlers.gemini.run_tool_loop", new_callable=AsyncMock),
    ):
        # Anthropic track
        with patch("autoresearch.researcher.get_anthropic_client", return_value=mock_client):
            await researcher.run_research(report="Report", track_id="track_claude", model_name="claude-haiku-4-5")
        assert len(captured) == 1
        assert captured[0].get("thinking") == {"type": "enabled", "budget_tokens": 4096}

        # Gemini track
        with patch("autoresearch.researcher.get_gemini_client", return_value=mock_client):
            await researcher.run_research(report="Report", track_id="track_default", model_name="gemini-3.5-flash-lite")
        assert len(captured) == 2
        assert captured[1].get("thinking_config") is not None
        assert captured[1]["thinking_config"].thinking_budget == 4096
