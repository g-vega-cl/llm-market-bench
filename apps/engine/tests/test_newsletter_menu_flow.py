"""TDD Tests for Newsletter Pre-Filter, Menu, and Memory RAG Tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.models import DecisionsResponse


# We define mock models to avoid importing nonexistent ones if pre_filter.py is not created yet
class MockTriageItem:
    def __init__(self, source_id, summary):
        self.source_id = source_id
        self.summary = summary


class MockTriageResponse:
    def __init__(self, summaries):
        self.summaries = summaries


@pytest.mark.asyncio
async def test_fetch_newsletter_tool_success():
    """Verify that fetch_newsletter_content queries the database and returns content."""
    mock_data = [
        {
            "source_id": "news_test_1",
            "content": "This is full newsletter text 1",
            "sender": "sender1@test.com",
            "subject": "Subject 1",
        },
        {
            "source_id": "news_test_2",
            "content": "This is full newsletter text 2",
            "sender": "sender2@test.com",
            "subject": "Subject 2",
        },
    ]

    mock_response = MagicMock()
    mock_response.data = mock_data

    mock_table = MagicMock()
    mock_table.select.return_value.in_.return_value.execute.return_value = mock_response

    mock_supabase = MagicMock()
    mock_supabase.table.return_value = mock_table

    with patch("core.llm.tools.get_supabase_client", return_value=mock_supabase):
        from core.llm.tools import execute_fetch_newsletter_content_tool

        result = await execute_fetch_newsletter_content_tool(["news_test_1", "news_test_2"])

        assert "news_test_1" in result
        assert "This is full newsletter text 1" in result
        assert "sender1@test.com" in result
        assert "news_test_2" in result
        assert "This is full newsletter text 2" in result


@pytest.mark.asyncio
async def test_memories_rag_tool_success():
    """Verify that search_past_memories calls retrieve_context and returns the RAG content."""
    mock_context_str = (
        "- [MARKET EVENT] Fed keeps interest rates unchanged.\n- [PAST REASONING] AAPL BUY: Strong earnings."
    )

    with patch("memory.store.retrieve_context", return_value=mock_context_str) as mock_retrieve:
        from core.llm.tools import execute_search_past_memories_tool

        result = await execute_search_past_memories_tool("Fed rates", limit=3, model_name="test_model")

        mock_retrieve.assert_called_once_with("Fed rates", model_name="test_model", limit=3)
        assert "Fed keeps interest rates unchanged" in result
        assert "AAPL BUY" in result


@pytest.mark.asyncio
async def test_pre_filter_summary_generation():
    """Verify that the pre-filter task calls the DeepSeek Flash model and returns a summary map."""
    chunks = [
        {
            "source_id": "news_bloomberg_1",
            "content": "Raw text Bloomberg about AI chips",
            "sender": "bloomberg",
            "subject": "AI Chips",
        },
        {
            "source_id": "news_reuters_2",
            "content": "Raw text Reuters about Fed policy",
            "sender": "reuters",
            "subject": "Fed rates",
        },
    ]

    mock_triage_item_1 = MagicMock()
    mock_triage_item_1.source_id = "news_bloomberg_1"
    mock_triage_item_1.summary = "Concise summary about AI chips."

    mock_triage_item_2 = MagicMock()
    mock_triage_item_2.source_id = "news_reuters_2"
    mock_triage_item_2.summary = "Concise summary about Fed rates."

    mock_instructor_resp = MagicMock()
    mock_instructor_resp.summaries = [mock_triage_item_1, mock_triage_item_2]

    # Mock get_deepseek_client and chat completions
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_instructor_resp)

    with patch("core.llm.clients.get_deepseek_client", return_value=mock_client):
        from analysis.pre_filter import summarize_newsletters

        summary_map = await summarize_newsletters(chunks)

        assert len(summary_map) == 2
        assert summary_map["news_bloomberg_1"] == "Concise summary about AI chips."
        assert summary_map["news_reuters_2"] == "Concise summary about Fed rates."


@pytest.mark.asyncio
async def test_analyze_chunks_incorporates_summaries():
    """Verify that analyze_chunks pre-filters newsletters and formats news_content with summaries."""
    chunks = [
        {"source_id": "news_test_1", "content": "Raw text 1", "sender": "test1", "subject": "Sub1"},
    ]

    mock_summaries = {"news_test_1": "Pre-filtered summary 1"}

    # Mock summarize_newsletters, analyze_with_provider and database queries inside analyze_chunks
    with (
        patch("analysis.pre_filter.summarize_newsletters", AsyncMock(return_value=mock_summaries)) as mock_pre_filter,
        patch(
            "core.llm.analyze_with_provider", AsyncMock(return_value=DecisionsResponse(decisions=[], macro_events=[]))
        ) as mock_analyze,
        patch("core.db.get_supabase_client") as mock_db,
        patch("memory.store.retrieve_top_memories", return_value=""),
        patch("memory.store.get_top_trending_concepts", return_value=""),
        patch("execution.market_data.MarketDataManager.get_quotes", AsyncMock(return_value={})),
        patch("execution.portfolio.Portfolio.initialize", AsyncMock()),
        patch("execution.portfolio.Portfolio.get_portfolio_summary", AsyncMock(return_value="")),
        patch("execution.portfolio.Portfolio.save_metrics", AsyncMock()),
    ):
        # Setup mock db query for idempotency
        mock_execute = MagicMock()
        mock_execute.data = []
        mock_db.return_value.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = mock_execute

        from analysis.analyze import analyze_chunks

        await analyze_chunks(chunks)

        mock_pre_filter.assert_called_once_with(chunks)

        # Verify that summaries was passed in
        called_kwargs = mock_analyze.call_args.kwargs
        assert "summaries" in called_kwargs
        assert called_kwargs["summaries"] == mock_summaries


@pytest.mark.asyncio
async def test_analyze_with_provider_builds_menu_from_summaries():
    """Verify that analyze_with_provider formats news_content with summary menu when summaries are provided."""
    chunks = [
        {"source_id": "news_test_1", "content": "Raw text 1", "sender": "test1@sender.com", "subject": "Sub1"},
    ]
    mock_summaries = {"news_test_1": "Pre-filtered summary 1"}

    # Mock CLIENT_FACTORIES to return a mock client
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=[DecisionsResponse(decisions=[], macro_events=[])])

    mock_factory = MagicMock(return_value=mock_client)
    mock_factories = {"openai": mock_factory}

    with (
        patch("core.llm.clients.CLIENT_FACTORIES", mock_factories),
        patch(
            "core.llm.prompt_factory.PromptFactory.build_analysis_messages", AsyncMock(return_value=[])
        ) as mock_build_messages,
    ):
        from core.llm.analysis import analyze_with_provider

        await analyze_with_provider(
            provider="openai",
            model_name="gpt-5.4-nano",
            chunks=chunks,
            summaries=mock_summaries,
        )

        # Verify that the build_analysis_messages was called with formatted menu in news_content
        mock_build_messages.assert_called_once()
        called_kwargs = mock_build_messages.call_args.kwargs
        assert "news_content" in called_kwargs
        assert "Pre-filtered summary 1" in called_kwargs["news_content"]
        assert "news_test_1" in called_kwargs["news_content"]
        # Raw text should not be in the menu
        assert "Raw text 1" not in called_kwargs["news_content"]
