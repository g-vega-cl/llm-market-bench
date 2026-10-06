import asyncio
import sys
from pathlib import Path

# Add apps/engine to path safely
ENGINE_DIR = Path(__file__).resolve().parent.parent
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

from core.llm.prompt_factory import PromptFactory  # noqa: E402


async def test_prompt_factory_refinements():
    print("Testing PromptFactory refinements...")

    # Standard analysis args
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

    try:
        # 1. Test Grammar Fix: Leading period in stripped system prompt
        # We need a provider that triggers stripping (e.g., openai)
        openai_msgs = await PromptFactory.build_analysis_messages("openai", **kwargs)
        system_content = openai_msgs[0]["content"]

        # Check for ". Use tools"
        assert ". Use tools to verify market data" in system_content, "Grammar fix: Leading period must be present"
        print("✅ Grammar Fix: System prompt has correct sentence boundary.")

        # 2. Verify Ticker Suggestion messages (centralized in PromptFactory)
        theme = "AI Chips"
        ticker_msgs = PromptFactory.build_ticker_suggestion_messages("gemini", event_summary=theme)
        assert len(ticker_msgs) == 1, "Ticker suggestion should have 1 message (user)"
        assert theme in ticker_msgs[0]["content"], "Theme must be present in content"
        print("✅ Ticker Suggestion: Centralized construction verified.")

    except AssertionError as e:
        print(f"❌ Assertion failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_prompt_factory_refinements())
    print("\nAll refinements verified! PromptFactory is now grammatically correct and Gemini-safe.")
