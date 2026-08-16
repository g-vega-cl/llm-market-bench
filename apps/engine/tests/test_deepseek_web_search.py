"""TDD Tests for DeepSeek Web Search Tool & Autoresearch Integration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autoresearch.researcher import PromptResearchResult
from core.llm import tools
from core.llm.handlers import base, deepseek


@pytest.mark.asyncio
async def test_execute_web_search_tool_success():
    """Verify execute_web_search_tool queries search backend and formats markdown results."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = """
    <html>
        <body>
            <div class="result">
                <a class="result__url" href="https://example.com/linde-news">https://example.com/linde-news</a>
                <a class="result__title">Linde Signs $1B Semiconductor Gas Deal</a>
                <div class="result__snippet">Linde plc announced a major long-term industrial gas contract for chip fabrication.</div>
            </div>
        </body>
    </html>
    """
    mock_resp.json.return_value = {}

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        output = await tools.execute_web_search_tool("Linde semiconductor contract")

        assert "Linde Signs $1B Semiconductor Gas Deal" in output
        assert "https://example.com/linde-news" in output
        assert "chip fabrication" in output


@pytest.mark.asyncio
async def test_execute_tool_web_search_dispatch():
    """Verify handlers.base.execute_tool dispatches 'web_search' to execute_web_search_tool."""
    with patch("core.llm.tools.execute_web_search_tool", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = "=== WEB SEARCH RESULTS ===\n- Result 1"
        res = await base.execute_tool(
            "web_search",
            {"query": "Linde fab demand"},
            model_name="deepseek-v4-flash",
        )
        mock_search.assert_awaited_once_with("Linde fab demand")
        assert "=== WEB SEARCH RESULTS ===" in res


@pytest.mark.asyncio
async def test_deepseek_run_tool_loop_executes_web_search():
    """Verify DeepSeek tool loop passes WEB_SEARCH_TOOL and handles tool execution."""
    raw_client = MagicMock()

    # Step 1: LLM returns a tool call for web_search
    tool_call_obj = MagicMock()
    tool_call_obj.id = "call_search_1"
    tool_call_obj.type = "function"
    tool_call_obj.function.name = "web_search"
    tool_call_obj.function.arguments = '{"query": "Linde latest earnings"}'

    msg1 = MagicMock()
    msg1.role = "assistant"
    msg1.content = "Let me search for Linde earnings..."
    msg1.tool_calls = [tool_call_obj]
    msg1.reasoning_content = None

    choice1 = MagicMock()
    choice1.message = msg1
    resp1 = MagicMock()
    resp1.choices = [choice1]

    # Step 2: LLM finishes after receiving tool output
    msg2 = MagicMock()
    msg2.role = "assistant"
    msg2.content = "Analysis complete."
    msg2.tool_calls = None
    msg2.reasoning_content = None

    choice2 = MagicMock()
    choice2.message = msg2
    resp2 = MagicMock()
    resp2.choices = [choice2]

    raw_client.chat.completions.create = AsyncMock(side_effect=[resp1, resp2])

    messages = [{"role": "user", "content": "Analyze LIN"}]

    with patch("core.llm.handlers.base.execute_tool", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = "=== SEARCH RESULTS: Linde Q2 Beat ==="
        await deepseek.run_tool_loop(
            raw_client=raw_client,
            model_name="deepseek-v4-flash",
            messages=messages,
            enable_web_search=True,
        )

        mock_exec.assert_awaited_once_with(
            "web_search",
            {"query": "Linde latest earnings"},
            "deepseek-v4-flash",
        )
        assert len(messages) >= 3
        # Check tool message was appended
        tool_msgs = [m for m in messages if m.get("role") == "tool"]
        assert len(tool_msgs) == 1
        assert "Linde Q2 Beat" in tool_msgs[0]["content"]


def test_autoresearch_selected_tools_allows_web_search():
    """Verify AutoResearcher PromptResearchResult accepts 'web_search' in selected_tools."""
    res = PromptResearchResult(
        new_prompt_text="Strategy prompt text...",
        selected_tools=["get_portfolio_ledger", "web_search"],
        selected_prompt_blocks=["let_winners_run"],
        change_description="Added web_search capability for catalyst discovery.",
        experiment_type="incremental",
        research_reasoning="Enables real-time news retrieval.",
        confidence=90,
    )
    assert "web_search" in res.selected_tools
