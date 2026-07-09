"""TDD Tests for the Pull-Based Autoresearch and Dynamic Tool Routing architecture."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from autoresearch.researcher import PromptResearchResult
from core.llm.analysis import analyze_with_provider
from core.llm.prompt_factory import PromptFactory
from core.llm.tools import (
    CALCULATE_BUY_QUANTITY_TOOL,
    CANONICAL_TOOLS_REGISTRY,
    GET_PORTFOLIO_LEDGER_TOOL,
    GET_TODAYS_NEWS_MENU_TOOL,
    active_news_chunks,
    active_news_summaries,
    execute_get_market_feeling_tool,
    execute_get_portfolio_ledger_tool,
    execute_get_todays_news_menu_tool,
)


def test_prompt_research_result_schema():
    """Verify that PromptResearchResult parses selected_tools correctly and performs validation."""
    data = {
        "new_prompt_text": "Choose only high-momentum tech stocks.",
        "selected_tools": ["get_portfolio_ledger", "get_todays_news_menu", "web_search"],
        "change_description": "Exposed ledger and menu to enable pull-based trading.",
        "experiment_type": "incremental",
        "research_reasoning": "Moving to a pull architecture keeps prompts smaller.",
        "confidence": 90,
    }
    result = PromptResearchResult(**data)
    assert result.selected_tools == ["get_portfolio_ledger", "get_todays_news_menu", "web_search"]
    assert result.confidence == 90

    # Ensure missing selected_tools raises validation error
    bad_data = data.copy()
    del bad_data["selected_tools"]
    with pytest.raises(ValidationError):
        PromptResearchResult(**bad_data)


def test_canonical_tools_registry():
    """Verify that the tool registry successfully maps all tools by name."""
    assert "get_portfolio_ledger" in CANONICAL_TOOLS_REGISTRY
    assert CANONICAL_TOOLS_REGISTRY["get_portfolio_ledger"] == GET_PORTFOLIO_LEDGER_TOOL
    assert CANONICAL_TOOLS_REGISTRY["get_todays_news_menu"] == GET_TODAYS_NEWS_MENU_TOOL
    assert CANONICAL_TOOLS_REGISTRY["calculate_buy_quantity"] == CALCULATE_BUY_QUANTITY_TOOL
    assert "web_search" in CANONICAL_TOOLS_REGISTRY


@pytest.mark.asyncio
async def test_prompt_factory_experiment_nudge():
    """Verify that PromptFactory selects the minimal user prompt and skips ledger injection for experiment agents."""
    from core.config import AUTORESEARCH_EXPERIMENT_OWNER_IDS

    # Select an ID that is in the experiment group
    exp_owner = list(AUTORESEARCH_EXPERIMENT_OWNER_IDS)[0]

    with (
        patch(
            "autoresearch.prompt_store.get_active_prompt",
            return_value="=== SYSTEM HEADER ===\nStrategy portion\n=== SMA RULES ===",
        ),
        patch(
            "attribution.service.get_active_ledger_xml",
            return_value="<CURRENT_PORTFOLIO_LEDGER>Thesis</CURRENT_PORTFOLIO_LEDGER>",
        ),
    ):
        # 1. Test for experiment agent: minimal template, no ledger injection
        messages = await PromptFactory.build_analysis_messages(
            provider="openai",
            owner_id=exp_owner,
            current_day_info="Date: 2026-07-09",
            market_data_block="Verified Price: AAPL $150.00",
        )

        user_content = messages[-1]["content"]
        system_content = messages[0]["content"]

        # Experiment user prompt should use EXPERIMENT_USER_PROMPT_TEMPLATE (minimal, no NEWS BATCH or GLOBAL MACRO environment header placeholders)
        assert "GLOBAL MACRO ENVIRONMENT:" not in user_content
        assert "OUTPUT FORMAT REQUIREMENTS" in user_content
        assert "calculate_buy_quantity/calculate_sell_quantity" in user_content
        # Assert ledger XML was NOT appended to system prompt
        assert "<CURRENT_PORTFOLIO_LEDGER>" not in system_content

        # 2. Test for control/standard agent: full template, with ledger injection
        control_messages = await PromptFactory.build_analysis_messages(
            provider="openai",
            owner_id="control-agent-id-not-in-experiment",
            current_day_info="Date: 2026-07-09",
            market_data_block="Verified Price: AAPL $150.00",
            portfolio_context="Positions: None",
            context="No context",
            news_content="No news",
            held_tickers_list="None",
            macro_context="No macro",
        )

        control_user_content = control_messages[-1]["content"]
        control_system_content = control_messages[0]["content"]

        # Should inject standard template & ledger XML
        assert "GLOBAL MACRO ENVIRONMENT:" in control_user_content
        assert "<CURRENT_PORTFOLIO_LEDGER>" in control_system_content


@pytest.mark.asyncio
async def test_execute_get_portfolio_ledger_tool_success():
    """Verify that execute_get_portfolio_ledger_tool retrieves cash, equity, positions, and history XML."""
    mock_p_data = [{"cash_balance": 5000.0, "sma": 10000.0, "buying_power": 8000.0, "total_equity": 12000.0}]
    mock_pos_data = [
        {
            "ticker": "AAPL",
            "quantity": 100,
            "average_cost_basis": 150.0,
            "current_price": 160.0,
            "unrealized_pnl_usd": 1000.0,
            "unrealized_pnl_pct": 6.67,
        }
    ]

    mock_response_p = MagicMock()
    mock_response_p.data = mock_p_data

    mock_response_pos = MagicMock()
    mock_response_pos.data = mock_pos_data

    mock_table_p = MagicMock()
    mock_table_p.select.return_value.eq.return_value.execute.return_value = mock_response_p

    mock_table_pos = MagicMock()
    mock_table_pos.select.return_value.eq.return_value.execute.return_value = mock_response_pos

    def table_router(name):
        if name == "portfolios":
            return mock_table_p
        elif name == "position_pnl":
            return mock_table_pos
        return MagicMock()

    mock_supabase = MagicMock()
    mock_supabase.table.side_effect = table_router

    mock_ledger_xml = "<CURRENT_PORTFOLIO_LEDGER>Thesis data</CURRENT_PORTFOLIO_LEDGER>"

    with (
        patch("core.llm.tools.get_supabase_client", return_value=mock_supabase),
        patch("attribution.service.get_active_ledger_xml", return_value=mock_ledger_xml),
    ):
        result = await execute_get_portfolio_ledger_tool("experiment-agent")

        assert "Account Owner: experiment-agent" in result
        assert "Total Account Equity: $12,000.00" in result
        assert "AAPL: 100 shares" in result
        assert "Avg Cost: $150.00" in result
        assert "Thesis data" in result


@pytest.mark.asyncio
async def test_execute_get_todays_news_menu_tool_success():
    """Verify that execute_get_todays_news_menu_tool extracts details from the active context variables."""
    mock_summaries = {
        "news_1": "AI chips demand surges.",
        "news_2": "Fed interest rates kept flat.",
    }
    mock_chunks = [
        {"source_id": "news_1", "sender": "Bloomberg", "subject": "Tech Update"},
        {"source_id": "news_2", "sender": "Reuters", "subject": "Central Bank"},
    ]

    token_summaries = active_news_summaries.set(mock_summaries)
    token_chunks = active_news_chunks.set(mock_chunks)

    try:
        result = await execute_get_todays_news_menu_tool()
        assert "=== TODAY'S NEWSLETTER MENU ===" in result
        assert "news_1" in result
        assert "AI chips demand surges." in result
        assert "Tech Update" in result
        assert "Reuters" in result
    finally:
        active_news_summaries.reset(token_summaries)
        active_news_chunks.reset(token_chunks)


@pytest.mark.asyncio
async def test_execute_get_market_feeling_tool_success():
    """Verify that execute_get_market_feeling_tool queries get_latest_market_feeling."""
    mock_feeling = {
        "sentiment_label": "Bullish",
        "sentiment_emoji": "🚀",
        "confidence_score": 80,
        "feeling_text": "Tech is looking strong today.",
        "causal_cues": "Rates flat.",
        "created_at": "2026-07-09T12:00:00",
    }

    with patch("analysis.market_feeling.get_latest_market_feeling", return_value=mock_feeling):
        result = await execute_get_market_feeling_tool()
        assert "=== LATEST MARKET FEELING ===" in result
        assert "Sentiment: Bullish 🚀" in result
        assert "Confidence: 80%" in result
        assert "Tech is looking strong today." in result


@pytest.mark.asyncio
async def test_analyze_with_provider_pulls_tools():
    """Verify that analyze_with_provider parses active tools from database and runs the loop with override_tools."""
    from core.config import AUTORESEARCH_EXPERIMENT_OWNER_IDS

    exp_owner = list(AUTORESEARCH_EXPERIMENT_OWNER_IDS)[0]

    mock_variant = {
        "variant_tag": "v1",
        "research_output": {"selected_tools": ["get_portfolio_ledger", "get_todays_news_menu", "web_search"]},
    }

    mock_client = MagicMock()
    mock_factory = MagicMock(return_value=mock_client)

    # Set up client factory patch
    with (
        patch("core.llm.clients.CLIENT_FACTORIES", {"openai": mock_factory}),
        patch("autoresearch.prompt_store.get_active_variant", return_value=mock_variant),
        patch(
            "core.llm.prompt_factory.PromptFactory.build_analysis_messages",
            return_value=[{"role": "system", "content": "mock"}],
        ),
        patch("core.llm.handlers.openai.run_tool_loop", new_callable=AsyncMock) as mock_tool_loop,
        patch("core.llm.analysis._try_parse_decisions_response") as mock_parser,
    ):
        mock_parser.return_value = MagicMock()

        # Run analysis for experiment agent
        await analyze_with_provider(
            provider="openai",
            model_name=exp_owner,
            chunks=[{"source_id": "news_1", "content": "mock"}],
            summaries={"news_1": "summary"},
        )

        # Assert that mock_tool_loop was called with override_tools containing selected tools + safety tools
        mock_tool_loop.assert_called_once()
        called_kwargs = mock_tool_loop.call_args[1]
        override_tools = called_kwargs["override_tools"]

        # Extract name list from override_tools schemas
        override_tool_names = [t["function"]["name"] for t in override_tools]
        assert "get_portfolio_ledger" in override_tool_names
        assert "get_todays_news_menu" in override_tool_names

        # Web search must be stripped from override_tools and enabled via enable_web_search flag
        assert "web_search" not in override_tool_names
        assert called_kwargs.get("enable_web_search") is True
        # Safety tools must be force-injected
        assert "calculate_buy_quantity" in override_tool_names
        assert "calculate_sell_quantity" in override_tool_names
