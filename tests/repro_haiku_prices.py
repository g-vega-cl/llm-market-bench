import asyncio
import logging
import sys
import os
from unittest.mock import MagicMock, AsyncMock, patch

# Add apps/engine to path
sys.path.append(os.path.join(os.getcwd(), "apps", "engine"))

from core.llm.analysis import analyze_with_provider
from core.models import DecisionsResponse, DecisionObject

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("repro")

async def test_haiku_price_backfill():
    print("\n--- Testing Haiku Price Backfill in analyze_with_provider ---")
    
    # Mock news chunks
    chunks = [{"source_id": "test_1", "content": "Tripadvisor (TRIP) is a buy at current levels."}]
    
    # Mock DecisionObject with missing price
    mock_decision = DecisionObject(
        ticker="TRIP",
        signal="BUY",
        confidence=80,
        reasoning="Activist stake reported.",
        source_id="test_1",
        price=None # MISSING PRICE
    )
    
    mock_response = DecisionsResponse(decisions=[mock_decision], macro_events=[])
    
    # Mock MarketDataManager for the backfill
    mock_quote = MagicMock()
    mock_quote.exists = True
    mock_quote.price = 28.50
    
    with patch('core.llm.clients.CLIENT_FACTORIES', {'anthropic': MagicMock()}), \
         patch('core.llm.handlers.anthropic.run_tool_loop', AsyncMock()), \
         patch('core.llm.clients.close_client', AsyncMock()), \
         patch('core.llm.logger.log_reasoning_trace', AsyncMock()):
        
        # Mock the final extraction call
        # The factory returns a client, client.chat.completions.create returns the response
        mock_client = MagicMock()
        from core.llm.clients import CLIENT_FACTORIES
        CLIENT_FACTORIES['anthropic'].return_value = mock_client
        
        # Note: Instructor wrapped clients return the model directly
        mock_client.chat.completions.create.return_value = mock_response
        
        # Mock MarketDataManager in analyze.py
        with patch('apps.engine.analyze.MarketDataManager') as MockMDM:
            MockMDM.return_value.get_quote = AsyncMock(return_value=mock_quote)
            
            # Import within patch or use full path
            from analyze import analyze_chunks
            
            # We need to mock Portfolio as well since it's used in analyze_chunks
            with patch('analyze.Portfolio') as MockPortfolio:
                mock_port = MockPortfolio.return_value
                mock_port.initialize = AsyncMock()
                mock_port.positions = {}
                mock_port.get_portfolio_summary.return_value = "Cash: 10000"
                mock_port.save_metrics = AsyncMock()
                
                # We need to mock MODELS to only include anthropic for this test
                with patch('analyze.MODELS', [{"provider": "anthropic", "model": "claude-haiku-4-5"}]):
                    decisions, events, context = await analyze_chunks(chunks)
                    
                    print(f"Decisions: {decisions}")
                    
                    if decisions:
                        d = decisions[0]
                        print(f"Ticker: {d.ticker}, Price: {d.price}")
                        assert d.price == 28.50, f"Expected 28.50, got {d.price}"
                        print("✅ PASS: Price was correctly backfilled when missing.")
                    else:
                        print("❌ FAIL: No decisions returned.")

if __name__ == "__main__":
    asyncio.run(test_haiku_price_backfill())
