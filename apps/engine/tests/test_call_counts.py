from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import memory.embeddings
from analysis.analyze import analyze_chunks
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

    mock_response = DecisionsResponse(decisions=[])

    with (
        patch("core.config.GEMINI_API_KEY", "fake-key"),
        patch("core.llm.clients.AsyncOpenAI"),
        patch("core.llm.clients.AsyncAnthropic"),
        patch("google.genai.Client"),
        patch("instructor.from_openai") as mock_openai,
        patch("instructor.from_anthropic") as mock_anthropic,
        patch("instructor.from_genai") as mock_from_genai,
        patch("memory.store.get_supabase_client") as mock_sb,
        patch("analysis.analyze.Portfolio") as mock_portfolio_class,
        patch("analysis.analyze.MarketDataManager") as mock_market_data_class,
        patch("analysis.analyze.get_supabase_client") as mock_analyze_sb,
        patch("autoresearch.prompt_store.get_active_prompt", AsyncMock(return_value="FAKE_PROMPT")),
    ):
        memory.embeddings._client = None

        mock_wrapped_openai = MagicMock()
        mock_wrapped_anthropic = MagicMock()
        mock_wrapped_gemini = MagicMock()

        mock_raw_openai = MagicMock()
        mock_raw_openai.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[
                    MagicMock(
                        message=MagicMock(tool_calls=None, model_dump=lambda: {"role": "assistant", "content": "done"})
                    )
                ]
            )
        )

        mock_raw_anthropic = MagicMock()
        mock_raw_anthropic.messages.create = AsyncMock(
            return_value=MagicMock(content=[MagicMock(type="text", text="done")])
        )

        mock_wrapped_openai.client = mock_raw_openai
        mock_wrapped_openai.chat.completions.create = AsyncMock(return_value=mock_response)

        mock_wrapped_anthropic.client = mock_raw_anthropic
        mock_wrapped_anthropic.chat.completions.create = AsyncMock(return_value=mock_response)

        mock_wrapped_gemini.chat.completions.create = AsyncMock(return_value=mock_response)

        mock_openai.return_value = mock_wrapped_openai
        mock_anthropic.return_value = mock_wrapped_anthropic
        mock_from_genai.return_value = mock_wrapped_gemini

        mock_chain = MagicMock()
        mock_execute = MagicMock()
        mock_execute.data = []
        mock_chain.execute.return_value = mock_execute
        mock_chain.limit.return_value = mock_chain
        mock_chain.order.return_value = mock_chain
        mock_chain.gte.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.select.return_value = mock_chain
        mock_chain.in_.return_value = mock_chain
        mock_chain.table.return_value = mock_chain
        mock_sb.return_value = mock_chain
        mock_analyze_sb.return_value = mock_chain
        mock_sb.return_value.rpc.return_value.execute.return_value.data = []

        mock_portfolio = MagicMock()
        mock_portfolio.positions = {}
        mock_portfolio.initialize = AsyncMock(return_value=None)
        mock_portfolio.calculate_reg_t_metrics = MagicMock()
        mock_portfolio.save_metrics = AsyncMock(return_value=None)
        mock_portfolio.get_portfolio_summary = AsyncMock(return_value="Portfolio: $10,000 cash")
        mock_portfolio_class.return_value = mock_portfolio

        mock_market_data = MagicMock()
        mock_market_data.get_quote = AsyncMock(return_value=None)
        mock_market_data.get_quotes = AsyncMock(return_value={})
        mock_market_data.get_history = AsyncMock(return_value=[])
        mock_market_data_class.return_value = mock_market_data

        await analyze_chunks(chunks)

        # OpenAI SDK: openai + deepseek only (minimax moved to Anthropic SDK) - 2 passes per model + 1 newsletter summary call
        assert mock_wrapped_openai.chat.completions.create.call_count == 5


        # Anthropic SDK: anthropic + minimax (minimax uses Anthropic-compatible endpoint) - 2 passes per model
        assert mock_wrapped_anthropic.chat.completions.create.call_count == 4

        assert mock_wrapped_gemini.chat.completions.create.call_count == 2



if __name__ == "__main__":
    import asyncio

    asyncio.run(test_consolidated_call_counts())
