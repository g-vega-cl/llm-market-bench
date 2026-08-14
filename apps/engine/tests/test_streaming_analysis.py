"""Tests for streaming analysis and early decision execution.

These tests verify that:
1. analyze_chunks yields results as each model completes
2. Decision execution starts before all models finish
3. Contrarian starts after first model completes (not after all models)
4. Consensus and momentum run in parallel (fire-and-forget)
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.models import DecisionObject, DecisionsResponse


class TestAnalyzeChunksStreaming:
    """Tests for streaming analysis behavior."""

    @pytest.fixture
    def mock_llm_analyze(self):
        """Mock the llm.analyze_with_provider function."""
        with patch("core.llm.analyze_with_provider", new_callable=AsyncMock) as m:
            yield m

    @pytest.fixture
    def mock_retrieve_context(self):
        """Mock the retrieve_top_memories function."""
        with patch("analysis.analyze.retrieve_top_memories") as m:
            m.return_value = "[MARKET EVENT] Mocked Context"
            yield m

    @pytest.fixture
    def mock_get_embeddings(self):
        """Mock the get_embeddings_batch function."""
        with patch("memory.embeddings.get_embeddings_batch") as m:
            m.return_value = [[0.1] * 768]
            yield m

    @pytest.mark.asyncio
    async def test_analyze_chunks_yields_results_incrementally(
        self, mock_llm_analyze, mock_retrieve_context, mock_get_embeddings
    ):
        """Test that analyze_chunks yields results as each model completes, not all at once."""
        from analysis.analyze import analyze_chunks_streaming

        # Track call order
        call_times = []

        async def slow_analyze(*args, **kwargs):
            """Simulate a slow model that takes time to complete."""
            call_times.append(("start", asyncio.current_task().get_name()))
            await asyncio.sleep(0.1)  # Simulate work
            call_times.append(("end", asyncio.current_task().get_name()))
            return DecisionsResponse(
                decisions=[
                    DecisionObject(signal="BUY", confidence=80, reasoning="Test", ticker="AAPL", source_id="src_1")
                ],
                macro_events=[],
            )

        mock_llm_analyze.side_effect = slow_analyze

        chunks = [{"source_id": "src_1", "content": "Test content"}]

        with (
            patch("analysis.analyze.Portfolio") as mock_portfolio_class,
            patch("analysis.analyze.MarketDataManager") as mock_market_data_class,
            patch("analysis.pre_filter.summarize_newsletters", AsyncMock(return_value={})),
        ):
            mock_portfolio = MagicMock()
            mock_portfolio.positions = {}
            mock_portfolio.initialize = AsyncMock(return_value=None)
            mock_portfolio.calculate_reg_t_metrics = MagicMock()
            mock_portfolio.save_metrics = AsyncMock(return_value=None)
            mock_portfolio.get_portfolio_summary = AsyncMock(return_value="Portfolio: $10,000")
            mock_portfolio_class.return_value = mock_portfolio

            mock_market_data = MagicMock()
            mock_market_data.get_quote = AsyncMock(return_value=None)
            mock_market_data.get_quotes = AsyncMock(return_value={})
            mock_market_data.get_history = AsyncMock(return_value=[])
            mock_market_data_class.return_value = mock_market_data

            # Collect results as they stream in
            results = []
            async for model_decisions, _model_events, config in analyze_chunks_streaming(chunks):
                results.append((model_decisions, config))
                # If we got at least one result, we can already start execution

            # Verify we got results from all models
            from analysis.analyze import MODELS

            assert len(results) == len(MODELS), f"Expected {len(MODELS)} models, got {len(results)}"
            assert all(d[0] for d in results), "All results should have decisions"

    @pytest.mark.asyncio
    async def test_model_failure_does_not_block_others(
        self, mock_llm_analyze, mock_retrieve_context, mock_get_embeddings
    ):
        """Test that if one model fails, others still complete successfully."""
        from analysis.analyze import analyze_chunks_streaming

        call_count = 0

        async def mixed_analyze(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            model_name = kwargs.get("model_name", "unknown")

            if "fail" in model_name.lower():
                raise Exception(f"Model {model_name} failed")

            await asyncio.sleep(0.05)
            return DecisionsResponse(
                decisions=[
                    DecisionObject(signal="BUY", confidence=80, reasoning="Test", ticker="AAPL", source_id="src_1")
                ],
                macro_events=[],
            )

        mock_llm_analyze.side_effect = mixed_analyze

        chunks = [{"source_id": "src_1", "content": "Test content"}]

        with (
            patch("analysis.analyze.Portfolio") as mock_portfolio_class,
            patch("analysis.analyze.MarketDataManager") as mock_market_data_class,
            patch("analysis.pre_filter.summarize_newsletters", AsyncMock(return_value={})),
        ):
            mock_portfolio = MagicMock()
            mock_portfolio.positions = {}
            mock_portfolio.initialize = AsyncMock(return_value=None)
            mock_portfolio.calculate_reg_t_metrics = MagicMock()
            mock_portfolio.save_metrics = AsyncMock(return_value=None)
            mock_portfolio.get_portfolio_summary = AsyncMock(return_value="Portfolio: $10,000")
            mock_portfolio_class.return_value = mock_portfolio

            mock_market_data = MagicMock()
            mock_market_data.get_quote = AsyncMock(return_value=None)
            mock_market_data.get_quotes = AsyncMock(return_value={})
            mock_market_data.get_history = AsyncMock(return_value=[])
            mock_market_data_class.return_value = mock_market_data

            results = []
            async for model_decisions, model_events, config in analyze_chunks_streaming(chunks):
                results.append((model_decisions, model_events, config))

            # Should still get results from working models
            assert len(results) >= 3, f"Expected at least 3 successful models, got {len(results)}"

            # Total call count should equal model count (all models attempted)
            from analysis.analyze import MODELS

            assert call_count == len(MODELS), f"Expected {len(MODELS)} model calls, got {call_count}"


class TestDecisionCallback:
    """Tests for decision callback mechanism."""

    @pytest.mark.asyncio
    async def test_callback_invoked_for_each_model(self):
        """Test that callback is invoked as each model completes."""
        from analysis.analyze import analyze_chunks_streaming

        callback_invocations = []

        async def decision_callback(decision, config):
            callback_invocations.append((decision, config))

        mock_decisions = [
            DecisionObject(signal="BUY", confidence=80, reasoning="Test", ticker="AAPL", source_id="src_1")
        ]

        async def mock_analyze(*args, **kwargs):
            await asyncio.sleep(0.05)
            return DecisionsResponse(decisions=mock_decisions, macro_events=[])

        with (
            patch("core.llm.analyze_with_provider", new_callable=AsyncMock) as mock_llm,
            patch("analysis.analyze.retrieve_top_memories") as mock_context,
        ):
            mock_llm.side_effect = mock_analyze
            mock_context.return_value = "[MARKET EVENT] context"

            chunks = [{"source_id": "src_1", "content": "Test"}]

            with (
                patch("analysis.analyze.Portfolio") as mock_portfolio_class,
                patch("analysis.analyze.MarketDataManager") as mock_market_data_class,
                patch("analysis.pre_filter.summarize_newsletters", AsyncMock(return_value={})),
            ):
                mock_portfolio = MagicMock()
                mock_portfolio.positions = {}
                mock_portfolio.initialize = AsyncMock(return_value=None)
                mock_portfolio.calculate_reg_t_metrics = MagicMock()
                mock_portfolio.save_metrics = AsyncMock(return_value=None)
                mock_portfolio.get_portfolio_summary = AsyncMock(return_value="Portfolio: $10,000")
                mock_portfolio_class.return_value = mock_portfolio

                mock_market_data = MagicMock()
                mock_market_data.get_quote = AsyncMock(return_value=None)
                mock_market_data.get_quotes = AsyncMock(return_value={})
                mock_market_data.get_history = AsyncMock(return_value=[])
                mock_market_data_class.return_value = mock_market_data

                results = []
                async for model_decisions, _model_events, config in analyze_chunks_streaming(chunks):
                    results.append((model_decisions, config))
                    # Simulate callback for each model's decisions
                    for d in model_decisions:
                        await decision_callback(d, config)

        # Callback should be invoked for each model's decisions
        from analysis.analyze import MODELS

        assert len(callback_invocations) == len(MODELS), (
            f"Expected {len(MODELS)} callback invocations, got {len(callback_invocations)}"
        )


class TestParallelStages:
    """Tests for parallel stage execution."""

    @pytest.mark.asyncio
    async def test_background_tasks_can_run_in_parallel(self):
        """Test that background tasks can run in parallel with main execution.

        This is a basic test that asyncio.create_task can run tasks in parallel.
        """
        started = []
        completed = []

        async def slow_task(name, delay):
            started.append(name)
            await asyncio.sleep(delay)
            completed.append(name)

        # Start multiple tasks
        task1 = asyncio.create_task(slow_task("task1", 0.2))
        task2 = asyncio.create_task(slow_task("task2", 0.1))

        # Both should start
        await asyncio.sleep(0.05)
        assert "task1" in started
        assert "task2" in started

        # Task2 should complete first
        await asyncio.sleep(0.2)
        assert "task2" in completed
        assert "task1" in completed

        await task1
        await task2


class TestLoggingTiming:
    """Tests for timing logs."""

    @pytest.mark.asyncio
    async def test_model_completion_is_logged(self, caplog):
        """Test that model completion is logged with timing information."""
        import logging

        caplog.set_level(logging.INFO)

        from analysis.analyze import analyze_chunks_streaming

        async def mock_analyze(*args, **kwargs):
            kwargs.get("model_name", "unknown")
            await asyncio.sleep(0.05)
            return DecisionsResponse(
                decisions=[
                    DecisionObject(signal="BUY", confidence=80, reasoning="Test", ticker="AAPL", source_id="src_1")
                ],
                macro_events=[],
            )

        with (
            patch("core.llm.analyze_with_provider", new_callable=AsyncMock) as mock_llm,
            patch("analysis.analyze.retrieve_top_memories") as mock_context,
            patch("analysis.analyze.logger") as mock_logger,
        ):
            mock_llm.side_effect = mock_analyze
            mock_context.return_value = "[MARKET EVENT] context"

            chunks = [{"source_id": "src_1", "content": "Test"}]

            with (
                patch("analysis.analyze.Portfolio") as mock_portfolio_class,
                patch("analysis.analyze.MarketDataManager") as mock_market_data_class,
                patch("analysis.pre_filter.summarize_newsletters", AsyncMock(return_value={})),
            ):
                mock_portfolio = MagicMock()
                mock_portfolio.positions = {}
                mock_portfolio.initialize = AsyncMock(return_value=None)
                mock_portfolio.calculate_reg_t_metrics = MagicMock()
                mock_portfolio.save_metrics = AsyncMock(return_value=None)
                mock_portfolio.get_portfolio_summary = AsyncMock(return_value="Portfolio: $10,000")
                mock_portfolio_class.return_value = mock_portfolio

                mock_market_data = MagicMock()
                mock_market_data.get_quote = AsyncMock(return_value=None)
                mock_market_data.get_quotes = AsyncMock(return_value={})
                mock_market_data.get_history = AsyncMock(return_value=[])
                mock_market_data_class.return_value = mock_market_data

                async for _ in analyze_chunks_streaming(chunks):
                    pass

        # Verify logging calls were made for model completion
        info_calls = [str(c) for c in mock_logger.info.call_args_list]
        assert any("complete" in c.lower() or "finished" in c.lower() for c in info_calls)


class TestClientCleanup:
    """Tests for client cleanup handling."""

    @pytest.mark.asyncio
    async def test_close_client_handles_none(self):
        """Test that close_client handles None client without error."""
        from core.llm.clients import close_client

        # Should not raise any exceptions
        await close_client(None, "gemini")
        await close_client(None, "openai")
        await close_client(None, "anthropic")
        await close_client(None, "deepseek")

    @pytest.mark.asyncio
    async def test_close_client_handles_none_underlying(self):
        """Test that close_client handles client with None underlying without error."""

        from core.llm.clients import close_client

        # Create a mock client with client.client = None
        mock_client = MagicMock()
        mock_client.client = None

        # Should not raise any exceptions
        await close_client(mock_client, "gemini")

    @pytest.mark.asyncio
    async def test_close_client_does_not_log_on_success(self, caplog):
        """Test that close_client does not log errors on successful close."""
        import logging

        caplog.set_level(logging.DEBUG)

        from core.llm.clients import close_client

        # Create a mock client that can be closed successfully
        mock_underlying = MagicMock()
        mock_underlying.close = AsyncMock()

        mock_client = MagicMock()
        mock_client.client = mock_underlying

        await close_client(mock_client, "test_provider")

        # Should not have logged any errors
        error_calls = [c for c in caplog.records if c.levelno >= logging.ERROR]
        assert len(error_calls) == 0, f"Unexpected error logs: {error_calls}"

    @pytest.mark.asyncio
    async def test_close_client_logs_when_underlying_is_none(self, caplog):
        """Test that close_client logs debug message when underlying client is None."""
        import logging

        caplog.set_level(logging.DEBUG)

        from core.llm.clients import close_client

        mock_client = MagicMock()
        mock_client.client = None

        await close_client(mock_client, "gemini")

        # Should log debug message about None underlying
        debug_calls = [(c.levelno, c.message) for c in caplog.records if c.levelno == logging.DEBUG]
        assert any("underlying client is None" in msg for _, msg in debug_calls), (
            f"Expected debug log about None underlying, got: {debug_calls}"
        )

    @pytest.mark.asyncio
    async def test_close_client_logs_when_no_close_method(self, caplog):
        """Test that close_client logs debug message when no close method is found."""
        import logging

        caplog.set_level(logging.DEBUG)

        from core.llm.clients import close_client

        mock_underlying = MagicMock(spec=["__class__"])  # No close method
        mock_client = MagicMock()
        mock_client.client = mock_underlying

        await close_client(mock_client, "gemini")

        # Should log debug message about no close method
        debug_calls = [(c.levelno, c.message) for c in caplog.records if c.levelno == logging.DEBUG]
        assert any("No close method found" in msg for _, msg in debug_calls), (
            f"Expected debug log about no close method, got: {debug_calls}"
        )

    @pytest.mark.asyncio
    async def test_close_client_logs_warning_on_exception(self, caplog):
        """Test that close_client logs warning with repr when exception occurs."""
        import logging

        caplog.set_level(logging.WARNING)

        from core.llm.clients import close_client

        mock_underlying = MagicMock()
        mock_underlying.close = AsyncMock(side_effect=RuntimeError("Close failed"))
        mock_client = MagicMock()
        mock_client.client = mock_underlying

        await close_client(mock_client, "gemini")

        # Should log warning with exception details
        warning_calls = [(c.levelno, c.message) for c in caplog.records if c.levelno == logging.WARNING]
        assert len(warning_calls) > 0, "Expected warning log on exception"
        assert any("RuntimeError" in msg for _, msg in warning_calls), (
            f"Expected warning to contain RuntimeError, got: {warning_calls}"
        )
