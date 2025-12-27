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
    
    # Patch all provider clients
    with patch("google.genai.Client", return_value=mock_gemini_client), \
         patch("instructor.from_openai") as mock_openai, \
         patch("instructor.from_anthropic") as mock_anthropic, \
         patch("instructor.from_genai") as mock_instructor_gemini, \
         patch("memory.store.get_supabase_client") as mock_sb:

        # Set up Instructor mocks to return the same mock response
        mock_openai.return_value.chat.completions.create.return_value = mock_response
        mock_anthropic.return_value.chat.completions.create.return_value = mock_response
        mock_instructor_gemini.return_value.chat.completions.create.return_value = mock_response
        
        # Mock Supabase RPC call
        mock_sb.return_value.rpc.return_value.execute.return_value.data = []

        # Run analysis
        await analyze_chunks(chunks)

        # ASSERTIONS
        
        # 1. Gemini Embedding Call: Should be called exactly ONCE for all 3 chunks
        assert mock_gemini_client.models.embed_content.call_count == 1
        call_args = mock_gemini_client.models.embed_content.call_args
        assert len(call_args.kwargs['contents']) == 3
        
        # 2. LLM Analysis Calls: Should be called exactly ONCE per provider (4 in total)
        # OpenAI provider (OpenAI and DeepSeek use the same SDK factory here)
        assert mock_openai.return_value.chat.completions.create.call_count == 2 # 1 for OpenAI, 1 for DeepSeek
        
        # Anthropic provider
        assert mock_anthropic.return_value.chat.completions.create.call_count == 1
        
        # Gemini provider
        assert mock_instructor_gemini.return_value.chat.completions.create.call_count == 1
        
        print("\nVerification Passed: 1 embedding call and 4 analysis calls made.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_consolidated_call_counts())
