"""Tests for MiniMax LLM client."""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from core.config import MINIMAX_MODEL


class TestMiniMaxClient:
    """Tests for MiniMaxClient class."""

    def test_client_initialization(self):
        """Test that MiniMaxClient initializes correctly."""
        from core.llm.minimax import MiniMaxClient

        client = MiniMaxClient(api_key="test-key-123")
        assert client.api_key == "test-key-123"
        assert client.BASE_URL == "https://api.minimax.io/v1/text/chatcompletion_v2"
        assert client.TIMEOUT == 120.0

    def test_client_requires_api_key(self):
        """Test that MiniMaxClient raises ValueError without API key."""
        from core.llm import minimax

        with patch.object(minimax, "config", MagicMock()):
            minimax.config.MINIMAX_API_KEY = None
            with pytest.raises(ValueError, match="MINIMAX_API_KEY is required"):
                minimax.MiniMaxClient()


class TestMiniMaxChatParsing:
    """Tests for parsing MiniMax chat responses."""

    @pytest.mark.asyncio
    async def test_chat_with_json_response_parses_correctly(self):
        """Test that JSON responses are parsed correctly."""
        from core.llm.minimax import MiniMaxClient

        mock_response_data = {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": '{"sentiment_label": "Cautiously Optimistic", "confidence_score": 75}',
                        "role": "assistant",
                    },
                }
            ],
            "model": MINIMAX_MODEL,
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        }

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        with patch.object(MiniMaxClient, "_get_client", return_value=mock_client):
            client = MiniMaxClient(api_key="test-key")
            result = await client.chat_with_json_response(
                messages=[{"role": "user", "content": "test"}], temperature=0.4
            )

            assert result["sentiment_label"] == "Cautiously Optimistic"
            assert result["confidence_score"] == 75

    @pytest.mark.asyncio
    async def test_chat_with_json_response_strips_markdown(self):
        """Test that markdown code blocks are stripped before parsing."""
        from core.llm.minimax import MiniMaxClient

        mock_response_data = {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": '```json\n{"sentiment_label": "Risk-Off", "confidence_score": 85}\n```',
                        "role": "assistant",
                    },
                }
            ],
            "model": MINIMAX_MODEL,
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        with patch.object(MiniMaxClient, "_get_client", return_value=mock_client):
            client = MiniMaxClient(api_key="test-key")
            result = await client.chat_with_json_response(messages=[{"role": "user", "content": "test"}])

            assert result["sentiment_label"] == "Risk-Off"

    @pytest.mark.asyncio
    async def test_chat_with_json_response_raises_on_invalid_json(self):
        """Test that invalid JSON raises ValueError."""
        from core.llm.minimax import MiniMaxClient

        mock_response_data = {
            "choices": [{"message": {"content": "This is not JSON at all", "role": "assistant"}}],
            "model": MINIMAX_MODEL,
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        with patch.object(MiniMaxClient, "_get_client", return_value=mock_client):
            client = MiniMaxClient(api_key="test-key")
            with pytest.raises(ValueError, match="Invalid JSON response"):
                await client.chat_with_json_response(messages=[{"role": "user", "content": "test"}])

    @pytest.mark.asyncio
    async def test_chat_returns_processing_time(self):
        """Test that chat returns processing time in milliseconds."""
        from core.llm.minimax import MiniMaxClient

        mock_response_data = {
            "choices": [{"finish_reason": "stop", "message": {"content": "Hello", "role": "assistant"}}],
            "model": MINIMAX_MODEL,
            "usage": {"prompt_tokens": 50, "completion_tokens": 10},
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        with patch.object(MiniMaxClient, "_get_client", return_value=mock_client):
            client = MiniMaxClient(api_key="test-key")
            result = await client.chat(messages=[{"role": "user", "content": "test"}])

            assert "processing_time_ms" in result
            assert result["processing_time_ms"] >= 0


class TestMiniMaxContextManager:
    """Tests for MiniMax async context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_close(self):
        """Test that context manager properly closes client."""
        from core.llm.minimax import MiniMaxClient

        mock_http_client = MagicMock()
        mock_http_client.is_closed = False
        mock_http_client.aclose = AsyncMock()

        client = MiniMaxClient(api_key="test-key")
        client._client = mock_http_client

        await client.close()

        mock_http_client.aclose.assert_called_once()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_context_manager_with_statement(self):
        """Test that async with statement works correctly."""
        from core.llm.minimax import MiniMaxClient

        with patch.object(MiniMaxClient, "close", new=AsyncMock()) as mock_close:
            async with MiniMaxClient(api_key="test-key") as client:
                assert client.api_key == "test-key"

            mock_close.assert_called_once()
