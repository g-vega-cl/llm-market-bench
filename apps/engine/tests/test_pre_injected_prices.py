"""Tests for Approach 3: Pre-Injected Prices.

Validates that LLM-produced price fields are removed from DecisionObject,
pre-fetch market data extraction works, prompts are rewritten, the execution
pipeline no longer relies on LLM-produced prices, and validation changes.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# =============================================================================
# Round 1 — DecisionObject field changes
# =============================================================================


class TestDecisionObjectNoLLMPriceFields:
    """Verify that price, limit_price, and price_source are gone."""

    def test_no_price_field(self):
        from core.models import DecisionObject

        assert "price" not in DecisionObject.model_fields

    def test_no_limit_price_field(self):
        from core.models import DecisionObject

        assert "limit_price" not in DecisionObject.model_fields

    def test_no_price_source_field(self):
        from core.models import DecisionObject

        assert "price_source" not in DecisionObject.model_fields

    def test_minimal_constructor_still_works(self):
        """Required fields only — no optional price fields needed."""
        from core.models import DecisionObject

        d = DecisionObject(signal="HOLD", ticker="MSFT", reasoning="waiting", source_id="src-2", confidence=50)
        assert d.signal == "HOLD"
        assert d.ticker == "MSFT"
        assert d.reasoning == "waiting"

    def test_buy_with_allocation_still_works(self):
        """BUY signal with allocation_percentage should still construct."""
        from core.models import DecisionObject

        d = DecisionObject(
            signal="BUY", ticker="NVDA", reasoning="thesis", source_id="src-3", allocation_percentage=30, confidence=90
        )
        assert d.signal == "BUY"
        assert d.allocation_percentage == 30

    def test_injected_market_price_field_exists(self):
        """injected_market_price is a system-set field (not LLM-produced)."""
        from core.models import DecisionObject

        assert "injected_market_price" in DecisionObject.model_fields
        d = DecisionObject(
            signal="BUY",
            ticker="AAPL",
            reasoning="test",
            source_id="src-1",
            confidence=80,
            injected_market_price=150.25,
        )
        assert d.injected_market_price == 150.25

    def test_injected_market_price_defaults_to_none(self):
        from core.models import DecisionObject

        d = DecisionObject(signal="BUY", ticker="AAPL", reasoning="test", source_id="src-1", confidence=80)
        assert d.injected_market_price is None

    def test_no_validate_price_validator(self):
        """The validate_price validator (NaN handling) was tied to the price field."""
        from core.models import DecisionObject

        assert not hasattr(DecisionObject, "validate_price")


# =============================================================================
# Round 2 — Prompt rewrites
# =============================================================================


class TestPromptsNoLLMPriceInstructions:
    """The system/user prompts no longer instruct LLMs to produce prices."""

    def test_core_system_prompt_has_no_get_stock_quote_requirement(self):
        from core.llm.prompts import CORE_ANALYSIS_SYSTEM_PROMPT

        assert "MUST call get_stock_quote" not in CORE_ANALYSIS_SYSTEM_PROMPT

    def test_core_system_prompt_says_not_to_produce_price_fields(self):
        from core.llm.prompts import CORE_ANALYSIS_SYSTEM_PROMPT

        assert "Do NOT produce price, limit_price, or price_source fields" in CORE_ANALYSIS_SYSTEM_PROMPT

    def test_core_system_prompt_does_not_require_limit_price(self):
        from core.llm.prompts import CORE_ANALYSIS_SYSTEM_PROMPT

        assert "You MUST set a 'limit_price'" not in CORE_ANALYSIS_SYSTEM_PROMPT
        assert "set limit slightly above" not in CORE_ANALYSIS_SYSTEM_PROMPT

    def test_core_system_prompt_mentions_verified_market_data(self):
        from core.llm.prompts import CORE_ANALYSIS_SYSTEM_PROMPT

        assert "VERIFIED MARKET DATA" in CORE_ANALYSIS_SYSTEM_PROMPT

    def test_analysis_user_prompt_does_not_instruct_to_call_get_stock_quote(self):
        from core.llm.prompts import ANALYSIS_USER_PROMPT_TEMPLATE

        assert "MUST actively execute the `get_stock_quote`" not in ANALYSIS_USER_PROMPT_TEMPLATE
        assert "MUST set a 'limit_price'" not in ANALYSIS_USER_PROMPT_TEMPLATE
        assert "set 'price_source' to" not in ANALYSIS_USER_PROMPT_TEMPLATE
        assert "hallucinated" not in ANALYSIS_USER_PROMPT_TEMPLATE

    def test_analysis_user_prompt_has_market_data_block_placeholder(self):
        from core.llm.prompts import ANALYSIS_USER_PROMPT_TEMPLATE

        assert "{market_data_block}" in ANALYSIS_USER_PROMPT_TEMPLATE

    def test_verifier_user_prompt_has_no_limit_price_reference(self):
        from core.llm.prompts import VERIFIER_USER_PROMPT_TEMPLATE

        assert "{limit_price}" not in VERIFIER_USER_PROMPT_TEMPLATE
        assert "{price}" not in VERIFIER_USER_PROMPT_TEMPLATE

    def test_verifier_user_prompt_uses_market_price(self):
        from core.llm.prompts import VERIFIER_USER_PROMPT_TEMPLATE

        assert "{market_price}" in VERIFIER_USER_PROMPT_TEMPLATE


# =============================================================================
# Round 3 — Pre-fetch market data logic
# =============================================================================


class TestPreFetchMarketData:
    """Ticker extraction from newsletter chunks."""

    def test_extracts_dollar_prefixed_tickers(self):
        """$AAPL, $TSLA patterns should be extracted."""
        from core.llm.analysis import _extract_tickers_from_chunks

        chunks = [{"source_id": "s1", "content": "Apple ($AAPL) is up today. Meanwhile $TSLA reports earnings."}]
        tickers = _extract_tickers_from_chunks(chunks, [])
        assert "AAPL" in tickers
        assert "TSLA" in tickers

    def test_filters_common_false_positives(self):
        """Common words like THE, AND, FOR should not be extracted."""
        from core.llm.analysis import _extract_tickers_from_chunks

        chunks = [{"source_id": "s1", "content": "THE market is UP AND $FOR real"}]
        tickers = _extract_tickers_from_chunks(chunks, [])
        assert "THE" not in tickers
        assert "AND" not in tickers
        assert "FOR" not in tickers

    def test_unions_with_portfolio_tickers(self):
        from core.llm.analysis import _extract_tickers_from_chunks

        chunks = [{"source_id": "s1", "content": "$NVDA is soaring."}]
        tickers = _extract_tickers_from_chunks(chunks, ["MSFT", "GOOGL"])
        assert "NVDA" in tickers
        assert "MSFT" in tickers
        assert "GOOGL" in tickers

    def test_returns_set_with_major_indices(self):
        from core.llm.analysis import _extract_tickers_from_chunks

        tickers = _extract_tickers_from_chunks([], [])
        for idx in ("SPY", "QQQ", "DIA", "IWM"):
            assert idx in tickers, f"Missing major index {idx}"

    def test_empty_chunks_returns_only_indices(self):
        from core.llm.analysis import _extract_tickers_from_chunks

        tickers = _extract_tickers_from_chunks([], [])
        assert tickers == {"SPY", "QQQ", "DIA", "IWM"}


# =============================================================================
# Round 4 — Validation changes
# =============================================================================


@pytest.mark.asyncio
class TestValidationNoPriceDeviation:
    """Guardrail B (price deviation banding) is removed."""

    async def test_validate_decision_no_longer_takes_ai_price(self):
        from execution.validation import validate_decision

        mock_data = MagicMock()
        mock_data.exists = True
        mock_data.price = 150.0
        mock_data.market_cap = 5_000_000_000_000  # $5T

        with patch("execution.validation.MarketDataManager") as mock_mgr:
            instance = mock_mgr.return_value
            instance.get_quote = AsyncMock(return_value=mock_data)
            instance.is_market_open = AsyncMock(return_value=True)
            result = await validate_decision("AAPL")
            assert result.status.value == "PASSED"

    async def test_validate_decision_passes_regardless_of_price(self):
        """Even if the old ai_price would have deviated, now it passes."""
        from execution.validation import validate_decision

        mock_data = MagicMock()
        mock_data.exists = True
        mock_data.price = 150.0
        mock_data.market_cap = 5_000_000_000_000

        with patch("execution.validation.MarketDataManager") as mock_mgr:
            instance = mock_mgr.return_value
            instance.get_quote = AsyncMock(return_value=mock_data)
            instance.is_market_open = AsyncMock(return_value=True)
            result = await validate_decision("AAPL")
            assert result.status.value == "PASSED"


class TestValidationEnumStatuses:
    """Enum-level checks — synchronous tests."""

    def test_rejected_price_deviation_removed_from_enum(self):
        from execution.validation import ValidationStatus

        assert not hasattr(ValidationStatus, "REJECTED_PRICE_DEVIATION")
        assert not hasattr(ValidationStatus, "REJECTED_LIMIT_PRICE")

    def test_rejected_stale_quote_added_to_enum(self):
        from execution.validation import ValidationStatus

        assert hasattr(ValidationStatus, "REJECTED_STALE_QUOTE")


@pytest.mark.asyncio
class TestPrimaryAnalysisInjectedPricesIntegration:
    """Verify that primary analysis extracts tickers from chunks and passes a populated market_data_block."""

    async def test_analyze_chunks_passes_market_data_block(self):
        from unittest.mock import AsyncMock, MagicMock, patch

        from analysis.analyze import analyze_chunks

        chunks = [{"source_id": "chunk-1", "content": "We look at $TSLA and $NVDA. Major news today."}]

        build_analysis_mock = AsyncMock(return_value=[])

        from execution.providers.base import TickerData

        tsla_quote = TickerData(ticker="TSLA", price=250.0, market_cap=800_000_000_000, exists=True)
        nvda_quote = TickerData(ticker="NVDA", price=120.0, market_cap=3_000_000_000_000, exists=True)
        mock_quotes = {"TSLA": tsla_quote, "NVDA": nvda_quote}

        for idx in ["SPY", "QQQ", "DIA", "IWM"]:
            mock_quotes[idx] = TickerData(ticker=idx, price=100.0, market_cap=0, exists=True)

        # Mock Supabase
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = (
            MagicMock(data=[])
        )

        with (
            patch("analysis.analyze.Portfolio") as mock_portfolio_class,
            patch("analysis.analyze.MarketDataManager") as mock_market_data_class,
            patch("analysis.analyze.get_supabase_client", return_value=mock_sb),
            patch("analysis.pre_filter.summarize_newsletters", AsyncMock(return_value={})),
            patch("core.llm.prompt_factory.PromptFactory.build_analysis_messages", build_analysis_mock),
            patch("analysis.analyze.MODELS", [{"provider": "openai", "model": "gpt-4"}]),
        ):
            mock_portfolio = MagicMock()
            mock_portfolio.positions = {"AAPL": MagicMock(quantity=10, average_cost_basis=150.0)}
            mock_portfolio.initialize = AsyncMock(return_value=None)
            mock_portfolio.calculate_reg_t_metrics = MagicMock()
            mock_portfolio.save_metrics = AsyncMock(return_value=None)
            mock_portfolio.get_portfolio_summary = AsyncMock(return_value="- AAPL: 10 shares")
            mock_portfolio_class.return_value = mock_portfolio

            mock_market_data = MagicMock()
            mock_market_data.get_quotes = AsyncMock(return_value=mock_quotes)
            mock_quotes["AAPL"] = TickerData(ticker="AAPL", price=175.0, market_cap=2_500_000_000_000, exists=True)
            mock_market_data_class.return_value = mock_market_data

            mock_client = MagicMock()
            from core.models import DecisionsResponse

            mock_client.chat.completions.create = MagicMock(
                return_value=DecisionsResponse(decisions=[], macro_events=[])
            )
            mock_factory = MagicMock(return_value=mock_client)

            with (
                patch("core.llm.analysis.clients.CLIENT_FACTORIES", {"openai": mock_factory}),
                patch("core.llm.handlers.openai.run_tool_loop", new_callable=AsyncMock) as mock_run_tool_loop,
                patch("core.macro_tracker.get_global_macro_context", AsyncMock(return_value="Mock Macro")),
            ):
                mock_run_tool_loop.side_effect = lambda *args, **kwargs: None
                await analyze_chunks(chunks)

            assert build_analysis_mock.called
            call_kwargs = build_analysis_mock.call_args.kwargs
            assert "market_data_block" in call_kwargs
            mkt_block = call_kwargs["market_data_block"]
            assert "TSLA" in mkt_block
            assert "$250.00" in mkt_block
            assert "NVDA" in mkt_block
            assert "$120.00" in mkt_block
            assert "AAPL" in mkt_block
            assert "$175.00" in mkt_block
