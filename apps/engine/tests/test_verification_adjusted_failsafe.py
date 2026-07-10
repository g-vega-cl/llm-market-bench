"""TDD tests verifying the verification fixes for HOLD gate, provider remapping, and JIT adjustment failsafes."""

import asyncio
from collections import defaultdict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.llm.verification import verify_trading_decision
from core.models import DecisionObject, VerificationResult
from execution.validation import ValidationResult as GateValidationResult
from execution.validation import ValidationStatus
from main import _process_single_decision


@pytest.mark.asyncio
async def test_verification_hold_case_insensitive():
    """Verify that signal 'hold' or 'Hold' is safely bypassed (case-insensitively)."""
    # Create a decision with lowercase 'hold' bypassing validation via model_construct
    decision = DecisionObject.model_construct(
        signal="hold", confidence=80, reasoning="Hold description", ticker="AAPL", source_id="src_1", price=180.0
    )

    # We do not mock CLIENT_FACTORIES. If it reaches client creation, it will raise because CLIENT_FACTORIES isn't patched.
    # If the bypass works correctly, it should exit early and return APPROVED.
    result = await verify_trading_decision(
        decision=decision, portfolio_context="Cash: $10,000", aggregated_context="Historical context"
    )

    assert result.status == "APPROVED"
    assert "HOLD decisions do not require second-step verification" in result.verification_reasoning


@pytest.mark.asyncio
async def test_verification_provider_remapping():
    """Verify that specialized agent model name 'deepseek_reasoner' updates provider to 'deepseek'."""
    decision = DecisionObject(
        signal="BUY",
        confidence=80,
        reasoning="Earnings growth",
        ticker="AAPL",
        source_id="src_1",
        price=180.0,
        model_provider="openai",  # Start with OpenAI provider
        model_name="deepseek_reasoner",  # Maps to DeepSeek model
    )

    mock_result = VerificationResult(
        status="APPROVED",
        verification_reasoning="Mapped properly",
        confidence_score=90,
    )

    # Mock the CLIENT_FACTORIES to assert it gets called with "deepseek"
    with patch("core.llm.clients.CLIENT_FACTORIES") as mock_factories:
        mock_factory = MagicMock()
        mock_client = MagicMock()

        # Instructor client mock
        mock_instructor_client = MagicMock()
        mock_completions = MagicMock()
        mock_completions.create = AsyncMock(return_value=[mock_result])
        mock_instructor_client.completions = mock_completions
        mock_client.chat = mock_instructor_client
        mock_client.client = MagicMock()  # For the tool loop

        mock_factory.return_value = mock_client
        mock_factories.get.return_value = mock_factory

        with (
            patch("core.llm.handlers.deepseek.run_tool_loop", new_callable=AsyncMock) as mock_ds_loop,
            patch("core.llm.handlers.openai.run_tool_loop", new_callable=AsyncMock) as mock_oa_loop,
            patch("core.llm.clients.close_client", new_callable=AsyncMock),
        ):
            await verify_trading_decision(
                decision=decision, portfolio_context="Cash: $10,000", aggregated_context="Historical context"
            )

            # Assert deepseek factory was looked up, not openai
            mock_factories.get.assert_called_with("deepseek")
            # And that the deepseek handler tool loop ran
            assert mock_ds_loop.called
            assert not mock_oa_loop.called


@pytest.mark.asyncio
async def test_adjusted_allocation_failsafe_rejection():
    """Verify that if verification status is ADJUSTED_ALLOCATION but adjusted_quantity is None/invalid,

    the main loop rejects the trade via REJECTED_VERIFICATION rather than executing full amount.
    """
    decision = DecisionObject(
        signal="BUY",
        confidence=80,
        reasoning="Test failsafe",
        ticker="AAPL",
        source_id="src_1",
        price=180.0,
        model_provider="openai",
        model_name="gpt-4o",
        allocation_percentage=20.0,
    )

    # Mock dependencies of _process_single_decision
    mock_sb_client = MagicMock()
    semaphore = asyncio.Semaphore(1)
    portfolio_locks = defaultdict(asyncio.Lock)
    counters = {"saved": 0, "rejected": 0, "lock": asyncio.Lock()}

    # Mock validation gate to pass
    mock_validate_result = GateValidationResult(status=ValidationStatus.PASSED, market_price=180.0, ticker="AAPL")

    # Mock verify_trading_decision to return ADJUSTED_ALLOCATION with invalid adjusted_quantity (None)
    mock_verification_result = MagicMock()
    mock_verification_result.status = "ADJUSTED_ALLOCATION"
    mock_verification_result.adjusted_quantity = None
    mock_verification_result.verification_reasoning = "Wants to reduce but quantity calculation failed"
    mock_verification_result.confidence_score = 90
    mock_verification_result.alternative_ticker = None

    with (
        patch("main.validate_decision", new_callable=AsyncMock, return_value=mock_validate_result),
        patch("main.verify_trading_decision", new_callable=AsyncMock, return_value=mock_verification_result),
        patch("main.save_decision") as mock_save,
        patch("main.validate_semantic_overlap", new_callable=AsyncMock, return_value=None),
        patch("main.Portfolio") as MockPortfolio,
        patch("execution.market_data.MarketDataManager") as MockMDM,
    ):
        mock_portfolio_instance = MagicMock()
        MockPortfolio.return_value = mock_portfolio_instance
        mock_portfolio_instance.initialize = AsyncMock()
        mock_portfolio_instance.get_portfolio_summary = AsyncMock(return_value="Summary")
        mock_portfolio_instance.execute_trade = AsyncMock()

        # Set up mock metrics and positions
        from execution.reg_t_validation import RegTMetrics

        mock_portfolio_instance.metrics = RegTMetrics(
            total_equity=50000.0,
            initial_margin_req=0.0,
            maintenance_margin_req=0.0,
            available_funds=0.0,
            excess_liquidity=0.0,
            sma=50000.0,
            realized=50000.0,
            buying_power=40000.0,
        )
        mock_portfolio_instance.positions = {}

        mock_mdm_instance = MockMDM.return_value
        mock_mdm_instance.get_quotes = AsyncMock(return_value={"AAPL": MagicMock(price=180.0)})
        mock_mdm_instance.get_quote = AsyncMock(return_value=MagicMock(price=180.0, exists=True))

        # Run process single decision
        result = await _process_single_decision(
            d=decision,
            contrarian_decisions=[],
            aggregated_context="Context",
            uncrowded_context="",
            sb_client=mock_sb_client,
            semaphore=semaphore,
            portfolio_locks=portfolio_locks,
            counters=counters,
        )

        # Assert that the decision was REJECTED
        assert result is False
        assert counters["rejected"] == 1

        # Check that save_decision was called with "REJECTED_VERIFICATION"
        saved_statuses = []
        for call in mock_save.call_args_list:
            args, kwargs = call
            if "status" in kwargs:
                saved_statuses.append(kwargs["status"])
            elif len(args) > 2:
                saved_statuses.append(args[2])
        assert "REJECTED_VERIFICATION" in saved_statuses
