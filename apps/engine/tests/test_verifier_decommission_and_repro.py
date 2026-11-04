"""TDD reproduction tests for verifier bypass, Anthropic 400 prefill fix, DeepSeek tool-result extraction, and adjusted allocation floor clamping."""

import asyncio
from collections import defaultdict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.llm.analysis_pipeline import prompt_assembly
from core.llm.handlers import deepseek
from core.models import DecisionObject, DecisionsResponse
from execution.reg_t_validation import RegTMetrics
from execution.validation import ValidationResult as GateValidationResult
from execution.validation import ValidationStatus
from main import _process_single_decision


def test_anthropic_extraction_ends_with_user_when_system_present():
    """Verify build_provider_extraction_args preserves the trailing user message when messages[0] is system.

    Without the fix, line 331 resets final_args['messages'] = messages[1:], wiping out the appended user extraction prompt
    and causing Anthropic to fail with HTTP 400 invalid_request_error (assistant message prefill).
    """
    messages = [
        {"role": "system", "content": "You are a professional trading analyst."},
        {"role": "user", "content": "Analyze AAPL with market data."},
        {"role": "assistant", "content": "I have completed my evaluation."},
    ]

    args = prompt_assembly.build_provider_extraction_args(
        provider="anthropic",
        model_name="claude-haiku-5-5",
        messages=messages,
        response_model=DecisionsResponse,
    )

    # Must extract system message into top-level system parameter
    assert "system" in args
    assert isinstance(args["system"], list)
    assert args["system"][0]["text"] == "You are a professional trading analyst."

    # Messages MUST NOT end with assistant or model role, otherwise Anthropic 400 occurs
    assert len(args["messages"]) >= 2
    assert args["messages"][-1]["role"] == "user", (
        f"Expected last message role to be 'user', but got '{args['messages'][-1]['role']}'. "
        "Anthropic rejects conversations ending with assistant role."
    )


def test_deepseek_has_valid_content_tool_call_only():
    """Verify has_valid_content returns False when assistant message only contains synthetic [Tool Call: ...] markers.

    Without the fix, flattened tool calls count as valid content, causing the pipeline to skip
    requesting structured decisions and resulting in 0-decision outputs.
    """
    messages = [
        {"role": "user", "content": "Analyze trading candidates."},
        {"role": "assistant", "content": "\n[Tool Call: get_portfolio_ledger({})]"},
        {"role": "user", "content": "[Tool Result: {'cash': 10000.0}]"},
    ]

    assert deepseek.has_valid_content(messages) is False, (
        "Expected has_valid_content to be False when assistant message only contains [Tool Call: ...], "
        "but it returned True."
    )


@pytest.mark.asyncio
async def test_resolve_experiment_tools_respects_track_id():
    """Verify resolve_experiment_tools queries get_active_variant with the model's assigned track_id."""
    with (
        patch("core.config.AUTORESEARCH_EXPERIMENT_OWNER_IDS", ["claude-haiku-5-5"]),
        patch("core.config.AUTORESEARCH_TRACKS", {"track_claude": ["claude-haiku-5-5"]}),
        patch("autoresearch.prompt_store.get_active_variant", new_callable=AsyncMock) as mock_get_variant,
    ):
        mock_get_variant.return_value = {
            "research_output": {"selected_tools": ["get_portfolio_ledger", "get_todays_news_menu"]}
        }

        await prompt_assembly.resolve_experiment_tools(
            model_name="claude-haiku-5-5",
            prompt_type="trading",
        )

        assert mock_get_variant.called
        kwargs = mock_get_variant.call_args.kwargs
        assert kwargs.get("track_id") == "track_claude", (
            f"Expected get_active_variant to be called with track_id='track_claude', got {kwargs.get('track_id')}"
        )


@pytest.mark.asyncio
async def test_adjusted_allocation_clamps_to_min_buy_threshold():
    """Verify that when verification returns ADJUSTED_ALLOCATION with quantity below 10% equity,

    it is clamped up to min_buy_threshold ($1,000) rather than rejected as REJECTED_MARGIN.
    """
    decision = DecisionObject(
        signal="BUY",
        confidence=80,
        reasoning="Test allocation clamp",
        ticker="XLV",
        source_id="src_test_1",
        model_provider="anthropic",
        model_name="claude-haiku-5-5",
        allocation_percentage=14.0,
    )

    mock_sb_client = MagicMock()
    semaphore = asyncio.Semaphore(1)
    portfolio_locks = defaultdict(asyncio.Lock)
    counters = {"saved": 0, "rejected": 0, "lock": asyncio.Lock()}

    mock_validate_result = GateValidationResult(status=ValidationStatus.PASSED, market_price=180.0, ticker="XLV")

    # Verifier cuts position in half: 4 shares = $720.00 (below $1,000 10% equity threshold)
    mock_verification_result = MagicMock()
    mock_verification_result.status = "ADJUSTED_ALLOCATION"
    mock_verification_result.adjusted_quantity = 4
    mock_verification_result.verification_reasoning = "ETF thesis approved but reduce size by 50%"
    mock_verification_result.confidence_score = 85
    mock_verification_result.alternative_ticker = None

    with (
        patch("core.config.is_verifier_enabled_for_owner", return_value=True),
        patch("main.validate_decision", new_callable=AsyncMock, return_value=mock_validate_result),
        patch("main.verify_trading_decision", new_callable=AsyncMock, return_value=mock_verification_result),
        patch("main.save_decision"),
        patch("main.validate_semantic_overlap", new_callable=AsyncMock, return_value=None),
        patch("main.Portfolio") as MockPortfolio,
        patch("execution.market_data.MarketDataManager") as MockMDM,
    ):
        mock_portfolio_instance = MagicMock()
        MockPortfolio.return_value = mock_portfolio_instance
        mock_portfolio_instance.initialize = AsyncMock()
        mock_portfolio_instance.get_portfolio_summary = AsyncMock(return_value="Summary")
        mock_portfolio_instance.execute_trade = AsyncMock(return_value="trade_uuid_123")

        # $10,000 portfolio: 10% floor is $1,000.
        mock_portfolio_instance.metrics = RegTMetrics(
            total_equity=10000.0,
            initial_margin_req=0.0,
            maintenance_margin_req=0.0,
            available_funds=10000.0,
            excess_liquidity=10000.0,
            sma=10000.0,
            realized=10000.0,
            buying_power=10000.0,
        )
        mock_portfolio_instance.positions = {}

        # Real portfolio validate_trade logic
        from execution.portfolio import Portfolio

        mock_portfolio_instance.validate_trade = lambda *args, **kwargs: Portfolio.validate_trade(
            mock_portfolio_instance, *args, **kwargs
        )

        mock_mdm_instance = MockMDM.return_value
        mock_mdm_instance.get_quotes = AsyncMock(return_value={"XLV": MagicMock(price=180.0)})
        mock_mdm_instance.get_quote = AsyncMock(return_value=MagicMock(price=180.0, exists=True))

        result = await _process_single_decision(
            d=decision,
            aggregated_context="Context",
            uncrowded_context="",
            sb_client=mock_sb_client,
            semaphore=semaphore,
            portfolio_locks=portfolio_locks,
            counters=counters,
        )

        # Must execute rather than reject with REJECTED_MARGIN
        assert result is True, "Decision should execute successfully when clamped up to min_buy_threshold"
        assert counters["saved"] == 1
        assert counters["rejected"] == 0

        # Verify trade executed with at least 6 shares ($1,080 >= $1,000 floor)
        call_args = mock_portfolio_instance.execute_trade.call_args
        executed_qty = call_args[0][1] if len(call_args[0]) > 1 else call_args.kwargs.get("quantity")
        assert executed_qty is not None and executed_qty >= 6, (
            f"Expected clamped quantity >= 6 to meet $1,000 floor, got {executed_qty}"
        )
