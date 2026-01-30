"""Mocked tests for the Gemini tool-calling loop."""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from core.llm import analyze_with_provider
from core.models import DecisionsResponse, DecisionObject

@pytest.mark.asyncio
async def test_analyze_with_provider_gemini_tool_loop():
    """Test that analyze_with_provider handles a Gemini tool call loop."""
    
    mock_chunks = [{"source_id": "src_g1", "content": "Check Apple price"}]
    
    # Mock Gemini Client and candidates
    mock_client = MagicMock()
    mock_raw_client = mock_client.client
    
    # 1. First response: Function Call
    mock_part = MagicMock()
    mock_part.text = "I'll check the price."
    mock_part.function_call.name = "get_stock_quote"
    mock_part.function_call.args = {"ticker": "AAPL"}
    
    mock_content = MagicMock()
    mock_content.parts = [mock_part]
    
    mock_candidate = MagicMock()
    mock_candidate.content = mock_content
    
    mock_resp_1 = MagicMock()
    mock_resp_1.candidates = [mock_candidate]
    
    # 2. Second response: No Function Call (break loop)
    mock_part_2 = MagicMock()
    mock_part_2.text = "Done."
    mock_part_2.function_call = None
    
    mock_content_2 = MagicMock()
    mock_content_2.parts = [mock_part_2]
    
    mock_candidate_2 = MagicMock()
    mock_candidate_2.content = mock_content_2
    
    mock_resp_2 = MagicMock()
    mock_resp_2.candidates = [mock_candidate_2]
    
    # Mock final decision
    mock_final_decision = DecisionsResponse(
        decisions=[
            DecisionObject(
                signal="BUY",
                confidence=95,
                reasoning="Price is good.",
                ticker="AAPL",
                source_id="src_g1",
                price=150.0
            )
        ]
    )
    
    with patch("core.llm.tools.MarketDataManager") as mock_manager_cls, \
         patch("core.llm.analysis.clients.CLIENT_FACTORIES") as mock_factories:
        
        mock_manager = mock_manager_cls.return_value
        mock_manager.get_quote = AsyncMock(return_value=MagicMock(ticker="AAPL", price=150.0, market_cap=2.5e12, exists=True))
        
        mock_factories.get.return_value = lambda: mock_client
        
        # Configure raw client for async generate_content
        # In analysis.py we use raw_client.aio.models.generate_content
        mock_aio = mock_raw_client.aio
        mock_aio.models.generate_content = AsyncMock(side_effect=[mock_resp_1, mock_resp_2])
        
        # Mock final instructor extraction
        mock_client.chat.completions.create = AsyncMock(return_value=mock_final_decision)
        
        # Execute
        result = await analyze_with_provider("gemini", "gemini-3-flash-preview", mock_chunks)
        
        # Assertions
        assert len(result.decisions) == 1
        assert result.decisions[0].ticker == "AAPL"
        assert mock_manager.get_quote.call_count == 1
        assert mock_aio.models.generate_content.call_count == 2
