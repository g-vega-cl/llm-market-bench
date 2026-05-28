"""Tests for analysis logic and Pydantic models."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from analysis.analyze import analyze_chunks
from core.llm.analysis import _repair_json_string, _try_parse_decisions_response
from core.models import DecisionObject, DecisionsResponse


class TestDecisionObject:
    """Tests for the DecisionObject Pydantic model."""

    def test_valid_decision_object(self):
        """Test that a valid dictionary can be parsed into a DecisionObject."""
        data = {
            "signal": "BUY",
            "confidence": 85,
            "reasoning": "Strong earnings report.",
            "ticker": "AAPL",
            "source_id": "news_123",
            "is_priced_in": False,
            "is_priced_in_reasoning": "News just broke",
            "profit_potential_reasoning": "First mover advantage",
            "strategy_reasoning": "Bullish on Apple due to new AI chips.",
            "advance_planning_notes": "None",
        }
        obj = DecisionObject(**data)
        assert obj.signal == "BUY"
        assert obj.confidence == 85
        assert obj.ticker == "AAPL"

    def test_invalid_signal(self):
        """Test that invalid signals raise a ValidationError."""
        data = {
            "signal": "PANIC_SELL",  # Invalid literal
            "confidence": 85,
            "reasoning": "Something bad.",
            "ticker": "AAPL",
            "source_id": "news_123",
            "is_priced_in": False,
            "is_priced_in_reasoning": "Logic",
            "profit_potential_reasoning": "Profit",
        }
        with pytest.raises(ValidationError):
            DecisionObject(**data)

    def test_confidence_range(self):
        """Test that confidence must be between 0 and 100."""
        data = {
            "signal": "HOLD",
            "confidence": 105,  # Out of range
            "reasoning": "Too confident.",
            "ticker": "AAPL",
            "source_id": "news_123",
            "is_priced_in": False,
            "is_priced_in_reasoning": "Logic",
            "profit_potential_reasoning": "Profit",
        }
        with pytest.raises(ValidationError):
            DecisionObject(**data)

    def test_ticker_uppercase(self):
        """Test that ticker symbols are automatically uppercased."""
        data = {
            "signal": "BUY",
            "confidence": 50,
            "reasoning": "Test.",
            "ticker": "aapl",
            "source_id": "news_123",
            "is_priced_in": False,
            "is_priced_in_reasoning": "Logic",
            "profit_potential_reasoning": "Profit",
        }
        obj = DecisionObject(**data)
        assert obj.ticker == "AAPL"


@pytest.mark.asyncio
class TestAnalysisOrchestration:
    """Tests for the analyze_chunks orchestration function."""

    async def test_analyze_chunks_orchestration(self, monkeypatch):
        """Test that analyze_chunks calls analyze_with_provider for each model and chunk."""

        from unittest.mock import MagicMock, patch

        from core.models import DecisionsResponse

        async def mock_analyze(provider, model_name, chunks, context=None, portfolio_context=None, **kwargs):
            # Return a DecisionsResponse object
            decisions = [
                DecisionObject(
                    signal="BUY",
                    confidence=80,
                    reasoning=f"{provider} says buy",
                    ticker="AAPL",
                    source_id=chunk.get("source_id", "unknown"),
                    is_priced_in=False,
                    is_priced_in_reasoning="Logic",
                    profit_potential_reasoning="Profit",
                    strategy_reasoning="Mock strategy",
                    advance_planning_notes="Mock notes",
                )
                for chunk in chunks
            ]
            return DecisionsResponse(decisions=decisions, macro_events=[])

        monkeypatch.setattr("core.llm.analyze_with_provider", mock_analyze)

        chunks = [{"source_id": "chunk_1", "content": "Apple is doing great."}]

        # Mock Portfolio and MarketDataManager to avoid Supabase dependency
        with (
            patch("analysis.analyze.Portfolio") as mock_portfolio_class,
            patch("analysis.analyze.MarketDataManager") as mock_market_data_class,
            patch("memory.embeddings.get_embeddings_batch") as mock_get_embeddings,
        ):
            mock_get_embeddings.return_value = [[0.1] * 768]

            # Mock portfolio instance
            from unittest.mock import AsyncMock

            mock_portfolio = MagicMock()
            mock_portfolio.positions = {}
            mock_portfolio.initialize = AsyncMock(return_value=None)
            mock_portfolio.calculate_reg_t_metrics = MagicMock()
            mock_portfolio.save_metrics = AsyncMock(return_value=None)
            mock_portfolio.get_portfolio_summary = AsyncMock(return_value="Portfolio: $10,000 cash")
            mock_portfolio_class.return_value = mock_portfolio

            # Mock market data manager
            mock_market_data = MagicMock()
            mock_market_data.get_quote = AsyncMock(return_value=None)
            mock_market_data.get_quotes = AsyncMock(return_value={})
            mock_market_data.get_history = AsyncMock(return_value=[])
            mock_market_data_class.return_value = mock_market_data

            decisions, events, _, _ = await analyze_chunks(chunks)

        assert len(decisions) > 0
        assert isinstance(decisions[0], DecisionObject)
        assert decisions[0].source_id == "chunk_1"

    async def test_analyze_chunks_skips_malformed(self, monkeypatch, caplog):
        """Test that malformed chunks are skipped with a warning."""

        from unittest.mock import MagicMock, patch

        from core.models import DecisionsResponse

        async def mock_analyze(provider, model_name, chunks, context=None, portfolio_context=None, **kwargs):
            decisions = [
                DecisionObject(
                    signal="HOLD",
                    confidence=50,
                    reasoning="Test",
                    ticker="TEST",
                    source_id=chunk.get("source_id", "unknown"),
                    is_priced_in=False,
                    is_priced_in_reasoning="Logic",
                    profit_potential_reasoning="Profit",
                    strategy_reasoning="Mock strategy",
                    advance_planning_notes="Mock notes",
                )
                for chunk in chunks
            ]
            return DecisionsResponse(decisions=decisions, macro_events=[])

        monkeypatch.setattr("core.llm.analyze_with_provider", mock_analyze)

        chunks = [
            {"source_id": "chunk_1"},  # Missing content
            {"content": "Some text"},  # Missing source_id
        ]

        # Mock Portfolio and MarketDataManager to avoid Supabase dependency
        with (
            patch("analysis.analyze.Portfolio") as mock_portfolio_class,
            patch("analysis.analyze.MarketDataManager") as mock_market_data_class,
            patch("memory.embeddings.get_embeddings_batch") as mock_get_embeddings,
        ):
            mock_get_embeddings.return_value = [[0.1] * 768]

            from unittest.mock import AsyncMock

            mock_portfolio = MagicMock()
            mock_portfolio.positions = {}
            mock_portfolio.initialize = AsyncMock(return_value=None)
            mock_portfolio.calculate_reg_t_metrics = MagicMock()
            mock_portfolio.save_metrics = AsyncMock(return_value=None)
            mock_portfolio.get_portfolio_summary = AsyncMock(return_value="Portfolio: $10,000 cash")
            mock_portfolio_class.return_value = mock_portfolio

            mock_market_data = MagicMock()
            mock_market_data.get_quote = AsyncMock(return_value=None)
            mock_market_data.get_quotes = AsyncMock(return_value={})
            mock_market_data.get_history = AsyncMock(return_value=[])
            mock_market_data_class.return_value = mock_market_data

            decisions, events, _, _ = await analyze_chunks(chunks)

        assert len(decisions) == 0
        assert len(events) == 0


class TestRepairJsonString:
    """Tests for the _repair_json_string helper function."""

    def test_repair_json_string_double_encoded(self):
        """Test that double-encoded JSON strings are repaired."""
        double_encoded = '"{\\"decisions\\": [], \\"macro_events\\": []}"'
        result = _repair_json_string(double_encoded)
        assert result.startswith("{") or result.startswith("[")

    def test_repair_json_string_with_extra_quotes(self):
        """Test that JSON wrapped in extra quotes is repaired."""
        quoted = '"{\\"key\\": \\"value\\"}"'
        result = _repair_json_string(quoted)
        assert result.startswith("{")
        assert not result.startswith('""')

    def test_repair_json_string_with_leading_text(self):
        """Test that JSON with leading text is trimmed correctly."""
        with_leading = 'Here is the JSON: {"key": "value"}'
        result = _repair_json_string(with_leading)
        assert result.startswith("{")

    def test_repair_json_string_with_trailing_text(self):
        """Test that JSON with trailing text is trimmed correctly."""
        with_trailing = '{"key": "value"} is the result'
        result = _repair_json_string(with_trailing)
        assert result.endswith("}")

    def test_repair_json_string_valid_json_unchanged(self):
        """Test that valid JSON is not modified."""
        valid = '{"decisions": [], "macro_events": []}'
        result = _repair_json_string(valid)
        assert result == valid

    def test_repair_json_string_list_unchanged(self):
        """Test that valid JSON lists are not modified."""
        valid_list = '[{"ticker": "AAPL"}, {"ticker": "GOOGL"}]'
        result = _repair_json_string(valid_list)
        assert result == valid_list

    def test_repair_json_string_none_input(self):
        """Test that None input returns None."""
        result = _repair_json_string(None)
        assert result is None

    def test_repair_json_string_with_escaped_quotes_and_newlines(self):
        """Test that normal JSON with escaped quotes and newlines is preserved."""
        json_with_escaped = '{"reasoning": "The company announced \\"strong earnings\\".\\nThis is a second line."}'
        result = _repair_json_string(json_with_escaped)
        assert result == json_with_escaped


class TestTryParseDecisionsResponse:
    """Tests for the _try_parse_decisions_response helper function."""

    def test_try_parse_valid_dict(self):
        """Test parsing a valid dictionary."""
        data = {
            "decisions": [
                {
                    "signal": "BUY",
                    "confidence": 80,
                    "reasoning": "Test reasoning",
                    "ticker": "AAPL",
                    "source_id": "test_1",
                    "is_priced_in": False,
                    "is_priced_in_reasoning": "",
                    "profit_potential_reasoning": "",
                    "strategy_reasoning": "",
                    "advance_planning_notes": "",
                }
            ],
            "macro_events": [],
        }
        result = _try_parse_decisions_response(data)
        assert result is not None
        assert len(result.decisions) == 1
        assert result.decisions[0].ticker == "AAPL"

    def test_try_parse_stringified_decisions(self):
        """Test parsing when decisions field is a stringified JSON."""
        data = {
            "decisions": '[{"ticker": "TSM", "signal": "HOLD", "confidence": 70, "reasoning": "Test", "source_id": "test_2", "is_priced_in": false, "is_priced_in_reasoning": "", "profit_potential_reasoning": "", "strategy_reasoning": "", "advance_planning_notes": ""}]',
            "macro_events": [],
        }
        result = _try_parse_decisions_response(data)
        assert result is not None
        assert len(result.decisions) == 1
        assert result.decisions[0].ticker == "TSM"

    def test_try_parse_valid_json_string(self):
        """Test parsing a valid JSON string."""
        data = '{"decisions": [], "macro_events": []}'
        result = _try_parse_decisions_response(data)
        assert result is not None
        assert len(result.decisions) == 0
        assert len(result.macro_events) == 0

    def test_try_parse_invalid_data_returns_none(self):
        """Test that invalid data returns None without raising."""
        result = _try_parse_decisions_response("not json at all")
        assert result is None

    def test_try_parse_partial_repair(self):
        """Test that partial repair of stringified fields works."""
        data = {
            "decisions": '[{"ticker": "META", "signal": "BUY", "confidence": 75, "reasoning": "Test", "source_id": "test_3", "is_priced_in": false, "is_priced_in_reasoning": "", "profit_potential_reasoning": "", "strategy_reasoning": "", "advance_planning_notes": ""}]',
            "macro_events": "[]",
        }
        result = _try_parse_decisions_response(data)
        assert result is not None
        assert len(result.decisions) == 1
        assert result.decisions[0].ticker == "META"

    def test_try_parse_macro_events(self):
        """Test parsing with macro events."""
        data = {
            "decisions": [],
            "macro_events": [
                {
                    "event_name": "Test Event",
                    "impact": "BULLISH",
                    "catalyst_type": "EARNINGS",
                    "is_ongoing": False,
                    "is_future_catalyst": True,
                    "historical_parallel": None,
                    "expiry_date": "2026-12-31",
                    "importance_score": 7,
                    "confidence": 80,
                    "reasoning": "Test reasoning",
                    "scenario_analysis": "Scenario A: Test",
                    "source_id": "test_4",
                    "model_provider": None,
                    "model_name": None,
                }
            ],
        }
        result = _try_parse_decisions_response(data)
        assert result is not None
        assert len(result.macro_events) == 1
        assert result.macro_events[0].event_name == "Test Event"

    def test_try_parse_minimax_raw_schema(self):
        """Test that correct schema returned by MiniMax parses successfully."""
        data = {
            "decisions": [
                {
                    "signal": "BUY",
                    "confidence": 78,
                    "reasoning": "Standard reasoning",
                    "ticker": "CVX",
                    "catalyst_type": "MACRO",
                    "catalyst_duration": "SHORT_TERM",
                    "source_id": "test_source",
                    "allocation_percentage": 15,
                    "is_priced_in": False,
                    "is_priced_in_reasoning": "No explicit priced-in reasoning provided.",
                    "profit_potential_reasoning": "No explicit profit potential reasoning provided.",
                }
            ],
            "macro_events": [
                {
                    "event_name": "US-Iran Geopolitical Escalation",
                    "impact": "BULLISH",
                    "catalyst_type": "MACRO",
                    "is_ongoing": True,
                    "is_future_catalyst": False,
                    "importance_score": 8,
                    "confidence": 85,
                    "reasoning": "Standard reasoning",
                    "source_id": "test_source",
                }
            ],
        }
        result = _try_parse_decisions_response(data)
        assert result is not None
        assert len(result.decisions) == 1
        assert result.decisions[0].ticker == "CVX"
        assert len(result.macro_events) == 1
        assert result.macro_events[0].event_name == "US-Iran Geopolitical Escalation"


@pytest.mark.asyncio
class TestAnalyzeWithProviderRetryLogic:
    """Tests for the retry logic in analyze_with_provider."""

    async def test_retry_on_validation_error_succeeds(self, monkeypatch):
        """Test that analyze_with_provider retries on validation error and succeeds."""
        from unittest.mock import AsyncMock, MagicMock, patch

        # Track call count to return different responses
        call_count = 0

        async def mock_create(**kwargs):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                # First call raises validation error (simulating stringified JSON issue)
                from pydantic import ValidationError

                raise ValidationError.from_exception_data(
                    title="DecisionsResponse",
                    line_errors=[
                        {
                            "type": "list_type",
                            "loc": ("decisions",),
                            "msg": "Input should be a valid array",
                            "input": '[\n  {\n    "ticker": "T...',
                        }
                    ],
                )
            else:
                # Second call succeeds
                return DecisionsResponse(decisions=[], macro_events=[])

        mock_client = MagicMock()
        mock_client.chat.completions.create = mock_create

        mock_factory = MagicMock(return_value=mock_client)

        chunks = [{"source_id": "test_1", "content": "Test content"}]

        with (
            patch("core.llm.clients.CLIENT_FACTORIES", {"anthropic": mock_factory}),
            patch("core.llm.handlers.anthropic.run_tool_loop", new_callable=AsyncMock),
        ):
            from core.llm.analysis import analyze_with_provider

            # Should not raise - should succeed on retry
            result = await analyze_with_provider(provider="anthropic", model_name="claude-haiku-4-5", chunks=chunks)

            assert call_count == 2  # First failed, second succeeded
            assert result is not None
            assert isinstance(result, DecisionsResponse)

    async def test_all_retries_fail_returns_empty_response(self, monkeypatch):
        """Test that all retries failing returns an empty response instead of raising."""

        async def mock_create(**kwargs):
            raise ValidationError.from_exception_data(
                title="DecisionsResponse",
                line_errors=[
                    {
                        "type": "list_type",
                        "loc": ("decisions",),
                        "msg": "Input should be a valid array",
                        "input": "invalid",
                    }
                ],
            )

        mock_client = MagicMock()
        mock_client.chat.completions.create = mock_create

        mock_factory = MagicMock(return_value=mock_client)

        chunks = [{"source_id": "test_1", "content": "Test content"}]

        with (
            patch("core.llm.clients.CLIENT_FACTORIES", {"openai": mock_factory}),
            patch("core.llm.handlers.openai.run_tool_loop", new_callable=AsyncMock),
        ):
            from core.llm.analysis import analyze_with_provider

            # Should return empty response instead of raising
            result = await analyze_with_provider(provider="openai", model_name="gpt-4", chunks=chunks)

            assert result is not None
            assert len(result.decisions) == 0
            assert len(result.macro_events) == 0


class TestAnthropicMessageFlattening:
    """Tests for Anthropic message content flattening in analyze_with_provider."""

    async def _run_flattening(self, messages_in):
        """Helper: run analyze_with_provider's flattening on messages by
        tracing what gets passed to the mocked LLM client."""
        from core.llm.analysis import analyze_with_provider

        captured = {}

        async def mock_create(**kwargs):
            captured["messages"] = kwargs.get("messages", [])
            captured["system"] = kwargs.get("system")
            return DecisionsResponse(decisions=[], macro_events=[])

        mock_client = MagicMock()
        mock_client.chat.completions.create = mock_create
        mock_factory = MagicMock(return_value=mock_client)
        chunks = [{"source_id": "test_1", "content": "test"}]

        with (
            patch("core.llm.clients.CLIENT_FACTORIES", {"anthropic": mock_factory}),
            patch("core.llm.handlers.anthropic.run_tool_loop", new_callable=AsyncMock),
            patch("core.llm.analysis.PromptFactory.build_analysis_messages", return_value=messages_in),
        ):
            await analyze_with_provider(provider="anthropic", model_name="claude-haiku-4-5", chunks=chunks)
            return captured.get("messages", [])

    @pytest.mark.asyncio
    async def test_flattens_nested_text_blocks(self):
        """Nested text content blocks are flattened to plain strings."""
        messages = [
            {"role": "system", "content": "You are a helpful trading assistant."},
            {"role": "user", "content": [{"type": "text", "text": "Analyze this market data."}]},
        ]
        flat = await self._run_flattening(messages)
        for msg in flat:
            assert isinstance(msg["content"], str)

    @pytest.mark.asyncio
    async def test_flattens_tool_calls(self):
        """Tool call blocks are rendered as [Tool Call: ...] strings."""
        messages = [
            {"role": "system", "content": "system prompt"},
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Let me check that."},
                    {"name": "web_search", "input": {"query": "NVDA price"}, "type": "tool_use", "id": "abc123"},
                ],
            },
        ]
        flat = await self._run_flattening(messages)
        assert "[Tool Call: web_search({'query': 'NVDA price'})]" in flat[-1]["content"]

    @pytest.mark.asyncio
    async def test_preserves_system_message(self):
        """System message is extracted to the 'system' kwarg (Anthropic convention)."""
        messages = [
            {"role": "system", "content": "You are a helpful trading assistant."},
            {"role": "user", "content": "plain text"},
        ]
        captured = {}

        async def mock_create(**kwargs):
            captured["system"] = kwargs.get("system")
            captured["messages"] = kwargs.get("messages", [])
            return DecisionsResponse(decisions=[], macro_events=[])

        mock_client = MagicMock()
        mock_client.chat.completions.create = mock_create
        mock_factory = MagicMock(return_value=mock_client)
        chunks = [{"source_id": "test_1", "content": "test"}]

        with (
            patch("core.llm.clients.CLIENT_FACTORIES", {"anthropic": mock_factory}),
            patch("core.llm.handlers.anthropic.run_tool_loop", new_callable=AsyncMock),
            patch("core.llm.analysis.PromptFactory.build_analysis_messages", return_value=messages),
        ):
            from core.llm.analysis import analyze_with_provider

            await analyze_with_provider(provider="anthropic", model_name="claude-haiku-4-5", chunks=chunks)
        assert captured["system"] == "You are a helpful trading assistant."
        # System removed from messages list; only user message remains
        roles = [m["role"] for m in captured["messages"]]
        assert "system" not in roles

    @pytest.mark.asyncio
    async def test_plain_string_content_unchanged(self):
        """Messages with plain string content pass through unchanged."""
        messages = [
            {"role": "user", "content": "Analyze NVDA."},
        ]
        flat = await self._run_flattening(messages)
        assert flat[0]["content"] == "Analyze NVDA."
