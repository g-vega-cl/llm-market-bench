"""TDD reproduction tests for decoupled analysis phase (Approach 1)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.models import DecisionObject, MacroEvent, MacroEventsResponse, TradingDecisionsResponse


@pytest.mark.asyncio
async def test_decoupled_schemas_exist():
    """Verify that MacroEventsResponse and TradingDecisionsResponse models are defined and correct."""
    assert issubclass(MacroEventsResponse, object)
    assert issubclass(TradingDecisionsResponse, object)

    macro_resp = MacroEventsResponse(macro_events=[])
    assert hasattr(macro_resp, "macro_events")

    trade_resp = TradingDecisionsResponse(decisions=[])
    assert hasattr(trade_resp, "decisions")


@pytest.mark.asyncio
async def test_analyze_macro_events_schema():
    """Test that analyze_macro_events uses the MacroEventsResponse schema and returns MacroEvents."""
    mock_response = MacroEventsResponse(
        macro_events=[
            MacroEvent(
                event_name="CPI Spike",
                impact="BEARISH",
                catalyst_type="MACRO",
                confidence=90,
                reasoning="CPI rose 0.5% month-over-month.",
                source_id="news_1",
            )
        ]
    )

    test_models = [{"provider": "openai", "model": "gpt-4o"}]

    with (
        patch("analysis.analyze.MODELS", test_models),
        patch("analysis.analyze.llm.analyze_with_provider", new_callable=AsyncMock) as mock_llm_call,
    ):
        mock_llm_call.return_value = mock_response

        chunks = [{"source_id": "news_1", "content": "Fake CPI spike news."}]

        from analysis.analyze import analyze_macro_events

        events = await analyze_macro_events(chunks)

        assert isinstance(events, list)
        assert len(events) == 1
        assert events[0].event_name == "CPI Spike"

        mock_llm_call.assert_called_once()
        call_kwargs = mock_llm_call.call_args[1]
        assert call_kwargs["response_model"] == MacroEventsResponse
        assert call_kwargs["prompt_type"] == "macro"


@pytest.mark.asyncio
async def test_analyze_trading_decisions_schema():
    """Test that analyze_trading_decisions uses TradingDecisionsResponse schema and receives consensus context."""
    mock_response = TradingDecisionsResponse(
        decisions=[
            DecisionObject(
                ticker="SPY",
                signal="BUY",
                allocation_percentage=10,
                catalyst_type="MACRO",
                catalyst_duration="SHORT_TERM",
                confidence=85,
                reasoning="Bullish inflation hedge play.",
                source_id="news_1",
            )
        ]
    )

    test_models = [{"provider": "openai", "model": "gpt-4o"}]

    # Mock all external system/database boundaries
    mock_portfolio = MagicMock()
    mock_portfolio.positions = {"AAPL": MagicMock()}
    mock_portfolio.initialize = AsyncMock()
    mock_portfolio.calculate_reg_t_metrics = MagicMock()
    mock_portfolio.save_metrics = AsyncMock()
    mock_portfolio.get_portfolio_summary = AsyncMock(return_value="AAPL: 100 shares")

    mock_quote = MagicMock()
    mock_quote.exists = True
    mock_quote.price = 150.0
    mock_quote.market_cap = 3000000000000.0

    mock_market_data = MagicMock()
    mock_market_data.get_quotes = AsyncMock(return_value={"SPY": mock_quote, "AAPL": mock_quote})
    mock_market_data.get_quote = AsyncMock(return_value=mock_quote)

    mock_sb_client = MagicMock()
    mock_sb_client.table().select().eq().in_().execute = MagicMock(return_value=MagicMock(data=[]))

    with (
        patch("analysis.analyze.MODELS", test_models),
        patch("analysis.analyze.llm.analyze_with_provider", new_callable=AsyncMock) as mock_llm_call,
        patch("analysis.analyze.Portfolio", return_value=mock_portfolio),
        patch("analysis.analyze.MarketDataManager", return_value=mock_market_data),
        patch("core.macro_tracker.get_global_macro_context", new_callable=AsyncMock, return_value="Strong USD"),
        patch("analysis.analyze.retrieve_top_memories", return_value="Historical rate hikes"),
        patch("analysis.analyze.get_top_trending_concepts", return_value="AI revolution"),
        patch("analysis.pre_filter.summarize_newsletters", new_callable=AsyncMock, return_value={}),
    ):
        mock_llm_call.return_value = mock_response

        chunks = [{"source_id": "news_1", "content": "Fake CPI spike news."}]
        consensus_events = [{"event_name": "CPI Inflation Spike", "summary": "Inflation went up"}]

        from analysis.analyze import analyze_trading_decisions

        decisions, uncrowded_ctx = await analyze_trading_decisions(
            chunks=chunks, consensus_events=consensus_events, sb_client=mock_sb_client
        )

        assert isinstance(decisions, list)
        assert len(decisions) == 1
        assert decisions[0].ticker == "SPY"
        assert decisions[0].injected_market_price == 150.0

        mock_llm_call.assert_called_once()
        call_kwargs = mock_llm_call.call_args[1]
        assert call_kwargs["response_model"] == TradingDecisionsResponse
        assert call_kwargs["prompt_type"] == "analysis"
        assert "consensus_context" in call_kwargs
        assert "CPI Inflation Spike" in call_kwargs["consensus_context"]
