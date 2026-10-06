import pytest

from core.llm.prompt_factory import PromptFactory


@pytest.mark.asyncio
async def test_prompt_factory_refinements():
    """Verify PromptFactory creates grammatically correct system prompts and centralized messages."""
    kwargs = {
        "calendar_knowledge": "Test Calendar",
        "current_day_info": "Monday",
        "portfolio_context": "None",
        "held_tickers_list": "AAPL",
        "macro_context": "Bullish",
        "context": "History",
        "news_content": "News",
        "min_trade_value": 1000.0,
    }

    # 1. Test Grammar Fix: Leading period in stripped system prompt for openai
    openai_msgs = await PromptFactory.build_analysis_messages("openai", **kwargs)
    system_content = openai_msgs[0]["content"]

    assert ". Use tools to verify market data" in system_content, "Grammar fix: Leading period must be present"

    # 2. Verify Ticker Suggestion messages (centralized in PromptFactory)
    theme = "AI Chips"
    ticker_msgs = PromptFactory.build_ticker_suggestion_messages("gemini", event_summary=theme)
    assert len(ticker_msgs) == 1, "Ticker suggestion should have 1 message (user)"
    assert theme in ticker_msgs[0]["content"], "Theme must be present in content"
