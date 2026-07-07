from unittest.mock import MagicMock, patch

import pytest

from core.llm.analysis import _extract_tickers_from_chunks
from core.llm.events import synthesize_event


@pytest.mark.asyncio
async def test_gemini_synthesis_model_direct():
    """Test that event synthesis uses SynthesisResponse directly and closes correctly."""
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.name = "Test Event"
    mock_resp.summary = "Test Summary"
    mock_resp.future_date = "2026-07-08"
    mock_resp.future_date_note = None
    mock_resp.is_ongoing = False
    mock_resp.is_future_catalyst = True
    mock_resp.historical_parallel = None
    mock_resp.scenarios = []
    mock_resp.importance_score = 5

    # Mock completions.create
    # Under GENAI_TOOLS or direct wrapper, Instructor returns the object directly
    mock_client.chat.completions.create.return_value = mock_resp

    with (
        patch("core.llm.clients.get_gemini_client", return_value=mock_client),
        patch("core.llm.clients.close_client") as mock_close_client,
    ):
        result = await synthesize_event(
            event_name="FOMC July 8 Minutes Release",
            impact="BULLISH",
            reasonings=["Model A thinks dovish surprise"],
            scenarios=["Scenario A: Dovish -> Plan: Buy QQQ"],
        )

        assert result["name"] == "Test Event"
        assert result["summary"] == "Test Summary"
        assert result["future_date"] == "2026-07-08"

        # Verify chat.completions.create was called with response_model=SynthesisResponse directly
        call_args, call_kwargs = mock_client.chat.completions.create.call_args
        from pydantic import BaseModel

        response_model = call_kwargs.get("response_model")
        assert response_model is not None
        # Assert that it is a single subclass of BaseModel (not a list)
        assert issubclass(response_model, BaseModel)
        assert response_model.__name__ == "SynthesisResponse"

        # Verify clients.close_client was called with 'gemini'
        mock_close_client.assert_called_once()
        assert mock_close_client.call_args[0][1] == "gemini"


def test_ticker_false_positives_political():
    """Test that political names like TRUMP, BIDEN, HARRIS are filtered out."""
    chunks = [
        {
            "source_id": "chunk_1",
            "content": "$TRUMP and $BIDEN are discussing $HARRIS policies at the $FED meeting. We also check $CPI and $GDP and $US.",
        }
    ]
    portfolio_tickers = ["MSFT"]

    extracted = _extract_tickers_from_chunks(chunks, portfolio_tickers)

    # Portfolio tickers and indices should be included
    assert "MSFT" in extracted
    assert "SPY" in extracted

    # Political names and macro indicators should NOT be extracted
    assert "TRUMP" not in extracted
    assert "BIDEN" not in extracted
    assert "HARRIS" not in extracted
    assert "FED" not in extracted
    assert "CPI" not in extracted
    assert "GDP" not in extracted
    assert "US" not in extracted
