import pytest
from unittest.mock import MagicMock, patch
from analyze import analyze_chunks
from core.models import DecisionsResponse

@pytest.mark.asyncio
async def test_consolidated_call_counts():
    """Verify that we only make one embedding call and one analysis call per LLM."""
    
    # Dummy chunks
    chunks = [
        {"source_id": "1", "content": "Apple releases new iPhone."},
        {"source_id": "2", "content": "Fed raises interest rates."},
        {"source_id": "3", "content": "Nvidia stock hits record high."},
    ]

    # Mock Gemini Client for embeddings and LLM
    mock_gemini_client = MagicMock()
    # Mock embedding response
    mock_embedding = MagicMock()
    mock_embedding.values = [0.1] * 768
    mock_gemini_client.models.embed_content.return_value.embeddings = [mock_embedding] * len(chunks)
    
    # Mock LLM response (DecisionsResponse is the response_model)
    mock_response = DecisionsResponse(decisions=[])
    
    # Patch all provider clients and their underlying SDK classes
    with patch("core.llm.clients.AsyncOpenAI"), \
         patch("core.llm.clients.AsyncAnthropic"), \
         patch("google.genai.Client", return_value=mock_gemini_client), \
         patch("instructor.from_openai") as mock_openai, \
         patch("instructor.from_anthropic") as mock_anthropic, \
         patch("instructor.from_genai") as mock_from_genai, \
         patch("memory.store.get_supabase_client") as mock_sb, \
         patch("analyze.Portfolio") as mock_portfolio_class, \
         patch("analyze.MarketDataManager") as mock_market_data_class:

        # Set up Instructor mocks to return the same mock response
        # The create() method needs to be an AsyncMock since it's awaited
        from unittest.mock import AsyncMock
        
        # Mock the instructor-wrapped clients
        mock_wrapped_openai = MagicMock()
        mock_wrapped_anthropic = MagicMock()
        mock_wrapped_gemini = MagicMock()
        
        # Mock the underlying raw clients (accessed via .client in the tool loop)
        mock_raw_openai = MagicMock()
        mock_raw_openai.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(tool_calls=None, model_dump=lambda: {"role": "assistant", "content": "done"}))]
        ))
        
        mock_raw_anthropic = MagicMock()
        mock_raw_anthropic.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(type="text", text="done")]
        ))
        
        # Set up the instructor clients to have the raw clients
        mock_wrapped_openai.client = mock_raw_openai
        mock_wrapped_openai.chat.completions.create = AsyncMock(return_value=mock_response)
        
        mock_wrapped_anthropic.client = mock_raw_anthropic
        mock_wrapped_anthropic.chat.completions.create = AsyncMock(return_value=mock_response)
        
        mock_wrapped_gemini.chat.completions.create = AsyncMock(return_value=mock_response)
        
        # Return the instructor clients from the from_* functions
        mock_openai.return_value = mock_wrapped_openai
        mock_anthropic.return_value = mock_wrapped_anthropic
        mock_from_genai.return_value = mock_wrapped_gemini
        
        # Mock Supabase RPC call
        mock_sb.return_value.rpc.return_value.execute.return_value.data = []
        
        # Mock Portfolio and MarketDataManager
        from unittest.mock import AsyncMock
        mock_portfolio = MagicMock()
        mock_portfolio.positions = {}
        mock_portfolio.initialize = AsyncMock(return_value=None)
        mock_portfolio.calculate_reg_t_metrics = MagicMock()
        mock_portfolio.save_metrics = AsyncMock(return_value=None)
        mock_portfolio.get_portfolio_summary = AsyncMock(return_value="Portfolio: $10,000 cash")
        mock_portfolio_class.return_value = mock_portfolio
        
        mock_market_data = MagicMock()
        mock_market_data.get_quote = AsyncMock(return_value=None)
        mock_market_data_class.return_value = mock_market_data

        # Run analysis
        await analyze_chunks(chunks)

        # ASSERTIONS
        
        # 1. Gemini Embedding Call: Should be called exactly ONCE for all 3 chunks
        assert mock_gemini_client.models.embed_content.call_count == 1
        call_args = mock_gemini_client.models.embed_content.call_args
        assert len(call_args.kwargs['contents']) == 3
        
        # 2. LLM Analysis Calls: Should be called exactly ONCE per provider (4 in total)
        # OpenAI provider (OpenAI and DeepSeek use the same SDK factory here)
        assert mock_wrapped_openai.chat.completions.create.call_count == 2 # 1 for OpenAI, 1 for DeepSeek
        
        # Anthropic provider
        assert mock_wrapped_anthropic.chat.completions.create.call_count == 1
        
        # Gemini provider
        assert mock_wrapped_gemini.chat.completions.create.call_count == 1
        
        print("\nVerification Passed: 1 embedding call and 4 analysis calls made.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_consolidated_call_counts())
