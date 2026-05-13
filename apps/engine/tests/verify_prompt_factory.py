
import os
import sys

# Add apps/engine to path
sys.path.append(os.path.join(os.getcwd(), "apps", "engine"))

from core.llm.prompt_factory import PromptFactory


def test_prompt_factory_refinements():
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
        "min_trade_value": 1000.0
    }
    
    try:
        # 1. Test Grammar Fix: Leading period in stripped system prompt
        # We need a provider that triggers stripping (e.g., openai)
        openai_msgs = PromptFactory.build_analysis_messages("openai", **kwargs)
        system_content = openai_msgs[0]["content"]
        
        # Check for ". Use tools"
        assert ". Use tools to verify market data" in system_content, "Grammar fix: Leading period must be present"
        print("✅ Grammar Fix: System prompt has correct sentence boundary.")

        # 2. Test Gemini Search Support
        # With enable_web_search=True, Gemini should retain the search instructions
        kwargs_with_search = {**kwargs, "enable_web_search": True}
        gemini_search = PromptFactory.build_analysis_messages("gemini", **kwargs_with_search)
        gemini_user_content = gemini_search[1]["content"]
        assert "WEB SEARCH CAPABILITY" in gemini_user_content, "Gemini should keep search info when enabled"
        assert "google_search" in gemini_user_content, "Gemini should keep google_search tool instructions when enabled"
        print("✅ Gemini Search: Instructions are preserved when enabled.")

        kwargs_without_search = dict(kwargs)
        gemini_no_search = PromptFactory.build_analysis_messages("gemini", **kwargs_without_search)
        gemini_no_search_content = gemini_no_search[1]["content"]
        assert "WEB SEARCH CAPABILITY" not in gemini_no_search_content, "Gemini should strip search info when disabled"
        print("✅ Gemini Safety: Search instructions are stripped when disabled.")

        # 3. Verify Ticker Suggestion messages (newly migrated to PromptFactory)
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
    test_prompt_factory_refinements()
    print("\nAll refinements verified! PromptFactory is now grammatically correct and Gemini-safe.")
