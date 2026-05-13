"""Verification script for Step 15: Decision Reasoning Embedding."""

import asyncio
import logging

from core.models import DecisionObject
from memory.store import add_memory, retrieve_context

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify")

async def verify_step_15():
    """Verify that decision reasoning can be embedded and retrieved."""
    
    # Simulate a decision
    decision = DecisionObject(
        ticker="AAPL",
        signal="BUY",
        confidence=90,
        reasoning="Apple's new AI features are driving strong iPhone demand.",
        source_id="news_test_123",
        model_provider="openai",
        model_name="gpt-4o"
    )
    
    memory_content = (
        f"DECISION REASONING: {decision.ticker} {decision.signal} | "
        f"REASONING: {decision.reasoning}"
    )
    
    print(f"\n1. Adding decision reasoning to memory: '{memory_content}'")
    success = add_memory(
        content=memory_content,
        metadata={
            "type": "decision_reasoning",
            "ticker": decision.ticker,
            "signal": decision.signal,
            "decision_id": "test_id_999"
        }
    )
    
    if success:
        print("✅ Decision reasoning embedded successfully.")
    else:
        print("❌ Failed to embed reasoning.")
        return

    print("\n2. Retrieving context for query: 'Apple iPhone demand'")
    context = retrieve_context("Apple iPhone demand")
    
    if decision.reasoning in context:
        print(f"✅ Context retrieved correctly:\n{context}")
    else:
        print(f"❌ Context retrieval failed. Result was: '{context}'")

if __name__ == "__main__":
    asyncio.run(verify_step_15())
