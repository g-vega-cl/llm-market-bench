import asyncio
import sys
import os

# Add apps/engine to path
sys.path.append(os.path.join(os.getcwd(), "apps", "engine"))

from core.llm.analysis import analyze_with_provider
from core.config import GEMINI_MODEL

async def test_horizon_extraction():
    print("\n--- Testing Horizon Watch Extraction Logic ---")
    
    # Example 1: The "Bad" event (memory-like, not a future catalyst)
    bad_news = {
        "source_id": "test_bad",
        "content": "January's lower-than-anticipated 2.4% inflation print has bolstered expectations for Federal Reserve rate cuts later in 2026, sparking a rally in Treasuries and equities."
    }
    
    # Example 2: The "Good" event (pending meeting with outcomes)
    good_news = {
        "source_id": "test_good",
        "content": "The FOMC is scheduled to meet next Wednesday to decide on interest rates. Analysts are split: some expect a 25bps cut, while others believe the Fed will stay hawkish given the recent wage growth data."
    }

    print("\n[TEST 1] Testing 'Later in 2026' event (Expected: is_future_catalyst = False)")
    try:
        resp1 = await analyze_with_provider(
            provider="gemini",
            model_name=GEMINI_MODEL,
            chunks=[bad_news],
            context="",
            portfolio_context=""
        )
        
        bad_event = next((e for e in resp1.macro_events if e.source_id == "test_bad"), None)
        if bad_event:
            print(f"Event: {bad_event.event_name}")
            print(f"is_future_catalyst: {bad_event.is_future_catalyst}")
            if bad_event.is_future_catalyst:
                print("❌ FAILED: Event was incorrectly marked as a future catalyst.")
            else:
                print("✅ PASSED: Event correctly ignored as a future catalyst.")
        else:
            print("⚠️ No macro event identified for Example 1.")
    except Exception as e:
        print(f"❌ TEST 1 FAILED with error: {e}")

    print("\n[TEST 2] Testing FOMC Meeting event (Expected: is_future_catalyst = True + Scenarios)")
    try:
        resp2 = await analyze_with_provider(
            provider="gemini",
            model_name=GEMINI_MODEL,
            chunks=[good_news],
            context="",
            portfolio_context=""
        )
        
        good_event = next((e for e in resp2.macro_events if e.source_id == "test_good"), None)
        if good_event:
            print(f"Event: {good_event.event_name}")
            print(f"is_future_catalyst: {good_event.is_future_catalyst}")
            print(f"Scenario Analysis:\n{good_event.scenario_analysis}")
            
            if good_event.is_future_catalyst and "Scenario A" in (good_event.scenario_analysis or ""):
                print("✅ PASSED: Event correctly identified as future catalyst with structured scenarios.")
            else:
                print("❌ FAILED: Event missing catalyst flag or structured scenarios.")
        else:
            print("⚠️ No macro event identified for Example 2.")
    except Exception as e:
        print(f"❌ TEST 2 FAILED with error: {e}")

if __name__ == "__main__":
    asyncio.run(test_horizon_extraction())
