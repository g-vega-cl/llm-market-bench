import asyncio
import logging
import json
from analyze import analyze_chunks
from consensus import process_consensus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("engine")

# User's examples
EXAMPLES = [
    {
        "source_id": "oil_armada",
        "content": "Oil climbed to a four-month high after President Trump warned Iran that a “massive armada” is on the way."
    },
    {
        "source_id": "gold_stocks",
        "content": "In fact, gold is surging so much that the S&P 500 is moving lower relative to gold, according to Stifel’s chief equity strategist Barry Bannister. That isn’t exactly an encouraging sign: according to Bannister, there have only been four instances that stocks have lagged gold in the past century, and each time it was a signal that the stock market was about to plateau."
    },
    {
        "source_id": "weak_dollar",
        "content": "What does a weaker dollar mean? For investors, the issue is confidence. When US leaders appear relaxed about a weaker dollar, markets see less commitment to currency stability. That pushes investors to reassess the risk of holding US assets and demand higher returns to compensate. Combined with growing doubts over policy direction, debt sustainability, and the Fed’s independence, a softer dollar stance risks discouraging foreign investment."
    }
]

async def verify():
    logger.info("Starting verification with user examples...")
    
    # 1. Analyze chunks
    decisions, macro_events = await analyze_chunks(EXAMPLES)
    
    logger.info(f"Generated {len(macro_events)} macro events.")
    
    for event in macro_events:
        logger.info(f"Event: {event.event_name}")
        logger.info(f"  Ongoing: {event.is_ongoing}")
        logger.info(f"  Future Catalyst: {event.is_future_catalyst}")
        logger.info(f"  Historical Parallel: {event.historical_parallel}")
        logger.info(f"  Reasoning: {event.reasoning}")

    # 2. Process consensus
    if macro_events:
        logger.info("Processing consensus...")
        consensus_events = await process_consensus(macro_events)
        
        logger.info(f"Promoted {len(consensus_events)} events to memory.")
        for ce in consensus_events:
            logger.info(f"Consensus Event: {ce['event_name']}")
            logger.info(f"  Is Ongoing: {ce['is_ongoing']}")
            logger.info(f"  Is Future Catalyst: {ce['is_future_catalyst']}")
            logger.info(f"  Historical Parallel: {ce['historical_parallel']}")
            logger.info(f"  Future Date: {ce['future_date']}")
    else:
        logger.warning("No macro events generated to process consensus.")

if __name__ == "__main__":
    asyncio.run(verify())
