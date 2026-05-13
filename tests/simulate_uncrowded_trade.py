import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../apps/engine')))

from analyze import analyze_chunks

async def run_simulation():
    news_batch = [
        {
            "source_id": "sim_001",
            "content": "Commodities: All eyes are on oil, but the effects of the war in Iran on fertilizer can't be understated. The prices of key chemicals like urea and ammonia are soaring just in time for the pivotal spring planting season, threatening to disrupt US food production."
        }
    ]

    print("Running analyze_chunks...")
    decisions, macro_events, agg_ctx, uncrowded_ctx = await analyze_chunks(news_batch)

    print("\n=== MACRO EVENTS ===")
    for event in macro_events:
        print(f"[{event.catalyst_type}] {event.event_name} (Conf: {event.confidence}) - {event.model_name}")
        print(f"Reasoning: {event.reasoning}")

    print("\n=== DECISIONS ===")
    for d in decisions:
        print(f"[{d.ticker}] {d.signal} (Conf: {d.confidence}) [{d.catalyst_type}] - {d.model_name}")
        print(f"Reasoning: {d.reasoning}")
        print(f"Strategic Intent: {getattr(d, 'strategy_reasoning', 'None')}")


if __name__ == "__main__":
    asyncio.run(run_simulation())
