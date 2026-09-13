"""Tests for the get_ticker_news tool and FMP stable stock news integration."""

from unittest.mock import AsyncMock, patch

import pytest

from core.llm.handlers.base import execute_tool
from core.llm.tools import CANONICAL_TOOLS_REGISTRY


def test_get_ticker_news_tool_registration():
    """Verify get_ticker_news is registered in CANONICAL_TOOLS_REGISTRY with valid schema."""
    assert "get_ticker_news" in CANONICAL_TOOLS_REGISTRY
    schema = CANONICAL_TOOLS_REGISTRY["get_ticker_news"]
    assert schema["type"] == "function"
    fn = schema["function"]
    assert fn["name"] == "get_ticker_news"
    assert "ticker" in fn["parameters"]["properties"]
    assert "limit" in fn["parameters"]["properties"]
    assert "ticker" in fn["parameters"]["required"]


@pytest.mark.asyncio
async def test_execute_get_ticker_news_success():
    """Verify execute_get_ticker_news_tool formats news articles into markdown."""
    from analysis.ticker_news import execute_get_ticker_news_tool

    mock_articles = [
        {
            "symbol": "AAPL",
            "publishedDate": "2026-09-12 12:22:05",
            "publisher": "Investors Business Daily",
            "title": "Apple, Taiwan Semi Lead Five Stocks Near Buy Points",
            "text": "Two hot health care plays are on the list.",
            "url": "https://www.investors.com/news/apple-taiwan-semiconductor/",
        },
        {
            "symbol": "AAPL",
            "publishedDate": "2026-09-12 10:34:16",
            "publisher": "24/7 Wall Street",
            "title": "$2.3 Billion in Daily Profits: Why Betting Against Apple Fails",
            "text": "The Magnificent 7 collectively generate roughly $2.3 billion in operating profits daily.",
            "url": "https://247wallst.com/investing/2026/09/12/apple-profits/",
        },
    ]

    with patch("analysis.ticker_news.fetch_ticker_news", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_articles
        result = await execute_get_ticker_news_tool(ticker="$aapl", limit=2)

        mock_fetch.assert_called_once_with(ticker="AAPL", limit=2)
        assert "=== REAL-TIME NEWS: AAPL (2 articles) ===" in result
        assert "Apple, Taiwan Semi Lead Five Stocks Near Buy Points" in result
        assert "Investors Business Daily" in result
        assert "2026-09-12 12:22:05" in result
        assert "https://www.investors.com/news/apple-taiwan-semiconductor/" in result


@pytest.mark.asyncio
async def test_execute_get_ticker_news_empty():
    """Verify handling when no articles are found for a ticker."""
    from analysis.ticker_news import execute_get_ticker_news_tool

    with patch("analysis.ticker_news.fetch_ticker_news", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = []
        result = await execute_get_ticker_news_tool(ticker="XYZUNKNOWN")

        assert "No recent news found for ticker 'XYZUNKNOWN'" in result


@pytest.mark.asyncio
async def test_execute_get_ticker_news_invalid_ticker():
    """Verify handling of invalid or empty ticker argument."""
    from analysis.ticker_news import execute_get_ticker_news_tool

    result = await execute_get_ticker_news_tool(ticker="  ")
    assert "Error: Invalid or empty ticker symbol provided." in result


@pytest.mark.asyncio
async def test_execute_get_ticker_news_missing_api_key():
    """Verify handling when FMP_API_KEY is not configured."""
    from analysis.ticker_news import fetch_ticker_news

    with patch("analysis.ticker_news.FMP_API_KEY", None):
        articles = await fetch_ticker_news("AAPL")
        assert articles == []


@pytest.mark.asyncio
async def test_execute_tool_dispatch():
    """Verify handlers.base.execute_tool routes get_ticker_news correctly."""
    with patch("core.llm.tools.execute_get_ticker_news_tool", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = "Mocked news markdown"
        res = await execute_tool("get_ticker_news", {"ticker": "NVDA", "limit": 3}, model_name="test_model")

        mock_exec.assert_called_once_with(ticker="NVDA", limit=3)
        assert res == "Mocked news markdown"


@pytest.mark.asyncio
async def test_fetch_ticker_news_http_errors_and_timeout():
    """Verify fetch_ticker_news handles 401, 403, 429, 500, and timeout without throwing exceptions."""
    import httpx

    from analysis.ticker_news import fetch_ticker_news

    for status in (401, 403, 429, 500):
        mock_resp = httpx.Response(status_code=status, text="Error body", request=httpx.Request("GET", "https://test"))
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            articles = await fetch_ticker_news("AAPL", api_key="fake-key")
            assert articles == []

    with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Timeout")):
        articles = await fetch_ticker_news("AAPL", api_key="fake-key")
        assert articles == []


@pytest.mark.asyncio
async def test_fetch_ticker_news_limit_clamping():
    """Verify limit is clamped between 1 and 20."""
    import httpx

    from analysis.ticker_news import fetch_ticker_news

    mock_resp = httpx.Response(status_code=200, json=[], request=httpx.Request("GET", "https://test"))
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        await fetch_ticker_news("AAPL", limit=100, api_key="fake-key")
        assert mock_get.call_args.kwargs["params"]["limit"] == 20

        await fetch_ticker_news("AAPL", limit=0, api_key="fake-key")
        assert mock_get.call_args.kwargs["params"]["limit"] == 1


@pytest.mark.asyncio
async def test_fetch_ticker_news_edge_cases():
    """Verify empty ticker, non-list response, and general exception handling."""
    import httpx

    from analysis.ticker_news import fetch_ticker_news, sanitize_ticker
    from core.llm.tools import execute_get_ticker_news_tool as core_exec_tool

    assert sanitize_ticker("") == ""
    assert await fetch_ticker_news("") == []

    # Non-list response
    mock_resp = httpx.Response(
        status_code=200, json={"error": "bad request"}, request=httpx.Request("GET", "https://test")
    )
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        articles = await fetch_ticker_news("AAPL", api_key="fake-key")
        assert articles == []

    # Unexpected exception in fetch
    with patch("httpx.AsyncClient.get", side_effect=RuntimeError("Network explosion")):
        articles = await fetch_ticker_news("AAPL", api_key="fake-key")
        assert articles == []

    # Exception in core tool wrapper
    with patch("analysis.ticker_news.execute_get_ticker_news_tool", side_effect=ValueError("Boom")):
        err_msg = await core_exec_tool("AAPL")
        assert "Error fetching news for 'AAPL': Boom" in err_msg


def test_tool_available_in_all_flows():
    """Verify get_ticker_news is available across all core model handlers and verification flows."""
    from autoresearch.prompt_blocks import AVAILABLE_PROMPT_BLOCKS, render_prompt_blocks
    from core.llm import tools
    from core.llm.handlers.anthropic import DEFAULT_ANTHROPIC_TOOLS
    from core.llm.handlers.gemini import DEFAULT_GEMINI_TOOLS
    from core.llm.handlers.openai import DEFAULT_OPENAI_TOOLS

    # 1. OpenAI / DeepSeek / MiniMax default tools
    assert tools.GET_TICKER_NEWS_TOOL in DEFAULT_OPENAI_TOOLS

    # 2. Anthropic default tools
    anthropic_names = [t.get("name") for t in DEFAULT_ANTHROPIC_TOOLS if isinstance(t, dict)]
    assert "get_ticker_news" in anthropic_names

    # 3. Gemini default tools
    gemini_names = [t.get("name") for t in DEFAULT_GEMINI_TOOLS if isinstance(t, dict) and "name" in t]
    assert "get_ticker_news" in gemini_names

    # 4. Verifier flow tools (inspect verification module source)
    import inspect

    from core.llm import verification

    source = inspect.getsource(verification.verify_trading_decision)
    assert "tools.GET_TICKER_NEWS_TOOL" in source

    # 5. Autoresearch modular block
    assert "ticker_news_verification" in AVAILABLE_PROMPT_BLOCKS
    rendered = render_prompt_blocks(["ticker_news_verification"])
    assert "TICKER NEWS VERIFICATION" in rendered
    assert "get_ticker_news" in rendered


@pytest.mark.asyncio
async def test_cross_provider_schema_and_call_compatibility():
    """Verify tool definition translates and dispatches identically across OpenAI, Anthropic, Gemini, DeepSeek, and MiniMax."""
    from google.genai import types as gemini_types

    from core.llm import tools
    from core.llm.handlers import base, deepseek

    # 1. Canonical / OpenAI
    openai_tool = tools.GET_TICKER_NEWS_TOOL
    assert openai_tool["type"] == "function"
    assert openai_tool["function"]["name"] == "get_ticker_news"

    # 2. Anthropic format
    anthropic_tool = tools.to_anthropic(openai_tool)
    assert anthropic_tool["name"] == "get_ticker_news"
    assert "input_schema" in anthropic_tool
    assert anthropic_tool["input_schema"]["type"] == "object"
    assert "ticker" in anthropic_tool["input_schema"]["required"]

    # 3. Gemini format
    gemini_tool = tools.to_gemini(openai_tool)
    assert gemini_tool["name"] == "get_ticker_news"
    assert "parameters" in gemini_tool
    # Verify Google GenAI SDK accepts the declaration without error
    sdk_tool = gemini_types.Tool(function_declarations=[gemini_tool])
    assert sdk_tool.function_declarations is not None
    assert len(sdk_tool.function_declarations) == 1

    # 4. DeepSeek tool list builder
    ds_tools = deepseek._build_deepseek_tool_list()
    assert any(t["function"]["name"] == "get_ticker_news" for t in ds_tools)

    # 5. Cross-provider simulated call dispatch
    mock_articles = [
        {
            "symbol": "SPY",
            "publishedDate": "2026-09-12 10:00:00",
            "publisher": "Financial News",
            "title": "Markets Steady Ahead of Open",
            "text": "S&P 500 futures trade flat.",
            "url": "https://example.com/spy-news",
        }
    ]

    with patch("analysis.ticker_news.fetch_ticker_news", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_articles

        # OpenAI style: arguments dict parsed from json string
        out_openai = await base.execute_tool("get_ticker_news", {"ticker": "SPY", "limit": 1}, model_name="gpt-4o")

        # Anthropic / MiniMax style: input dict from tool_use block
        out_anthropic = await base.execute_tool(
            "get_ticker_news", {"ticker": "SPY", "limit": 1}, model_name="claude-3-5-sonnet"
        )

        # Gemini style: args dict from function_call
        out_gemini = await base.execute_tool(
            "get_ticker_news", {"ticker": "SPY", "limit": 1}, model_name="gemini-2.0-flash"
        )

        # DeepSeek style: arguments dict
        out_deepseek = await base.execute_tool(
            "get_ticker_news", {"ticker": "SPY", "limit": 1}, model_name="deepseek-v3"
        )

        assert out_openai == out_anthropic == out_gemini == out_deepseek
        assert "Markets Steady Ahead of Open" in out_openai
